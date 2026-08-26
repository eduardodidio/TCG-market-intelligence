"""Admin daily Liga scan orchestrator.

Collects all admin users' collection entries (deduplicated by card_id)
and runs a single Liga scan. Used by the scheduler for the
``admin_daily_liga`` scan type. No credit deduction — this is a
system-level job.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime

import structlog

from src.collectors.liga_scan import run_liga_scan
from src.database.repository import Repository
from src.domain.models import ScanFilter, ScanRun

log = structlog.get_logger()


async def run_admin_daily_liga_scan(
    db_url: str,
    run_id: int | None = None,
    max_age_days: int = 1,
    on_complete: Callable | None = None,
) -> ScanRun:
    """Run a Liga scan for all admin users' collections.

    Gathers collection entries from every admin user, deduplicates by
    ``card_id``, and delegates to :func:`run_liga_scan`.

    Args:
        db_url: Database connection string.
        run_id: Pre-created scan run ID (from scheduler).
        max_age_days: Skip cards scanned within this many days (default 1).
        on_complete: Hook called after scan finishes.

    Returns:
        The completed :class:`ScanRun`.
    """
    repo = Repository(db_url)
    admin_ids = repo.get_admin_user_ids()

    if not admin_ids:
        log.info("admin_daily_liga_no_admins")
        # Return a completed scan with 0 cards
        if run_id is not None:
            repo.update_scan_run(
                run_id,
                status="completed",
                cards_total=0,
                cards_processed=0,
                started_at=datetime.now(),
                finished_at=datetime.now(),
            )
        return ScanRun(
            id=run_id,
            scan_type="admin_daily_liga",
            status="completed",
            cards_total=0,
            cards_processed=0,
        )

    # Collect all card_ids from admin users, deduplicated
    all_card_ids: set[int] = set()
    for uid in admin_ids:
        entries = repo.get_cards_for_liga_scan(
            ScanFilter(), user_id=str(uid), max_age_days=max_age_days
        )
        all_card_ids.update(e["card_id"] for e in entries if e.get("card_id"))

    if not all_card_ids:
        log.info("admin_daily_liga_all_fresh", admin_count=len(admin_ids))
        if run_id is not None:
            repo.update_scan_run(
                run_id,
                status="completed",
                cards_total=0,
                cards_processed=0,
                started_at=datetime.now(),
                finished_at=datetime.now(),
            )
        return ScanRun(
            id=run_id,
            scan_type="admin_daily_liga",
            status="completed",
            cards_total=0,
            cards_processed=0,
        )

    log.info(
        "admin_daily_liga_start",
        admin_count=len(admin_ids),
        card_count=len(all_card_ids),
        max_age_days=max_age_days,
    )

    scan_filter = ScanFilter(card_ids=list(all_card_ids))
    return await run_liga_scan(
        db_url=db_url,
        scan_filter=scan_filter,
        run_id=run_id,
        max_age_days=max_age_days,
        on_complete=on_complete,
    )
