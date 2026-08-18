"""Backfill collector — discovers cards and collects all available history."""

from __future__ import annotations

import asyncio
from datetime import datetime

import structlog

from src.database.repository import Repository
from src.domain.models import CollectionError, CollectionSummary, SourceCard
from src.providers.myp.provider import MypCardsProvider, MypConfig

log = structlog.get_logger()


async def run_backfill(
    db_url: str = "sqlite:///tcg_market.db",
    set_filter: str | None = None,
    limit: int | None = None,
    dry_run: bool = False,
    delay: float = 1.0,
    history_days: int = 1095,
    concurrency: int = 3,
    resume: bool = True,
) -> CollectionSummary:
    """Run a full backfill collection.

    Args:
        db_url: Database connection string.
        set_filter: If set, only collect from this set slug.
        limit: Maximum number of cards to process.
        dry_run: If True, don't write to database.
        delay: Seconds between requests.
        history_days: How many days of history to fetch.
        concurrency: Max concurrent cards to process (default 3).
        resume: If True, skip cards that already have observations in DB.
    """
    config = MypConfig(delay_seconds=delay, history_days=history_days)
    provider = MypCardsProvider(config)
    repo = Repository(db_url) if not dry_run else None
    summary = CollectionSummary()

    try:
        # Phase 1: Discover cards
        log.info("phase_discover_start", set_filter=set_filter)
        if set_filter:
            discovered = await provider.discover_cards(set_id=set_filter)
        else:
            discovered = await provider.discover_cards()

        summary.cards_discovered = len(discovered)
        log.info("cards_discovered", count=summary.cards_discovered)

        if limit:
            discovered = discovered[:limit]
            log.info("limit_applied", processing=len(discovered))

        # Phase 1b: Resume — skip already-collected cards
        if resume and repo and not dry_run:
            collected_ids = {
                eid for eid, _ in repo.get_cards_with_observations(provider.source_name)
            }
            before = len(discovered)
            discovered = [c for c in discovered if c.external_id not in collected_ids]
            skipped = before - len(discovered)
            if skipped > 0:
                log.info("resume_filtered", skipped=skipped, remaining=len(discovered))

        # Phase 2: Process cards concurrently
        total = len(discovered)
        sem = asyncio.Semaphore(concurrency)
        lock = asyncio.Lock()

        async def process_with_sem(card: SourceCard, index: int) -> None:
            async with sem:
                log.info(
                    "processing_card",
                    index=index,
                    total=total,
                    external_id=card.external_id,
                )
                try:
                    await _process_card(provider, repo, card, summary, history_days, dry_run)
                    async with lock:
                        summary.cards_processed += 1
                except Exception as e:
                    async with lock:
                        summary.cards_failed += 1
                        error = CollectionError(
                            source=provider.source_name,
                            external_id=card.external_id,
                            url=card.url,
                            error_type=type(e).__name__,
                            error_message=str(e),
                        )
                        summary.errors.append(error)
                        if repo:
                            repo.insert_error(error)
                    log.warning(
                        "card_failed",
                        external_id=card.external_id,
                        error=str(e),
                    )

        tasks = [process_with_sem(card, i) for i, card in enumerate(discovered, 1)]
        await asyncio.gather(*tasks)

        summary.finished_at = datetime.now()
        _log_summary(summary)
        return summary

    finally:
        await provider.close()


async def _process_card(
    provider: MypCardsProvider,
    repo: Repository | None,
    card: SourceCard,
    summary: CollectionSummary,
    history_days: int,
    dry_run: bool,
) -> None:
    """Process a single card: fetch details + history, persist."""
    # Get card details
    detailed = await provider.get_card_details(card)
    if not detailed:
        raise ValueError(f"Could not parse card page: {card.url}")

    if not dry_run and repo:
        repo.upsert_source_card(detailed)
        repo.upsert_card(detailed)

    # Get price history
    history = await provider.get_price_history(card, days=history_days)

    if dry_run:
        log.info(
            "dry_run_card",
            name=detailed.identity.name_en if detailed.identity else "?",
            sku=detailed.sku,
            history_points=len(history),
        )
        summary.observations_saved += len(history)
    elif repo:
        inserted = repo.insert_price_observations(history)
        summary.observations_saved += inserted
        log.info(
            "card_saved",
            name=detailed.identity.name_en if detailed.identity else "?",
            sku=detailed.sku,
            history_points=len(history),
            new_observations=inserted,
        )

    # Mark any previous errors as resolved
    if not dry_run and repo:
        repo.mark_errors_resolved(provider.source_name, card.external_id)


async def run_update(
    db_url: str = "sqlite:///tcg_market.db",
    delay: float = 1.0,
    history_days: int = 30,
) -> CollectionSummary:
    """Incremental update — fetch recent data for known cards only."""
    config = MypConfig(delay_seconds=delay, history_days=history_days)
    provider = MypCardsProvider(config)
    repo = Repository(db_url)
    summary = CollectionSummary()

    try:
        source_cards = repo.get_all_source_cards(provider.source_name)
        summary.cards_discovered = len(source_cards)
        log.info("update_start", known_cards=len(source_cards))

        for i, sc_row in enumerate(source_cards, 1):
            card = SourceCard(
                source=provider.source_name,
                external_id=sc_row.external_id,
                url=sc_row.url,
                sku=sc_row.sku,
            )
            log.info(
                "updating_card",
                index=i,
                total=len(source_cards),
                external_id=card.external_id,
            )
            try:
                history = await provider.get_price_history(card, days=history_days)
                inserted = repo.insert_price_observations(history)
                summary.observations_saved += inserted
                summary.cards_processed += 1
            except Exception as e:
                summary.cards_failed += 1
                error = CollectionError(
                    source=provider.source_name,
                    external_id=card.external_id,
                    url=card.url,
                    error_type=type(e).__name__,
                    error_message=str(e),
                )
                summary.errors.append(error)
                repo.insert_error(error)
                log.warning("update_card_failed", external_id=card.external_id, error=str(e))

        summary.finished_at = datetime.now()
        _log_summary(summary)
        return summary

    finally:
        await provider.close()


async def run_retry_failed(
    db_url: str = "sqlite:///tcg_market.db",
    delay: float = 2.0,
    history_days: int = 1095,
) -> CollectionSummary:
    """Retry previously failed cards."""
    config = MypConfig(delay_seconds=delay, history_days=history_days)
    provider = MypCardsProvider(config)
    repo = Repository(db_url)
    summary = CollectionSummary()

    try:
        errors = repo.get_unresolved_errors(provider.source_name)
        # Deduplicate by external_id
        seen: set[str] = set()
        cards_to_retry: list[SourceCard] = []
        for err in errors:
            if err.external_id and err.external_id not in seen:
                seen.add(err.external_id)
                cards_to_retry.append(
                    SourceCard(
                        source=provider.source_name,
                        external_id=err.external_id,
                        url=err.url,
                    )
                )

        summary.cards_discovered = len(cards_to_retry)
        log.info("retry_start", failed_cards=len(cards_to_retry))

        for i, card in enumerate(cards_to_retry, 1):
            log.info(
                "retrying_card",
                index=i,
                total=len(cards_to_retry),
                external_id=card.external_id,
            )
            try:
                await _process_card(provider, repo, card, summary, history_days, False)
                summary.cards_processed += 1
            except Exception as e:
                summary.cards_failed += 1
                error = CollectionError(
                    source=provider.source_name,
                    external_id=card.external_id,
                    url=card.url,
                    error_type=type(e).__name__,
                    error_message=str(e),
                    attempt=2,
                )
                summary.errors.append(error)
                repo.insert_error(error)
                log.warning("retry_failed", external_id=card.external_id, error=str(e))

        summary.finished_at = datetime.now()
        _log_summary(summary)
        return summary

    finally:
        await provider.close()


def _log_summary(summary: CollectionSummary) -> None:
    elapsed = None
    if summary.finished_at:
        elapsed = (summary.finished_at - summary.started_at).total_seconds()

    log.info(
        "collection_summary",
        cards_discovered=summary.cards_discovered,
        cards_processed=summary.cards_processed,
        cards_failed=summary.cards_failed,
        observations_saved=summary.observations_saved,
        elapsed_seconds=elapsed,
    )
