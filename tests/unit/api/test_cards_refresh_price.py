"""Tests for POST /api/v1/cards/{card_id}/refresh-price endpoint.

Updated for F130 queue-based implementation: the endpoint now queues a
PriceUpdateRequest instead of calling Liga directly.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from src.api.routers.cards import router
from src.database.models import Base, CardRow, PriceUpdateRequestRow
from src.database.repository import Repository
from src.domain.models import User

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_app(repo: Repository, user: User | None = None, credit_balance: int = 100) -> tuple:
    """Build a minimal FastAPI app with the cards router and mocked dependencies.

    Returns (app, credit_svc_mock).
    """
    from src.api.deps import (
        get_credit_service,
        get_currency_converter_dep,
        get_current_user,
        get_db,
        get_optional_user,
    )
    from src.credits.service import CreditService

    app = FastAPI()
    app.include_router(router, prefix="/api/v1")

    # Override DB dependency with generator
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


@pytest.fixture()
def repo_with_card():
    """In-memory SQLite repo seeded with one card.

    Uses StaticPool so the same connection is shared across threads
    (required for TestClient which runs handlers in a thread pool).
    """
    from sqlalchemy.pool import StaticPool

    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        session.add(
            CardRow(
                game="magic",
                name_en="Lightning Bolt",
                name_pt=None,
                set_code="m10",
                collector_number="146",
            )
        )
        session.commit()
    repo = Repository.__new__(Repository)
    repo.engine = engine
    return repo


@pytest.fixture()
def test_user():
    return User(id=1, email="test@test.com", display_name="testuser")


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestRefreshCardPrice:
    """Tests for POST /api/v1/cards/{card_id}/refresh-price (queue-based)."""

    def test_refresh_price_returns_queued(self, repo_with_card, test_user):
        """Successfully queues a price update request."""
        app, _ = _make_app(repo_with_card, user=test_user)
        client = TestClient(app)

        resp = client.post("/api/v1/cards/1/refresh-price")
        assert resp.status_code == 200
        body = resp.json()
        assert body["data"]["status"] == "queued"
        assert "request_id" in body["data"]
        assert body["data"]["card_id"] == 1

    def test_refresh_price_card_not_found(self, repo_with_card, test_user):
        """Return 404 when card ID doesn't exist."""
        app, _ = _make_app(repo_with_card, user=test_user)
        client = TestClient(app)

        resp = client.post("/api/v1/cards/999/refresh-price")
        assert resp.status_code == 404

    def test_refresh_price_insufficient_credits(self, repo_with_card, test_user):
        """Return 402 when user has insufficient credits."""
        app, _ = _make_app(repo_with_card, user=test_user, credit_balance=0)
        client = TestClient(app)

        resp = client.post("/api/v1/cards/1/refresh-price")
        assert resp.status_code == 402

    def test_refresh_price_creates_db_request(self, repo_with_card, test_user):
        """Verify a PriceUpdateRequestRow is created in the database."""
        app, _ = _make_app(repo_with_card, user=test_user)
        client = TestClient(app)

        resp = client.post("/api/v1/cards/1/refresh-price")
        assert resp.status_code == 200

        with Session(repo_with_card.engine) as session:
            rows = session.query(PriceUpdateRequestRow).all()
            assert len(rows) == 1
            assert rows[0].card_id == 1
            assert rows[0].user_id == test_user.id
            assert rows[0].status == "pending"

    def test_refresh_price_deducts_credit(self, repo_with_card, test_user):
        """Verify credit is deducted at request time (before processing)."""
        app, credit_svc = _make_app(repo_with_card, user=test_user)
        client = TestClient(app)

        resp = client.post("/api/v1/cards/1/refresh-price")
        assert resp.status_code == 200

        credit_svc.deduct.assert_called_once()

    def test_refresh_price_card_without_name(self, repo_with_card, test_user):
        """Return 422 when card has no usable name (empty string)."""
        with Session(repo_with_card.engine) as session:
            card = session.query(CardRow).first()
            card.name_en = ""
            card.name_pt = None
            session.commit()

        app, _ = _make_app(repo_with_card, user=test_user)
        client = TestClient(app)

        resp = client.post("/api/v1/cards/1/refresh-price")
        assert resp.status_code == 422
