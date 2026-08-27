"""Tests for scan hygiene: delete_all_scan_runs and mark_stale_scans_as_error (F73)."""

from __future__ import annotations

from datetime import datetime, timedelta

import pytest

from src.database.repository import Repository


@pytest.fixture()
def repo():
    """Create a Repository backed by an in-memory SQLite DB."""
    return Repository(db_url="sqlite:///:memory:")


class TestDeleteAllScanRuns:
    def test_deletes_all_records(self, repo: Repository):
        repo.create_scan_run("collection")
        repo.create_scan_run("collection")
        repo.create_scan_run("liga")

        assert len(repo.list_scan_runs(limit=100)) == 3

        count = repo.delete_all_scan_runs()

        assert count == 3
        assert len(repo.list_scan_runs(limit=100)) == 0

    def test_returns_zero_when_empty(self, repo: Repository):
        count = repo.delete_all_scan_runs()
        assert count == 0


class TestMarkStaleScanRuns:
    def test_marks_running_scans_from_yesterday(self, repo: Repository):
        """Running scans started before the cutoff should be marked as error."""
        run_id = repo.create_scan_run("collection")
        yesterday = datetime.now() - timedelta(days=1)
        repo.update_scan_run(
            run_id,
            status="running",
            started_at=yesterday,
        )

        today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        marked = repo.mark_stale_scans_as_error(before=today_start)

        assert marked == 1
        scan = repo.get_scan_run(run_id)
        assert scan is not None
        assert scan["status"] == "error"
        assert "stale" in scan["error_summary"].lower()
        assert scan["finished_at"] is not None

    def test_skips_todays_running_scans(self, repo: Repository):
        """Running scans started today (after cutoff) should NOT be marked."""
        run_id = repo.create_scan_run("collection")
        repo.update_scan_run(
            run_id,
            status="running",
            started_at=datetime.now(),
        )

        today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        marked = repo.mark_stale_scans_as_error(before=today_start)

        assert marked == 0
        scan = repo.get_scan_run(run_id)
        assert scan is not None
        assert scan["status"] == "running"

    def test_skips_completed_scans(self, repo: Repository):
        """Completed/error scans should not be touched, even if old."""
        run_id = repo.create_scan_run("collection")
        yesterday = datetime.now() - timedelta(days=1)
        repo.update_scan_run(
            run_id,
            status="completed",
            started_at=yesterday,
            finished_at=yesterday + timedelta(minutes=5),
        )

        today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        marked = repo.mark_stale_scans_as_error(before=today_start)

        assert marked == 0
        scan = repo.get_scan_run(run_id)
        assert scan is not None
        assert scan["status"] == "completed"

    def test_mixed_scans(self, repo: Repository):
        """Only old running scans are marked; others are left alone."""
        yesterday = datetime.now() - timedelta(days=1)

        # Old running (should be marked)
        r1 = repo.create_scan_run("collection")
        repo.update_scan_run(r1, status="running", started_at=yesterday)

        # Old completed (should NOT be marked)
        r2 = repo.create_scan_run("collection")
        repo.update_scan_run(
            r2,
            status="completed",
            started_at=yesterday,
            finished_at=yesterday + timedelta(minutes=5),
        )

        # Today running (should NOT be marked)
        r3 = repo.create_scan_run("liga")
        repo.update_scan_run(r3, status="running", started_at=datetime.now())

        today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        marked = repo.mark_stale_scans_as_error(before=today_start)

        assert marked == 1
        assert repo.get_scan_run(r1)["status"] == "error"
        assert repo.get_scan_run(r2)["status"] == "completed"
        assert repo.get_scan_run(r3)["status"] == "running"
