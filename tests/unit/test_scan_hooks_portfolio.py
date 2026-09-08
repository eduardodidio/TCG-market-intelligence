"""Tests for portfolio snapshot scan hook (F112-T03)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from src.domain.models import ScanRun
from src.services.scan_hooks import ScanHookRegistry, make_portfolio_snapshot_hook


@pytest.fixture()
def scan_run():
    return ScanRun(id=42, scan_type="collection", status="completed")


@pytest.fixture()
def registry():
    return ScanHookRegistry()


class TestMakePortfolioSnapshotHook:
    """Test make_portfolio_snapshot_hook factory and behaviour."""

    @patch("src.services.scan_hooks.take_snapshot")
    @patch("src.services.scan_hooks.Session")
    @patch("src.services.scan_hooks.Repository")
    def test_snapshots_all_users_with_collection(
        self, mock_repo_cls, mock_session_cls, mock_take_snapshot, scan_run
    ):
        """Hook should call take_snapshot for every user with collection entries."""
        mock_repo = MagicMock()
        mock_repo_cls.return_value = mock_repo

        # Simulate two users with collection entries
        mock_session = MagicMock()
        mock_session_cls.return_value.__enter__ = MagicMock(return_value=mock_session)
        mock_session_cls.return_value.__exit__ = MagicMock(return_value=False)
        mock_session.execute.return_value.scalars.return_value.all.return_value = [
            "user-1",
            "user-2",
        ]

        hook = make_portfolio_snapshot_hook("sqlite:///test.db")
        hook(scan_run, ["ext1", "ext2"])

        assert mock_take_snapshot.call_count == 2
        mock_take_snapshot.assert_any_call("user-1", mock_repo)
        mock_take_snapshot.assert_any_call("user-2", mock_repo)

    @patch("src.services.scan_hooks.take_snapshot")
    @patch("src.services.scan_hooks.Session")
    @patch("src.services.scan_hooks.Repository")
    def test_skips_when_no_external_ids(
        self, mock_repo_cls, mock_session_cls, mock_take_snapshot, scan_run
    ):
        """Hook should be a no-op when external_ids is empty."""
        hook = make_portfolio_snapshot_hook("sqlite:///test.db")
        hook(scan_run, [])

        mock_repo_cls.assert_not_called()
        mock_take_snapshot.assert_not_called()

    @patch("src.services.scan_hooks.take_snapshot")
    @patch("src.services.scan_hooks.Session")
    @patch("src.services.scan_hooks.Repository")
    def test_skips_when_no_users(
        self, mock_repo_cls, mock_session_cls, mock_take_snapshot, scan_run
    ):
        """Hook should be a no-op when no users have collection entries."""
        mock_repo = MagicMock()
        mock_repo_cls.return_value = mock_repo

        mock_session = MagicMock()
        mock_session_cls.return_value.__enter__ = MagicMock(return_value=mock_session)
        mock_session_cls.return_value.__exit__ = MagicMock(return_value=False)
        mock_session.execute.return_value.scalars.return_value.all.return_value = []

        hook = make_portfolio_snapshot_hook("sqlite:///test.db")
        hook(scan_run, ["ext1"])

        mock_take_snapshot.assert_not_called()

    @patch("src.services.scan_hooks.take_snapshot")
    @patch("src.services.scan_hooks.Session")
    @patch("src.services.scan_hooks.Repository")
    def test_error_in_one_user_does_not_block_others(
        self, mock_repo_cls, mock_session_cls, mock_take_snapshot, scan_run
    ):
        """If take_snapshot fails for one user, it should continue with the rest."""
        mock_repo = MagicMock()
        mock_repo_cls.return_value = mock_repo

        mock_session = MagicMock()
        mock_session_cls.return_value.__enter__ = MagicMock(return_value=mock_session)
        mock_session_cls.return_value.__exit__ = MagicMock(return_value=False)
        mock_session.execute.return_value.scalars.return_value.all.return_value = [
            "user-fail",
            "user-ok",
        ]

        # First call raises, second succeeds
        mock_take_snapshot.side_effect = [RuntimeError("db error"), {"user_id": "user-ok"}]

        hook = make_portfolio_snapshot_hook("sqlite:///test.db")
        # Should NOT raise
        hook(scan_run, ["ext1"])

        assert mock_take_snapshot.call_count == 2
        mock_take_snapshot.assert_any_call("user-fail", mock_repo)
        mock_take_snapshot.assert_any_call("user-ok", mock_repo)

    @patch("src.services.scan_hooks.take_snapshot")
    @patch("src.services.scan_hooks.Session")
    @patch("src.services.scan_hooks.Repository")
    def test_hook_works_in_registry(
        self, mock_repo_cls, mock_session_cls, mock_take_snapshot, scan_run, registry
    ):
        """Hook should work correctly when registered in a ScanHookRegistry."""
        mock_repo = MagicMock()
        mock_repo_cls.return_value = mock_repo

        mock_session = MagicMock()
        mock_session_cls.return_value.__enter__ = MagicMock(return_value=mock_session)
        mock_session_cls.return_value.__exit__ = MagicMock(return_value=False)
        mock_session.execute.return_value.scalars.return_value.all.return_value = [
            "user-1",
        ]

        hook = make_portfolio_snapshot_hook("sqlite:///test.db")
        registry.register(hook)
        registry.notify(scan_run, ["ext1"])

        mock_take_snapshot.assert_called_once_with("user-1", mock_repo)
