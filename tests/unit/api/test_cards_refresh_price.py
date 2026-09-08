"""Tests for POST /api/v1/cards/{card_id}/refresh-price endpoint (F113-T09)."""

from __future__ import annotations

from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from src.api.routers.cards import router
from src.database.models import Base, CardRow
from src.database.repository import Repository
from src.domain.models import User

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_app(
    repo: Repository, user: User | None = None, provider=None, credit_balance: int = 100
) -> tuple:
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

    # Mock provider registry
    registry = MagicMock()
    if provider is not None:
        registry.providers = [provider]
    else:
        registry.providers = []
    app.state.provider_registry = registry

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
    """Tests for POST /api/v1/cards/{card_id}/refresh-price."""

    def test_refresh_price_success(self, repo_with_card, test_user):
        """Successfully refresh a card's price from Liga."""
        from src.providers.liga.provider import LigaMagicProvider

        mock_provider = MagicMock(spec=LigaMagicProvider)
        mock_provider.search_card = AsyncMock(
            return_value={
                "normal": {"low": Decimal("2.50"), "mid": Decimal("3.00"), "high": Decimal("4.00")},
                "foil": {},
            }
        )

        app, _ = _make_app(repo_with_card, user=test_user, provider=mock_provider)
        client = TestClient(app)

        resp = client.post("/api/v1/cards/1/refresh-price")
        assert resp.status_code == 200
        body = resp.json()
        assert body["data"]["latest_price"] == 2.5
        assert body["data"]["name_en"] == "Lightning Bolt"

    def test_refresh_price_card_not_found(self, repo_with_card, test_user):
        """Return 404 when card ID doesn't exist."""
        from src.providers.liga.provider import LigaMagicProvider

        mock_provider = MagicMock(spec=LigaMagicProvider)
        app, _ = _make_app(repo_with_card, user=test_user, provider=mock_provider)
        client = TestClient(app)

        resp = client.post("/api/v1/cards/999/refresh-price")
        assert resp.status_code == 404

    def test_refresh_price_no_provider(self, repo_with_card, test_user):
        """Return 503 when Liga provider is not available."""
        app, _ = _make_app(repo_with_card, user=test_user, provider=None)
        client = TestClient(app)

        resp = client.post("/api/v1/cards/1/refresh-price")
        assert resp.status_code == 503

    def test_refresh_price_insufficient_credits(self, repo_with_card, test_user):
        """Return 402 when user has insufficient credits."""
        from src.providers.liga.provider import LigaMagicProvider

        mock_provider = MagicMock(spec=LigaMagicProvider)
        app, _ = _make_app(repo_with_card, user=test_user, provider=mock_provider, credit_balance=0)
        client = TestClient(app)

        resp = client.post("/api/v1/cards/1/refresh-price")
        assert resp.status_code == 402

    def test_refresh_price_liga_not_found(self, repo_with_card, test_user):
        """Return 404 when Liga can't find the card."""
        from src.providers.liga.exceptions import LigaNotFoundError
        from src.providers.liga.provider import LigaMagicProvider

        mock_provider = MagicMock(spec=LigaMagicProvider)
        mock_provider.search_card = AsyncMock(side_effect=LigaNotFoundError("Not found"))

        app, _ = _make_app(repo_with_card, user=test_user, provider=mock_provider)
        client = TestClient(app)

        resp = client.post("/api/v1/cards/1/refresh-price")
        assert resp.status_code == 404

    def test_refresh_price_liga_rate_limited(self, repo_with_card, test_user):
        """Return 429 when Liga rate-limits us."""
        from src.providers.liga.exceptions import LigaRateLimitError
        from src.providers.liga.provider import LigaMagicProvider

        mock_provider = MagicMock(spec=LigaMagicProvider)
        mock_provider.search_card = AsyncMock(side_effect=LigaRateLimitError("Rate limited"))

        app, _ = _make_app(repo_with_card, user=test_user, provider=mock_provider)
        client = TestClient(app)

        resp = client.post("/api/v1/cards/1/refresh-price")
        assert resp.status_code == 429

    def test_refresh_price_stores_observation(self, repo_with_card, test_user):
        """Verify that a price observation is stored in the DB."""
        from src.providers.liga.provider import LigaMagicProvider

        mock_provider = MagicMock(spec=LigaMagicProvider)
        mock_provider.search_card = AsyncMock(
            return_value={
                "normal": {"low": Decimal("5.00")},
                "foil": {},
            }
        )

        app, _ = _make_app(repo_with_card, user=test_user, provider=mock_provider)
        client = TestClient(app)

        resp = client.post("/api/v1/cards/1/refresh-price")
        assert resp.status_code == 200

        # Check that price observation was stored
        with Session(repo_with_card.engine) as session:
            from src.database.models import PriceObservationRow

            obs = session.query(PriceObservationRow).filter_by(external_id="liga_1").all()
            assert len(obs) == 1
            assert float(obs[0].median_price) == 5.0

    def test_refresh_price_deducts_credit(self, repo_with_card, test_user):
        """Verify credit is deducted after successful refresh."""
        from src.providers.liga.provider import LigaMagicProvider

        mock_provider = MagicMock(spec=LigaMagicProvider)
        mock_provider.search_card = AsyncMock(
            return_value={
                "normal": {"low": Decimal("1.00")},
                "foil": {},
            }
        )

        app, credit_svc = _make_app(repo_with_card, user=test_user, provider=mock_provider)
        client = TestClient(app)

        resp = client.post("/api/v1/cards/1/refresh-price")
        assert resp.status_code == 200

        credit_svc.deduct.assert_called_once()
