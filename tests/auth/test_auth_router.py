"""Tests for the auth API router."""

from __future__ import annotations

from unittest.mock import MagicMock

from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.api.deps import get_db
from src.api.routers.auth import router
from src.auth.jwt import create_access_token, create_refresh_token
from src.auth.passwords import hash_password
from src.database.models import UserRow


def _mock_user_row(**overrides):
    defaults = {
        "id": 1,
        "email": "test@example.com",
        "display_name": "Test User",
        "avatar_url": None,
        "auth_provider": "email",
        "provider_id": None,
        "password_hash": hash_password("validpass123"),
        "preferred_currency": "BRL",
        "is_active": 1,
    }
    defaults.update(overrides)
    row = MagicMock(spec=UserRow)
    for k, v in defaults.items():
        setattr(row, k, v)
    return row


def _make_app(mock_repo):
    app = FastAPI()
    app.include_router(router, prefix="/api/v1")
    app.dependency_overrides[get_db] = lambda: mock_repo
    return app


class TestRegister:
    def test_successful_registration(self):
        mock_repo = MagicMock()
        mock_repo.get_user_by_email.return_value = None
        mock_repo.create_user.return_value = _mock_user_row()

        client = TestClient(_make_app(mock_repo))
        resp = client.post(
            "/api/v1/auth/register",
            json={"email": "new@test.com", "password": "securepass8"},
        )
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"

    def test_duplicate_email_returns_409(self):
        mock_repo = MagicMock()
        mock_repo.get_user_by_email.return_value = _mock_user_row()

        client = TestClient(_make_app(mock_repo))
        resp = client.post(
            "/api/v1/auth/register",
            json={"email": "dup@test.com", "password": "securepass8"},
        )
        assert resp.status_code == 409

    def test_short_password_returns_422(self):
        mock_repo = MagicMock()
        client = TestClient(_make_app(mock_repo))
        resp = client.post(
            "/api/v1/auth/register",
            json={"email": "x@test.com", "password": "short"},
        )
        assert resp.status_code == 422

    def test_invalid_email_returns_422(self):
        mock_repo = MagicMock()
        client = TestClient(_make_app(mock_repo))
        resp = client.post(
            "/api/v1/auth/register",
            json={"email": "not-an-email", "password": "securepass8"},
        )
        assert resp.status_code == 422


class TestLogin:
    def test_successful_login(self):
        mock_repo = MagicMock()
        mock_repo.get_user_by_email.return_value = _mock_user_row()

        client = TestClient(_make_app(mock_repo))
        resp = client.post(
            "/api/v1/auth/login",
            json={"email": "test@example.com", "password": "validpass123"},
        )
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert "access_token" in data
        assert "refresh_token" in data

    def test_wrong_password_returns_401(self):
        mock_repo = MagicMock()
        mock_repo.get_user_by_email.return_value = _mock_user_row()

        client = TestClient(_make_app(mock_repo))
        resp = client.post(
            "/api/v1/auth/login",
            json={"email": "test@example.com", "password": "wrongpass123"},
        )
        assert resp.status_code == 401

    def test_nonexistent_user_returns_401(self):
        mock_repo = MagicMock()
        mock_repo.get_user_by_email.return_value = None

        client = TestClient(_make_app(mock_repo))
        resp = client.post(
            "/api/v1/auth/login",
            json={"email": "nobody@test.com", "password": "anything1"},
        )
        assert resp.status_code == 401

    def test_inactive_user_returns_401(self):
        mock_repo = MagicMock()
        mock_repo.get_user_by_email.return_value = _mock_user_row(is_active=0)

        client = TestClient(_make_app(mock_repo))
        resp = client.post(
            "/api/v1/auth/login",
            json={"email": "test@example.com", "password": "validpass123"},
        )
        assert resp.status_code == 401

    def test_sets_cookie(self):
        mock_repo = MagicMock()
        mock_repo.get_user_by_email.return_value = _mock_user_row()

        client = TestClient(_make_app(mock_repo))
        resp = client.post(
            "/api/v1/auth/login",
            json={"email": "test@example.com", "password": "validpass123"},
        )
        assert "access_token" in resp.cookies


class TestRefresh:
    def test_valid_refresh_token(self):
        mock_repo = MagicMock()
        mock_repo.get_user_by_id.return_value = _mock_user_row()

        client = TestClient(_make_app(mock_repo))
        refresh = create_refresh_token(user_id=1)
        resp = client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": refresh},
        )
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert "access_token" in data

    def test_invalid_refresh_token_returns_401(self):
        mock_repo = MagicMock()
        client = TestClient(_make_app(mock_repo))
        resp = client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": "bad.token.here"},
        )
        assert resp.status_code == 401

    def test_access_token_as_refresh_returns_401(self):
        mock_repo = MagicMock()
        client = TestClient(_make_app(mock_repo))
        access = create_access_token(user_id=1, email="x@y.com")
        resp = client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": access},
        )
        assert resp.status_code == 401


class TestLogout:
    def test_clears_cookie(self):
        mock_repo = MagicMock()
        client = TestClient(_make_app(mock_repo))
        resp = client.post("/api/v1/auth/logout")
        assert resp.status_code == 200


class TestGetMe:
    def test_returns_profile(self):
        mock_repo = MagicMock()
        mock_repo.get_user_by_id.return_value = _mock_user_row()

        client = TestClient(_make_app(mock_repo))
        token = create_access_token(user_id=1, email="test@example.com")
        resp = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["email"] == "test@example.com"
        assert data["display_name"] == "Test User"
        assert data["auth_provider"] == "email"

    def test_unauthenticated_returns_401(self):
        mock_repo = MagicMock()
        client = TestClient(_make_app(mock_repo))
        resp = client.get("/api/v1/auth/me")
        assert resp.status_code == 401


class TestUpdatePreferences:
    def test_set_pila_currency(self):
        mock_repo = MagicMock()
        mock_repo.get_user_by_id.return_value = _mock_user_row()
        mock_repo.update_user.return_value = _mock_user_row(preferred_currency="PILA")

        client = TestClient(_make_app(mock_repo))
        token = create_access_token(user_id=1, email="test@example.com")
        resp = client.patch(
            "/api/v1/auth/me/preferences",
            json={"preferred_currency": "PILA"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["preferred_currency"] == "PILA"
        mock_repo.update_user.assert_called_once_with(1, preferred_currency="PILA")

    def test_set_usd_currency(self):
        mock_repo = MagicMock()
        mock_repo.get_user_by_id.return_value = _mock_user_row()
        mock_repo.update_user.return_value = _mock_user_row(preferred_currency="USD")

        client = TestClient(_make_app(mock_repo))
        token = create_access_token(user_id=1, email="test@example.com")
        resp = client.patch(
            "/api/v1/auth/me/preferences",
            json={"preferred_currency": "USD"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["preferred_currency"] == "USD"

    def test_invalid_currency_returns_422(self):
        mock_repo = MagicMock()
        mock_repo.get_user_by_id.return_value = _mock_user_row()

        client = TestClient(_make_app(mock_repo))
        token = create_access_token(user_id=1, email="test@example.com")
        resp = client.patch(
            "/api/v1/auth/me/preferences",
            json={"preferred_currency": "EUR"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 422

    def test_unauthenticated_returns_401(self):
        mock_repo = MagicMock()
        client = TestClient(_make_app(mock_repo))
        resp = client.patch(
            "/api/v1/auth/me/preferences",
            json={"preferred_currency": "PILA"},
        )
        assert resp.status_code == 401

    def test_profile_includes_preferred_currency(self):
        mock_repo = MagicMock()
        mock_repo.get_user_by_id.return_value = _mock_user_row(preferred_currency="PILA")

        client = TestClient(_make_app(mock_repo))
        token = create_access_token(user_id=1, email="test@example.com")
        resp = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["preferred_currency"] == "PILA"


class TestOAuthRedirect:
    def test_unconfigured_provider_returns_501(self):
        mock_repo = MagicMock()
        client = TestClient(_make_app(mock_repo))
        resp = client.get("/api/v1/auth/google")
        assert resp.status_code == 501

    def test_unknown_provider_returns_400(self):
        mock_repo = MagicMock()
        client = TestClient(_make_app(mock_repo))
        resp = client.get("/api/v1/auth/github")
        assert resp.status_code == 400
