"""Tests for ScanHookRegistry and cache invalidation hook (F44-T04)."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from src.domain.models import ScanRun
from src.services.scan_hooks import (
    ScanHookRegistry,
    make_cache_invalidation_hook,
)


@pytest.fixture()
def registry():
    return ScanHookRegistry()


@pytest.fixture()
def scan_run():
    return ScanRun(id=1, scan_type="collection", status="completed")


class TestScanHookRegistry:
    def test_register_and_notify_calls_hook(self, registry, scan_run):
        hook = MagicMock()
        registry.register(hook)
        registry.notify(scan_run, ["ext1", "ext2"])
        hook.assert_called_once_with(scan_run, ["ext1", "ext2"])

    def test_notify_with_multiple_hooks(self, registry, scan_run):
        hook1 = MagicMock()
        hook2 = MagicMock()
        registry.register(hook1)
        registry.register(hook2)
        registry.notify(scan_run, ["ext1"])
        hook1.assert_called_once()
        hook2.assert_called_once()

    def test_hook_error_is_logged_not_raised(self, registry, scan_run):
        bad_hook = MagicMock(side_effect=ValueError("boom"))
        good_hook = MagicMock()
        registry.register(bad_hook)
        registry.register(good_hook)

        # Should not raise
        registry.notify(scan_run, ["ext1"])

        # Good hook should still be called
        good_hook.assert_called_once()

    def test_notify_with_no_hooks_is_noop(self, registry, scan_run):
        # Should not raise
        registry.notify(scan_run, ["ext1"])

    def test_notify_with_empty_external_ids(self, registry, scan_run):
        hook = MagicMock()
        registry.register(hook)
        registry.notify(scan_run, [])
        hook.assert_called_once_with(scan_run, [])


class TestMakeCacheInvalidationHook:
    def test_calls_invalidate(self, scan_run):
        mock_service = MagicMock()
        mock_service._repo.resolve_external_ids_to_card_ids.return_value = [1, 2]

        hook = make_cache_invalidation_hook(mock_service)
        hook(scan_run, ["ext1", "ext2"])

        mock_service._repo.resolve_external_ids_to_card_ids.assert_called_once_with(
            ["ext1", "ext2"]
        )
        mock_service.invalidate_cards.assert_called_once_with([1, 2])

    def test_with_empty_external_ids(self, scan_run):
        mock_service = MagicMock()

        hook = make_cache_invalidation_hook(mock_service)
        hook(scan_run, [])

        mock_service._repo.resolve_external_ids_to_card_ids.assert_not_called()
        mock_service.invalidate_cards.assert_not_called()

    def test_with_no_resolved_card_ids(self, scan_run):
        mock_service = MagicMock()
        mock_service._repo.resolve_external_ids_to_card_ids.return_value = []

        hook = make_cache_invalidation_hook(mock_service)
        hook(scan_run, ["unknown"])

        mock_service.invalidate_cards.assert_not_called()
