"""Collection scan orchestrator -- runs filtered price scans with
tracking via scan_runs table."""

from __future__ import annotations

import asyncio
import json
from datetime import date, datetime

import structlog

from src.database.repository import Repository
from src.domain.models import (
    HistoricalPrice,
    ScanFilter,
    ScanRun,
    ScanStatus,
)
from src.providers.myp.provider import MypCardsProvider, MypConfig

log = structlog.get_logger()


async def run_scan(
    db_url: str = "sqlite:///tcg_market.db",
    scan_filter: ScanFilter | None = None,
    dry_run: bool = False,
    delay: float = 1.0,
    concurrency: int = 3,
    run_id: int | None = None,
) -> ScanRun:
    """Run a collection price scan with optional filtering.

    Args:
        db_url: Database connection string.
        scan_filter: Filter criteria (defaults to full collection).
        dry_run: If True, create scan run and get cards but skip fetching.
        delay: Seconds between requests.
        concurrency: Max concurrent requests.
    """
    scan_filter = scan_filter or ScanFilter()
    config = MypConfig(delay_seconds=delay)
    provider = MypCardsProvider(config)
    repo = Repository(db_url)
    today = date.today()

    # 1. Create scan run row (or reuse pre-created one from API)
    if run_id is None:
        run_id = repo.create_scan_run(scan_filter.scan_type.value, scan_filter.to_json())
    repo.update_scan_run(run_id, status=ScanStatus.RUNNING.value, started_at=datetime.now())

    try:
        # 2. Get cards matching filter
        entries = repo.get_cards_for_scan(scan_filter)
        cards_total = len(entries)
        repo.update_scan_run(run_id, cards_total=cards_total)
        log.info("scan_start", run_id=run_id, cards_total=cards_total, dry_run=dry_run)

        if dry_run:
            repo.update_scan_run(
                run_id,
                status=ScanStatus.COMPLETED.value,
                cards_processed=0,
                finished_at=datetime.now(),
            )
            return _build_scan_run(repo, run_id)

        # 3. Process entries with concurrency control
        cards_processed = 0
        cards_failed = 0
        observations_saved = 0
        error_messages: list[str] = []
        sem = asyncio.Semaphore(concurrency)
        lock = asyncio.Lock()

        async def process_entry(entry: dict, index: int) -> None:
            nonlocal cards_processed, cards_failed, observations_saved

            async with sem:
                external_id = entry["external_id"]
                slug = entry["slug"]

                try:
                    jsonld_price = await provider.fetch_current_price(external_id, slug)
                except Exception as e:
                    async with lock:
                        cards_failed += 1
                        error_messages.append(f"{external_id}: {type(e).__name__}: {e}")
                    log.warning(
                        "scan_fetch_error",
                        run_id=run_id,
                        external_id=external_id,
                        error=str(e),
                    )
                    return

                if jsonld_price is None or jsonld_price.price is None:
                    async with lock:
                        cards_processed += 1
                    log.debug(
                        "scan_skip_no_price",
                        external_id=external_id,
                    )
                    return

                observation = HistoricalPrice(
                    source="jsonld_snapshot",
                    external_id=external_id,
                    observed_at=today,
                    median_price=jsonld_price.price,
                    tcg_price=None,
                    currency=jsonld_price.currency,
                )

                inserted = repo.insert_price_observations([observation])
                async with lock:
                    cards_processed += 1
                    observations_saved += inserted

                log.info(
                    "scan_stored",
                    run_id=run_id,
                    index=index,
                    external_id=external_id,
                    price=str(jsonld_price.price),
                )

        tasks = [process_entry(entry, i) for i, entry in enumerate(entries, 1)]
        await asyncio.gather(*tasks)

        # 4. Determine final status
        if cards_total == 0:
            status = ScanStatus.COMPLETED.value
        elif cards_failed > cards_total * 0.5:
            status = ScanStatus.FAILED.value
        else:
            status = ScanStatus.COMPLETED.value

        error_summary = json.dumps(error_messages) if error_messages else None

        repo.update_scan_run(
            run_id,
            status=status,
            cards_processed=cards_processed,
            cards_failed=cards_failed,
            observations_saved=observations_saved,
            error_summary=error_summary,
            finished_at=datetime.now(),
        )

        log.info(
            "scan_finished",
            run_id=run_id,
            status=status,
            cards_total=cards_total,
            cards_processed=cards_processed,
            cards_failed=cards_failed,
            observations_saved=observations_saved,
        )

        return _build_scan_run(repo, run_id)

    except Exception:
        repo.update_scan_run(
            run_id,
            status=ScanStatus.FAILED.value,
            finished_at=datetime.now(),
        )
        raise
    finally:
        await provider.close()


def _build_scan_run(repo: Repository, run_id: int) -> ScanRun:
    """Read the scan run row from DB and return a ScanRun domain object."""
    row = repo.get_scan_run(run_id)
    if row is None:
        raise ValueError(f"Scan run {run_id} not found")
    return ScanRun(
        id=row["id"],
        scan_type=row["scan_type"],
        filters_json=row["filters_json"],
        status=row["status"],
        cards_total=row["cards_total"],
        cards_processed=row["cards_processed"],
        cards_failed=row["cards_failed"],
        observations_saved=row["observations_saved"],
        error_summary=row["error_summary"],
        started_at=row["started_at"],
        finished_at=row["finished_at"],
    )
