"""Admin daily scan orchestrator.

Collects all admin users' collection entries (deduplicated by card_id)
and runs a single MYP sweep. Used by the scheduler for the
``admin_daily_myp`` scan type. No credit deduction -- this is a
system-level job.

Note: Previously used Liga Magic; now delegates to MYP sweep.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime

import structlog

from src.collectors.myp_sweep import run_myp_sweep
from src.database.repository import Repository
from src.domain.models import ScanRun

log = structlog.get_logger()


async def run_admin_daily_scan(
    db_url: str,
    run_id: int | None = None,
    max_age_days: int = 1,
    on_complete: Callable | None = None,
) -> ScanRun:
    """Run an MYP sweep for all admin users' collections.

    Gathers collection entries from every admin user, deduplicates by
    ``card_id``, and delegates to :func:`run_myp_sweep`.

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
        log.info("admin_daily_scan_no_admins")
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
            scan_type="admin_daily_myp",
            status="completed",
            cards_total=0,
            cards_processed=0,
        )

    log.info(
        "admin_daily_scan_start",
        admin_count=len(admin_ids),
        max_age_days=max_age_days,
    )

    result = await run_myp_sweep(
        db_url=db_url,
        max_age_days=max_age_days,
        on_complete=on_complete,
    )

    return ScanRun(
        id=run_id,
        scan_type="admin_daily_myp",
        status="completed",
        cards_total=result.total_eligible,
        cards_processed=result.total_processed,
    )


# Keep old name as alias for backward compatibility
run_admin_daily_liga_scan = run_admin_daily_scan
