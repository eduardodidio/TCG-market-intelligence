"""Tests for the admin API router (F66-T01)."""

from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.api.deps import get_current_user, get_db, require_admin
from src.api.routers.admin import router
from src.api.routers.auth import router as auth_router
from src.credits.service import CreditService
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


@pytest.fixture()
def repo(tmp_path):
    db_path = tmp_path / "test_admin.db"
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
    """Create a FastAPI test app with admin router and admin user."""
    app = FastAPI()
    app.include_router(router, prefix="/api/v1")
    app.include_router(auth_router, prefix="/api/v1")
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
    """Create a FastAPI test app with admin router but non-admin user."""
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
    """App with NO auth override -- endpoints should return 401."""
    app = FastAPI()
    app.include_router(router, prefix="/api/v1")
    app.dependency_overrides[get_db] = lambda: repo
    return app


@pytest.fixture()
def noauth_client(noauth_app):
    return TestClient(noauth_app)


# --- require_admin unit tests ---


class TestRequireAdmin:
    def test_allows_admin_user(self):
        admin = _make_user(is_admin=True)
        result = require_admin(admin)
        assert result is admin

    def test_rejects_non_admin_user(self):
        from fastapi import HTTPException

        user = _make_user(is_admin=False)
        with pytest.raises(HTTPException) as exc_info:
            require_admin(user)
        assert exc_info.value.status_code == 403
        assert "Admin access required" in str(exc_info.value.detail)


# --- GET /admin/users ---


class TestListUsers:
    def test_returns_users_with_balances(self, admin_client, repo):
        # Create a second user with credits
        user2 = repo.create_user(email="user2@example.com", display_name="User 2")
        svc = CreditService(repo)
        svc.grant(user2.id, 25, "test_grant")

        resp = admin_client.get("/api/v1/admin/users")
        assert resp.status_code == 200
        body = resp.json()
        assert body["meta"]["total"] == 2
        users = body["data"]
        assert len(users) == 2

        # Find user2 in results
        u2 = next(u for u in users if u["email"] == "user2@example.com")
        assert u2["credit_balance"] == 25

    def test_users_without_credits_show_zero(self, admin_client, repo):
        # The admin user was created without credits
        resp = admin_client.get("/api/v1/admin/users")
        assert resp.status_code == 200
        users = resp.json()["data"]
        # All users should have credit_balance field
        for u in users:
            assert "credit_balance" in u
            assert isinstance(u["credit_balance"], int)

    def test_pagination(self, admin_client, repo):
        # Create extra users
        for i in range(5):
            repo.create_user(email=f"batch{i}@example.com")

        resp = admin_client.get("/api/v1/admin/users?limit=2&offset=0")
        assert resp.status_code == 200
        body = resp.json()
        assert len(body["data"]) == 2
        assert body["meta"]["total"] == 6  # 1 admin + 5 batch
        assert body["meta"]["offset"] == 0

        resp2 = admin_client.get("/api/v1/admin/users?limit=2&offset=2")
        assert resp2.status_code == 200
        assert len(resp2.json()["data"]) == 2

    def test_returns_403_for_non_admin(self, nonadmin_client):
        resp = nonadmin_client.get("/api/v1/admin/users")
        assert resp.status_code == 403

    def test_returns_401_for_unauthenticated(self, noauth_client):
        resp = noauth_client.get("/api/v1/admin/users")
        assert resp.status_code == 401


# --- PATCH /admin/users/{id}/credits ---


class TestAdjustCredits:
    def test_grant_credits(self, admin_client, repo):
        user = repo.create_user(email="target@example.com")
        repo.ensure_credit_balance(user.id)

        resp = admin_client.patch(
            f"/api/v1/admin/users/{user.id}/credits",
            json={"amount": 10, "reason": "test grant"},
        )
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["user_id"] == user.id
        assert data["new_balance"] == 10
        assert data["amount_applied"] == 10

    def test_revoke_credits(self, admin_client, repo):
        user = repo.create_user(email="target@example.com")
        svc = CreditService(repo)
        svc.grant(user.id, 20, "seed")

        resp = admin_client.patch(
            f"/api/v1/admin/users/{user.id}/credits",
            json={"amount": -5, "reason": "penalty"},
        )
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["new_balance"] == 15
        assert data["amount_applied"] == -5

    def test_revoke_clamped_to_zero(self, admin_client, repo):
        user = repo.create_user(email="target@example.com")
        svc = CreditService(repo)
        svc.grant(user.id, 3, "seed")

        resp = admin_client.patch(
            f"/api/v1/admin/users/{user.id}/credits",
            json={"amount": -999},
        )
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["new_balance"] == 0
        # amount_applied should reflect the actual clamped deduction (-3), not the requested (-999)
        assert data["amount_applied"] == -3

    def test_revoke_from_zero_balance(self, admin_client, repo):
        user = repo.create_user(email="target@example.com")
        repo.ensure_credit_balance(user.id)

        resp = admin_client.patch(
            f"/api/v1/admin/users/{user.id}/credits",
            json={"amount": -10},
        )
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["new_balance"] == 0
        # No deduction was possible, so amount_applied should be 0
        assert data["amount_applied"] == 0

    def test_nonexistent_user_returns_404(self, admin_client):
        resp = admin_client.patch(
            "/api/v1/admin/users/99999/credits",
            json={"amount": 10},
        )
        assert resp.status_code == 404

    def test_returns_403_for_non_admin(self, nonadmin_client):
        resp = nonadmin_client.patch(
            "/api/v1/admin/users/1/credits",
            json={"amount": 10},
        )
        assert resp.status_code == 403

    def test_returns_401_for_unauthenticated(self, noauth_client):
        resp = noauth_client.patch(
            "/api/v1/admin/users/1/credits",
            json={"amount": 10},
        )
        assert resp.status_code == 401

    def test_default_reason(self, admin_client, repo):
        user = repo.create_user(email="target@example.com")
        repo.ensure_credit_balance(user.id)

        resp = admin_client.patch(
            f"/api/v1/admin/users/{user.id}/credits",
            json={"amount": 5},
        )
        assert resp.status_code == 200
        # Verify transaction reason in DB
        txns = repo.get_credit_transactions(user.id)
        assert any(t.reason == "admin_adjust" for t in txns)


# --- GET /admin/dashboard ---


class TestAdminDashboard:
    def test_returns_stats(self, admin_client, repo):
        # Create extra user and some data
        user2 = repo.create_user(email="user2@example.com")
        svc = CreditService(repo)
        svc.grant(user2.id, 30, "seed")
        svc.deduct(user2.id, 5, "spend")

        resp = admin_client.get("/api/v1/admin/dashboard")
        assert resp.status_code == 200
        data = resp.json()["data"]

        assert data["total_users"] == 2
        assert data["active_users"] == 2
        assert data["total_credits_in_circulation"] == 25  # 30 - 5
        assert data["total_credits_granted"] == 30
        assert data["total_credits_spent"] == 5
        assert "total_collection_entries" in data
        assert "total_scans" in data
        assert "admin_users" in data

    def test_returns_403_for_non_admin(self, nonadmin_client):
        resp = nonadmin_client.get("/api/v1/admin/dashboard")
        assert resp.status_code == 403

    def test_returns_401_for_unauthenticated(self, noauth_client):
        resp = noauth_client.get("/api/v1/admin/dashboard")
        assert resp.status_code == 401


# --- /auth/me includes is_admin ---


class TestAuthMeIsAdmin:
    def test_me_includes_is_admin_true(self, admin_client):
        resp = admin_client.get("/api/v1/auth/me")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert "is_admin" in data
        assert data["is_admin"] is True

    def test_me_includes_is_admin_false(self, repo, regular_user):
        app = FastAPI()
        app.include_router(auth_router, prefix="/api/v1")
        app.dependency_overrides[get_db] = lambda: repo
        app.dependency_overrides[get_current_user] = lambda: regular_user
        repo.create_user(email=regular_user.email)

        client = TestClient(app)
        resp = client.get("/api/v1/auth/me")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert "is_admin" in data
        assert data["is_admin"] is False
