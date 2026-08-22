"""Tests for scheduled scan repository CRUD methods (F37-T03)."""

from __future__ import annotations

import pytest

from src.database.repository import Repository


@pytest.fixture()
def repo():
    """Create a Repository backed by an in-memory SQLite DB."""
    return Repository(db_url="sqlite:///:memory:")


def _create_schedule(repo, **overrides):
    """Helper to create a scheduled scan with sensible defaults."""
    defaults = {
        "user_id": "1",
        "name": "Test Schedule",
        "cron_expression": "0 6 * * *",
        "scan_type": "collection",
    }
    defaults.update(overrides)
    return repo.create_scheduled_scan(**defaults)


class TestCreateGetRoundTrip:
    """1. Create + get round-trip -- all fields match."""

    def test_create_returns_id(self, repo) -> None:
        schedule_id = _create_schedule(repo)
        assert isinstance(schedule_id, int)
        assert schedule_id > 0

    def test_get_returns_all_fields(self, repo) -> None:
        schedule_id = _create_schedule(
            repo,
            name="Daily Collection",
            cron_expression="0 6 * * *",
            scan_type="collection",
            filters_json='{"limit": 10}',
            description="Daily scan",
            max_retries=5,
        )
        result = repo.get_scheduled_scan(schedule_id)
        assert result is not None
        assert result["id"] == schedule_id
        assert result["user_id"] == "1"
        assert result["name"] == "Daily Collection"
        assert result["cron_expression"] == "0 6 * * *"
        assert result["scan_type"] == "collection"
        assert result["filters_json"] == '{"limit": 10}'
        assert result["description"] == "Daily scan"
        assert result["max_retries"] == 5
        assert result["status"] == "active"
        assert result["error_count"] == 0
        assert result["last_run_id"] is None
        assert result["created_at"] is not None
        assert result["updated_at"] is not None

    def test_get_nonexistent_returns_none(self, repo) -> None:
        result = repo.get_scheduled_scan(99999)
        assert result is None


class TestListWithStatusFilter:
    """2. List with status filter -- returns only matching."""

    def test_filter_by_status(self, repo) -> None:
        id1 = _create_schedule(repo, name="S1")
        id2 = _create_schedule(repo, name="S2")
        repo.update_scheduled_scan(id2, status="paused")

        active = repo.list_scheduled_scans(status="active")
        assert len(active) == 1
        assert active[0]["id"] == id1

        paused = repo.list_scheduled_scans(status="paused")
        assert len(paused) == 1
        assert paused[0]["id"] == id2

    def test_list_all(self, repo) -> None:
        _create_schedule(repo, name="S1")
        _create_schedule(repo, name="S2")
        _create_schedule(repo, name="S3")
        all_schedules = repo.list_scheduled_scans()
        assert len(all_schedules) == 3

    def test_list_by_user(self, repo) -> None:
        _create_schedule(repo, name="S1", user_id="1")
        _create_schedule(repo, name="S2", user_id="2")
        user1 = repo.list_scheduled_scans(user_id="1")
        assert len(user1) == 1
        assert user1[0]["name"] == "S1"


class TestListPagination:
    """3. List pagination -- offset/limit work."""

    def test_offset_limit(self, repo) -> None:
        for i in range(5):
            _create_schedule(repo, name=f"S{i}")
        page = repo.list_scheduled_scans(limit=2, offset=2)
        assert len(page) == 2

        all_schedules = repo.list_scheduled_scans(limit=50)
        expected = [s["id"] for s in all_schedules[2:4]]
        actual = [s["id"] for s in page]
        assert actual == expected


class TestUpdateSingleField:
    """4. Update single field -- only that field changes."""

    def test_update_name(self, repo) -> None:
        schedule_id = _create_schedule(repo, name="Original")
        repo.update_scheduled_scan(schedule_id, name="Updated")
        result = repo.get_scheduled_scan(schedule_id)
        assert result["name"] == "Updated"
        assert result["cron_expression"] == "0 6 * * *"  # unchanged


class TestUpdateMultipleFields:
    """5. Update multiple fields -- all change."""

    def test_update_multiple(self, repo) -> None:
        schedule_id = _create_schedule(repo)
        repo.update_scheduled_scan(
            schedule_id,
            name="New Name",
            status="paused",
            error_count=2,
        )
        result = repo.get_scheduled_scan(schedule_id)
        assert result["name"] == "New Name"
        assert result["status"] == "paused"
        assert result["error_count"] == 2


class TestDeleteExisting:
    """6. Delete existing -- returns True, row gone."""

    def test_delete_existing(self, repo) -> None:
        schedule_id = _create_schedule(repo)
        assert repo.delete_scheduled_scan(schedule_id) is True
        assert repo.get_scheduled_scan(schedule_id) is None


class TestDeleteNonExistent:
    """7. Delete non-existent -- returns False."""

    def test_delete_nonexistent(self, repo) -> None:
        assert repo.delete_scheduled_scan(99999) is False


class TestGetActiveSchedules:
    """8. Get active schedules -- skips paused/disabled."""

    def test_returns_only_active(self, repo) -> None:
        _create_schedule(repo, name="Active1")
        id2 = _create_schedule(repo, name="Paused")
        _create_schedule(repo, name="Active2")
        id4 = _create_schedule(repo, name="Disabled")

        repo.update_scheduled_scan(id2, status="paused")
        repo.update_scheduled_scan(id4, status="disabled")

        active = repo.get_active_schedules()
        assert len(active) == 2
        names = {s["name"] for s in active}
        assert names == {"Active1", "Active2"}


class TestCountScheduledScans:
    """Count schedules per user with optional status filter."""

    def test_count_by_user(self, repo) -> None:
        _create_schedule(repo, name="S1", user_id="1")
        _create_schedule(repo, name="S2", user_id="1")
        _create_schedule(repo, name="S3", user_id="2")
        assert repo.count_scheduled_scans("1") == 2
        assert repo.count_scheduled_scans("2") == 1

    def test_count_with_status(self, repo) -> None:
        _create_schedule(repo, name="S1", user_id="1")
        id2 = _create_schedule(repo, name="S2", user_id="1")
        repo.update_scheduled_scan(id2, status="paused")
        assert repo.count_scheduled_scans("1", status="active") == 1
        assert repo.count_scheduled_scans("1", status="paused") == 1
