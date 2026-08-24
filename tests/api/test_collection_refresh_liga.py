"""Tests for POST /collection/{entry_id}/refresh-liga — LigaMagic price refresh."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.api.deps import get_currency_converter_dep, get_db, require_auth_or_api_key
from src.api.routers.collection import router
from src.database.models import PriceObservationRow, UserCollectionRow
from src.providers.liga.exceptions import (
    LigaError,
    LigaNotFoundError,
    LigaRateLimitError,
)
from src.services.currency import CurrencyConverter

_TEST_USER_ID = "eduardo"


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
        "external_id": "liga_Lightning Bolt",
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


def _make_app(
    mock_repo: MagicMock,
    mock_converter: MagicMock | None = None,
    user_id: str = _TEST_USER_ID,
) -> FastAPI:
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_db] = lambda: mock_repo
    app.dependency_overrides[require_auth_or_api_key] = lambda: user_id
    if mock_converter is not None:
        app.dependency_overrides[get_currency_converter_dep] = lambda: mock_converter
    else:
        converter = MagicMock(spec=CurrencyConverter)
        converter.convert.return_value = Decimal("5.50")
        converter.get_display_rate.return_value = Decimal("5.00")
        app.dependency_overrides[get_currency_converter_dep] = lambda: converter
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

    @patch("src.providers.liga.provider.LigaMagicProvider", autospec=False)
    def test_returns_detail_with_price(self, mock_provider_cls) -> None:
        entry = _make_collection_row()
        mock_repo = MagicMock()
        _mock_repo_for_detail(mock_repo, entry)

        provider_instance = AsyncMock()
        provider_instance.search_card.return_value = _liga_prices(mid=Decimal("5.50"))
        provider_instance.close = AsyncMock()
        mock_provider_cls.return_value = provider_instance

        app = _make_app(mock_repo)
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
        assert obs_list[0].external_id == "liga_Lightning Bolt"
        assert obs_list[0].median_price == Decimal("5.50")

    @patch("src.providers.liga.provider.LigaMagicProvider", autospec=False)
    def test_prefers_mid_price(self, mock_provider_cls) -> None:
        entry = _make_collection_row()
        mock_repo = MagicMock()
        _mock_repo_for_detail(mock_repo, entry)

        provider_instance = AsyncMock()
        provider_instance.search_card.return_value = _liga_prices(
            mid=Decimal("10.00"), low=Decimal("8.00"), high=Decimal("12.00")
        )
        provider_instance.close = AsyncMock()
        mock_provider_cls.return_value = provider_instance

        app = _make_app(mock_repo)
        client = TestClient(app)
        resp = client.post("/collection/1/refresh-liga")

        assert resp.status_code == 200
        obs_list = mock_repo.insert_price_observations.call_args[0][0]
        assert obs_list[0].median_price == Decimal("10.00")

    @patch("src.providers.liga.provider.LigaMagicProvider", autospec=False)
    def test_falls_back_to_low_price(self, mock_provider_cls) -> None:
        entry = _make_collection_row()
        mock_repo = MagicMock()
        _mock_repo_for_detail(mock_repo, entry)

        provider_instance = AsyncMock()
        provider_instance.search_card.return_value = _liga_prices(low=Decimal("3.00"))
        provider_instance.close = AsyncMock()
        mock_provider_cls.return_value = provider_instance

        app = _make_app(mock_repo)
        client = TestClient(app)
        resp = client.post("/collection/1/refresh-liga")

        assert resp.status_code == 200
        obs_list = mock_repo.insert_price_observations.call_args[0][0]
        assert obs_list[0].median_price == Decimal("3.00")

    @patch("src.providers.liga.provider.LigaMagicProvider", autospec=False)
    def test_falls_back_to_high_price(self, mock_provider_cls) -> None:
        entry = _make_collection_row()
        mock_repo = MagicMock()
        _mock_repo_for_detail(mock_repo, entry)

        provider_instance = AsyncMock()
        provider_instance.search_card.return_value = _liga_prices(high=Decimal("15.00"))
        provider_instance.close = AsyncMock()
        mock_provider_cls.return_value = provider_instance

        app = _make_app(mock_repo)
        client = TestClient(app)
        resp = client.post("/collection/1/refresh-liga")

        assert resp.status_code == 200
        obs_list = mock_repo.insert_price_observations.call_args[0][0]
        assert obs_list[0].median_price == Decimal("15.00")

    @patch("src.providers.liga.provider.LigaMagicProvider", autospec=False)
    def test_uses_name_pt_fallback(self, mock_provider_cls) -> None:
        """When name_en is None, should use name_pt for search."""
        entry = _make_collection_row(name_en=None, name_pt="Raio")
        mock_repo = MagicMock()
        _mock_repo_for_detail(mock_repo, entry)

        provider_instance = AsyncMock()
        provider_instance.search_card.return_value = _liga_prices(mid=Decimal("5.50"))
        provider_instance.close = AsyncMock()
        mock_provider_cls.return_value = provider_instance

        app = _make_app(mock_repo)
        client = TestClient(app)
        resp = client.post("/collection/1/refresh-liga")

        assert resp.status_code == 200
        provider_instance.search_card.assert_called_once_with("Raio")

    @patch("src.providers.liga.provider.LigaMagicProvider", autospec=False)
    def test_provider_close_called(self, mock_provider_cls) -> None:
        entry = _make_collection_row()
        mock_repo = MagicMock()
        _mock_repo_for_detail(mock_repo, entry)

        provider_instance = AsyncMock()
        provider_instance.search_card.return_value = _liga_prices(mid=Decimal("5.50"))
        provider_instance.close = AsyncMock()
        mock_provider_cls.return_value = provider_instance

        app = _make_app(mock_repo)
        client = TestClient(app)
        client.post("/collection/1/refresh-liga")

        provider_instance.close.assert_called_once()


class TestRefreshLigaNoPrice:
    """Provider returns empty prices — 200 with warning."""

    @patch("src.providers.liga.provider.LigaMagicProvider", autospec=False)
    def test_no_price_returns_warning(self, mock_provider_cls) -> None:
        entry = _make_collection_row()
        mock_repo = MagicMock()
        _mock_repo_for_detail(mock_repo, entry)

        provider_instance = AsyncMock()
        provider_instance.search_card.return_value = _liga_prices()  # all None
        provider_instance.close = AsyncMock()
        mock_provider_cls.return_value = provider_instance

        app = _make_app(mock_repo)
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

    @patch("src.providers.liga.provider.LigaMagicProvider", autospec=False)
    def test_nonexistent_entry_404(self, mock_provider_cls) -> None:
        mock_repo = MagicMock()
        mock_repo.get_collection_entry.return_value = None

        app = _make_app(mock_repo)
        client = TestClient(app)
        resp = client.post("/collection/999/refresh-liga")

        assert resp.status_code == 404


class TestRefreshLigaIDOR:
    """Entry belongs to different user — 404."""

    @patch("src.providers.liga.provider.LigaMagicProvider", autospec=False)
    def test_wrong_user_404(self, mock_provider_cls) -> None:
        entry = _make_collection_row(user_id="other_user")
        mock_repo = MagicMock()
        mock_repo.get_collection_entry.return_value = entry

        app = _make_app(mock_repo, user_id=_TEST_USER_ID)
        client = TestClient(app)
        resp = client.post("/collection/1/refresh-liga")

        assert resp.status_code == 404


class TestRefreshLigaNoName:
    """Card has no name — 422."""

    @patch("src.providers.liga.provider.LigaMagicProvider", autospec=False)
    def test_no_name_422(self, mock_provider_cls) -> None:
        entry = _make_collection_row(name_en=None, name_pt=None)
        mock_repo = MagicMock()
        mock_repo.get_collection_entry.return_value = entry

        app = _make_app(mock_repo)
        client = TestClient(app)
        resp = client.post("/collection/1/refresh-liga")

        assert resp.status_code == 422
        assert "name" in resp.json()["detail"].lower()


class TestRefreshLigaProviderErrors:
    """Provider raises exceptions — 200 with warning, never 500."""

    @patch("src.providers.liga.provider.LigaMagicProvider", autospec=False)
    def test_not_found_error_warning(self, mock_provider_cls) -> None:
        entry = _make_collection_row()
        mock_repo = MagicMock()
        _mock_repo_for_detail(mock_repo, entry)

        provider_instance = AsyncMock()
        provider_instance.search_card.side_effect = LigaNotFoundError("not found")
        provider_instance.close = AsyncMock()
        mock_provider_cls.return_value = provider_instance

        app = _make_app(mock_repo)
        client = TestClient(app)
        resp = client.post("/collection/1/refresh-liga")

        assert resp.status_code == 200
        body = resp.json()
        assert len(body["errors"]) == 1
        assert "not found" in body["errors"][0]["message"].lower()

    @patch("src.providers.liga.provider.LigaMagicProvider", autospec=False)
    def test_rate_limit_error_warning(self, mock_provider_cls) -> None:
        entry = _make_collection_row()
        mock_repo = MagicMock()
        _mock_repo_for_detail(mock_repo, entry)

        provider_instance = AsyncMock()
        provider_instance.search_card.side_effect = LigaRateLimitError("rate limited")
        provider_instance.close = AsyncMock()
        mock_provider_cls.return_value = provider_instance

        app = _make_app(mock_repo)
        client = TestClient(app)
        resp = client.post("/collection/1/refresh-liga")

        assert resp.status_code == 200
        body = resp.json()
        assert len(body["errors"]) == 1
        assert "rate limit" in body["errors"][0]["message"].lower()

    @patch("src.providers.liga.provider.LigaMagicProvider", autospec=False)
    def test_generic_liga_error_warning(self, mock_provider_cls) -> None:
        entry = _make_collection_row()
        mock_repo = MagicMock()
        _mock_repo_for_detail(mock_repo, entry)

        provider_instance = AsyncMock()
        provider_instance.search_card.side_effect = LigaError("timeout")
        provider_instance.close = AsyncMock()
        mock_provider_cls.return_value = provider_instance

        app = _make_app(mock_repo)
        client = TestClient(app)
        resp = client.post("/collection/1/refresh-liga")

        assert resp.status_code == 200
        body = resp.json()
        assert len(body["errors"]) == 1
        assert body["errors"][0]["code"] == "liga_warning"

    @patch("src.providers.liga.provider.LigaMagicProvider", autospec=False)
    def test_unexpected_error_warning(self, mock_provider_cls) -> None:
        entry = _make_collection_row()
        mock_repo = MagicMock()
        _mock_repo_for_detail(mock_repo, entry)

        provider_instance = AsyncMock()
        provider_instance.search_card.side_effect = RuntimeError("unexpected")
        provider_instance.close = AsyncMock()
        mock_provider_cls.return_value = provider_instance

        app = _make_app(mock_repo)
        client = TestClient(app)
        resp = client.post("/collection/1/refresh-liga")

        assert resp.status_code == 200
        body = resp.json()
        assert len(body["errors"]) == 1
        assert "unexpected" in body["errors"][0]["message"].lower()

    @patch("src.providers.liga.provider.LigaMagicProvider", autospec=False)
    def test_provider_close_on_error(self, mock_provider_cls) -> None:
        """Provider.close() is called even when search raises."""
        entry = _make_collection_row()
        mock_repo = MagicMock()
        _mock_repo_for_detail(mock_repo, entry)

        provider_instance = AsyncMock()
        provider_instance.search_card.side_effect = LigaError("boom")
        provider_instance.close = AsyncMock()
        mock_provider_cls.return_value = provider_instance

        app = _make_app(mock_repo)
        client = TestClient(app)
        client.post("/collection/1/refresh-liga")

        provider_instance.close.assert_called_once()


class TestRefreshLigaAutoCreateCard:
    """Entry has no card_id — auto-create canonical card."""

    @patch("src.providers.liga.provider.LigaMagicProvider", autospec=False)
    def test_auto_creates_card_id(self, mock_provider_cls) -> None:
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

        provider_instance = AsyncMock()
        provider_instance.search_card.return_value = _liga_prices(mid=Decimal("7.00"))
        provider_instance.close = AsyncMock()
        mock_provider_cls.return_value = provider_instance

        app = _make_app(mock_repo)
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
