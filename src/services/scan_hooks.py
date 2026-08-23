"""Scan completion hook registry for event-driven cache invalidation."""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING

import structlog

from src.domain.models import ScanRun

if TYPE_CHECKING:
    from src.services.market_data import MarketDataService
    from src.services.trending import TrendingService

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
