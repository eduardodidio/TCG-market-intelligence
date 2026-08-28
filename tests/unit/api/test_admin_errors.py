"""Tests for admin error log API endpoints (F85-T04)."""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime, timedelta

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.api.deps import get_current_user, get_db
from src.api.routers.admin import router
from src.database.repository import Repository
from src.domain.models import User


def _make_user(user_id: int = 1, is_admin: bool = False, email: str = "user@example.com") -> User:
    return User(
        id=user_id,
        email=email,
        display_name="Test User",
        auth_provider="email",
        is_active=True,
        is_admin=is_admin,
    )


def _make_error_row(
    *,
    error_id: str | None = None,
    level: str = "ERROR",
    error_type: str = "ValueError",
    message: str = "something went wrong",
    module: str | None = "src.api.routers.collection",
    function: str | None = "list_collection",
    line: int | None = 42,
    traceback: str | None = "Traceback (most recent call last):\n  ...",
    request_method: str | None = "GET",
    request_path: str | None = "/api/v1/collection",
    request_user_id: int | None = 1,
    request_id: str | None = None,
    request_params: str | None = None,
    extra: str | None = None,
    timestamp: datetime | None = None,
) -> dict:
    return {
        "id": error_id or str(uuid.uuid4()),
        "timestamp": timestamp or datetime.now(UTC),
        "level": level,
        "error_type": error_type,
        "message": message,
        "module": module,
        "function": function,
        "line": line,
        "traceback": traceback,
        "request_method": request_method,
        "request_path": request_path,
        "request_user_id": request_user_id,
        "request_id": request_id or str(uuid.uuid4()),
        "request_params": request_params,
        "extra": extra,
    }


@pytest.fixture()
def repo(tmp_path):
    db_path = tmp_path / "test_admin_errors.db"
    db_url = f"sqlite:///{db_path}"
    return Repository(db_url=db_url)


@pytest.fixture()
def admin_user():
    return _make_user(user_id=1, is_admin=True, email="admin@example.com")


@pytest.fixture()
def regular_user():
    return _make_user(user_id=2, is_admin=False, email="user@example.com")


@pytest.fixture()
def admin_app(repo, admin_user):
    app = FastAPI()
    app.include_router(router, prefix="/api/v1")
    app.dependency_overrides[get_db] = lambda: repo
    app.dependency_overrides[get_current_user] = lambda: admin_user
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


@pytest.fixture()
def noauth_app(repo):
    app = FastAPI()
    app.include_router(router, prefix="/api/v1")
    app.dependency_overrides[get_db] = lambda: repo
    return app


@pytest.fixture()
def noauth_client(noauth_app):
    return TestClient(noauth_app)


# ── GET /admin/errors ────────────────────────────────────────────


class TestListErrors:
    def test_happy_path(self, admin_client, repo):
        """List errors returns correct data shape."""
        row = _make_error_row(level="ERROR", message="test error")
        repo.insert_error_log(row)

        resp = admin_client.get("/api/v1/admin/errors")
        assert resp.status_code == 200
        body = resp.json()
        assert body["meta"]["total"] == 1
        assert len(body["data"]) == 1

        entry = body["data"][0]
        assert entry["id"] == row["id"]
        assert entry["level"] == "ERROR"
        assert entry["error_type"] == "ValueError"
        assert entry["message"] == "test error"
        assert entry["module"] == "src.api.routers.collection"
        assert entry["function"] == "list_collection"

    def test_pagination(self, admin_client, repo):
        """Verify limit/offset/total in response."""
        for i in range(5):
            repo.insert_error_log(
                _make_error_row(
                    message=f"error {i}",
                    timestamp=datetime.now(UTC) - timedelta(seconds=5 - i),
                )
            )

        resp = admin_client.get("/api/v1/admin/errors?limit=2&offset=0")
        assert resp.status_code == 200
        body = resp.json()
        assert len(body["data"]) == 2
        assert body["meta"]["total"] == 5
        assert body["meta"]["offset"] == 0

        resp2 = admin_client.get("/api/v1/admin/errors?limit=2&offset=2")
        assert resp2.status_code == 200
        body2 = resp2.json()
        assert len(body2["data"]) == 2
        assert body2["meta"]["offset"] == 2

    def test_filter_by_level(self, admin_client, repo):
        """level=CRITICAL returns only critical errors."""
        repo.insert_error_log(_make_error_row(level="ERROR", message="err"))
        repo.insert_error_log(_make_error_row(level="CRITICAL", message="crit"))
        repo.insert_error_log(_make_error_row(level="WARNING", message="warn"))

        resp = admin_client.get("/api/v1/admin/errors?level=CRITICAL")
        assert resp.status_code == 200
        body = resp.json()
        assert body["meta"]["total"] == 1
        assert len(body["data"]) == 1
        assert body["data"][0]["level"] == "CRITICAL"
        assert body["data"][0]["message"] == "crit"

    def test_filter_by_module(self, admin_client, repo):
        """module filter uses contains matching."""
        repo.insert_error_log(_make_error_row(module="src.api.routers.collection"))
        repo.insert_error_log(_make_error_row(module="src.collectors.scan"))
        repo.insert_error_log(_make_error_row(module="src.api.routers.admin"))

        resp = admin_client.get("/api/v1/admin/errors?module=api.routers")
        assert resp.status_code == 200
        body = resp.json()
        assert body["meta"]["total"] == 2

    def test_empty_list(self, admin_client):
        """No errors returns empty list with total 0."""
        resp = admin_client.get("/api/v1/admin/errors")
        assert resp.status_code == 200
        body = resp.json()
        assert body["data"] == []
        assert body["meta"]["total"] == 0

    def test_returns_403_for_non_admin(self, nonadmin_client):
        resp = nonadmin_client.get("/api/v1/admin/errors")
        assert resp.status_code == 403

    def test_returns_401_for_unauthenticated(self, noauth_client):
        resp = noauth_client.get("/api/v1/admin/errors")
        assert resp.status_code == 401


# ── GET /admin/errors/{error_id} ─────────────────────────────────


class TestGetError:
    def test_detail_view(self, admin_client, repo):
        """Get single error includes traceback and request context."""
        params = json.dumps({"page": 1, "limit": 50})
        extra = json.dumps({"retry_count": 3})
        row = _make_error_row(
            traceback="Traceback:\n  File ...\nValueError: bad",
            request_method="GET",
            request_path="/api/v1/collection",
            request_user_id=42,
            request_params=params,
            extra=extra,
            line=99,
        )
        repo.insert_error_log(row)

        resp = admin_client.get(f"/api/v1/admin/errors/{row['id']}")
        assert resp.status_code == 200
        data = resp.json()["data"]

        assert data["id"] == row["id"]
        assert data["traceback"] == "Traceback:\n  File ...\nValueError: bad"
        assert data["line"] == 99
        assert data["request_method"] == "GET"
        assert data["request_path"] == "/api/v1/collection"
        assert data["request_user_id"] == 42
        # JSON strings should be parsed into dicts
        assert data["request_params"] == {"page": 1, "limit": 50}
        assert data["extra"] == {"retry_count": 3}

    def test_detail_null_json_fields(self, admin_client, repo):
        """Detail with null request_params and extra returns None."""
        row = _make_error_row(request_params=None, extra=None)
        repo.insert_error_log(row)

        resp = admin_client.get(f"/api/v1/admin/errors/{row['id']}")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["request_params"] is None
        assert data["extra"] is None

    def test_detail_invalid_json_fields(self, admin_client, repo):
        """Invalid JSON in request_params/extra results in None."""
        row = _make_error_row(request_params="not-json{{", extra="also-bad")
        repo.insert_error_log(row)

        resp = admin_client.get(f"/api/v1/admin/errors/{row['id']}")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["request_params"] is None
        assert data["extra"] is None

    def test_404_unknown_id(self, admin_client):
        """Unknown error_id returns 404."""
        resp = admin_client.get("/api/v1/admin/errors/nonexistent-id")
        assert resp.status_code == 404

    def test_returns_403_for_non_admin(self, nonadmin_client):
        resp = nonadmin_client.get("/api/v1/admin/errors/some-id")
        assert resp.status_code == 403

    def test_returns_401_for_unauthenticated(self, noauth_client):
        resp = noauth_client.get("/api/v1/admin/errors/some-id")
        assert resp.status_code == 401
