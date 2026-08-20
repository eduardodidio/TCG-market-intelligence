"""Daily price snapshot collector -- extracts current prices from
JSON-LD on MYP product pages for collection cards."""

from __future__ import annotations

import asyncio
from datetime import date, datetime

import structlog

from src.database.repository import Repository
from src.domain.models import CollectionError, HistoricalPrice, SnapshotSummary
from src.providers.myp.provider import MypCardsProvider, MypConfig

log = structlog.get_logger()


async def run_snapshot_prices(
    db_url: str = "sqlite:///tcg_market.db",
    limit: int | None = None,
    dry_run: bool = False,
    delay: float = 1.0,
    concurrency: int = 3,
) -> SnapshotSummary:
    """Fetch current JSON-LD prices for linked collection cards.

    Args:
        db_url: Database connection string.
        limit: Maximum number of cards to process.
        dry_run: If True, don't write to database.
        delay: Seconds between requests.
        concurrency: Max concurrent requests.
    """
    config = MypConfig(delay_seconds=delay)
    provider = MypCardsProvider(config)
    repo = Repository(db_url)
    summary = SnapshotSummary()
    today = date.today()

    try:
        # Load linked collection entries with their source_card info
        entries = repo.get_linked_collection_with_source(source="myp")
        summary.total_entries = len(entries)
        log.info("snapshot_start", total_entries=summary.total_entries)

        if limit is not None:
            entries = entries[:limit]
            log.info("limit_applied", processing=len(entries))

        sem = asyncio.Semaphore(concurrency)
        lock = asyncio.Lock()

        async def process_entry(entry: dict, index: int) -> None:
            async with sem:
                external_id = entry["external_id"]
                slug = entry["slug"]

                # Idempotency check
                if not dry_run and repo.has_snapshot_for_date(external_id, today):
                    async with lock:
                        summary.skipped_existing += 1
                    log.debug(
                        "snapshot_skip_existing",
                        external_id=external_id,
                    )
                    return

                try:
                    jsonld_price = await provider.fetch_current_price(external_id, slug)
                except Exception as e:
                    async with lock:
                        summary.errors += 1
                        summary.error_details.append(
                            CollectionError(
                                source="jsonld_snapshot",
                                external_id=external_id,
                                url=f"https://mypcards.com/magic/produto/{external_id}/{slug}",
                                error_type=type(e).__name__,
                                error_message=str(e),
                            )
                        )
                    log.warning(
                        "snapshot_fetch_error",
                        external_id=external_id,
                        error=str(e),
                    )
                    return

                if jsonld_price is None or jsonld_price.price is None:
                    async with lock:
                        summary.skipped_zero_price += 1
                    log.debug(
                        "snapshot_skip_no_price",
                        external_id=external_id,
                    )
                    return

                async with lock:
                    summary.fetched += 1

                observation = HistoricalPrice(
                    source="jsonld_snapshot",
                    external_id=external_id,
                    observed_at=today,
                    median_price=jsonld_price.price,
                    tcg_price=None,
                    currency=jsonld_price.currency,
                )

                if not dry_run:
                    inserted = repo.insert_price_observations([observation])
                    async with lock:
                        summary.stored += inserted
                else:
                    async with lock:
                        summary.stored += 1

                log.info(
                    "snapshot_stored",
                    index=index,
                    external_id=external_id,
                    price=str(jsonld_price.price),
                    dry_run=dry_run,
                )

        tasks = [process_entry(entry, i) for i, entry in enumerate(entries, 1)]
        await asyncio.gather(*tasks)

        summary.finished_at = datetime.now()
        _log_summary(summary)
        return summary

    finally:
        await provider.close()


def _log_summary(summary: SnapshotSummary) -> None:
    elapsed = None
    if summary.finished_at:
        elapsed = (summary.finished_at - summary.started_at).total_seconds()
    log.info(
        "snapshot_summary",
        total_entries=summary.total_entries,
        fetched=summary.fetched,
        stored=summary.stored,
        skipped_existing=summary.skipped_existing,
        skipped_zero_price=summary.skipped_zero_price,
        errors=summary.errors,
        elapsed_seconds=elapsed,
    )
