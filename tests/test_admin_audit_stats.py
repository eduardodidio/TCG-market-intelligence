"""Tests for F213-T10: Admin audit log endpoint + DB stats dashboard data."""

from __future__ import annotations

import json
import time
from unittest.mock import patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from src.api.deps import get_current_user, get_db
from src.api.routers.admin import (
    _DB_STATS_TTL_SECONDS,
    router,
)
from src.database.models import CardRow
from src.database.repository import Repository
from src.domain.models import User


def _insert_card(repo: Repository, name: str, set_code: str, num: str) -> int:
    """Insert a card directly via SQLAlchemy for testing."""
    with Session(repo.engine) as session:
        row = CardRow(
            name_en=name,
            game="mtg",
            set_code=set_code,
            collector_number=num,
        )
        session.add(row)
        session.commit()
        session.refresh(row)
        return row.id


def _make_user(user_id: int = 1, is_admin: bool = False, email: str = "u@test.com") -> User:
    return User(
        id=user_id,
        email=email,
        display_name="Test User",
        auth_provider="email",
        is_active=True,
        is_admin=is_admin,
    )


@pytest.fixture()
def repo(tmp_path):
    db_path = tmp_path / "test_audit_stats.db"
    return Repository(db_url=f"sqlite:///{db_path}")


@pytest.fixture()
def admin_user():
    return _make_user(user_id=1, is_admin=True, email="admin@test.com")


@pytest.fixture()
def regular_user():
    return _make_user(user_id=2, is_admin=False, email="user@test.com")


@pytest.fixture()
def admin_app(repo, admin_user):
    """App with admin auth overridden."""
    app = FastAPI()
    app.include_router(router, prefix="/api/v1")
    app.dependency_overrides[get_db] = lambda: repo
    app.dependency_overrides[get_current_user] = lambda: admin_user
    # Create admin user in DB so audit logs have a valid actor
    user_row = repo.create_user(email=admin_user.email, display_name=admin_user.display_name)
    repo.update_user(user_row.id, is_admin=1)
    # Reset db-stats cache between tests
    import src.api.routers.admin as admin_mod

    admin_mod._db_stats_cache = None
    admin_mod._db_stats_cache_ts = 0.0
    yield app
    # Clean up cache after test
    admin_mod._db_stats_cache = None
    admin_mod._db_stats_cache_ts = 0.0


@pytest.fixture()
def admin_client(admin_app):
    return TestClient(admin_app)


@pytest.fixture()
def nonadmin_app(repo, regular_user):
    app = FastAPI()
    app.include_router(router, prefix="/api/v1")
    app.dependency_overrides[get_db] = lambda: repo
    app.dependency_overrides[get_current_user] = lambda: regular_user
    repo.create_user(email=regular_user.email, display_name=regular_user.display_name)
    return app


@pytest.fixture()
def nonadmin_client(nonadmin_app):
    return TestClient(nonadmin_app)


# ── Audit log creation and retrieval ─────────────────────────────────


class TestAuditLogCreationRetrieval:
    def test_audit_log_created_and_retrieved(self, admin_client, repo):
        """Audit log entries can be created via repo and retrieved via endpoint."""
        repo.log_audit(
            actor_id=1,
            actor_email="admin@test.com",
            action="test_action",
            target_type="system",
            target_id="123",
            details={"key": "value"},
            ip_address="10.0.0.1",
        )

        resp = admin_client.get("/api/v1/admin/audit-log")
        assert resp.status_code == 200
        body = resp.json()
        assert body["meta"]["total"] == 1
        entry = body["data"][0]
        assert entry["action"] == "test_action"
        assert entry["target_type"] == "system"
        assert entry["target_id"] == "123"
        assert entry["ip_address"] == "10.0.0.1"
        details = json.loads(entry["details_json"])
        assert details["key"] == "value"

    def test_multiple_entries_ordered_desc(self, admin_client, repo):
        """Multiple audit entries are returned newest-first."""
        repo.log_audit(1, "admin@test.com", "first_action")
        repo.log_audit(1, "admin@test.com", "second_action")

        resp = admin_client.get("/api/v1/admin/audit-log")
        body = resp.json()
        assert body["data"][0]["action"] == "second_action"
        assert body["data"][1]["action"] == "first_action"


# ── Audit log pagination ─────────────────────────────────────────────


class TestAuditLogPagination:
    def test_pagination_limit_offset(self, admin_client, repo):
        """Audit log respects limit and offset query parameters."""
        for i in range(7):
            repo.log_audit(1, "admin@test.com", f"action_{i}")

        resp = admin_client.get("/api/v1/admin/audit-log", params={"limit": 3, "offset": 0})
        body = resp.json()
        assert len(body["data"]) == 3
        assert body["meta"]["total"] == 7

        resp2 = admin_client.get("/api/v1/admin/audit-log", params={"limit": 3, "offset": 3})
        body2 = resp2.json()
        assert len(body2["data"]) == 3
        # Different entries
        ids_page1 = {e["id"] for e in body["data"]}
        ids_page2 = {e["id"] for e in body2["data"]}
        assert ids_page1.isdisjoint(ids_page2)

        # Last page
        resp3 = admin_client.get("/api/v1/admin/audit-log", params={"limit": 3, "offset": 6})
        body3 = resp3.json()
        assert len(body3["data"]) == 1


# ── Audit log filter by action type ──────────────────────────────────


class TestAuditLogFilterByAction:
    def test_filter_returns_matching_only(self, admin_client, repo):
        """Filtering by action returns only matching entries."""
        repo.log_audit(1, "admin@test.com", "user_create")
        repo.log_audit(1, "admin@test.com", "credit_adjust")
        repo.log_audit(1, "admin@test.com", "user_create")
        repo.log_audit(1, "admin@test.com", "db_backup")

        resp = admin_client.get("/api/v1/admin/audit-log", params={"action": "user_create"})
        body = resp.json()
        assert body["meta"]["total"] == 2
        assert all(e["action"] == "user_create" for e in body["data"])

    def test_filter_nonexistent_action_empty(self, admin_client, repo):
        """Filtering by a non-existent action returns empty results."""
        repo.log_audit(1, "admin@test.com", "user_create")

        resp = admin_client.get("/api/v1/admin/audit-log", params={"action": "nonexistent"})
        body = resp.json()
        assert body["meta"]["total"] == 0
        assert body["data"] == []


# ── DB stats schema ──────────────────────────────────────────────────


class TestDbStats:
    def test_returns_expected_schema(self, admin_client):
        """GET /admin/db-stats returns table_counts and last_sync keys."""
        resp = admin_client.get("/api/v1/admin/db-stats")
        assert resp.status_code == 200
        body = resp.json()
        data = body["data"]

        assert "table_counts" in data
        assert "last_sync" in data

        counts = data["table_counts"]
        expected_tables = {
            "cards",
            "user_collection",
            "price_observations",
            "source_cards",
            "decks",
            "wishlists",
        }
        assert set(counts.keys()) == expected_tables
        # All counts should be non-negative integers
        for key, val in counts.items():
            assert isinstance(val, int), f"{key} should be int, got {type(val)}"
            assert val >= 0

        sync = data["last_sync"]
        assert "latest_price_observation" in sync
        assert "latest_legality_history" in sync

    def test_counts_reflect_data(self, admin_client, repo):
        """DB stats counts reflect actual data in the database."""
        # Insert some cards
        _insert_card(repo, "Lightning Bolt", "m10", "1")
        _insert_card(repo, "Counterspell", "m10", "2")

        resp = admin_client.get("/api/v1/admin/db-stats")
        data = resp.json()["data"]
        assert data["table_counts"]["cards"] == 2

    def test_empty_db_returns_zeros_and_nulls(self, admin_client):
        """On an empty DB, counts are 0 and sync dates are null."""
        resp = admin_client.get("/api/v1/admin/db-stats")
        data = resp.json()["data"]

        for val in data["table_counts"].values():
            assert val == 0

        assert data["last_sync"]["latest_price_observation"] is None
        assert data["last_sync"]["latest_legality_history"] is None


# ── DB stats caching ─────────────────────────────────────────────────


class TestDbStatsCaching:
    def test_cached_within_ttl(self, admin_client, repo):
        """Second call within TTL returns cached data (same result even after DB change)."""
        resp1 = admin_client.get("/api/v1/admin/db-stats")
        data1 = resp1.json()["data"]
        assert data1["table_counts"]["cards"] == 0

        # Insert a card — but cache should still return 0
        _insert_card(repo, "Lightning Bolt", "m10", "1")

        resp2 = admin_client.get("/api/v1/admin/db-stats")
        data2 = resp2.json()["data"]
        # Should still be 0 due to cache
        assert data2["table_counts"]["cards"] == 0

    def test_cache_expires_after_ttl(self, admin_client, repo):
        """After TTL expires, fresh data is returned."""
        import src.api.routers.admin as admin_mod

        resp1 = admin_client.get("/api/v1/admin/db-stats")
        assert resp1.json()["data"]["table_counts"]["cards"] == 0

        # Insert a card
        _insert_card(repo, "Lightning Bolt", "m10", "1")

        # Expire the cache by backdating the timestamp
        admin_mod._db_stats_cache_ts = time.monotonic() - _DB_STATS_TTL_SECONDS - 1

        resp2 = admin_client.get("/api/v1/admin/db-stats")
        assert resp2.json()["data"]["table_counts"]["cards"] == 1


# ── Admin-only auth (403 for non-admin) ──────────────────────────────


class TestAdminOnlyAuth:
    def test_audit_log_403_non_admin(self, nonadmin_client):
        resp = nonadmin_client.get("/api/v1/admin/audit-log")
        assert resp.status_code == 403

    def test_db_stats_403_non_admin(self, nonadmin_client):
        resp = nonadmin_client.get("/api/v1/admin/db-stats")
        assert resp.status_code == 403


# ── Snapshot-prices audit logging ────────────────────────────────────


class TestSnapshotPricesAudit:
    def test_snapshot_prices_logs_audit(self, admin_client, repo):
        """POST /jobs/snapshot-prices creates an audit log entry."""
        with patch("src.collectors.price_snapshot.run_daily_snapshot", return_value=42):
            resp = admin_client.post("/api/v1/admin/jobs/snapshot-prices")
        assert resp.status_code == 200
        assert resp.json()["data"]["observations_created"] == 42

        logs, total = repo.list_audit_logs(action="job_trigger")
        assert total == 1
        details = json.loads(logs[0]["details_json"])
        assert details["job_type"] == "snapshot_prices"
        assert details["observations_created"] == 42
