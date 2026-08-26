"""Tests for POST /collection/{entry_id}/refresh-liga — LigaMagic price refresh."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.api.deps import (
    get_credit_service,
    get_currency_converter_dep,
    get_current_user,
    get_db,
    require_auth_or_api_key,
)
from src.api.routers.collection import router
from src.credits.service import CreditService
from src.database.models import PriceObservationRow, UserCollectionRow
from src.domain.models import User
from src.providers.liga.exceptions import (
    LigaError,
    LigaNotFoundError,
    LigaRateLimitError,
)
from src.providers.liga.provider import LigaMagicProvider
from src.providers.registry import ProviderRegistry
from src.services.currency import CurrencyConverter

_TEST_USER_ID = "eduardo"

# Admin user so existing tests bypass credit guards
_TEST_USER = User(
    id=1,
    email="test@example.com",
    display_name="Test",
    is_active=True,
    is_admin=True,
)


def _make_collection_row(**overrides) -> MagicMock:
    defaults = {
        "id": 1,
        "user_id": _TEST_USER_ID,
        "card_id": 42,
        "set_code": "DMR",
        "collector_number": "123",
        "name_en": "Lightning Bolt",
        "name_pt": "Raio",
        "set_name_en": "Dominaria Remastered",
        "quantity": 2,
        "quality": "NM",
        "language": "EN",
        "rarity": "R",
        "color": "R",
        "extras": "Foil",
    }
    defaults.update(overrides)
    row = MagicMock(spec=UserCollectionRow)
    for k, v in defaults.items():
        setattr(row, k, v)
    return row


def _make_price_obs(**overrides) -> MagicMock:
    defaults = {
        "id": 100,
        "source": "liga",
        "external_id": "liga_42",
        "observed_at": date(2026, 8, 24),
        "median_price": Decimal("5.50"),
        "tcg_price": None,
        "last_sold_price": None,
        "quantity_available": None,
        "last_sold_meta": None,
        "currency": "BRL",
    }
    defaults.update(overrides)
    obs = MagicMock(spec=PriceObservationRow)
    for k, v in defaults.items():
        setattr(obs, k, v)
    return obs


def _make_mock_provider(**overrides) -> MagicMock:
    """Create a mock LigaMagicProvider that passes isinstance checks."""
    provider = MagicMock(spec=LigaMagicProvider)
    provider.source_name = "liga"
    provider.search_card = AsyncMock()
    provider.close = AsyncMock()
    for k, v in overrides.items():
        setattr(provider, k, v)
    return provider


def _make_credit_svc() -> MagicMock:
    svc = MagicMock(spec=CreditService)
    svc.check_sufficient.return_value = True
    return svc


def _make_app(
    mock_repo: MagicMock,
    mock_provider: MagicMock | None = None,
    mock_converter: MagicMock | None = None,
    user_id: str = _TEST_USER_ID,
    include_registry: bool = True,
) -> FastAPI:
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_db] = lambda: mock_repo
    app.dependency_overrides[require_auth_or_api_key] = lambda: user_id
    app.dependency_overrides[get_current_user] = lambda: _TEST_USER
    app.dependency_overrides[get_credit_service] = _make_credit_svc
    if mock_converter is not None:
        app.dependency_overrides[get_currency_converter_dep] = lambda: mock_converter
    else:
        converter = MagicMock(spec=CurrencyConverter)
        converter.convert.return_value = Decimal("5.50")
        converter.get_display_rate.return_value = Decimal("5.00")
        app.dependency_overrides[get_currency_converter_dep] = lambda: converter

    # Set up provider registry on app.state
    if include_registry and mock_provider is not None:
        registry = ProviderRegistry([mock_provider])
        app.state.provider_registry = registry
    elif not include_registry:
        # Simulate no registry (or empty one)
        pass

    return app


def _mock_repo_for_detail(mock_repo: MagicMock, entry: MagicMock) -> None:
    """Configure mock_repo to support _build_collection_detail after refresh."""
    mock_repo.get_collection_entry.return_value = entry
    price_obs = _make_price_obs()
    mock_repo.get_latest_prices_batch.return_value = {entry.card_id: price_obs}
    mock_repo.get_source_cards_for_card.return_value = []


def _liga_prices(mid=None, low=None, high=None) -> dict:
    """Build a LigaMagic price dict matching parse_card_prices structure."""
    return {
        "card_name": "Lightning Bolt",
        "normal": {"low": low, "mid": mid, "high": high},
        "foil": {"low": None, "mid": None, "high": None},
    }


class TestRefreshLigaHappyPath:
    """Happy path: provider returns prices, price is stored."""

    def test_returns_detail_with_price(self) -> None:
        entry = _make_collection_row()
        mock_repo = MagicMock()
        _mock_repo_for_detail(mock_repo, entry)

        provider = _make_mock_provider()
        provider.search_card.return_value = _liga_prices(mid=Decimal("5.50"))

        app = _make_app(mock_repo, mock_provider=provider)
        client = TestClient(app)
        resp = client.post("/collection/1/refresh-liga")

        assert resp.status_code == 200
        body = resp.json()
        assert body["data"]["id"] == 1
        assert body["errors"] == []

        # Verify price was inserted
        mock_repo.insert_price_observations.assert_called_once()
        obs_list = mock_repo.insert_price_observations.call_args[0][0]
        assert len(obs_list) == 1
        assert obs_list[0].source == "liga"
        assert obs_list[0].external_id == "liga_42"
        assert obs_list[0].median_price == Decimal("5.50")

    def test_prefers_mid_price(self) -> None:
        entry = _make_collection_row()
        mock_repo = MagicMock()
        _mock_repo_for_detail(mock_repo, entry)

        provider = _make_mock_provider()
        provider.search_card.return_value = _liga_prices(
            mid=Decimal("10.00"), low=Decimal("8.00"), high=Decimal("12.00")
        )

        app = _make_app(mock_repo, mock_provider=provider)
        client = TestClient(app)
        resp = client.post("/collection/1/refresh-liga")

        assert resp.status_code == 200
        obs_list = mock_repo.insert_price_observations.call_args[0][0]
        assert obs_list[0].median_price == Decimal("10.00")

    def test_falls_back_to_low_price(self) -> None:
        entry = _make_collection_row()
        mock_repo = MagicMock()
        _mock_repo_for_detail(mock_repo, entry)

        provider = _make_mock_provider()
        provider.search_card.return_value = _liga_prices(low=Decimal("3.00"))

        app = _make_app(mock_repo, mock_provider=provider)
        client = TestClient(app)
        resp = client.post("/collection/1/refresh-liga")

        assert resp.status_code == 200
        obs_list = mock_repo.insert_price_observations.call_args[0][0]
        assert obs_list[0].median_price == Decimal("3.00")

    def test_falls_back_to_high_price(self) -> None:
        entry = _make_collection_row()
        mock_repo = MagicMock()
        _mock_repo_for_detail(mock_repo, entry)

        provider = _make_mock_provider()
        provider.search_card.return_value = _liga_prices(high=Decimal("15.00"))

        app = _make_app(mock_repo, mock_provider=provider)
        client = TestClient(app)
        resp = client.post("/collection/1/refresh-liga")

        assert resp.status_code == 200
        obs_list = mock_repo.insert_price_observations.call_args[0][0]
        assert obs_list[0].median_price == Decimal("15.00")

    def test_uses_name_pt_fallback(self) -> None:
        """When name_en is None, should use name_pt for search."""
        entry = _make_collection_row(name_en=None, name_pt="Raio")
        mock_repo = MagicMock()
        _mock_repo_for_detail(mock_repo, entry)

        provider = _make_mock_provider()
        provider.search_card.return_value = _liga_prices(mid=Decimal("5.50"))

        app = _make_app(mock_repo, mock_provider=provider)
        client = TestClient(app)
        resp = client.post("/collection/1/refresh-liga")

        assert resp.status_code == 200
        provider.search_card.assert_called_once_with("Raio")

    def test_no_provider_close_per_request(self) -> None:
        """Singleton provider should NOT be closed per request."""
        entry = _make_collection_row()
        mock_repo = MagicMock()
        _mock_repo_for_detail(mock_repo, entry)

        provider = _make_mock_provider()
        provider.search_card.return_value = _liga_prices(mid=Decimal("5.50"))

        app = _make_app(mock_repo, mock_provider=provider)
        client = TestClient(app)
        client.post("/collection/1/refresh-liga")

        provider.close.assert_not_called()


class TestRefreshLigaNoPrice:
    """Provider returns empty prices — 200 with warning."""

    def test_no_price_returns_warning(self) -> None:
        entry = _make_collection_row()
        mock_repo = MagicMock()
        _mock_repo_for_detail(mock_repo, entry)

        provider = _make_mock_provider()
        provider.search_card.return_value = _liga_prices()  # all None

        app = _make_app(mock_repo, mock_provider=provider)
        client = TestClient(app)
        resp = client.post("/collection/1/refresh-liga")

        assert resp.status_code == 200
        body = resp.json()
        assert len(body["errors"]) == 1
        assert body["errors"][0]["code"] == "liga_warning"
        assert "No price found" in body["errors"][0]["message"]
        mock_repo.insert_price_observations.assert_not_called()


class TestRefreshLigaEntryNotFound:
    """Entry does not exist — 404."""

    def test_nonexistent_entry_404(self) -> None:
        mock_repo = MagicMock()
        mock_repo.get_collection_entry.return_value = None

        provider = _make_mock_provider()
        app = _make_app(mock_repo, mock_provider=provider)
        client = TestClient(app)
        resp = client.post("/collection/999/refresh-liga")

        assert resp.status_code == 404


class TestRefreshLigaIDOR:
    """Entry belongs to different user — 404."""

    def test_wrong_user_404(self) -> None:
        entry = _make_collection_row(user_id="other_user")
        mock_repo = MagicMock()
        mock_repo.get_collection_entry.return_value = entry

        provider = _make_mock_provider()
        app = _make_app(mock_repo, mock_provider=provider, user_id=_TEST_USER_ID)
        client = TestClient(app)
        resp = client.post("/collection/1/refresh-liga")

        assert resp.status_code == 404


class TestRefreshLigaNoName:
    """Card has no name — 422."""

    def test_no_name_422(self) -> None:
        entry = _make_collection_row(name_en=None, name_pt=None)
        mock_repo = MagicMock()
        mock_repo.get_collection_entry.return_value = entry

        provider = _make_mock_provider()
        app = _make_app(mock_repo, mock_provider=provider)
        client = TestClient(app)
        resp = client.post("/collection/1/refresh-liga")

        assert resp.status_code == 422
        assert "name" in resp.json()["detail"].lower()


class TestRefreshLigaProviderErrors:
    """Provider raises exceptions — 200 with warning, never 500."""

    def test_not_found_error_warning(self) -> None:
        entry = _make_collection_row()
        mock_repo = MagicMock()
        _mock_repo_for_detail(mock_repo, entry)

        provider = _make_mock_provider()
        provider.search_card.side_effect = LigaNotFoundError("not found")

        app = _make_app(mock_repo, mock_provider=provider)
        client = TestClient(app)
        resp = client.post("/collection/1/refresh-liga")

        assert resp.status_code == 200
        body = resp.json()
        assert len(body["errors"]) == 1
        assert "not found" in body["errors"][0]["message"].lower()

    def test_rate_limit_error_warning(self) -> None:
        entry = _make_collection_row()
        mock_repo = MagicMock()
        _mock_repo_for_detail(mock_repo, entry)

        provider = _make_mock_provider()
        provider.search_card.side_effect = LigaRateLimitError("rate limited")

        app = _make_app(mock_repo, mock_provider=provider)
        client = TestClient(app)
        resp = client.post("/collection/1/refresh-liga")

        assert resp.status_code == 200
        body = resp.json()
        assert len(body["errors"]) == 1
        assert "rate limit" in body["errors"][0]["message"].lower()

    def test_generic_liga_error_warning(self) -> None:
        entry = _make_collection_row()
        mock_repo = MagicMock()
        _mock_repo_for_detail(mock_repo, entry)

        provider = _make_mock_provider()
        provider.search_card.side_effect = LigaError("timeout")

        app = _make_app(mock_repo, mock_provider=provider)
        client = TestClient(app)
        resp = client.post("/collection/1/refresh-liga")

        assert resp.status_code == 200
        body = resp.json()
        assert len(body["errors"]) == 1
        assert body["errors"][0]["code"] == "liga_warning"

    def test_unexpected_error_includes_type_name(self) -> None:
        """Catch-all error includes exception type in message."""
        entry = _make_collection_row()
        mock_repo = MagicMock()
        _mock_repo_for_detail(mock_repo, entry)

        provider = _make_mock_provider()
        provider.search_card.side_effect = RuntimeError("unexpected")

        app = _make_app(mock_repo, mock_provider=provider)
        client = TestClient(app)
        resp = client.post("/collection/1/refresh-liga")

        assert resp.status_code == 200
        body = resp.json()
        assert len(body["errors"]) == 1
        msg = body["errors"][0]["message"]
        assert "RuntimeError" in msg
        assert "unexpected" in msg

    def test_empty_message_error_includes_type(self) -> None:
        """Exception with empty str() still produces readable error."""
        entry = _make_collection_row()
        mock_repo = MagicMock()
        _mock_repo_for_detail(mock_repo, entry)

        provider = _make_mock_provider()
        provider.search_card.side_effect = RuntimeError("")

        app = _make_app(mock_repo, mock_provider=provider)
        client = TestClient(app)
        resp = client.post("/collection/1/refresh-liga")

        assert resp.status_code == 200
        body = resp.json()
        assert len(body["errors"]) == 1
        msg = body["errors"][0]["message"]
        assert "RuntimeError" in msg
        assert "no details" in msg

    def test_no_provider_close_on_error(self) -> None:
        """Singleton provider.close() is NOT called on error."""
        entry = _make_collection_row()
        mock_repo = MagicMock()
        _mock_repo_for_detail(mock_repo, entry)

        provider = _make_mock_provider()
        provider.search_card.side_effect = LigaError("boom")

        app = _make_app(mock_repo, mock_provider=provider)
        client = TestClient(app)
        client.post("/collection/1/refresh-liga")

        provider.close.assert_not_called()


class TestRefreshLigaNoRegistry:
    """Liga provider not in registry — 503."""

    def test_no_registry_returns_503(self) -> None:
        entry = _make_collection_row()
        mock_repo = MagicMock()
        mock_repo.get_collection_entry.return_value = entry

        app = _make_app(mock_repo, include_registry=False)
        client = TestClient(app)
        resp = client.post("/collection/1/refresh-liga")

        assert resp.status_code == 503
        assert "Liga provider" in resp.json()["detail"]

    def test_registry_without_liga_returns_503(self) -> None:
        """Registry exists but has no Liga provider."""
        entry = _make_collection_row()
        mock_repo = MagicMock()
        mock_repo.get_collection_entry.return_value = entry

        # Registry with a non-Liga provider
        other_provider = MagicMock()
        other_provider.source_name = "myp"
        registry = ProviderRegistry([other_provider])

        app = _make_app(mock_repo, include_registry=False)
        app.state.provider_registry = registry
        client = TestClient(app)
        resp = client.post("/collection/1/refresh-liga")

        assert resp.status_code == 503


class TestRefreshLigaAutoCreateCard:
    """Entry has no card_id — auto-create canonical card."""

    def test_auto_creates_card_id(self) -> None:
        entry_no_card = _make_collection_row(card_id=None)
        entry_with_card = _make_collection_row(card_id=99)

        mock_repo = MagicMock()
        # First call returns entry without card_id, second returns with card_id
        mock_repo.get_collection_entry.side_effect = [
            entry_no_card,
            entry_with_card,
            entry_with_card,  # for _build_collection_detail
        ]
        mock_repo.create_canonical_card.return_value = 99
        price_obs = _make_price_obs()
        mock_repo.get_latest_prices_batch.return_value = {99: price_obs}
        mock_repo.get_source_cards_for_card.return_value = []

        provider = _make_mock_provider()
        provider.search_card.return_value = _liga_prices(mid=Decimal("7.00"))

        app = _make_app(mock_repo, mock_provider=provider)
        client = TestClient(app)
        resp = client.post("/collection/1/refresh-liga")

        assert resp.status_code == 200
        mock_repo.create_canonical_card.assert_called_once_with(
            game="magic",
            name_en="Lightning Bolt",
            name_pt="Raio",
            set_code="DMR",
            collector_number="123",
        )
        mock_repo.link_collection_entry.assert_called_once_with(1, 99)
        mock_repo.insert_price_observations.assert_called_once()
