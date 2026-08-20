"""Collection sync orchestrator — searches, matches, fetches, and stores
price data for every card in the user collection."""

from __future__ import annotations

import asyncio
from datetime import datetime

import structlog

from src.collection.matcher import CollectionEntry, match_collection_card
from src.database.models import UserCollectionRow
from src.database.repository import Repository
from src.domain.models import SourceCard, SyncError, SyncResult, SyncSummary
from src.providers.myp.provider import MypCardsProvider, MypConfig

log = structlog.get_logger()

BASE_URL = "https://mypcards.com"


def _row_to_entry(row: UserCollectionRow) -> CollectionEntry:
    """Convert a DB row to a CollectionEntry for the matcher."""
    return CollectionEntry(
        set_code=row.set_code,
        collector_number=row.collector_number,
        name_en=row.name_en,
    )


async def run_sync_collection(
    db_url: str = "sqlite:///tcg_market.db",
    limit: int | None = None,
    dry_run: bool = False,
    delay: float = 1.0,
    history_days: int = 365,
    concurrency: int = 3,
    skip_matched: bool = True,
) -> SyncSummary:
    """Run collection sync: search -> match -> fetch -> store -> link.

    Args:
        db_url: Database connection string.
        limit: Maximum number of entries to process.
        dry_run: If True, don't write to database.
        delay: Seconds between requests.
        history_days: How many days of history to fetch.
        concurrency: Max concurrent cards to process (default 3).
        skip_matched: If True, skip entries where card_id is already set.
    """
    config = MypConfig(delay_seconds=delay, history_days=history_days)
    provider = MypCardsProvider(config)
    repo = Repository(db_url)
    summary = SyncSummary()

    try:
        all_entries = repo.get_all_collection_entries()
        summary.total_entries = len(all_entries)
        log.info("sync_collection_start", total_entries=summary.total_entries)

        # Filter out already-linked entries if skip_matched
        if skip_matched:
            entries_to_process = []
            for entry in all_entries:
                if entry.card_id is not None:
                    summary.skipped_already_linked += 1
                else:
                    entries_to_process.append(entry)
            if summary.skipped_already_linked > 0:
                log.info(
                    "skip_matched_filtered",
                    skipped=summary.skipped_already_linked,
                    remaining=len(entries_to_process),
                )
        else:
            entries_to_process = list(all_entries)

        # Apply limit
        if limit is not None:
            entries_to_process = entries_to_process[:limit]
            log.info("limit_applied", processing=len(entries_to_process))

        total = len(entries_to_process)
        sem = asyncio.Semaphore(concurrency)
        lock = asyncio.Lock()

        async def process_entry(row: UserCollectionRow, index: int) -> None:
            async with sem:
                entry = _row_to_entry(row)

                # Skip entries without name_en
                if not entry.name_en:
                    async with lock:
                        result = SyncResult(
                            entry_id=row.id,
                            name_en=entry.name_en,
                            set_code=entry.set_code,
                            collector_number=entry.collector_number,
                            status="no_name",
                        )
                        summary.results.append(result)
                    log.info(
                        "skipped_no_name",
                        index=index,
                        total=total,
                        set_code=entry.set_code,
                        collector_number=entry.collector_number,
                    )
                    return

                log.info(
                    "syncing_card",
                    index=index,
                    total=total,
                    name_en=entry.name_en,
                    set_code=entry.set_code,
                )

                try:
                    await _process_single_entry(
                        provider,
                        repo,
                        row,
                        entry,
                        summary,
                        lock,
                        history_days,
                        dry_run,
                    )
                except Exception as e:
                    async with lock:
                        sync_error = SyncError(
                            entry_id=row.id,
                            name_en=entry.name_en,
                            set_code=entry.set_code,
                            collector_number=entry.collector_number,
                            error_type=type(e).__name__,
                            error_message=str(e),
                        )
                        summary.errors.append(sync_error)
                        result = SyncResult(
                            entry_id=row.id,
                            name_en=entry.name_en,
                            set_code=entry.set_code,
                            collector_number=entry.collector_number,
                            status="error",
                            error_message=str(e),
                        )
                        summary.results.append(result)
                    log.warning(
                        "sync_card_failed",
                        name_en=entry.name_en,
                        set_code=entry.set_code,
                        error=str(e),
                    )

        tasks = [process_entry(row, i) for i, row in enumerate(entries_to_process, 1)]
        await asyncio.gather(*tasks)

        summary.finished_at = datetime.now()
        _log_summary(summary)
        return summary

    finally:
        await provider.close()


async def _process_single_entry(
    provider: MypCardsProvider,
    repo: Repository,
    row: UserCollectionRow,
    entry: CollectionEntry,
    summary: SyncSummary,
    lock: asyncio.Lock,
    history_days: int,
    dry_run: bool,
) -> None:
    """Process a single collection entry through the full sync pipeline."""
    # Step 1: Search MYP
    search_results = await provider.search_card(entry.name_en)

    async with lock:
        summary.searched += 1

    # Step 2: Match
    match_result = match_collection_card(entry, search_results)

    if match_result.status == "unmatched":
        async with lock:
            summary.unmatched += 1
            result = SyncResult(
                entry_id=row.id,
                name_en=entry.name_en,
                set_code=entry.set_code,
                collector_number=entry.collector_number,
                status="unmatched",
                match_confidence=match_result.confidence,
            )
            summary.results.append(result)
        log.info(
            "card_unmatched",
            name_en=entry.name_en,
            set_code=entry.set_code,
            candidates=len(search_results),
        )
        return

    if match_result.status == "ambiguous":
        async with lock:
            summary.ambiguous += 1
            result = SyncResult(
                entry_id=row.id,
                name_en=entry.name_en,
                set_code=entry.set_code,
                collector_number=entry.collector_number,
                status="ambiguous",
                match_confidence=match_result.confidence,
            )
            summary.results.append(result)
        log.info(
            "card_ambiguous",
            name_en=entry.name_en,
            set_code=entry.set_code,
            candidates=len(match_result.candidates),
        )
        return

    # Step 3: Matched — build a SourceCard from the search result
    myp_result = match_result.myp_result
    source_card = SourceCard(
        source="myp",
        external_id=myp_result.external_id,
        url=myp_result.url,
        sku=myp_result.sku,
    )

    # Step 3a: Fetch full card details from MYP card page
    detailed = await provider.get_card_details(source_card)
    if not detailed:
        raise ValueError(f"Could not parse card page: {source_card.url}")

    # Step 3b-c: Upsert card and source_card
    card_id = None
    if not dry_run:
        card_id = repo.upsert_card(detailed)
        repo.upsert_source_card(detailed, card_id=card_id)

    # Step 3d: Fetch price history
    history = await provider.get_price_history(source_card, days=history_days)

    # Step 3e: Store observations
    inserted = 0
    if not dry_run:
        inserted = repo.insert_price_observations(history)
    else:
        inserted = len(history)

    # Step 3f: Link collection entry
    if not dry_run and card_id is not None:
        repo.link_collection_entry(row.id, card_id)

    # Step 3g: Mark previous errors as resolved
    if not dry_run:
        repo.mark_errors_resolved("myp", source_card.external_id)

    async with lock:
        summary.matched += 1
        if card_id is not None:
            summary.cards_created += 1
        summary.observations_saved += inserted
        result = SyncResult(
            entry_id=row.id,
            name_en=entry.name_en,
            set_code=entry.set_code,
            collector_number=entry.collector_number,
            status="synced",
            card_id=card_id,
            observations_count=inserted,
            match_confidence=match_result.confidence,
        )
        summary.results.append(result)

    log.info(
        "card_synced",
        name_en=entry.name_en,
        set_code=entry.set_code,
        card_id=card_id,
        observations=inserted,
        confidence=match_result.confidence,
        dry_run=dry_run,
    )


def _log_summary(summary: SyncSummary) -> None:
    """Log the final sync summary."""
    elapsed = None
    if summary.finished_at:
        elapsed = (summary.finished_at - summary.started_at).total_seconds()

    log.info(
        "sync_collection_summary",
        total_entries=summary.total_entries,
        skipped_already_linked=summary.skipped_already_linked,
        searched=summary.searched,
        matched=summary.matched,
        ambiguous=summary.ambiguous,
        unmatched=summary.unmatched,
        cards_created=summary.cards_created,
        observations_saved=summary.observations_saved,
        error_count=len(summary.errors),
        elapsed_seconds=elapsed,
    )
