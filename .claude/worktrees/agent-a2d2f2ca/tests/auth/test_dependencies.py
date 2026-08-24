"""Tests for FastAPI auth dependencies."""

from __future__ import annotations

from unittest.mock import MagicMock

from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.api.deps import get_db
from src.auth.dependencies import get_current_user_id, get_optional_user
from src.auth.jwt import create_access_token
from src.database.models import UserRow


def _mock_user_row(**overrides):
    defaults = {
        "id": 1,
        "email": "test@example.com",
        "display_name": "Test User",
        "avatar_url": None,
        "auth_provider": "email",
        "provider_id": None,
        "password_hash": "$2b$hash",
        "is_active": 1,
    }
    defaults.update(overrides)
    row = MagicMock(spec=UserRow)
    for k, v in defaults.items():
        setattr(row, k, v)
    return row


def _make_app(mock_repo):
    app = FastAPI()
    app.dependency_overrides[get_db] = lambda: mock_repo

    @app.get("/test-auth")
    def test_auth(user_id: str = __import__("fastapi").Depends(get_current_user_id)):
        return {"user_id": user_id}

    @app.get("/test-optional")
    def test_optional(
        user=__import__("fastapi").Depends(get_optional_user),
    ):
        return {"user": user.email if user else None}

    return app


class TestGetCurrentUser:
    def test_valid_bearer_token(self):
        mock_repo = MagicMock()
        mock_repo.get_user_by_id.return_value = _mock_user_row()

        app = _make_app(mock_repo)
        client = TestClient(app)

        token = create_access_token(user_id=1, email="test@example.com")
        resp = client.get("/test-auth", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200
        assert resp.json()["user_id"] == "1"

    def test_missing_token_returns_401(self):
        mock_repo = MagicMock()
        app = _make_app(mock_repo)
        client = TestClient(app)

        resp = client.get("/test-auth")
        assert resp.status_code == 401

    def test_invalid_token_returns_401(self):
        mock_repo = MagicMock()
        app = _make_app(mock_repo)
        client = TestClient(app)

        resp = client.get("/test-auth", headers={"Authorization": "Bearer invalid.token.here"})
        assert resp.status_code == 401

    def test_user_not_found_returns_401(self):
        mock_repo = MagicMock()
        mock_repo.get_user_by_id.return_value = None

        app = _make_app(mock_repo)
        client = TestClient(app)

        token = create_access_token(user_id=999, email="gone@test.com")
        resp = client.get("/test-auth", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 401

    def test_inactive_user_returns_401(self):
        mock_repo = MagicMock()
        mock_repo.get_user_by_id.return_value = _mock_user_row(is_active=0)

        app = _make_app(mock_repo)
        client = TestClient(app)

        token = create_access_token(user_id=1, email="test@example.com")
        resp = client.get("/test-auth", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 401

    def test_cookie_based_auth(self):
        mock_repo = MagicMock()
        mock_repo.get_user_by_id.return_value = _mock_user_row()

        app = _make_app(mock_repo)
        client = TestClient(app)

        token = create_access_token(user_id=1, email="test@example.com")
        client.cookies.set("access_token", token)
        resp = client.get("/test-auth")
        assert resp.status_code == 200


class TestGetOptionalUser:
    def test_returns_none_without_token(self):
        mock_repo = MagicMock()
        app = _make_app(mock_repo)
        client = TestClient(app)

        resp = client.get("/test-optional")
        assert resp.status_code == 200
        assert resp.json()["user"] is None

    def test_returns_user_with_valid_token(self):
        mock_repo = MagicMock()
        mock_repo.get_user_by_id.return_value = _mock_user_row()

        app = _make_app(mock_repo)
        client = TestClient(app)

        token = create_access_token(user_id=1, email="test@example.com")
        resp = client.get("/test-optional", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200
        assert resp.json()["user"] == "test@example.com"

    def test_returns_none_with_invalid_token(self):
        mock_repo = MagicMock()
        app = _make_app(mock_repo)
        client = TestClient(app)

        resp = client.get("/test-optional", headers={"Authorization": "Bearer bad"})
        assert resp.status_code == 200
        assert resp.json()["user"] is None
