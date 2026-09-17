"""Tests for the price request queue endpoints (F130-T05).

Tests the queue-based refresh-price flow, price-request-status endpoint,
and admin price-request management endpoints.
"""

from __future__ import annotations

from datetime import datetime
from unittest.mock import MagicMock

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from src.api.deps import (
    get_credit_service,
    get_currency_converter_dep,
    get_current_user,
    get_db,
    get_optional_user,
)
from src.api.routers.admin import router as admin_router
from src.api.routers.cards import router as cards_router
from src.credits.service import CreditService
from src.database.models import Base, CardRow, PriceUpdateRequestRow
from src.database.repository import Repository
from src.domain.models import User

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_user(user_id: int = 1, is_admin: bool = False, email: str = "user@test.com") -> User:
    return User(
        id=user_id,
        email=email,
        display_name="Test User",
        auth_provider="email",
        is_active=True,
        is_admin=is_admin,
    )


def _make_repo():
    """Create an in-memory SQLite repo with StaticPool for TestClient compat."""
    from sqlalchemy.pool import StaticPool

    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    repo = Repository.__new__(Repository)
    repo.engine = engine
    return repo


def _seed_card(repo: Repository, card_id: int = 1, name: str = "Lightning Bolt") -> CardRow:
    """Insert a card into the repo and return it."""
    with Session(repo.engine) as session:
        card = CardRow(
            game="magic",
            name_en=name,
            name_pt=None,
            set_code="m10",
            collector_number="146",
        )
        session.add(card)
        session.commit()
        session.refresh(card)
        # Detach so we can use it outside the session
        card_id_val = card.id
    return repo.get_card_by_id(card_id_val)


def _seed_price_request(repo: Repository, card_id: int, user_id: int, status: str = "pending"):
    """Insert a PriceUpdateRequestRow directly."""
    with Session(repo.engine) as session:
        row = PriceUpdateRequestRow(
            card_id=card_id,
            user_id=user_id,
            status=status,
            requested_at=datetime.now(),
        )
        session.add(row)
        session.commit()
        session.refresh(row)
        return row.id


def _make_cards_app(repo, user, credit_balance: int = 100):
    """Build a FastAPI test app with cards router and mocked deps."""
    app = FastAPI()
    app.include_router(cards_router, prefix="/api/v1")

    def override_db():
        yield repo

    app.dependency_overrides[get_db] = override_db

    mock_converter = MagicMock()
    mock_converter.convert = lambda price, dt, curr: price
    app.dependency_overrides[get_currency_converter_dep] = lambda: mock_converter

    if user is not None:
        app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_optional_user] = lambda: user

    mock_credit_svc = MagicMock(spec=CreditService)
    mock_credit_svc.check_sufficient.return_value = credit_balance > 0
    app.dependency_overrides[get_credit_service] = lambda: mock_credit_svc

    return app, mock_credit_svc


def _make_admin_app(repo, admin_user):
    """Build a FastAPI test app with admin router and admin user."""
    app = FastAPI()
    app.include_router(admin_router, prefix="/api/v1")

    def override_db():
        yield repo

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_current_user] = lambda: admin_user

    return app


# ---------------------------------------------------------------------------
# Tests: refresh-price (queued)
# ---------------------------------------------------------------------------


class TestRefreshCardPriceQueued:
    """Tests for POST /api/v1/cards/{card_id}/refresh-price (queue-based)."""

    def test_refresh_returns_queued_status(self):
        """Endpoint returns status='queued' with a request_id."""
        repo = _make_repo()
        card = _seed_card(repo)
        user = _make_user()
        app, _ = _make_cards_app(repo, user)
        client = TestClient(app)

        resp = client.post(f"/api/v1/cards/{card.id}/refresh-price")
        assert resp.status_code == 200
        body = resp.json()
        assert body["data"]["status"] == "queued"
        assert "request_id" in body["data"]
        assert body["data"]["card_id"] == card.id
        assert "message" in body["data"]

    def test_credit_deducted_at_request_time(self):
        """Credit is deducted immediately when the request is queued."""
        repo = _make_repo()
        card = _seed_card(repo)
        user = _make_user()
        app, credit_svc = _make_cards_app(repo, user)
        client = TestClient(app)

        resp = client.post(f"/api/v1/cards/{card.id}/refresh-price")
        assert resp.status_code == 200

        # Credit deduction should have been called
        credit_svc.deduct.assert_called_once()
        call_args = credit_svc.deduct.call_args
        assert call_args[0][0] == user.id  # user_id

    def test_refresh_insufficient_credits(self):
        """Return 402 when user has insufficient credits."""
        repo = _make_repo()
        card = _seed_card(repo)
        user = _make_user()
        app, _ = _make_cards_app(repo, user, credit_balance=0)
        client = TestClient(app)

        resp = client.post(f"/api/v1/cards/{card.id}/refresh-price")
        assert resp.status_code == 402

    def test_refresh_card_not_found(self):
        """Return 404 when card doesn't exist."""
        repo = _make_repo()
        user = _make_user()
        app, _ = _make_cards_app(repo, user)
        client = TestClient(app)

        resp = client.post("/api/v1/cards/999/refresh-price")
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Tests: price-request-status
# ---------------------------------------------------------------------------


class TestPriceRequestStatus:
    """Tests for GET /api/v1/cards/{card_id}/price-request-status."""

    def test_status_returns_existing_request(self):
        """Returns correct status for an existing price request."""
        repo = _make_repo()
        card = _seed_card(repo)
        user = _make_user()
        _seed_price_request(repo, card.id, user.id, status="completed")

        app, _ = _make_cards_app(repo, user)
        client = TestClient(app)

        resp = client.get(f"/api/v1/cards/{card.id}/price-request-status")
        assert resp.status_code == 200
        body = resp.json()
        assert body["data"]["status"] == "completed"
        assert "requested_at" in body["data"]

    def test_status_returns_none_for_no_request(self):
        """Returns status='none' when no request exists for the card."""
        repo = _make_repo()
        card = _seed_card(repo)
        user = _make_user()

        app, _ = _make_cards_app(repo, user)
        client = TestClient(app)

        resp = client.get(f"/api/v1/cards/{card.id}/price-request-status")
        assert resp.status_code == 200
        body = resp.json()
        assert body["data"]["status"] == "none"


# ---------------------------------------------------------------------------
# Tests: admin price-request endpoints
# ---------------------------------------------------------------------------


class TestAdminPriceRequests:
    """Tests for admin price request management endpoints."""

    def test_list_price_requests(self):
        """Admin can list price requests."""
        repo = _make_repo()
        card = _seed_card(repo)
        admin = _make_user(user_id=1, is_admin=True, email="admin@test.com")
        _seed_price_request(repo, card.id, user_id=2, status="pending")

        app = _make_admin_app(repo, admin)
        client = TestClient(app)

        resp = client.get("/api/v1/admin/price-requests")
        assert resp.status_code == 200
        body = resp.json()
        assert "items" in body["data"]
        assert body["data"]["total"] >= 1
        item = body["data"]["items"][0]
        assert item["card_id"] == card.id
        assert item["status"] == "pending"
        assert "card_name" in item

    def test_price_request_stats(self):
        """Admin can view aggregated price request stats."""
        repo = _make_repo()
        card = _seed_card(repo)
        admin = _make_user(user_id=1, is_admin=True, email="admin@test.com")
        _seed_price_request(repo, card.id, user_id=2, status="pending")
        _seed_price_request(repo, card.id, user_id=3, status="completed")

        app = _make_admin_app(repo, admin)
        client = TestClient(app)

        resp = client.get("/api/v1/admin/price-requests/stats")
        assert resp.status_code == 200
        body = resp.json()
        # Should have counts by status
        assert isinstance(body["data"], dict)
        assert body["data"].get("pending", 0) >= 1
        assert body["data"].get("completed", 0) >= 1
