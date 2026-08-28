"""Integration tests for error log filter combinations (F85-T08).

Verifies: level, module, date range, and combined filters return correct subsets.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.api.deps import get_current_user, get_db
from src.api.routers.admin import router as admin_router
from src.database.repository import Repository
from src.domain.models import User


def _make_admin_user() -> User:
    return User(
        id=1,
        email="admin@test.com",
        display_name="Admin",
        auth_provider="email",
        is_active=True,
        is_admin=True,
    )


def _make_error_row(
    *,
    level: str = "ERROR",
    error_type: str = "ValueError",
    message: str = "test error",
    module: str | None = "src.api.routers.collection",
    timestamp: datetime | None = None,
) -> dict:
    return {
        "id": str(uuid.uuid4()),
        "timestamp": timestamp or datetime.now(UTC),
        "level": level,
        "error_type": error_type,
        "message": message,
        "module": module,
        "function": "test_fn",
        "line": 42,
        "traceback": "Traceback ...",
        "request_method": "GET",
        "request_path": "/test",
        "request_user_id": 1,
        "request_id": str(uuid.uuid4()),
        "request_params": None,
        "extra": None,
    }


@pytest.fixture()
def repo(tmp_path):
    db_path = tmp_path / "test_filters.db"
    db_url = f"sqlite:///{db_path}"
    return Repository(db_url=db_url)


@pytest.fixture()
def admin_user(repo):
    user = _make_admin_user()
    user_row = repo.create_user(email=user.email, display_name=user.display_name)
    repo.update_user(user_row.id, is_admin=1)
    return user


@pytest.fixture()
def client(repo, admin_user):
    app = FastAPI()
    app.include_router(admin_router, prefix="/api/v1")
    app.dependency_overrides[get_db] = lambda: repo
    app.dependency_overrides[get_current_user] = lambda: admin_user
    return TestClient(app)


@pytest.fixture()
def seeded_repo(repo):
    """Insert errors at different levels, modules, and dates."""
    now = datetime.now(UTC)

    # Different levels
    repo.insert_error_log(
        _make_error_row(
            level="ERROR",
            message="error msg",
            module="src.api.routers.collection",
            timestamp=now - timedelta(hours=1),
        )
    )
    repo.insert_error_log(
        _make_error_row(
            level="CRITICAL",
            message="critical msg",
            module="src.collectors.scan",
            timestamp=now - timedelta(hours=2),
        )
    )
    repo.insert_error_log(
        _make_error_row(
            level="WARNING",
            message="warning msg",
            module="src.providers.liga.provider",
            timestamp=now - timedelta(hours=3),
        )
    )
    repo.insert_error_log(
        _make_error_row(
            level="ERROR",
            message="old error",
            module="src.api.routers.admin",
            timestamp=now - timedelta(days=45),
        )
    )
    repo.insert_error_log(
        _make_error_row(
            level="CRITICAL",
            message="old critical",
            module="src.collectors.scan",
            timestamp=now - timedelta(days=60),
        )
    )

    return repo


class TestLevelFilter:
    """Filter by error level returns only matching entries."""

    def test_filter_error_only(self, client, seeded_repo):
        resp = client.get("/api/v1/admin/errors?level=ERROR")
        assert resp.status_code == 200
        body = resp.json()
        assert body["meta"]["total"] == 2
        for entry in body["data"]:
            assert entry["level"] == "ERROR"

    def test_filter_critical_only(self, client, seeded_repo):
        resp = client.get("/api/v1/admin/errors?level=CRITICAL")
        assert resp.status_code == 200
        body = resp.json()
        assert body["meta"]["total"] == 2
        for entry in body["data"]:
            assert entry["level"] == "CRITICAL"

    def test_filter_warning_only(self, client, seeded_repo):
        resp = client.get("/api/v1/admin/errors?level=WARNING")
        assert resp.status_code == 200
        body = resp.json()
        assert body["meta"]["total"] == 1
        assert body["data"][0]["level"] == "WARNING"
        assert body["data"][0]["message"] == "warning msg"

    def test_no_results_for_nonexistent_level(self, client, seeded_repo):
        resp = client.get("/api/v1/admin/errors?level=DEBUG")
        assert resp.status_code == 200
        assert resp.json()["meta"]["total"] == 0


class TestModuleFilter:
    """Filter by module uses contains matching."""

    def test_filter_api_routers(self, client, seeded_repo):
        resp = client.get("/api/v1/admin/errors?module=api.routers")
        assert resp.status_code == 200
        body = resp.json()
        assert body["meta"]["total"] == 2
        for entry in body["data"]:
            assert "api.routers" in entry["module"]

    def test_filter_collectors(self, client, seeded_repo):
        resp = client.get("/api/v1/admin/errors?module=collectors.scan")
        assert resp.status_code == 200
        body = resp.json()
        assert body["meta"]["total"] == 2
        for entry in body["data"]:
            assert "collectors.scan" in entry["module"]

    def test_filter_providers(self, client, seeded_repo):
        resp = client.get("/api/v1/admin/errors?module=providers.liga")
        assert resp.status_code == 200
        body = resp.json()
        assert body["meta"]["total"] == 1
        assert body["data"][0]["module"] == "src.providers.liga.provider"

    def test_no_results_for_nonexistent_module(self, client, seeded_repo):
        resp = client.get("/api/v1/admin/errors?module=nonexistent.module")
        assert resp.status_code == 200
        assert resp.json()["meta"]["total"] == 0


class TestDateRangeFilter:
    """Filter by date range returns only matching entries."""

    def test_filter_last_24h(self, client, seeded_repo):
        date_from = (datetime.now(UTC) - timedelta(hours=24)).strftime("%Y-%m-%dT%H:%M:%S")
        resp = client.get("/api/v1/admin/errors", params={"date_from": date_from})
        assert resp.status_code == 200
        body = resp.json()
        # Should get the 3 recent errors (1h, 2h, 3h ago), not the old ones
        assert body["meta"]["total"] == 3

    def test_filter_older_than_30_days(self, client, seeded_repo):
        date_to = (datetime.now(UTC) - timedelta(days=30)).strftime("%Y-%m-%dT%H:%M:%S")
        resp = client.get("/api/v1/admin/errors", params={"date_to": date_to})
        assert resp.status_code == 200
        body = resp.json()
        # Should get the 2 old errors (45 and 60 days ago)
        assert body["meta"]["total"] == 2

    def test_filter_date_range(self, client, seeded_repo):
        date_from = (datetime.now(UTC) - timedelta(days=50)).strftime("%Y-%m-%dT%H:%M:%S")
        date_to = (datetime.now(UTC) - timedelta(days=40)).strftime("%Y-%m-%dT%H:%M:%S")
        resp = client.get(
            "/api/v1/admin/errors", params={"date_from": date_from, "date_to": date_to}
        )
        assert resp.status_code == 200
        body = resp.json()
        # Should get only the 45-day-old error
        assert body["meta"]["total"] == 1
        assert body["data"][0]["message"] == "old error"


class TestCombinedFilters:
    """Multiple filters applied simultaneously."""

    def test_level_and_module(self, client, seeded_repo):
        resp = client.get("/api/v1/admin/errors?level=ERROR&module=api.routers")
        assert resp.status_code == 200
        body = resp.json()
        # ERROR + api.routers: "error msg" (collection) and "old error" (admin)
        assert body["meta"]["total"] == 2
        for entry in body["data"]:
            assert entry["level"] == "ERROR"
            assert "api.routers" in entry["module"]

    def test_level_and_date_range(self, client, seeded_repo):
        date_from = (datetime.now(UTC) - timedelta(hours=24)).strftime("%Y-%m-%dT%H:%M:%S")
        resp = client.get("/api/v1/admin/errors", params={"level": "ERROR", "date_from": date_from})
        assert resp.status_code == 200
        body = resp.json()
        # Recent ERROR only: "error msg" (1h ago)
        assert body["meta"]["total"] == 1
        assert body["data"][0]["message"] == "error msg"

    def test_module_and_date_range(self, client, seeded_repo):
        date_from = (datetime.now(UTC) - timedelta(days=70)).strftime("%Y-%m-%dT%H:%M:%S")
        date_to = (datetime.now(UTC) - timedelta(days=30)).strftime("%Y-%m-%dT%H:%M:%S")
        resp = client.get(
            "/api/v1/admin/errors",
            params={"module": "collectors.scan", "date_from": date_from, "date_to": date_to},
        )
        assert resp.status_code == 200
        body = resp.json()
        # collectors.scan + 30-70 days ago: "old critical" (60d)
        assert body["meta"]["total"] == 1
        assert body["data"][0]["message"] == "old critical"

    def test_all_three_filters(self, client, seeded_repo):
        date_from = (datetime.now(UTC) - timedelta(hours=24)).strftime("%Y-%m-%dT%H:%M:%S")
        resp = client.get(
            "/api/v1/admin/errors",
            params={"level": "CRITICAL", "module": "collectors", "date_from": date_from},
        )
        assert resp.status_code == 200
        body = resp.json()
        # CRITICAL + collectors + last 24h: "critical msg" (2h ago)
        assert body["meta"]["total"] == 1
        assert body["data"][0]["message"] == "critical msg"

    def test_all_filters_no_results(self, client, seeded_repo):
        date_from = (datetime.now(UTC) - timedelta(hours=24)).strftime("%Y-%m-%dT%H:%M:%S")
        resp = client.get(
            "/api/v1/admin/errors",
            params={"level": "WARNING", "module": "collectors", "date_from": date_from},
        )
        assert resp.status_code == 200
        # WARNING + collectors + last 24h: no match
        assert resp.json()["meta"]["total"] == 0

    def test_no_filters_returns_all(self, client, seeded_repo):
        resp = client.get("/api/v1/admin/errors")
        assert resp.status_code == 200
        assert resp.json()["meta"]["total"] == 5
