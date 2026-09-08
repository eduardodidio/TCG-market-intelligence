"""Scan completion hook registry for event-driven cache invalidation."""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING

import structlog

from src.domain.models import ScanRun

if TYPE_CHECKING:
    from src.services.market_data import MarketDataService
    from src.services.trending import TrendingService

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.collectors.portfolio_snapshot import take_snapshot
from src.database.models import UserCollectionRow
from src.database.repository import Repository

log = structlog.get_logger()

# Type alias for hook functions
ScanHook = Callable[[ScanRun, list[str]], None]


class ScanHookRegistry:
    """Registry of callbacks invoked after a scan completes.

    Each hook receives the ScanRun and a list of external_ids that
    were processed.
    """

    def __init__(self) -> None:
        self._hooks: list[ScanHook] = []

    def register(self, hook: ScanHook) -> None:
        """Register a callback."""
        self._hooks.append(hook)

    def notify(self, scan_run: ScanRun, external_ids: list[str]) -> None:
        """Invoke all registered hooks. Errors are logged, not raised."""
        for hook in self._hooks:
            try:
                hook(scan_run, external_ids)
            except Exception:
                hook_name = getattr(hook, "__name__", repr(hook))
                log.exception("scan_hook_error", hook=hook_name)


# Module-level default registry (singleton pattern)
default_registry = ScanHookRegistry()


def make_cache_invalidation_hook(
    service: MarketDataService,
) -> ScanHook:
    """Create a hook that invalidates cached data for scanned cards."""

    def _hook(scan_run: ScanRun, external_ids: list[str]) -> None:
        if not external_ids:
            return
        # Resolve external_ids -> card_ids via the service's repo
        card_ids = service._repo.resolve_external_ids_to_card_ids(external_ids)
        if card_ids:
            service.invalidate_cards(card_ids)
            log.info(
                "cache_invalidated_after_scan",
                scan_id=scan_run.id,
                cards_invalidated=len(card_ids),
            )

    return _hook


def make_trending_invalidation_hook(
    trending_service: TrendingService,
) -> ScanHook:
    """Create a hook that invalidates trending cache after a scan completes."""

    def _hook(scan_run: ScanRun, external_ids: list[str]) -> None:
        if not external_ids:
            return
        trending_service.invalidate_cache()
        log.info(
            "trending_cache_invalidated_after_scan",
            scan_id=scan_run.id,
            scanned_cards=len(external_ids),
        )

    return _hook


def make_portfolio_snapshot_hook(db_url: str) -> ScanHook:
    """Create a hook that takes portfolio snapshots after a scan completes.

    Snapshots ALL active users (users with collection entries) since
    take_snapshot is idempotent (upserts by date) and lightweight.

    Usage:
        from src.services.scan_hooks import make_portfolio_snapshot_hook
        hook = make_portfolio_snapshot_hook(db_url)
        default_registry.register(hook)
    """

    def _hook(scan_run: ScanRun, external_ids: list[str]) -> None:
        if not external_ids:
            return

        repo = Repository(db_url)

        # Get all distinct user_ids that have collection entries
        with Session(repo.engine) as session:
            user_ids = session.execute(select(UserCollectionRow.user_id).distinct()).scalars().all()

        if not user_ids:
            return

        snapshots_taken = 0
        for user_id in user_ids:
            try:
                take_snapshot(user_id, repo)
                snapshots_taken += 1
            except Exception:
                log.exception(
                    "portfolio_snapshot_hook_user_error",
                    scan_id=scan_run.id,
                    user_id=user_id,
                )

        log.info(
            "portfolio_snapshots_after_scan",
            scan_id=scan_run.id,
            users_snapshotted=snapshots_taken,
            users_total=len(user_ids),
        )

    return _hook
