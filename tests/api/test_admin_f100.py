"""Tests for F100 admin endpoints -- audit log, job triggers, backup."""

from __future__ import annotations

import json
from unittest.mock import patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.api.deps import get_audit_service, get_current_user, get_db
from src.api.routers.admin import router
from src.database.repository import Repository
from src.domain.models import User
from src.services.audit import AuditService


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
    db_path = tmp_path / "test_admin_f100.db"
    return Repository(db_url=f"sqlite:///{db_path}")


@pytest.fixture()
def admin_user():
    return _make_user(user_id=1, is_admin=True, email="admin@test.com")


@pytest.fixture()
def regular_user():
    return _make_user(user_id=2, is_admin=False, email="user@test.com")


@pytest.fixture()
def admin_app(repo, admin_user):
    app = FastAPI()
    app.include_router(router, prefix="/api/v1")
    app.dependency_overrides[get_db] = lambda: repo
    app.dependency_overrides[get_current_user] = lambda: admin_user
    # Create admin user in DB
    user_row = repo.create_user(email=admin_user.email, display_name=admin_user.display_name)
    repo.update_user(user_row.id, is_admin=1)
    return app


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


# ── T02: Audit log endpoint ─────────────────────────────────────────


class TestAuditLogEndpoint:
    def test_returns_403_for_non_admin(self, nonadmin_client):
        resp = nonadmin_client.get("/api/v1/admin/audit-log")
        assert resp.status_code == 403

    def test_returns_empty_list(self, admin_client):
        resp = admin_client.get("/api/v1/admin/audit-log")
        assert resp.status_code == 200
        body = resp.json()
        assert body["data"] == []
        assert body["meta"]["total"] == 0

    def test_returns_filtered_results(self, admin_client, repo):
        repo.log_audit(1, "admin@test.com", "user_create", target_type="user", target_id="2")
        repo.log_audit(1, "admin@test.com", "credit_adjust", target_type="user", target_id="3")

        resp = admin_client.get("/api/v1/admin/audit-log", params={"action": "user_create"})
        assert resp.status_code == 200
        body = resp.json()
        assert body["meta"]["total"] == 1
        assert body["data"][0]["action"] == "user_create"

    def test_pagination(self, admin_client, repo):
        for i in range(5):
            repo.log_audit(1, "admin@test.com", f"action_{i}")

        resp = admin_client.get("/api/v1/admin/audit-log", params={"limit": "2", "offset": "0"})
        assert resp.status_code == 200
        body = resp.json()
        assert len(body["data"]) == 2
        assert body["meta"]["total"] == 5


# ── T03: Job trigger endpoints ──────────────────────────────────────


class TestJobTriggerEndpoints:
    def test_liga_scan_403_non_admin(self, nonadmin_client):
        resp = nonadmin_client.post("/api/v1/admin/jobs/liga-scan")
        assert resp.status_code == 403

    @patch("src.collectors.admin_scan.run_admin_daily_liga_scan")
    def test_liga_scan_returns_scan_id(self, mock_scan, admin_client):
        """POST /admin/jobs/liga-scan returns scan_id and pending status."""
        resp = admin_client.post("/api/v1/admin/jobs/liga-scan", params={"max_age_days": "2"})
        assert resp.status_code == 200
        body = resp.json()
        assert "scan_id" in body["data"]
        assert body["data"]["status"] == "pending"

    def test_catalog_scan_403_non_admin(self, nonadmin_client):
        resp = nonadmin_client.post("/api/v1/admin/jobs/catalog-scan", params={"set_code": "mh3"})
        assert resp.status_code == 403

    @patch("src.collectors.liga_sweep.run_liga_sweep")
    def test_catalog_scan_returns_scan_id(self, mock_sweep, admin_client):
        resp = admin_client.post(
            "/api/v1/admin/jobs/catalog-scan",
            params={"set_code": "mh3", "delay": "3.0"},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert "scan_id" in body["data"]
        assert body["data"]["set_code"] == "mh3"
        assert body["data"]["status"] == "pending"

    def test_catalog_scan_validates_set_code(self, admin_client):
        """set_code must be at least 2 chars."""
        resp = admin_client.post(
            "/api/v1/admin/jobs/catalog-scan",
            params={"set_code": "x"},
        )
        assert resp.status_code == 422

    def test_job_status_403_non_admin(self, nonadmin_client):
        resp = nonadmin_client.get("/api/v1/admin/jobs/status")
        assert resp.status_code == 403

    def test_job_status_returns_runs(self, admin_client, repo):
        repo.create_scan_run("admin_liga_scan", "{}")
        resp = admin_client.get("/api/v1/admin/jobs/status")
        assert resp.status_code == 200
        body = resp.json()
        assert len(body["data"]) >= 1


# ── T04: Backup endpoint ────────────────────────────────────────────


class TestBackupEndpoint:
    def test_returns_403_for_non_admin(self, nonadmin_client):
        resp = nonadmin_client.get("/api/v1/admin/backup")
        assert resp.status_code == 403

    def test_returns_404_if_db_missing(self, admin_app, admin_user):
        """Returns 404 when the DB file does not exist at the expected path."""
        with patch("src.config.get_db_url", return_value="sqlite:///no_such_file.db"):
            client = TestClient(admin_app)
            resp = client.get("/api/v1/admin/backup")
            assert resp.status_code == 404

    def test_downloads_valid_sqlite(self, admin_client, repo, tmp_path):
        """GET /admin/backup returns a valid SQLite file."""
        db_url = f"sqlite:///{tmp_path / 'test_admin_f100.db'}"
        with patch("src.config.get_db_url", return_value=db_url):
            resp = admin_client.get("/api/v1/admin/backup")
            assert resp.status_code == 200
            assert resp.headers["content-type"] == "application/x-sqlite3"
            # Check SQLite magic bytes
            assert resp.content[:16].startswith(b"SQLite format 3")


# ── T05: Audit logging on existing endpoints ─────────────────────────


class TestAuditRetrofit:
    def test_create_user_logs_audit(self, admin_client, repo):
        """POST /admin/users creates an audit log entry."""
        resp = admin_client.post(
            "/api/v1/admin/users",
            json={"email": "new@test.com", "display_name": "New User"},
        )
        assert resp.status_code == 200

        logs, total = repo.list_audit_logs(action="user_create")
        assert total == 1
        assert logs[0]["action"] == "user_create"
        details = json.loads(logs[0]["details_json"])
        assert details["email"] == "new@test.com"

    def test_delete_user_logs_audit(self, admin_client, repo):
        """DELETE /admin/users/{id} creates an audit log entry."""
        # Create a user to delete
        target = repo.create_user(email="victim@test.com", display_name="Victim")

        resp = admin_client.delete(f"/api/v1/admin/users/{target.id}")
        assert resp.status_code == 200

        logs, total = repo.list_audit_logs(action="user_delete")
        assert total == 1
        assert logs[0]["target_id"] == str(target.id)

    def test_adjust_credits_logs_audit(self, admin_client, repo):
        """PATCH /admin/users/{id}/credits creates an audit log entry."""
        target = repo.create_user(email="target@test.com", display_name="Target")

        resp = admin_client.patch(
            f"/api/v1/admin/users/{target.id}/credits",
            json={"amount": 100, "reason": "bonus"},
        )
        assert resp.status_code == 200

        logs, total = repo.list_audit_logs(action="credit_adjust")
        assert total == 1
        details = json.loads(logs[0]["details_json"])
        assert details["amount_requested"] == 100
        assert details["reason"] == "bonus"

    def test_audit_failure_does_not_block_action(self, repo, admin_user):
        """Even if audit logging fails, the admin action succeeds."""
        app = FastAPI()
        app.include_router(router, prefix="/api/v1")
        app.dependency_overrides[get_db] = lambda: repo
        app.dependency_overrides[get_current_user] = lambda: admin_user

        # Create a broken audit service
        broken_audit = AuditService(repo)
        broken_audit._repo = type(
            "BrokenRepo",
            (),
            {
                "log_audit": staticmethod(
                    lambda *a, **kw: (_ for _ in ()).throw(RuntimeError("DB crash"))
                )
            },
        )()
        app.dependency_overrides[get_audit_service] = lambda: broken_audit

        client = TestClient(app)
        resp = client.post(
            "/api/v1/admin/users",
            json={"email": "still-works@test.com"},
        )
        # The user creation should still succeed
        assert resp.status_code == 200
