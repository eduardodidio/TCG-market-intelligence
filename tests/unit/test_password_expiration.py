"""Tests for password expiration and change-password flow (F74)."""

from __future__ import annotations

from datetime import datetime, timedelta
from unittest.mock import MagicMock

from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.api.deps import get_db
from src.api.routers.auth import router
from src.auth.jwt import create_access_token
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
        "password_expires_at": None,
        "preferred_currency": "BRL",
        "preferred_language": "en",
        "is_active": 1,
        "is_admin": 0,
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


class TestLoginPasswordExpiration:
    def test_login_with_expired_password_returns_flag(self):
        """Login with expired password returns password_expired=True and short token."""
        mock_repo = MagicMock()
        user = _mock_user_row(
            password_expires_at=datetime.now() - timedelta(hours=1),
        )
        mock_repo.get_user_by_email.return_value = user

        client = TestClient(_make_app(mock_repo))
        resp = client.post(
            "/api/v1/auth/login",
            json={"email": "test@example.com", "password": "validpass123"},
        )
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["password_expired"] is True
        assert data["access_token"] is not None
        assert data["refresh_token"] is None

    def test_login_with_non_expired_password_works_normally(self):
        """Login with no expiration or future expiration works normally."""
        mock_repo = MagicMock()
        user = _mock_user_row(password_expires_at=None)
        mock_repo.get_user_by_email.return_value = user

        client = TestClient(_make_app(mock_repo))
        resp = client.post(
            "/api/v1/auth/login",
            json={"email": "test@example.com", "password": "validpass123"},
        )
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert "password_expired" not in data
        assert data["access_token"] is not None
        assert data["refresh_token"] is not None

    def test_login_with_future_expiration_works_normally(self):
        """Password with future expiration date is not considered expired."""
        mock_repo = MagicMock()
        user = _mock_user_row(
            password_expires_at=datetime.now() + timedelta(days=30),
        )
        mock_repo.get_user_by_email.return_value = user

        client = TestClient(_make_app(mock_repo))
        resp = client.post(
            "/api/v1/auth/login",
            json={"email": "test@example.com", "password": "validpass123"},
        )
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert "password_expired" not in data


class TestChangePassword:
    def _auth_client(self, mock_repo, user_row):
        """Create a TestClient with auth token for the given user."""
        mock_repo.get_user_by_id.return_value = user_row
        app = _make_app(mock_repo)
        client = TestClient(app)
        token = create_access_token(user_row.id, user_row.email, expires_minutes=5)
        return client, token

    def test_change_password_success(self):
        mock_repo = MagicMock()
        user = _mock_user_row(
            password_expires_at=datetime.now() - timedelta(hours=1),
        )
        client, token = self._auth_client(mock_repo, user)
        mock_repo.update_user.return_value = user

        resp = client.post(
            "/api/v1/auth/change-password",
            json={
                "current_password": "validpass123",
                "new_password": "newstrongpass8",
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["access_token"] is not None
        assert data["refresh_token"] is not None

        # Verify update_user was called to clear expiration
        mock_repo.update_user.assert_called_once()
        call_kwargs = mock_repo.update_user.call_args.kwargs
        assert call_kwargs["password_expires_at"] is None

    def test_change_password_wrong_current(self):
        mock_repo = MagicMock()
        user = _mock_user_row()
        client, token = self._auth_client(mock_repo, user)

        resp = client.post(
            "/api/v1/auth/change-password",
            json={
                "current_password": "wrongpassword",
                "new_password": "newstrongpass8",
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 400
        assert "incorrect" in resp.json()["detail"].lower()

    def test_change_password_too_short(self):
        mock_repo = MagicMock()
        user = _mock_user_row()
        client, token = self._auth_client(mock_repo, user)

        resp = client.post(
            "/api/v1/auth/change-password",
            json={
                "current_password": "validpass123",
                "new_password": "short",
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 422

    def test_change_password_no_auth(self):
        mock_repo = MagicMock()
        client = TestClient(_make_app(mock_repo))

        resp = client.post(
            "/api/v1/auth/change-password",
            json={
                "current_password": "validpass123",
                "new_password": "newstrongpass8",
            },
        )
        assert resp.status_code == 401


class TestGetMePasswordExpiration:
    def test_me_shows_must_change_password(self):
        mock_repo = MagicMock()
        user = _mock_user_row(
            password_expires_at=datetime.now() - timedelta(hours=1),
        )
        mock_repo.get_user_by_id.return_value = user

        app = _make_app(mock_repo)
        client = TestClient(app)
        token = create_access_token(user.id, user.email)

        resp = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["must_change_password"] is True

    def test_me_no_password_expiration(self):
        mock_repo = MagicMock()
        user = _mock_user_row(password_expires_at=None)
        mock_repo.get_user_by_id.return_value = user

        app = _make_app(mock_repo)
        client = TestClient(app)
        token = create_access_token(user.id, user.email)

        resp = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["must_change_password"] is False
