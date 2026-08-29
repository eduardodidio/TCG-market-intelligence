"""Tests for GET /cards/search-web — web card search via Liga."""

from __future__ import annotations

from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.api.deps import (
    get_credit_service,
    get_current_user,
    get_db,
    require_auth_or_api_key,
)
from src.api.routers.card_search import router
from src.credits.exceptions import InsufficientCreditsError
from src.credits.service import CreditService
from src.database.models import CardRow
from src.domain.models import User
from src.providers.liga.provider import LigaMagicProvider
from src.providers.registry import ProviderRegistry

_TEST_USER_ID = "testuser"

_TEST_USER = User(
    id=1,
    email="test@example.com",
    display_name="Test",
    is_active=True,
    is_admin=False,
)


def _liga_prices(
    low=None,
    mid=None,
    high=None,
    foil_low=None,
    foil_mid=None,
    foil_high=None,
    card_name="Lightning Bolt",
) -> dict:
    return {
        "card_name": card_name,
        "normal": {"low": low, "mid": mid, "high": high},
        "foil": {"low": foil_low, "mid": foil_mid, "high": foil_high},
    }


def _make_credit_svc(sufficient: bool = True) -> MagicMock:
    svc = MagicMock(spec=CreditService)
    if not sufficient:
        svc.deduct.side_effect = InsufficientCreditsError(balance=0, cost=1)
    return svc


def _make_mock_provider() -> MagicMock:
    provider = MagicMock(spec=LigaMagicProvider)
    provider.source_name = "liga"
    provider.search_card = AsyncMock()
    return provider


def _make_app(
    mock_repo: MagicMock,
    mock_provider: MagicMock | None = None,
    credit_svc: MagicMock | None = None,
    user: User | None = None,
    include_auth: bool = True,
) -> FastAPI:
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_db] = lambda: mock_repo

    if include_auth:
        app.dependency_overrides[get_current_user] = lambda: (user or _TEST_USER)
        app.dependency_overrides[require_auth_or_api_key] = lambda: _TEST_USER_ID

    app.dependency_overrides[get_credit_service] = lambda: (credit_svc or _make_credit_svc())

    if mock_provider is not None:
        registry = ProviderRegistry([mock_provider])
        app.state.provider_registry = registry

    return app


class TestSearchWebReturnsResults:
    def test_returns_results_with_prices(self):
        mock_repo = MagicMock()
        mock_repo.list_cards.return_value = []

        provider = _make_mock_provider()
        provider.search_card.return_value = _liga_prices(
            low=Decimal("2.50"),
            mid=Decimal("3.00"),
            high=Decimal("5.00"),
            foil_low=Decimal("10.00"),
        )

        app = _make_app(mock_repo, mock_provider=provider)
        client = TestClient(app)

        resp = client.get("/cards/search-web", params={"q": "Lightning Bolt"})
        assert resp.status_code == 200

        data = resp.json()["data"]
        assert len(data) == 1
        assert data[0]["card_name"] == "Lightning Bolt"
        assert data[0]["normal_price"] == 2.5
        assert data[0]["foil_price"] == 10.0
        assert data[0]["liga_url"] is not None
        assert "ligamagic" in data[0]["liga_url"]

    def test_empty_results_when_no_prices(self):
        mock_repo = MagicMock()
        provider = _make_mock_provider()
        provider.search_card.return_value = _liga_prices()  # all None

        app = _make_app(mock_repo, mock_provider=provider)
        client = TestClient(app)

        resp = client.get("/cards/search-web", params={"q": "Nonexistent Card"})
        assert resp.status_code == 200
        assert resp.json()["data"] == []

    def test_includes_local_card_id_when_match(self):
        mock_repo = MagicMock()
        local_card = MagicMock(spec=CardRow)
        local_card.id = 42
        local_card.name_en = "Lightning Bolt"
        mock_repo.list_cards.return_value = [local_card]

        provider = _make_mock_provider()
        provider.search_card.return_value = _liga_prices(mid=Decimal("3.00"))

        app = _make_app(mock_repo, mock_provider=provider)
        client = TestClient(app)

        resp = client.get("/cards/search-web", params={"q": "Lightning Bolt"})
        assert resp.status_code == 200
        assert resp.json()["data"][0]["local_card_id"] == 42


class TestSearchWebDeductsToken:
    def test_deduct_called(self):
        mock_repo = MagicMock()
        mock_repo.list_cards.return_value = []

        provider = _make_mock_provider()
        provider.search_card.return_value = _liga_prices(mid=Decimal("3.00"))

        credit_svc = _make_credit_svc()
        app = _make_app(mock_repo, mock_provider=provider, credit_svc=credit_svc)
        client = TestClient(app)

        client.get("/cards/search-web", params={"q": "Test"})
        credit_svc.deduct.assert_called_once()
        args = credit_svc.deduct.call_args
        assert args[0][0] == 1  # user_id
        assert args[0][1] == 1  # cost


class TestSearchWebInsufficientCredits:
    def test_returns_402(self):
        mock_repo = MagicMock()
        provider = _make_mock_provider()

        credit_svc = _make_credit_svc(sufficient=False)
        app = _make_app(mock_repo, mock_provider=provider, credit_svc=credit_svc)
        client = TestClient(app)

        resp = client.get("/cards/search-web", params={"q": "Test"})
        assert resp.status_code == 402
        assert "Insufficient" in resp.json()["detail"]


class TestSearchWebLigaUnavailable:
    def test_returns_503_when_no_provider(self):
        mock_repo = MagicMock()
        # No provider registered
        app = _make_app(mock_repo, mock_provider=None)
        client = TestClient(app)

        resp = client.get("/cards/search-web", params={"q": "Test"})
        assert resp.status_code == 503
        assert "unavailable" in resp.json()["detail"].lower()


class TestSearchWebEmptyQuery:
    def test_returns_422_for_empty_q(self):
        mock_repo = MagicMock()
        app = _make_app(mock_repo)
        client = TestClient(app)

        resp = client.get("/cards/search-web", params={"q": ""})
        assert resp.status_code == 422

    def test_returns_422_for_missing_q(self):
        mock_repo = MagicMock()
        app = _make_app(mock_repo)
        client = TestClient(app)

        resp = client.get("/cards/search-web")
        assert resp.status_code == 422


class TestSearchWebRequiresAuth:
    def test_returns_401_without_auth(self):
        """When no auth dependency override is provided, get_current_user
        should fail. We simulate this by not overriding auth deps."""
        mock_repo = MagicMock()
        app = FastAPI()
        app.include_router(router)
        app.dependency_overrides[get_db] = lambda: mock_repo
        app.dependency_overrides[get_credit_service] = lambda: _make_credit_svc()
        # Note: NOT overriding get_current_user — it requires a real JWT
        client = TestClient(app, raise_server_exceptions=False)

        resp = client.get("/cards/search-web", params={"q": "Test"})
        # Without valid auth, should get 401 or 403
        assert resp.status_code in (401, 403, 422)


class TestSearchWebLigaError:
    def test_returns_502_on_liga_error(self):
        from src.providers.liga.exceptions import LigaError

        mock_repo = MagicMock()
        provider = _make_mock_provider()
        provider.search_card.side_effect = LigaError(
            "Connection failed", url="", status_code=0, attempts=1
        )

        app = _make_app(mock_repo, mock_provider=provider)
        client = TestClient(app)

        resp = client.get("/cards/search-web", params={"q": "Test"})
        assert resp.status_code == 502
        assert "failed" in resp.json()["detail"].lower()
