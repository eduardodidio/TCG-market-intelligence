"""Liga scan orchestrator -- thin wrapper around run_scan() with
Liga-specific defaults (LigaMagicProvider, 5s delay, concurrency=1)."""

from __future__ import annotations

from collections.abc import Callable

import structlog

from src.collectors.scan import run_scan
from src.config import get_db_url
from src.domain.models import ScanFilter, ScanRun
from src.providers.liga.provider import LigaMagicProvider

log = structlog.get_logger()


async def run_liga_scan(
    db_url: str | None = None,
    scan_filter: ScanFilter | None = None,
    dry_run: bool = False,
    delay: float = 5.0,
    run_id: int | None = None,
    on_complete: Callable | None = None,
    max_age_days: int | None = None,
) -> ScanRun:
    """Run a collection price scan using the LigaMagic provider.

    This is a thin wrapper around :func:`run_scan` that:
    1. Creates and manages a :class:`LigaMagicProvider` instance.
    2. Passes ``provider_name="liga"`` so run_scan applies Liga-specific
       constraints (concurrency=1, minimum delay, LIGA_FULL/LIGA_PARTIAL
       scan types, Liga error handling).
    3. Ensures the provider browser is closed in a ``finally`` block.

    Args:
        db_url: Database connection string (defaults to :func:`get_db_url`).
        scan_filter: Filter criteria (defaults to full collection).
        dry_run: If True, create scan run but skip fetching.
        delay: Seconds between requests (default 5.0, enforced minimum by run_scan).
        run_id: Pre-created scan run ID (from API).
        on_complete: Hook called after scan finishes.
        max_age_days: If set, skip cards scanned within this many days.
    """
    effective_db_url = db_url if db_url is not None else get_db_url()

    provider = LigaMagicProvider()
    try:
        await provider.open()
        return await run_scan(
            db_url=effective_db_url,
            scan_filter=scan_filter,
            dry_run=dry_run,
            delay=delay,
            run_id=run_id,
            on_complete=on_complete,
            provider=provider,
            provider_name="liga",
            max_age_days=max_age_days,
        )
    finally:
        await provider.close()
