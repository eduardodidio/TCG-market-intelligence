"""Tests for admin daily Liga scan orchestrator (F67-T02)."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.collectors.admin_scan import run_admin_daily_liga_scan
from src.domain.models import ScanRun


@pytest.fixture()
def mock_repo():
    with patch("src.collectors.admin_scan.Repository") as MockRepo:
        yield MockRepo.return_value


class TestRunAdminDailyLigaScanNoAdmins:
    """When no admin users exist, scan completes with 0 cards."""

    @pytest.mark.asyncio()
    async def test_no_admins_returns_completed_scan(self, mock_repo):
        mock_repo.get_admin_user_ids.return_value = []

        result = await run_admin_daily_liga_scan(db_url="sqlite:///:memory:", run_id=42)

        assert result.status == "completed"
        assert result.cards_total == 0
        assert result.cards_processed == 0
        assert result.id == 42

    @pytest.mark.asyncio()
    async def test_no_admins_updates_scan_run(self, mock_repo):
        mock_repo.get_admin_user_ids.return_value = []

        await run_admin_daily_liga_scan(db_url="sqlite:///:memory:", run_id=42)

        mock_repo.update_scan_run.assert_called_once()
        call_kwargs = mock_repo.update_scan_run.call_args
        assert call_kwargs[0][0] == 42  # run_id
        assert call_kwargs[1]["status"] == "completed"
        assert call_kwargs[1]["cards_total"] == 0

    @pytest.mark.asyncio()
    async def test_no_admins_no_run_id(self, mock_repo):
        mock_repo.get_admin_user_ids.return_value = []

        result = await run_admin_daily_liga_scan(db_url="sqlite:///:memory:", run_id=None)

        assert result.status == "completed"
        mock_repo.update_scan_run.assert_not_called()


class TestRunAdminDailyLigaScanAllFresh:
    """When all admin cards are recently scanned, scan completes with 0."""

    @pytest.mark.asyncio()
    async def test_all_fresh_returns_completed(self, mock_repo):
        mock_repo.get_admin_user_ids.return_value = [1, 2]
        mock_repo.get_cards_for_liga_scan.return_value = []

        result = await run_admin_daily_liga_scan(db_url="sqlite:///:memory:", run_id=10)

        assert result.status == "completed"
        assert result.cards_total == 0


class TestRunAdminDailyLigaScanWithCards:
    """When admin users have cards, delegates to run_liga_scan."""

    @pytest.mark.asyncio()
    async def test_collects_cards_from_all_admins(self, mock_repo):
        mock_repo.get_admin_user_ids.return_value = [1, 2]
        mock_repo.get_cards_for_liga_scan.side_effect = [
            [{"card_id": 100}, {"card_id": 200}],
            [{"card_id": 200}, {"card_id": 300}],
        ]

        mock_scan_run = ScanRun(id=10, status="completed", cards_total=3)

        with patch(
            "src.collectors.admin_scan.run_liga_scan",
            new_callable=AsyncMock,
            return_value=mock_scan_run,
        ) as mock_liga:
            result = await run_admin_daily_liga_scan(db_url="sqlite:///:memory:", run_id=10)

            mock_liga.assert_called_once()
            call_kwargs = mock_liga.call_args[1]
            # Should be deduplicated: {100, 200, 300}
            assert set(call_kwargs["scan_filter"].card_ids) == {100, 200, 300}
            assert call_kwargs["run_id"] == 10
            assert call_kwargs["max_age_days"] == 1
            assert result.status == "completed"

    @pytest.mark.asyncio()
    async def test_respects_max_age_days(self, mock_repo):
        mock_repo.get_admin_user_ids.return_value = [1]
        mock_repo.get_cards_for_liga_scan.return_value = [{"card_id": 100}]

        mock_scan_run = ScanRun(id=10, status="completed")

        with patch(
            "src.collectors.admin_scan.run_liga_scan",
            new_callable=AsyncMock,
            return_value=mock_scan_run,
        ) as mock_liga:
            await run_admin_daily_liga_scan(db_url="sqlite:///:memory:", run_id=10, max_age_days=7)

            # max_age_days passed to both get_cards_for_liga_scan and run_liga_scan
            liga_call = mock_repo.get_cards_for_liga_scan.call_args
            assert liga_call[1]["max_age_days"] == 7

            liga_scan_call = mock_liga.call_args[1]
            assert liga_scan_call["max_age_days"] == 7

    @pytest.mark.asyncio()
    async def test_skips_entries_without_card_id(self, mock_repo):
        mock_repo.get_admin_user_ids.return_value = [1]
        mock_repo.get_cards_for_liga_scan.return_value = [
            {"card_id": 100},
            {"card_id": None},  # orphan entry
        ]

        mock_scan_run = ScanRun(id=10, status="completed")

        with patch(
            "src.collectors.admin_scan.run_liga_scan",
            new_callable=AsyncMock,
            return_value=mock_scan_run,
        ) as mock_liga:
            await run_admin_daily_liga_scan(db_url="sqlite:///:memory:", run_id=10)

            call_kwargs = mock_liga.call_args[1]
            assert call_kwargs["scan_filter"].card_ids == [100]

    @pytest.mark.asyncio()
    async def test_passes_on_complete_callback(self, mock_repo):
        mock_repo.get_admin_user_ids.return_value = [1]
        mock_repo.get_cards_for_liga_scan.return_value = [{"card_id": 100}]

        callback = MagicMock()
        mock_scan_run = ScanRun(id=10, status="completed")

        with patch(
            "src.collectors.admin_scan.run_liga_scan",
            new_callable=AsyncMock,
            return_value=mock_scan_run,
        ) as mock_liga:
            await run_admin_daily_liga_scan(
                db_url="sqlite:///:memory:", run_id=10, on_complete=callback
            )

            assert mock_liga.call_args[1]["on_complete"] is callback
