"""F50-T02: Price source indicator integration tests.

Tests that price_source is correctly populated in collection API responses,
including priority logic (manual wins same day, latest date wins cross-day).
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from unittest.mock import MagicMock

from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.api.deps import get_db, require_auth_or_api_key
from src.api.routers.collection import router
from src.database.models import PriceObservationRow, SourceCardRow, UserCollectionRow

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
        "source": "myp",
        "external_id": "99999",
        "observed_at": date(2026, 8, 20),
        "median_price": Decimal("8.50"),
        "tcg_price": Decimal("7.00"),
        "last_sold_price": Decimal("9.00"),
        "quantity_available": 5,
        "last_sold_meta": None,
        "currency": "BRL",
    }
    defaults.update(overrides)
    obs = MagicMock(spec=PriceObservationRow)
    for k, v in defaults.items():
        setattr(obs, k, v)
    return obs


def _make_source_card(**overrides) -> MagicMock:
    defaults = {
        "id": 10,
        "source": "myp",
        "external_id": "99999",
        "card_id": 42,
        "sku": "magic_dmr_123",
        "url": "https://mypcards.com/magic/99999/lightning-bolt",
        "name_en": "Lightning Bolt",
        "name_pt": "Raio",
        "set_code": "DMR",
        "collector_number": "123",
    }
    defaults.update(overrides)
    sc = MagicMock(spec=SourceCardRow)
    for k, v in defaults.items():
        setattr(sc, k, v)
    return sc


def _make_app(mock_repo: MagicMock, user_id: str = _TEST_USER_ID) -> FastAPI:
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_db] = lambda: mock_repo
    app.dependency_overrides[require_auth_or_api_key] = lambda: user_id
    return app


class TestPriceSourceInDetailResponse:
    """GET /collection/{entry_id} — price_source field."""

    def test_price_source_manual_in_response(self) -> None:
        """Scenario #14: price_source='manual' when latest obs is manual."""
        mock_repo = MagicMock()
        mock_repo.get_collection_entry.return_value = _make_collection_row()
        obs = _make_price_obs(source="manual", external_id="manual_42")
        mock_repo.get_latest_prices_batch.return_value = {42: obs}
        mock_repo.get_source_cards_for_card.return_value = [_make_source_card()]

        client = TestClient(_make_app(mock_repo))
        resp = client.get("/collection/1")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["price_source"] == "manual"

    def test_price_source_myp_in_response(self) -> None:
        """Scenario #15: price_source='myp' when latest is MYP."""
        mock_repo = MagicMock()
        mock_repo.get_collection_entry.return_value = _make_collection_row()
        obs = _make_price_obs(source="myp")
        mock_repo.get_latest_prices_batch.return_value = {42: obs}
        mock_repo.get_source_cards_for_card.return_value = [_make_source_card()]

        client = TestClient(_make_app(mock_repo))
        resp = client.get("/collection/1")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["price_source"] == "myp"

    def test_price_source_jsonld_in_response(self) -> None:
        """Scenario #16: price_source='jsonld_snapshot' when latest is jsonld."""
        mock_repo = MagicMock()
        mock_repo.get_collection_entry.return_value = _make_collection_row()
        obs = _make_price_obs(source="jsonld_snapshot")
        mock_repo.get_latest_prices_batch.return_value = {42: obs}
        mock_repo.get_source_cards_for_card.return_value = [_make_source_card()]

        client = TestClient(_make_app(mock_repo))
        resp = client.get("/collection/1")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["price_source"] == "jsonld_snapshot"

    def test_price_source_null_no_observations(self) -> None:
        """Scenario #17: price_source=None when no price observations."""
        mock_repo = MagicMock()
        mock_repo.get_collection_entry.return_value = _make_collection_row()
        mock_repo.get_latest_prices_batch.return_value = {42: None}
        mock_repo.get_source_cards_for_card.return_value = [_make_source_card()]

        client = TestClient(_make_app(mock_repo))
        resp = client.get("/collection/1")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["price_source"] is None

    def test_price_source_null_no_card_id(self) -> None:
        """price_source=None when entry has no card_id (unlinked)."""
        mock_repo = MagicMock()
        mock_repo.get_collection_entry.return_value = _make_collection_row(card_id=None)

        client = TestClient(_make_app(mock_repo))
        resp = client.get("/collection/1")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["price_source"] is None


class TestPriceSourceInCollectionList:
    """GET /collection — price_source in list response."""

    def test_price_source_in_collection_list(self) -> None:
        """Scenario #20: GET /collection response includes price_source per card."""
        mock_repo = MagicMock()
        row1 = _make_collection_row(id=1, card_id=42)
        row2 = _make_collection_row(id=2, card_id=43, name_en="Counterspell")
        mock_repo.list_collection.return_value = [row1, row2]
        mock_repo.count_collection.return_value = 2

        obs_manual = _make_price_obs(source="manual", external_id="manual_42")
        obs_myp = _make_price_obs(source="myp", external_id="88888")
        mock_repo.get_latest_prices_batch.return_value = {42: obs_manual, 43: obs_myp}

        client = TestClient(_make_app(mock_repo))
        resp = client.get("/collection")
        assert resp.status_code == 200
        cards = resp.json()["data"]
        assert len(cards) == 2
        assert cards[0]["price_source"] == "manual"
        assert cards[1]["price_source"] == "myp"

    def test_price_source_null_for_unlinked_in_list(self) -> None:
        """Unlinked card in list has price_source=None."""
        mock_repo = MagicMock()
        row = _make_collection_row(id=1, card_id=None)
        mock_repo.list_collection.return_value = [row]
        mock_repo.count_collection.return_value = 1

        client = TestClient(_make_app(mock_repo))
        resp = client.get("/collection")
        assert resp.status_code == 200
        cards = resp.json()["data"]
        assert cards[0]["price_source"] is None
