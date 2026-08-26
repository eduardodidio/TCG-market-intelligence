"""Tests for the credits API router (F65-T03)."""

from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.api.deps import get_current_user, get_db
from src.api.routers.credits import router
from src.credits.constants import BONUS_AMOUNT
from src.database.repository import Repository
from src.domain.models import User


def _make_user(user_id: int = 1, is_admin: bool = False) -> User:
    return User(
        id=user_id,
        email="test@example.com",
        display_name="Test User",
        auth_provider="email",
        is_active=True,
        is_admin=is_admin,
    )


@pytest.fixture()
def repo(tmp_path):
    db_path = tmp_path / "test_credits.db"
    db_url = f"sqlite:///{db_path}"
    return Repository(db_url=db_url)


@pytest.fixture()
def test_app(repo):
    """Create a FastAPI test app with credits router and auth override."""
    user = _make_user()

    app = FastAPI()
    app.include_router(router, prefix="/api/v1")
    app.dependency_overrides[get_db] = lambda: repo
    app.dependency_overrides[get_current_user] = lambda: user

    # Create user in DB so credit operations work
    repo.create_user(email=user.email, display_name=user.display_name)

    return app


@pytest.fixture()
def client(test_app):
    return TestClient(test_app)


@pytest.fixture()
def admin_app(repo):
    """Create a FastAPI test app with admin user."""
    admin = _make_user(is_admin=True)

    app = FastAPI()
    app.include_router(router, prefix="/api/v1")
    app.dependency_overrides[get_db] = lambda: repo
    app.dependency_overrides[get_current_user] = lambda: admin

    repo.create_user(email=admin.email, display_name=admin.display_name)

    return app


@pytest.fixture()
def admin_client(admin_app):
    return TestClient(admin_app)


@pytest.fixture()
def noauth_app(repo):
    """App with NO auth override — endpoints should return 401."""
    app = FastAPI()
    app.include_router(router, prefix="/api/v1")
    app.dependency_overrides[get_db] = lambda: repo
    return app


@pytest.fixture()
def noauth_client(noauth_app):
    return TestClient(noauth_app)


# --- GET /credits/balance ---


class TestGetBalance:
    def test_returns_zero_for_new_user(self, client):
        resp = client.get("/api/v1/credits/balance")
        assert resp.status_code == 200
        data = resp.json()
        assert data["balance"] == 0
        assert data["is_admin"] is False

    def test_returns_is_admin_true_for_admin(self, admin_client):
        resp = admin_client.get("/api/v1/credits/balance")
        assert resp.status_code == 200
        data = resp.json()
        assert data["is_admin"] is True

    def test_includes_bonus_eligibility_fields(self, client):
        resp = client.get("/api/v1/credits/balance")
        assert resp.status_code == 200
        data = resp.json()
        assert "bonus_eligible" in data
        assert "next_bonus_at" in data
        assert "bonus_amount" in data
        assert "last_bonus_at" in data
        # New user should be eligible
        assert data["bonus_eligible"] is True
        assert data["bonus_amount"] == BONUS_AMOUNT

    def test_requires_auth(self, noauth_client):
        resp = noauth_client.get("/api/v1/credits/balance")
        assert resp.status_code in (401, 422)


# --- GET /credits/history ---


class TestGetHistory:
    def test_returns_empty_for_new_user(self, client):
        resp = client.get("/api/v1/credits/history")
        assert resp.status_code == 200
        data = resp.json()
        assert data["transactions"] == []

    def test_returns_transactions_after_bonus(self, client, repo):
        # Claim bonus to create a transaction
        client.post("/api/v1/credits/claim-bonus")
        resp = client.get("/api/v1/credits/history")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["transactions"]) > 0
        tx = data["transactions"][0]
        assert tx["amount"] == BONUS_AMOUNT
        assert tx["reason"] == "bonus_claim"
        assert "id" in tx
        assert "created_at" in tx

    def test_respects_limit_param(self, client, repo):
        # Create multiple transactions
        from src.credits.service import CreditService

        svc = CreditService(repo)
        for i in range(5):
            svc.grant(1, 1, f"test_grant_{i}")

        resp = client.get("/api/v1/credits/history?limit=2")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["transactions"]) == 2

    def test_respects_offset_param(self, client, repo):
        from src.credits.service import CreditService

        svc = CreditService(repo)
        for i in range(5):
            svc.grant(1, 1, f"test_grant_{i}")

        # Get all
        resp_all = client.get("/api/v1/credits/history?limit=100")
        all_txs = resp_all.json()["transactions"]

        # Get with offset
        resp_offset = client.get("/api/v1/credits/history?limit=100&offset=2")
        offset_txs = resp_offset.json()["transactions"]

        assert len(offset_txs) == len(all_txs) - 2
        assert offset_txs[0]["id"] == all_txs[2]["id"]

    def test_requires_auth(self, noauth_client):
        resp = noauth_client.get("/api/v1/credits/history")
        assert resp.status_code in (401, 422)


# --- POST /credits/claim-bonus ---


class TestClaimBonus:
    def test_grants_bonus_credits(self, client):
        resp = client.post("/api/v1/credits/claim-bonus")
        assert resp.status_code == 200
        data = resp.json()
        assert data["balance"] == BONUS_AMOUNT
        assert data["credited"] == BONUS_AMOUNT

    def test_second_claim_within_interval_returns_429(self, client):
        # First claim succeeds
        resp1 = client.post("/api/v1/credits/claim-bonus")
        assert resp1.status_code == 200

        # Second claim within 12h fails
        resp2 = client.post("/api/v1/credits/claim-bonus")
        assert resp2.status_code == 429

    def test_429_detail_has_bonus_not_ready(self, client):
        client.post("/api/v1/credits/claim-bonus")
        resp = client.post("/api/v1/credits/claim-bonus")
        assert resp.status_code == 429
        # The exception handler wraps detail — check the error structure
        body = resp.json()
        # FastAPI wraps HTTPException detail into the response
        # With the custom exception handler it may be in errors[0].message
        # or directly in "detail"
        detail = body.get("detail", body.get("errors", [{}])[0].get("message"))
        if isinstance(detail, dict):
            assert detail["code"] == "BONUS_NOT_READY"
            assert "next_eligible_at" in detail
        elif isinstance(detail, str):
            assert "BONUS_NOT_READY" in detail

    def test_requires_auth(self, noauth_client):
        resp = noauth_client.post("/api/v1/credits/claim-bonus")
        assert resp.status_code in (401, 422)
