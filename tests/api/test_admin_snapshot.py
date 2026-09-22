"""Tests for POST /admin/jobs/snapshot-prices endpoint (F168-T02)."""

from __future__ import annotations

from unittest.mock import patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.api.deps import get_current_user, get_db
from src.api.routers.admin import router
from src.database.repository import Repository
from src.domain.models import User


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
    db_path = tmp_path / "test_admin_snapshot.db"
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
    """App with no user override -- simulates unauthenticated access."""
    app = FastAPI()
    app.include_router(router, prefix="/api/v1")
    app.dependency_overrides[get_db] = lambda: repo
    # Do NOT override get_current_user -> require_admin will raise 401
    return app


@pytest.fixture()
def noauth_client(noauth_app):
    return TestClient(noauth_app)


def test_admin_snapshot_returns_count(admin_client):
    """POST as admin returns 200 with observations_created count."""
    with patch("src.collectors.price_snapshot.run_daily_snapshot", return_value=123):
        resp = admin_client.post("/api/v1/admin/jobs/snapshot-prices")

    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["observations_created"] == 123


def test_admin_snapshot_zero_observations(admin_client):
    """POST returns 200 with observations_created=0 when idempotent."""
    with patch("src.collectors.price_snapshot.run_daily_snapshot", return_value=0):
        resp = admin_client.post("/api/v1/admin/jobs/snapshot-prices")

    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["observations_created"] == 0


def test_nonadmin_rejected(nonadmin_client):
    """Non-admin user gets 403."""
    resp = nonadmin_client.post("/api/v1/admin/jobs/snapshot-prices")
    assert resp.status_code == 403


def test_noauth_rejected(noauth_client):
    """Unauthenticated request gets 401."""
    resp = noauth_client.post("/api/v1/admin/jobs/snapshot-prices")
    assert resp.status_code == 401
