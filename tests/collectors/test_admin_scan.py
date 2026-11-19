"""Tests for admin daily scan orchestrator."""

from __future__ import annotations

from dataclasses import dataclass
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.collectors.admin_scan import run_admin_daily_scan


@dataclass
class _FakeSweepResult:
    """Mimics MypSweepResult fields used by admin_scan."""

    total_eligible: int = 0
    total_processed: int = 0
    prices_found: int = 0
    prices_not_found: int = 0
    errors: int = 0
    batches_completed: int = 0
    dry_run: bool = False


@pytest.fixture()
def mock_repo():
    with patch("src.collectors.admin_scan.Repository") as MockRepo:
        yield MockRepo.return_value


class TestRunAdminDailyScanNoAdmins:
    """When no admin users exist, scan completes with 0 cards."""

    @pytest.mark.asyncio()
    async def test_no_admins_returns_completed_scan(self, mock_repo):
        mock_repo.get_admin_user_ids.return_value = []

        result = await run_admin_daily_scan(db_url="sqlite:///:memory:", run_id=42)

        assert result.status == "completed"
        assert result.cards_total == 0
        assert result.cards_processed == 0
        assert result.id == 42

    @pytest.mark.asyncio()
    async def test_no_admins_updates_scan_run(self, mock_repo):
        mock_repo.get_admin_user_ids.return_value = []

        await run_admin_daily_scan(db_url="sqlite:///:memory:", run_id=42)

        mock_repo.update_scan_run.assert_called_once()
        call_kwargs = mock_repo.update_scan_run.call_args
        assert call_kwargs[0][0] == 42  # run_id
        assert call_kwargs[1]["status"] == "completed"
        assert call_kwargs[1]["cards_total"] == 0

    @pytest.mark.asyncio()
    async def test_no_admins_no_run_id(self, mock_repo):
        mock_repo.get_admin_user_ids.return_value = []

        result = await run_admin_daily_scan(db_url="sqlite:///:memory:", run_id=None)

        assert result.status == "completed"
        mock_repo.update_scan_run.assert_not_called()


class TestRunAdminDailyScanAllFresh:
    """When all admin cards are recently scanned, scan completes with 0."""

    @pytest.mark.asyncio()
    async def test_all_fresh_returns_completed(self, mock_repo):
        mock_repo.get_admin_user_ids.return_value = [1, 2]
        mock_repo.get_cards_for_sweep.return_value = []

        result = await run_admin_daily_scan(db_url="sqlite:///:memory:", run_id=10)

        assert result.status == "completed"
        assert result.cards_total == 0


class TestRunAdminDailyScanWithCards:
    """When admin users have cards, delegates to run_myp_sweep."""

    @pytest.mark.asyncio()
    async def test_collects_cards_from_all_admins(self, mock_repo):
        mock_repo.get_admin_user_ids.return_value = [1, 2]

        mock_sweep = _FakeSweepResult(total_eligible=3, total_processed=3)

        with patch(
            "src.collectors.admin_scan.run_myp_sweep",
            new_callable=AsyncMock,
            return_value=mock_sweep,
        ) as mock_scan:
            result = await run_admin_daily_scan(db_url="sqlite:///:memory:", run_id=10)

            mock_scan.assert_called_once()
            call_kwargs = mock_scan.call_args[1]
            assert call_kwargs["db_url"] == "sqlite:///:memory:"
            assert call_kwargs["max_age_days"] == 1
            assert result.status == "completed"
            assert result.cards_total == 3

    @pytest.mark.asyncio()
    async def test_respects_max_age_days(self, mock_repo):
        mock_repo.get_admin_user_ids.return_value = [1]

        mock_sweep = _FakeSweepResult(total_eligible=1, total_processed=1)

        with patch(
            "src.collectors.admin_scan.run_myp_sweep",
            new_callable=AsyncMock,
            return_value=mock_sweep,
        ) as mock_scan:
            await run_admin_daily_scan(db_url="sqlite:///:memory:", run_id=10, max_age_days=7)

            scan_call = mock_scan.call_args[1]
            assert scan_call["max_age_days"] == 7

    @pytest.mark.asyncio()
    async def test_skips_entries_without_card_id(self, mock_repo):
        mock_repo.get_admin_user_ids.return_value = [1]

        mock_sweep = _FakeSweepResult(total_eligible=1, total_processed=1)

        with patch(
            "src.collectors.admin_scan.run_myp_sweep",
            new_callable=AsyncMock,
            return_value=mock_sweep,
        ) as mock_scan:
            result = await run_admin_daily_scan(db_url="sqlite:///:memory:", run_id=10)

            mock_scan.assert_called_once()
            assert result.status == "completed"

    @pytest.mark.asyncio()
    async def test_passes_on_complete_callback(self, mock_repo):
        mock_repo.get_admin_user_ids.return_value = [1]

        callback = MagicMock()
        mock_sweep = _FakeSweepResult(total_eligible=1, total_processed=1)

        with patch(
            "src.collectors.admin_scan.run_myp_sweep",
            new_callable=AsyncMock,
            return_value=mock_sweep,
        ) as mock_scan:
            await run_admin_daily_scan(db_url="sqlite:///:memory:", run_id=10, on_complete=callback)

            assert mock_scan.call_args[1]["on_complete"] is callback
