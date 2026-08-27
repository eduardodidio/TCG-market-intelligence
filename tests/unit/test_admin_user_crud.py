"""Tests for admin user CRUD endpoints (F74)."""

from __future__ import annotations

from datetime import datetime
from unittest.mock import MagicMock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.api.deps import get_db, require_admin
from src.api.routers.admin import router
from src.auth.passwords import hash_password
from src.database.models import UserRow
from src.domain.models import User


def _admin_user(**overrides) -> User:
    defaults = dict(
        id=1,
        email="admin@test.com",
        display_name="Admin",
        is_active=True,
        is_admin=True,
    )
    defaults.update(overrides)
    return User(**defaults)


def _mock_user_row(**overrides):
    defaults = {
        "id": 2,
        "email": "new@test.com",
        "display_name": "New User",
        "avatar_url": None,
        "auth_provider": "email",
        "provider_id": None,
        "password_hash": hash_password("temppass123"),
        "password_expires_at": datetime.now(),
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


def _make_app(mock_repo, admin=None):
    app = FastAPI()
    app.include_router(router, prefix="/api/v1")
    app.dependency_overrides[get_db] = lambda: mock_repo
    if admin:
        app.dependency_overrides[require_admin] = lambda: admin
    return app


class TestCreateUser:
    def test_creates_user_with_temp_password(self):
        mock_repo = MagicMock()
        mock_repo.get_user_by_email.return_value = None
        created_row = _mock_user_row()
        mock_repo.create_user.return_value = created_row
        mock_repo.update_user.return_value = created_row

        admin = _admin_user()
        client = TestClient(_make_app(mock_repo, admin))

        with patch("src.api.routers.admin.CreditService") as MockCreditSvc:
            mock_svc = MockCreditSvc.return_value
            resp = client.post(
                "/api/v1/admin/users",
                json={"email": "new@test.com", "display_name": "New User"},
            )

        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["user_id"] == 2
        assert data["email"] == "new@test.com"
        assert "temporary_password" in data
        assert len(data["temporary_password"]) > 8

        # Verify create_user was called
        mock_repo.create_user.assert_called_once()
        # Verify password_expires_at was set
        mock_repo.update_user.assert_called_once()
        call_kwargs = mock_repo.update_user.call_args
        assert "password_expires_at" in call_kwargs.kwargs

        # Verify credits were granted
        mock_svc.grant.assert_called_once()

    def test_duplicate_email_returns_409(self):
        mock_repo = MagicMock()
        mock_repo.get_user_by_email.return_value = _mock_user_row()

        admin = _admin_user()
        client = TestClient(_make_app(mock_repo, admin))
        resp = client.post(
            "/api/v1/admin/users",
            json={"email": "dup@test.com"},
        )
        assert resp.status_code == 409

    def test_non_admin_gets_403(self):
        mock_repo = MagicMock()
        app = FastAPI()
        app.include_router(router, prefix="/api/v1")
        app.dependency_overrides[get_db] = lambda: mock_repo
        # Don't override require_admin — it will check the real user
        # Instead, make require_admin raise 403
        from fastapi import HTTPException

        def fake_require_admin():
            raise HTTPException(status_code=403, detail="Admin access required")

        app.dependency_overrides[require_admin] = fake_require_admin
        client = TestClient(app)
        resp = client.post(
            "/api/v1/admin/users",
            json={"email": "x@test.com"},
        )
        assert resp.status_code == 403


class TestDeleteUser:
    def test_soft_deletes_user(self):
        mock_repo = MagicMock()
        mock_repo.get_user_by_id.return_value = _mock_user_row(id=5)
        mock_repo.update_user.return_value = _mock_user_row(id=5, is_active=0)

        admin = _admin_user(id=1)
        client = TestClient(_make_app(mock_repo, admin))
        resp = client.delete("/api/v1/admin/users/5")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["user_id"] == 5
        assert data["deleted"] is True

        mock_repo.update_user.assert_called_once_with(5, is_active=0)

    def test_cannot_delete_self(self):
        mock_repo = MagicMock()
        admin = _admin_user(id=1)
        client = TestClient(_make_app(mock_repo, admin))
        resp = client.delete("/api/v1/admin/users/1")
        assert resp.status_code == 400
        assert "yourself" in resp.json()["detail"].lower()

    def test_delete_nonexistent_returns_404(self):
        mock_repo = MagicMock()
        mock_repo.get_user_by_id.return_value = None

        admin = _admin_user(id=1)
        client = TestClient(_make_app(mock_repo, admin))
        resp = client.delete("/api/v1/admin/users/999")
        assert resp.status_code == 404
