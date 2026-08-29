"""Tests for ScanScheduler service (F37-T04).

Uses mocks for APScheduler and Repository to test logic in isolation.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from src.scheduler.service import ScanScheduler, validate_cron


class TestValidateCron:
    """Cron expression validation tests."""

    def test_valid_expression(self) -> None:
        validate_cron("0 6 * * *")  # daily at 6am

    def test_valid_twice_daily(self) -> None:
        validate_cron("0 */12 * * *")  # every 12 hours

    def test_valid_weekly(self) -> None:
        validate_cron("0 3 * * 1")  # Monday at 3am

    def test_invalid_expression_raises(self) -> None:
        with pytest.raises(ValueError, match="Invalid cron"):
            validate_cron("not a cron")

    def test_sub_hour_star_rejected(self) -> None:
        with pytest.raises(ValueError, match="Sub-hour"):
            validate_cron("* * * * *")  # every minute

    def test_sub_hour_every_5_minutes_rejected(self) -> None:
        with pytest.raises(ValueError, match="Sub-hour"):
            validate_cron("*/5 * * * *")

    def test_sub_hour_every_15_minutes_rejected(self) -> None:
        with pytest.raises(ValueError, match="Sub-hour"):
            validate_cron("*/15 * * * *")

    def test_sub_hour_every_30_minutes_rejected(self) -> None:
        with pytest.raises(ValueError, match="Sub-hour"):
            validate_cron("*/30 * * * *")

    def test_hourly_is_allowed(self) -> None:
        validate_cron("0 * * * *")  # every hour at :00


class TestScanSchedulerInit:
    """Basic lifecycle tests."""

    def test_instantiation(self) -> None:
        scheduler = ScanScheduler("sqlite:///:memory:")
        assert scheduler._scheduler is None

    @patch("src.scheduler.service.Repository")
    def test_start_loads_active_schedules(self, MockRepo) -> None:
        mock_repo = MockRepo.return_value
        mock_repo.get_active_schedules.return_value = [
            {
                "id": 1,
                "name": "Daily",
                "cron_expression": "0 6 * * *",
                "scan_type": "collection",
                "filters_json": "{}",
                "status": "active",
            },
        ]

        scheduler = ScanScheduler("sqlite:///:memory:")
        scheduler.start()

        mock_repo.get_active_schedules.assert_called_once()
        assert scheduler._scheduler is not None

        # Verify job was added
        job = scheduler._scheduler.get_job("scheduled_scan_1")
        assert job is not None
        assert job.name == "Daily"

        scheduler.shutdown()

    def test_shutdown(self) -> None:
        scheduler = ScanScheduler("sqlite:///:memory:")
        scheduler.start()
        assert scheduler._scheduler is not None
        scheduler.shutdown()
        assert scheduler._scheduler is None


class TestAddRemoveSchedule:
    """Job management tests."""

    @patch("src.scheduler.service.Repository")
    def test_add_schedule_creates_job(self, MockRepo) -> None:
        mock_repo = MockRepo.return_value
        mock_repo.get_active_schedules.return_value = []
        mock_repo.get_scheduled_scan.return_value = {
            "id": 5,
            "name": "Weekly",
            "cron_expression": "0 3 * * 1",
            "scan_type": "collection",
            "filters_json": "{}",
            "status": "active",
        }

        scheduler = ScanScheduler("sqlite:///:memory:")
        scheduler.start()
        scheduler.add_schedule(5)

        job = scheduler._scheduler.get_job("scheduled_scan_5")
        assert job is not None
        assert job.name == "Weekly"

        scheduler.shutdown()

    @patch("src.scheduler.service.Repository")
    def test_add_schedule_not_found_raises(self, MockRepo) -> None:
        mock_repo = MockRepo.return_value
        mock_repo.get_active_schedules.return_value = []
        mock_repo.get_scheduled_scan.return_value = None

        scheduler = ScanScheduler("sqlite:///:memory:")
        scheduler.start()

        with pytest.raises(ValueError, match="not found"):
            scheduler.add_schedule(999)

        scheduler.shutdown()

    @patch("src.scheduler.service.Repository")
    def test_remove_schedule_removes_job(self, MockRepo) -> None:
        mock_repo = MockRepo.return_value
        mock_repo.get_active_schedules.return_value = [
            {
                "id": 1,
                "name": "Daily",
                "cron_expression": "0 6 * * *",
                "scan_type": "collection",
                "filters_json": "{}",
                "status": "active",
            },
        ]

        scheduler = ScanScheduler("sqlite:///:memory:")
        scheduler.start()
        assert scheduler._scheduler.get_job("scheduled_scan_1") is not None

        scheduler.remove_schedule(1)
        assert scheduler._scheduler.get_job("scheduled_scan_1") is None

        scheduler.shutdown()

    @patch("src.scheduler.service.Repository")
    def test_pause_and_resume(self, MockRepo) -> None:
        mock_repo = MockRepo.return_value
        mock_repo.get_active_schedules.return_value = [
            {
                "id": 1,
                "name": "Daily",
                "cron_expression": "0 6 * * *",
                "scan_type": "collection",
                "filters_json": "{}",
                "status": "active",
            },
        ]

        scheduler = ScanScheduler("sqlite:///:memory:")
        scheduler.start()

        scheduler.pause_schedule(1)
        job = scheduler._scheduler.get_job("scheduled_scan_1")
        assert job is not None
        assert job.next_run_time is None  # paused job has no next run

        scheduler.resume_schedule(1)
        job = scheduler._scheduler.get_job("scheduled_scan_1")
        assert job.next_run_time is not None  # resumed

        scheduler.shutdown()


class TestTriggerNow:
    """Manual trigger tests."""

    @patch("src.scheduler.service.Repository")
    def test_trigger_now_creates_scan_and_returns_id(self, MockRepo) -> None:
        mock_repo = MockRepo.return_value
        mock_repo.get_active_schedules.return_value = []
        mock_repo.get_scheduled_scan.return_value = {
            "id": 1,
            "name": "Daily",
            "cron_expression": "0 6 * * *",
            "scan_type": "collection",
            "filters_json": "{}",
            "status": "active",
            "last_run_id": None,
        }
        mock_repo.create_scan_run.return_value = 42

        scheduler = ScanScheduler("sqlite:///:memory:")
        scheduler.start()

        # Patch _execute_scheduled_scan to avoid running actual scan
        scheduler._execute_scheduled_scan = MagicMock()

        scan_id = scheduler.trigger_now(1)
        assert scan_id == 42
        mock_repo.create_scan_run.assert_called_once_with("collection", "{}")

        scheduler.shutdown()

    @patch("src.scheduler.service.Repository")
    def test_trigger_now_not_found_raises(self, MockRepo) -> None:
        mock_repo = MockRepo.return_value
        mock_repo.get_active_schedules.return_value = []
        mock_repo.get_scheduled_scan.return_value = None

        scheduler = ScanScheduler("sqlite:///:memory:")
        scheduler.start()

        with pytest.raises(ValueError, match="not found"):
            scheduler.trigger_now(999)

        scheduler.shutdown()


class TestExecuteScheduledScan:
    """_execute_scheduled_scan callback tests."""

    @patch("src.scheduler.service.Repository")
    @patch("src.scheduler.service.asyncio.run")
    def test_happy_path_updates_metadata(self, mock_asyncio_run, MockRepo) -> None:
        mock_repo = MockRepo.return_value
        mock_repo.get_scheduled_scan.return_value = {
            "id": 1,
            "user_id": "1",
            "name": "Daily",
            "cron_expression": "0 6 * * *",
            "scan_type": "collection",
            "filters_json": "{}",
            "status": "active",
            "last_run_id": None,
            "error_count": 0,
            "max_retries": 3,
        }
        mock_repo.create_scan_run.return_value = 10
        mock_repo.count_collection.return_value = 0

        scheduler = ScanScheduler("sqlite:///:memory:")
        scheduler._scheduler = MagicMock()
        scheduler._scheduler.get_job.return_value = None

        scheduler._execute_scheduled_scan(1, scan_id=10)

        mock_asyncio_run.assert_called_once()
        # Verify metadata update was called with expected fields
        calls = mock_repo.update_scheduled_scan.call_args_list
        success_call = [c for c in calls if c[1].get("error_count") == 0]
        assert len(success_call) >= 1
        assert success_call[0][0][0] == 1  # schedule_id
        assert success_call[0][1]["last_run_id"] == 10
        assert success_call[0][1]["last_run_at"] is not None

    @patch("src.scheduler.service.Repository")
    @patch("src.scheduler.service.asyncio.run")
    def test_failure_increments_error_count(self, mock_asyncio_run, MockRepo) -> None:
        mock_asyncio_run.side_effect = RuntimeError("scan failed")

        mock_repo = MockRepo.return_value
        mock_repo.get_scheduled_scan.return_value = {
            "id": 1,
            "user_id": "1",
            "name": "Daily",
            "cron_expression": "0 6 * * *",
            "scan_type": "collection",
            "filters_json": "{}",
            "status": "active",
            "last_run_id": None,
            "error_count": 0,
            "max_retries": 3,
        }
        mock_repo.count_collection.return_value = 0

        scheduler = ScanScheduler("sqlite:///:memory:")
        scheduler._scheduler = MagicMock()
        scheduler._scheduler.get_job.return_value = None

        scheduler._execute_scheduled_scan(1, scan_id=10)

        # Check that error_count was set to 1
        calls = mock_repo.update_scheduled_scan.call_args_list
        assert any(call[1].get("error_count") == 1 for call in calls)

    @patch("src.scheduler.service.Repository")
    @patch("src.scheduler.service.asyncio.run")
    def test_auto_pause_after_max_retries(self, mock_asyncio_run, MockRepo) -> None:
        mock_asyncio_run.side_effect = RuntimeError("scan failed")

        mock_repo = MockRepo.return_value
        mock_repo.get_scheduled_scan.return_value = {
            "id": 1,
            "user_id": "1",
            "name": "Daily",
            "cron_expression": "0 6 * * *",
            "scan_type": "collection",
            "filters_json": "{}",
            "status": "active",
            "last_run_id": None,
            "error_count": 2,  # already at max_retries - 1
            "max_retries": 3,
        }
        mock_repo.count_collection.return_value = 0

        scheduler = ScanScheduler("sqlite:///:memory:")
        scheduler._scheduler = MagicMock()
        scheduler._scheduler.get_job.return_value = None

        scheduler._execute_scheduled_scan(1, scan_id=10)

        # Should auto-pause (error_count 2 -> 3, which >= max_retries 3)
        calls = mock_repo.update_scheduled_scan.call_args_list
        assert any(call[1].get("status") == "paused" for call in calls)

    @patch("src.scheduler.service.Repository")
    def test_skip_if_previous_scan_running(self, MockRepo) -> None:
        mock_repo = MockRepo.return_value
        mock_repo.get_scheduled_scan.return_value = {
            "id": 1,
            "user_id": "1",
            "name": "Daily",
            "cron_expression": "0 6 * * *",
            "scan_type": "collection",
            "filters_json": "{}",
            "status": "active",
            "last_run_id": 5,
            "error_count": 0,
            "max_retries": 3,
        }
        mock_repo.get_scan_run.return_value = {
            "id": 5,
            "status": "running",
        }

        scheduler = ScanScheduler("sqlite:///:memory:")
        scheduler._scheduler = MagicMock()

        scheduler._execute_scheduled_scan(1)

        # Should not have created a new scan run
        mock_repo.create_scan_run.assert_not_called()


class TestScheduleTokenCost:
    """Token cost enforcement for scheduled scans (F90-T04)."""

    def _make_schedule(self, **overrides) -> dict:
        """Create a schedule dict with sensible defaults."""
        base = {
            "id": 1,
            "user_id": "42",
            "name": "Daily",
            "cron_expression": "0 6 * * *",
            "scan_type": "collection",
            "filters_json": "{}",
            "status": "active",
            "last_run_id": None,
            "error_count": 0,
            "max_retries": 3,
        }
        base.update(overrides)
        return base

    @patch("src.scheduler.service.Repository")
    @patch("src.scheduler.service.asyncio.run")
    def test_scheduled_scan_deducts_tokens(self, mock_asyncio_run, MockRepo) -> None:
        """When user has enough credits, tokens are deducted and scan proceeds."""
        mock_repo = MockRepo.return_value
        mock_repo.get_scheduled_scan.return_value = self._make_schedule()
        mock_repo.count_collection.return_value = 10
        mock_repo.create_scan_run.return_value = 100

        # Mock CreditService balance check
        mock_balance_row = MagicMock()
        mock_balance_row.user_id = "42"
        mock_balance_row.balance = 50
        mock_balance_row.last_bonus_at = None
        mock_repo.ensure_credit_balance.return_value = mock_balance_row

        # Mock the deduction
        mock_deducted_row = MagicMock()
        mock_deducted_row.user_id = "42"
        mock_deducted_row.balance = 40
        mock_deducted_row.last_bonus_at = None
        mock_repo.update_credit_balance.return_value = mock_deducted_row

        scheduler = ScanScheduler("sqlite:///:memory:")
        scheduler._scheduler = MagicMock()
        scheduler._scheduler.get_job.return_value = None

        scheduler._execute_scheduled_scan(1, scan_id=100)

        # Verify deduction was called
        mock_repo.update_credit_balance.assert_called_once_with(
            user_id="42",
            delta=-10,
            reason="scheduled_scan",
            reference_id="schedule_1",
        )

        # Verify scan actually ran
        mock_asyncio_run.assert_called_once()

    @patch("src.scheduler.service.Repository")
    @patch("src.scheduler.service.asyncio.run")
    def test_scheduled_scan_insufficient_credits(self, mock_asyncio_run, MockRepo) -> None:
        """When user lacks credits, schedule is paused and scan is skipped."""
        mock_repo = MockRepo.return_value
        mock_repo.get_scheduled_scan.return_value = self._make_schedule()
        mock_repo.count_collection.return_value = 10

        # User has only 5 credits but needs 10
        mock_balance_row = MagicMock()
        mock_balance_row.user_id = "42"
        mock_balance_row.balance = 5
        mock_balance_row.last_bonus_at = None
        mock_repo.ensure_credit_balance.return_value = mock_balance_row

        scheduler = ScanScheduler("sqlite:///:memory:")
        scheduler._scheduler = MagicMock()
        scheduler._scheduler.get_job.return_value = MagicMock()

        scheduler._execute_scheduled_scan(1, scan_id=100)

        # Scan should NOT have run
        mock_asyncio_run.assert_not_called()

        # Schedule should be paused with insufficient credits status
        mock_repo.update_scheduled_scan.assert_called_once_with(
            1, status="paused_insufficient_credits"
        )

    @patch("src.scheduler.service.Repository")
    @patch("src.scheduler.service.asyncio.run")
    def test_admin_daily_liga_exempt(self, mock_asyncio_run, MockRepo) -> None:
        """admin_daily_liga scans skip token checks entirely."""
        mock_repo = MockRepo.return_value
        mock_repo.get_scheduled_scan.return_value = self._make_schedule(
            scan_type="admin_daily_liga",
            filters_json='{"provider": "liga", "max_age_days": 1}',
        )
        mock_repo.create_scan_run.return_value = 200

        scheduler = ScanScheduler("sqlite:///:memory:")
        scheduler._scheduler = MagicMock()
        scheduler._scheduler.get_job.return_value = None

        scheduler._execute_scheduled_scan(1, scan_id=200)

        # Should not check credits at all
        mock_repo.count_collection.assert_not_called()
        mock_repo.ensure_credit_balance.assert_not_called()

        # Scan should have run
        mock_asyncio_run.assert_called_once()

    @patch("src.scheduler.service.Repository")
    @patch("src.scheduler.service.asyncio.run")
    def test_scheduled_scan_zero_cards(self, mock_asyncio_run, MockRepo) -> None:
        """If user has 0 cards, scan proceeds with 0 cost (no deduction)."""
        mock_repo = MockRepo.return_value
        mock_repo.get_scheduled_scan.return_value = self._make_schedule()
        mock_repo.count_collection.return_value = 0
        mock_repo.create_scan_run.return_value = 300

        scheduler = ScanScheduler("sqlite:///:memory:")
        scheduler._scheduler = MagicMock()
        scheduler._scheduler.get_job.return_value = None

        scheduler._execute_scheduled_scan(1, scan_id=300)

        # Should not attempt deduction
        mock_repo.update_credit_balance.assert_not_called()
        mock_repo.ensure_credit_balance.assert_not_called()

        # Scan should have run
        mock_asyncio_run.assert_called_once()
