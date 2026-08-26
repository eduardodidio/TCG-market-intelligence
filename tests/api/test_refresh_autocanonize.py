"""Tests for POST /collection/{entry_id}/refresh — auto-canonize orphan entries."""

from __future__ import annotations

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

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
from src.database.models import UserCollectionRow
from src.domain.models import User

_TEST_USER_ID = "eduardo"

_TEST_USER = User(
    id=1,
    email="test@example.com",
    display_name="Test",
    is_active=True,
    is_admin=True,  # admin to bypass credit checks in existing tests
)

# Patch targets — refresh uses inline imports from these modules
_PATCH_PROVIDER = "src.providers.myp.provider.MypCardsProvider"
_PATCH_MATCHER = "src.collection.matcher.match_collection_card"
_PATCH_CONVERTER = "src.collection.converter.row_to_collection_entry"


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
        "quantity": 1,
        "quality": "NM",
        "language": "EN",
        "rarity": "R",
        "color": "R",
        "extras": None,
        "created_at": datetime(2026, 1, 1),
    }
    defaults.update(overrides)
    row = MagicMock(spec=UserCollectionRow)
    for k, v in defaults.items():
        setattr(row, k, v)
    return row


def _make_converter():
    """Create a mock CurrencyConverter that returns BRL price as-is."""
    converter = MagicMock()
    converter.convert.side_effect = lambda price, dt, currency: price
    return converter


def _make_credit_svc():
    svc = MagicMock(spec=CreditService)
    svc.check_sufficient.return_value = True
    return svc


def _make_app(mock_repo: MagicMock, user_id: str = _TEST_USER_ID) -> FastAPI:
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_db] = lambda: mock_repo
    app.dependency_overrides[require_auth_or_api_key] = lambda: user_id
    app.dependency_overrides[get_current_user] = lambda: _TEST_USER
    app.dependency_overrides[get_credit_service] = _make_credit_svc
    app.dependency_overrides[get_currency_converter_dep] = _make_converter
    return app


def _make_collection_entry_mock():
    """Mock return value for row_to_collection_entry."""
    ce = MagicMock()
    ce.name_en = "Lightning Bolt"
    ce.name_pt = "Raio"
    return ce


def _make_match_result(status="matched", external_id="12345"):
    """Create a mock match result."""
    result = MagicMock()
    result.status = status
    if status == "matched":
        myp = MagicMock()
        myp.external_id = external_id
        myp.url = f"https://mypcards.com/magic/{external_id}/lightning-bolt"
        myp.sku = "magic_dmr_123"
        result.myp_result = myp
    else:
        result.myp_result = None
    return result


def _make_myp_source(external_id="12345"):
    """Create a mock MYP source card with all fields needed by SourceCardSchema."""
    sc = MagicMock()
    sc.source = "myp"
    sc.external_id = external_id
    sc.url = f"https://mypcards.com/magic/{external_id}/lightning-bolt"
    sc.sku = "magic_dmr_123"
    return sc


def _make_jsonld(price=10.50):
    """Create a mock JSON-LD result."""
    jsonld = MagicMock()
    jsonld.price = price
    return jsonld


class TestRefreshAutoCanonize:
    """POST /collection/{entry_id}/refresh — auto-canonize orphan entries."""

    @patch(_PATCH_PROVIDER)
    @patch(_PATCH_MATCHER)
    @patch(_PATCH_CONVERTER)
    def test_refresh_orphan_auto_canonizes_and_fetches_price(
        self, mock_converter, mock_match, mock_provider_cls
    ) -> None:
        """Entry has card_id but no MYP source. Auto-canonize succeeds,
        then price fetch proceeds normally."""
        mock_repo = MagicMock()
        orphan_row = _make_collection_row(card_id=42)
        # get_collection_entry called twice: once in refresh, once in _build_collection_detail
        mock_repo.get_collection_entry.side_effect = [orphan_row, orphan_row]
        # First call: no sources (triggers auto-canonize), second call: has source
        myp_source = _make_myp_source()
        mock_repo.get_source_cards_for_card.side_effect = [[], [myp_source], [myp_source]]
        mock_repo.get_latest_prices_batch.return_value = {}

        mock_converter.return_value = _make_collection_entry_mock()
        mock_match.return_value = _make_match_result(status="matched")

        # Two providers: one for auto-canonize, one for price fetch
        canonize_provider = AsyncMock()
        canonize_provider.search_card.return_value = [MagicMock()]
        canonize_provider.get_card_details.return_value = MagicMock()
        canonize_provider.close = AsyncMock()

        price_provider = AsyncMock()
        price_provider.fetch_current_price.return_value = _make_jsonld(10.50)
        price_provider.close = AsyncMock()

        mock_provider_cls.side_effect = [canonize_provider, price_provider]

        app = _make_app(mock_repo)
        client = TestClient(app)

        resp = client.post("/collection/1/refresh")
        assert resp.status_code == 200

        # Auto-canonize: provider called get_card_details and repo upserted
        canonize_provider.get_card_details.assert_called_once()
        mock_repo.upsert_card.assert_called_once()
        mock_repo.upsert_source_card.assert_called_once()

        # Price fetch: provider called fetch_current_price
        price_provider.fetch_current_price.assert_called_once()
        mock_repo.insert_price_observations.assert_called_once()

    @patch(_PATCH_PROVIDER)
    @patch(_PATCH_MATCHER)
    @patch(_PATCH_CONVERTER)
    def test_refresh_orphan_auto_canonize_match_fails_returns_422(
        self, mock_converter, mock_match, mock_provider_cls
    ) -> None:
        """Entry has card_id but no MYP source. Matcher returns unmatched.
        Should return 422 with auto-match failed message."""
        mock_repo = MagicMock()
        orphan_row = _make_collection_row(card_id=42)
        mock_repo.get_collection_entry.return_value = orphan_row
        mock_repo.get_source_cards_for_card.return_value = []

        mock_converter.return_value = _make_collection_entry_mock()
        mock_match.return_value = _make_match_result(status="no_match")

        mock_provider = AsyncMock()
        mock_provider.search_card.return_value = []
        mock_provider.close = AsyncMock()
        mock_provider_cls.return_value = mock_provider

        app = _make_app(mock_repo)
        client = TestClient(app)

        resp = client.post("/collection/1/refresh")
        assert resp.status_code == 422
        assert "auto-match failed" in resp.json()["detail"]

        mock_provider.close.assert_awaited_once()

    @patch(_PATCH_PROVIDER)
    @patch(_PATCH_MATCHER)
    @patch(_PATCH_CONVERTER)
    def test_refresh_orphan_auto_canonize_provider_error_returns_422(
        self, mock_converter, mock_match, mock_provider_cls
    ) -> None:
        """Entry has card_id but no MYP source. Provider raises exception.
        Should return 422 with auto-canonize failed message."""
        mock_repo = MagicMock()
        orphan_row = _make_collection_row(card_id=42)
        mock_repo.get_collection_entry.return_value = orphan_row
        mock_repo.get_source_cards_for_card.return_value = []

        mock_converter.return_value = _make_collection_entry_mock()

        mock_provider = AsyncMock()
        mock_provider.search_card.side_effect = ConnectionError("MYP timeout")
        mock_provider.close = AsyncMock()
        mock_provider_cls.return_value = mock_provider

        app = _make_app(mock_repo)
        client = TestClient(app)

        resp = client.post("/collection/1/refresh")
        assert resp.status_code == 422
        assert "auto-canonize failed" in resp.json()["detail"]
        assert "MYP timeout" in resp.json()["detail"]

        mock_provider.close.assert_awaited_once()

    @patch(_PATCH_PROVIDER)
    def test_refresh_with_existing_source_skips_auto_canonize(self, mock_provider_cls) -> None:
        """Entry has card_id AND MYP source. No auto-canonize, normal price fetch."""
        mock_repo = MagicMock()
        row = _make_collection_row(card_id=42)
        mock_repo.get_collection_entry.side_effect = [row, row]
        myp_source = _make_myp_source()
        mock_repo.get_source_cards_for_card.return_value = [myp_source]
        mock_repo.get_latest_prices_batch.return_value = {}

        mock_provider = AsyncMock()
        mock_provider.fetch_current_price.return_value = _make_jsonld(5.00)
        mock_provider.close = AsyncMock()
        mock_provider_cls.return_value = mock_provider

        app = _make_app(mock_repo)
        client = TestClient(app)

        resp = client.post("/collection/1/refresh")
        assert resp.status_code == 200

        # No search_card call — auto-canonize was not triggered
        mock_provider.search_card.assert_not_called()
        # Normal price fetch happened
        mock_provider.fetch_current_price.assert_called_once()

    def test_refresh_no_card_id_still_returns_422(self) -> None:
        """Entry has card_id=None. Should return 422 unchanged."""
        mock_repo = MagicMock()
        row = _make_collection_row(card_id=None)
        mock_repo.get_collection_entry.return_value = row

        app = _make_app(mock_repo)
        client = TestClient(app)

        resp = client.post("/collection/1/refresh")
        assert resp.status_code == 422
        assert resp.json()["detail"] == "Card not linked to a price source"

    @patch(_PATCH_PROVIDER)
    @patch(_PATCH_MATCHER)
    @patch(_PATCH_CONVERTER)
    def test_refresh_orphan_pt_fallback(
        self, mock_converter, mock_match, mock_provider_cls
    ) -> None:
        """Entry has card_id but no MYP source. EN search returns empty,
        PT search returns results. Auto-canonize succeeds via PT fallback."""
        mock_repo = MagicMock()
        orphan_row = _make_collection_row(card_id=42)
        mock_repo.get_collection_entry.side_effect = [orphan_row, orphan_row]
        myp_source = _make_myp_source()
        mock_repo.get_source_cards_for_card.side_effect = [[], [myp_source], [myp_source]]
        mock_repo.get_latest_prices_batch.return_value = {}

        ce = _make_collection_entry_mock()
        ce.name_en = "Abrade"
        ce.name_pt = "Abrasao"
        mock_converter.return_value = ce

        mock_match.return_value = _make_match_result(status="matched")

        # Two providers: canonize + price fetch
        canonize_provider = AsyncMock()
        canonize_provider.search_card.side_effect = [[], [MagicMock()]]
        canonize_provider.get_card_details.return_value = MagicMock()
        canonize_provider.close = AsyncMock()

        price_provider = AsyncMock()
        price_provider.fetch_current_price.return_value = _make_jsonld(3.00)
        price_provider.close = AsyncMock()

        mock_provider_cls.side_effect = [canonize_provider, price_provider]

        app = _make_app(mock_repo)
        client = TestClient(app)

        resp = client.post("/collection/1/refresh")
        assert resp.status_code == 200

        # search_card called twice: EN (empty) then PT (results)
        assert canonize_provider.search_card.call_count == 2
        canonize_provider.search_card.assert_any_call("Abrade")
        canonize_provider.search_card.assert_any_call("Abrasao")

    @patch(_PATCH_PROVIDER)
    @patch(_PATCH_MATCHER)
    @patch(_PATCH_CONVERTER)
    def test_refresh_orphan_auto_canonize_then_price_fetch(
        self, mock_converter, mock_match, mock_provider_cls
    ) -> None:
        """Full flow: auto-canonize succeeds, price fetch returns valid price.
        Assert repo.insert_price_observations called with correct data."""
        mock_repo = MagicMock()
        orphan_row = _make_collection_row(card_id=42)
        mock_repo.get_collection_entry.side_effect = [orphan_row, orphan_row]
        myp_source = _make_myp_source(external_id="99999")
        mock_repo.get_source_cards_for_card.side_effect = [[], [myp_source], [myp_source]]
        mock_repo.get_latest_prices_batch.return_value = {}

        mock_converter.return_value = _make_collection_entry_mock()
        mock_match.return_value = _make_match_result(status="matched", external_id="99999")

        canonize_provider = AsyncMock()
        canonize_provider.search_card.return_value = [MagicMock()]
        canonize_provider.get_card_details.return_value = MagicMock()
        canonize_provider.close = AsyncMock()

        price_provider = AsyncMock()
        price_provider.fetch_current_price.return_value = _make_jsonld(25.00)
        price_provider.close = AsyncMock()

        mock_provider_cls.side_effect = [canonize_provider, price_provider]

        app = _make_app(mock_repo)
        client = TestClient(app)

        resp = client.post("/collection/1/refresh")
        assert resp.status_code == 200

        # Verify insert_price_observations called with correct external_id and price
        mock_repo.insert_price_observations.assert_called_once()
        obs_list = mock_repo.insert_price_observations.call_args[0][0]
        assert len(obs_list) == 1
        assert obs_list[0].external_id == "99999"
        assert obs_list[0].median_price == 25.00
        assert obs_list[0].source == "jsonld_snapshot"

    @patch(_PATCH_PROVIDER)
    @patch(_PATCH_MATCHER)
    @patch(_PATCH_CONVERTER)
    def test_refresh_orphan_auto_canonize_get_details_returns_none(
        self, mock_converter, mock_match, mock_provider_cls
    ) -> None:
        """provider.get_card_details returns None. No source card created,
        falls through to 422."""
        mock_repo = MagicMock()
        orphan_row = _make_collection_row(card_id=42)
        mock_repo.get_collection_entry.return_value = orphan_row
        # First call: no sources, second call (after canonize attempt): still no sources
        mock_repo.get_source_cards_for_card.side_effect = [[], []]

        mock_converter.return_value = _make_collection_entry_mock()
        mock_match.return_value = _make_match_result(status="matched")

        mock_provider = AsyncMock()
        mock_provider.search_card.return_value = [MagicMock()]
        mock_provider.get_card_details.return_value = None  # details failed
        mock_provider.close = AsyncMock()
        mock_provider_cls.return_value = mock_provider

        app = _make_app(mock_repo)
        client = TestClient(app)

        resp = client.post("/collection/1/refresh")
        assert resp.status_code == 422
        assert "auto-canonize failed" in resp.json()["detail"]

        # upsert_card should NOT have been called since details was None
        mock_repo.upsert_card.assert_not_called()
        mock_provider.close.assert_awaited_once()
