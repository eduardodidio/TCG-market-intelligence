"""Tests for the require_auth_or_api_key dependency."""

from __future__ import annotations

import os
from unittest.mock import MagicMock, patch

from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from src.api.deps import get_db, require_auth_or_api_key
from src.auth.jwt import create_access_token
from src.database.models import UserRow


def _mock_user_row(**overrides):
    defaults = {
        "id": 1,
        "email": "test@example.com",
        "display_name": "Test",
        "avatar_url": None,
        "auth_provider": "email",
        "provider_id": None,
        "password_hash": None,
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

    @app.get("/test")
    def test_endpoint(user_id: str = Depends(require_auth_or_api_key)):
        return {"user_id": user_id}

    return app


class TestDevMode:
    """No TCG_API_KEY set — dev mode allows everything."""

    def test_no_auth_returns_fallback(self):
        mock_repo = MagicMock()
        with patch.dict(os.environ, {}, clear=True):
            # Make sure TCG_API_KEY is not set
            os.environ.pop("TCG_API_KEY", None)
            client = TestClient(_make_app(mock_repo))
            resp = client.get("/test")
            assert resp.status_code == 200
            assert resp.json()["user_id"] == "api_key_user"


class TestJwtAuth:
    def test_valid_jwt_returns_user_id(self):
        mock_repo = MagicMock()
        mock_repo.get_user_by_id.return_value = _mock_user_row()

        client = TestClient(_make_app(mock_repo))
        token = create_access_token(user_id=1, email="test@example.com")
        resp = client.get("/test", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200
        assert resp.json()["user_id"] == "1"

    def test_invalid_jwt_without_api_key_returns_401(self):
        mock_repo = MagicMock()
        with patch.dict(os.environ, {"TCG_API_KEY": "secret"}):
            client = TestClient(_make_app(mock_repo))
            resp = client.get("/test", headers={"Authorization": "Bearer invalid"})
            assert resp.status_code == 401


class TestApiKeyAuth:
    def test_valid_api_key_returns_fallback(self):
        mock_repo = MagicMock()
        with patch.dict(os.environ, {"TCG_API_KEY": "mysecret"}):
            client = TestClient(_make_app(mock_repo))
            resp = client.get("/test", headers={"x-api-key": "mysecret"})
            assert resp.status_code == 200
            assert resp.json()["user_id"] == "api_key_user"

    def test_wrong_api_key_returns_401(self):
        mock_repo = MagicMock()
        with patch.dict(os.environ, {"TCG_API_KEY": "mysecret"}):
            client = TestClient(_make_app(mock_repo))
            resp = client.get("/test", headers={"x-api-key": "wrong"})
            assert resp.status_code == 401

    def test_no_auth_with_api_key_required_returns_401(self):
        mock_repo = MagicMock()
        with patch.dict(os.environ, {"TCG_API_KEY": "mysecret"}):
            client = TestClient(_make_app(mock_repo))
            resp = client.get("/test")
            assert resp.status_code == 401


class TestCombinedAuth:
    """JWT takes precedence over API key."""

    def test_jwt_preferred_over_api_key(self):
        mock_repo = MagicMock()
        mock_repo.get_user_by_id.return_value = _mock_user_row(id=42)

        with patch.dict(os.environ, {"TCG_API_KEY": "mysecret"}):
            client = TestClient(_make_app(mock_repo))
            token = create_access_token(user_id=42, email="x@y.com")
            resp = client.get(
                "/test",
                headers={
                    "Authorization": f"Bearer {token}",
                    "x-api-key": "mysecret",
                },
            )
            assert resp.status_code == 200
            assert resp.json()["user_id"] == "42"
