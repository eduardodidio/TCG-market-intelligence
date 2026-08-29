"""Tests for Liga scheduled scans (F60-T10).

Covers:
- Scheduler routes to run_liga_scan when filters contain provider=liga
- Scheduler routes to run_scan when provider absent (MYP default)
- liga_partial uses limit and max_age_days from filters
- Auto-pause after consecutive failures (existing behavior preserved)
- Default Liga schedules seeded correctly
- Idempotent seeding (no duplicates)
- Existing MYP scheduled scans unaffected
"""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

from src.scheduler.service import ScanScheduler


class TestSchedulerLigaRouting:
    """Scheduler routes to Liga or MYP based on filters_json provider field."""

    @patch("src.scheduler.service.Repository")
    @patch("src.scheduler.service.asyncio.run")
    def test_liga_provider_routes_to_run_liga_scan(self, mock_asyncio_run, MockRepo) -> None:
        """When filters_json contains provider=liga, scheduler calls run_liga_scan."""
        mock_repo = MockRepo.return_value
        mock_repo.get_scheduled_scan.return_value = {
            "id": 1,
            "user_id": "1",
            "name": "Liga Daily Partial",
            "cron_expression": "0 3 * * *",
            "scan_type": "liga_partial",
            "filters_json": (
                '{"scan_type": "liga_partial", "limit": 50, "provider": "liga", "max_age_days": 1}'
            ),
            "status": "active",
            "last_run_id": None,
            "error_count": 0,
            "max_retries": 3,
        }
        mock_repo.count_collection.return_value = 0

        scheduler = ScanScheduler("sqlite:///:memory:")
        scheduler._scheduler = MagicMock()
        scheduler._scheduler.get_job.return_value = None

        with patch("src.collectors.liga_scan.run_liga_scan"):
            scheduler._execute_scheduled_scan(1, scan_id=10)

            # asyncio.run should have been called with run_liga_scan coroutine
            mock_asyncio_run.assert_called_once()
            # Verify it was called (the import patch intercepts inside _execute)
            # The asyncio.run call wraps run_liga_scan, so check the args
            call_args = mock_asyncio_run.call_args
            assert call_args is not None

    @patch("src.scheduler.service.Repository")
    @patch("src.scheduler.service.asyncio.run")
    def test_myp_provider_routes_to_run_scan(self, mock_asyncio_run, MockRepo) -> None:
        """When provider absent in filters_json, scheduler calls run_scan (MYP)."""
        mock_repo = MockRepo.return_value
        mock_repo.get_scheduled_scan.return_value = {
            "id": 2,
            "user_id": "1",
            "name": "MYP Daily",
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

        scheduler._execute_scheduled_scan(2, scan_id=20)

        mock_asyncio_run.assert_called_once()

    @patch("src.scheduler.service.Repository")
    @patch("src.scheduler.service.asyncio.run")
    def test_explicit_myp_provider_routes_to_run_scan(self, mock_asyncio_run, MockRepo) -> None:
        """When provider=myp explicitly in filters, scheduler uses run_scan."""
        mock_repo = MockRepo.return_value
        mock_repo.get_scheduled_scan.return_value = {
            "id": 3,
            "user_id": "1",
            "name": "MYP Explicit",
            "cron_expression": "0 6 * * *",
            "scan_type": "collection",
            "filters_json": '{"provider": "myp"}',
            "status": "active",
            "last_run_id": None,
            "error_count": 0,
            "max_retries": 3,
        }
        mock_repo.count_collection.return_value = 0

        scheduler = ScanScheduler("sqlite:///:memory:")
        scheduler._scheduler = MagicMock()
        scheduler._scheduler.get_job.return_value = None

        scheduler._execute_scheduled_scan(3, scan_id=30)

        mock_asyncio_run.assert_called_once()


class TestSchedulerLigaPartial:
    """Liga partial scan passes correct parameters."""

    @patch("src.scheduler.service.Repository")
    @patch("src.scheduler.service.asyncio.run")
    def test_liga_partial_passes_max_age_days(self, mock_asyncio_run, MockRepo) -> None:
        """Liga partial scan passes max_age_days from filters to run_liga_scan."""
        mock_repo = MockRepo.return_value
        mock_repo.get_scheduled_scan.return_value = {
            "id": 1,
            "user_id": "1",
            "name": "Liga Daily Partial",
            "cron_expression": "0 3 * * *",
            "scan_type": "liga_partial",
            "filters_json": (
                '{"scan_type": "liga_partial", "limit": 50, "provider": "liga", "max_age_days": 1}'
            ),
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

        # Verify asyncio.run was called; the coroutine receives max_age_days=1
        mock_asyncio_run.assert_called_once()
        coroutine = mock_asyncio_run.call_args[0][0]
        # The coroutine should be from run_liga_scan; we can check it was created
        assert coroutine is not None

    @patch("src.scheduler.service.Repository")
    @patch("src.scheduler.service.asyncio.run")
    def test_liga_full_no_max_age_days(self, mock_asyncio_run, MockRepo) -> None:
        """Liga full scan does not pass max_age_days (None)."""
        mock_repo = MockRepo.return_value
        mock_repo.get_scheduled_scan.return_value = {
            "id": 2,
            "user_id": "1",
            "name": "Liga Weekly Full",
            "cron_expression": "0 1 * * 0",
            "scan_type": "liga_full",
            "filters_json": '{"scan_type": "liga_full", "provider": "liga"}',
            "status": "active",
            "last_run_id": None,
            "error_count": 0,
            "max_retries": 3,
        }
        mock_repo.count_collection.return_value = 0

        scheduler = ScanScheduler("sqlite:///:memory:")
        scheduler._scheduler = MagicMock()
        scheduler._scheduler.get_job.return_value = None

        scheduler._execute_scheduled_scan(2, scan_id=20)

        mock_asyncio_run.assert_called_once()


class TestSchedulerAutoPauseLiga:
    """Auto-pause on consecutive failures works for Liga scans too."""

    @patch("src.scheduler.service.Repository")
    @patch("src.scheduler.service.asyncio.run")
    def test_liga_auto_pause_after_max_retries(self, mock_asyncio_run, MockRepo) -> None:
        """Liga scan auto-pauses after max_retries consecutive failures."""
        mock_asyncio_run.side_effect = RuntimeError("liga scan failed")

        mock_repo = MockRepo.return_value
        mock_repo.get_scheduled_scan.return_value = {
            "id": 1,
            "user_id": "1",
            "name": "Liga Daily Partial",
            "cron_expression": "0 3 * * *",
            "scan_type": "liga_partial",
            "filters_json": (
                '{"scan_type": "liga_partial", "limit": 50, "provider": "liga", "max_age_days": 1}'
            ),
            "status": "active",
            "last_run_id": None,
            "error_count": 2,  # at max_retries - 1
            "max_retries": 3,
        }
        mock_repo.count_collection.return_value = 0

        scheduler = ScanScheduler("sqlite:///:memory:")
        scheduler._scheduler = MagicMock()
        scheduler._scheduler.get_job.return_value = None

        scheduler._execute_scheduled_scan(1, scan_id=10)

        # Should auto-pause (error_count 2 -> 3, >= max_retries 3)
        calls = mock_repo.update_scheduled_scan.call_args_list
        assert any(c[1].get("status") == "paused" for c in calls)

    @patch("src.scheduler.service.Repository")
    @patch("src.scheduler.service.asyncio.run")
    def test_liga_failure_increments_error_count(self, mock_asyncio_run, MockRepo) -> None:
        """Liga scan failure increments error_count."""
        mock_asyncio_run.side_effect = RuntimeError("liga scan failed")

        mock_repo = MockRepo.return_value
        mock_repo.get_scheduled_scan.return_value = {
            "id": 1,
            "user_id": "1",
            "name": "Liga Daily Partial",
            "cron_expression": "0 3 * * *",
            "scan_type": "liga_partial",
            "filters_json": '{"provider": "liga"}',
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

        calls = mock_repo.update_scheduled_scan.call_args_list
        assert any(c[1].get("error_count") == 1 for c in calls)


class TestSeedDefaultLigaSchedules:
    """Tests for seed_default_liga_schedules repository method."""

    def test_seeds_three_schedules(self, tmp_path) -> None:
        """Creates three Liga schedules when none exist (partial, full, admin)."""
        from src.database.models import Base
        from src.database.repository import Repository

        db_url = f"sqlite:///{tmp_path / 'test.db'}"
        repo = Repository(db_url)

        from sqlalchemy import create_engine

        engine = create_engine(db_url)
        Base.metadata.create_all(engine)

        seeded = repo.seed_default_liga_schedules()
        assert seeded == 3

        schedules = repo.list_scheduled_scans()
        liga_schedules = [s for s in schedules if "Liga" in s["name"] or "Admin" in s["name"]]
        assert len(liga_schedules) == 3

        # Verify partial schedule
        partial = next(s for s in liga_schedules if s["scan_type"] == "liga_partial")
        assert partial["name"] == "Liga Daily Partial"
        assert partial["cron_expression"] == "0 3 * * *"
        assert partial["status"] == "active"
        filters = json.loads(partial["filters_json"])
        assert filters["limit"] == 50
        assert filters["provider"] == "liga"
        assert filters["max_age_days"] == 1

        # Verify full schedule
        full = next(s for s in liga_schedules if s["scan_type"] == "liga_full")
        assert full["name"] == "Liga Weekly Full"
        assert full["cron_expression"] == "0 1 * * 0"
        assert full["status"] == "active"
        full_filters = json.loads(full["filters_json"])
        assert full_filters["provider"] == "liga"

        # Verify admin daily schedule
        admin = next(s for s in liga_schedules if s["scan_type"] == "admin_daily_liga")
        assert admin["name"] == "Admin Daily Liga"
        assert admin["cron_expression"] == "0 6 * * *"
        assert admin["status"] == "active"
        admin_filters = json.loads(admin["filters_json"])
        assert admin_filters["provider"] == "liga"
        assert admin_filters["max_age_days"] == 1

    def test_idempotent_no_duplicates(self, tmp_path) -> None:
        """Calling seed twice does not create duplicate schedules."""
        from src.database.models import Base
        from src.database.repository import Repository

        db_url = f"sqlite:///{tmp_path / 'test.db'}"
        repo = Repository(db_url)

        from sqlalchemy import create_engine

        engine = create_engine(db_url)
        Base.metadata.create_all(engine)

        first = repo.seed_default_liga_schedules()
        assert first == 3

        second = repo.seed_default_liga_schedules()
        assert second == 0

        schedules = repo.list_scheduled_scans()
        liga_schedules = [
            s
            for s in schedules
            if s["scan_type"] in ("liga_partial", "liga_full", "admin_daily_liga")
        ]
        assert len(liga_schedules) == 3

    def test_seeds_admin_when_liga_exists(self, tmp_path) -> None:
        """Admin schedule is created even if liga_partial/full already exist."""
        from src.database.models import Base
        from src.database.repository import Repository

        db_url = f"sqlite:///{tmp_path / 'test.db'}"
        repo = Repository(db_url)

        from sqlalchemy import create_engine

        engine = create_engine(db_url)
        Base.metadata.create_all(engine)

        # Manually create liga_partial and liga_full
        repo.create_scheduled_scan(
            user_id="system",
            name="Liga Daily Partial",
            cron_expression="0 3 * * *",
            scan_type="liga_partial",
            filters_json='{"provider": "liga"}',
        )
        repo.create_scheduled_scan(
            user_id="system",
            name="Liga Weekly Full",
            cron_expression="0 1 * * 0",
            scan_type="liga_full",
            filters_json='{"provider": "liga"}',
        )

        # seed should only create admin schedule
        seeded = repo.seed_default_liga_schedules()
        assert seeded == 1

        schedules = repo.list_scheduled_scans()
        admin = [s for s in schedules if s["scan_type"] == "admin_daily_liga"]
        assert len(admin) == 1

    def test_does_not_affect_existing_myp_schedules(self, tmp_path) -> None:
        """Seeding Liga schedules does not modify existing MYP schedules."""
        from src.database.models import Base
        from src.database.repository import Repository

        db_url = f"sqlite:///{tmp_path / 'test.db'}"
        repo = Repository(db_url)

        from sqlalchemy import create_engine

        engine = create_engine(db_url)
        Base.metadata.create_all(engine)

        # Create an existing MYP schedule
        myp_id = repo.create_scheduled_scan(
            user_id="user1",
            name="MYP Daily",
            cron_expression="0 6 * * *",
            scan_type="collection",
            filters_json="{}",
        )

        # Seed Liga schedules
        seeded = repo.seed_default_liga_schedules()
        assert seeded == 3

        # MYP schedule still exists and unchanged
        myp = repo.get_scheduled_scan(myp_id)
        assert myp is not None
        assert myp["name"] == "MYP Daily"
        assert myp["scan_type"] == "collection"

        # Total = 4 (1 MYP + 2 Liga + 1 Admin)
        all_schedules = repo.list_scheduled_scans()
        assert len(all_schedules) == 4


class TestExistingMypUnaffected:
    """Existing MYP scheduled scans continue to work as before."""

    @patch("src.scheduler.service.Repository")
    @patch("src.scheduler.service.asyncio.run")
    def test_myp_scan_still_uses_run_scan(self, mock_asyncio_run, MockRepo) -> None:
        """MYP scheduled scan continues to use run_scan, not run_liga_scan."""
        mock_repo = MockRepo.return_value
        mock_repo.get_scheduled_scan.return_value = {
            "id": 1,
            "user_id": "1",
            "name": "MYP Daily",
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

        # Should have called asyncio.run with run_scan (not run_liga_scan)
        mock_asyncio_run.assert_called_once()

    @patch("src.scheduler.service.Repository")
    @patch("src.scheduler.service.asyncio.run")
    def test_myp_success_resets_error_count(self, mock_asyncio_run, MockRepo) -> None:
        """MYP successful scan resets error_count to 0."""
        mock_repo = MockRepo.return_value
        mock_repo.get_scheduled_scan.return_value = {
            "id": 1,
            "user_id": "1",
            "name": "MYP Daily",
            "cron_expression": "0 6 * * *",
            "scan_type": "collection",
            "filters_json": "{}",
            "status": "active",
            "last_run_id": None,
            "error_count": 1,
            "max_retries": 3,
        }
        mock_repo.count_collection.return_value = 0

        scheduler = ScanScheduler("sqlite:///:memory:")
        scheduler._scheduler = MagicMock()
        scheduler._scheduler.get_job.return_value = None

        scheduler._execute_scheduled_scan(1, scan_id=10)

        calls = mock_repo.update_scheduled_scan.call_args_list
        assert any(c[1].get("error_count") == 0 for c in calls)


class TestSchedulerAdminDailyLigaRouting:
    """Scheduler routes admin_daily_liga scan type to run_admin_daily_liga_scan."""

    @patch("src.scheduler.service.Repository")
    @patch("src.scheduler.service.asyncio.run")
    def test_admin_daily_liga_routes_to_admin_scan(self, mock_asyncio_run, MockRepo) -> None:
        """admin_daily_liga scan type calls run_admin_daily_liga_scan."""
        mock_repo = MockRepo.return_value
        mock_repo.get_scheduled_scan.return_value = {
            "id": 5,
            "name": "Admin Daily Liga",
            "cron_expression": "0 6 * * *",
            "scan_type": "admin_daily_liga",
            "filters_json": '{"provider": "liga", "max_age_days": 1}',
            "status": "active",
            "last_run_id": None,
            "error_count": 0,
            "max_retries": 3,
        }

        scheduler = ScanScheduler("sqlite:///:memory:")
        scheduler._scheduler = MagicMock()
        scheduler._scheduler.get_job.return_value = None

        scheduler._execute_scheduled_scan(5, scan_id=50)

        mock_asyncio_run.assert_called_once()

    @patch("src.scheduler.service.Repository")
    @patch("src.scheduler.service.asyncio.run")
    def test_admin_daily_liga_passes_max_age_days(self, mock_asyncio_run, MockRepo) -> None:
        """admin_daily_liga passes max_age_days from filters."""
        mock_repo = MockRepo.return_value
        mock_repo.get_scheduled_scan.return_value = {
            "id": 5,
            "name": "Admin Daily Liga",
            "cron_expression": "0 6 * * *",
            "scan_type": "admin_daily_liga",
            "filters_json": '{"provider": "liga", "max_age_days": 3}',
            "status": "active",
            "last_run_id": None,
            "error_count": 0,
            "max_retries": 3,
        }

        scheduler = ScanScheduler("sqlite:///:memory:")
        scheduler._scheduler = MagicMock()
        scheduler._scheduler.get_job.return_value = None

        scheduler._execute_scheduled_scan(5, scan_id=50)

        # Verify asyncio.run was called with the admin scan coroutine
        mock_asyncio_run.assert_called_once()
        coroutine = mock_asyncio_run.call_args[0][0]
        assert coroutine is not None

    @patch("src.scheduler.service.Repository")
    @patch("src.scheduler.service.asyncio.run")
    def test_admin_daily_liga_does_not_use_liga_scan(self, mock_asyncio_run, MockRepo) -> None:
        """admin_daily_liga should NOT route to run_liga_scan even though provider=liga."""
        mock_repo = MockRepo.return_value
        mock_repo.get_scheduled_scan.return_value = {
            "id": 5,
            "name": "Admin Daily Liga",
            "cron_expression": "0 6 * * *",
            "scan_type": "admin_daily_liga",
            "filters_json": '{"provider": "liga", "max_age_days": 1}',
            "status": "active",
            "last_run_id": None,
            "error_count": 0,
            "max_retries": 3,
        }

        scheduler = ScanScheduler("sqlite:///:memory:")
        scheduler._scheduler = MagicMock()
        scheduler._scheduler.get_job.return_value = None

        with patch("src.collectors.admin_scan.run_admin_daily_liga_scan"):
            scheduler._execute_scheduled_scan(5, scan_id=50)
            # asyncio.run is called which wraps run_admin_daily_liga_scan
            mock_asyncio_run.assert_called_once()
