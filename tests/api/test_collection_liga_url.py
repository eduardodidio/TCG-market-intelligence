"""Tests for Liga URL resolution in collection detail endpoint.

Verifies that _build_collection_detail uses resolve_liga_card_url
(stored URL lookup with foil awareness) instead of a plain name-based fallback.
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from unittest.mock import MagicMock

from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.api.deps import get_db, require_auth_or_api_key
from src.api.routers.collection import router
from src.database.models import CardRow, PriceObservationRow, UserCollectionRow

_TEST_USER_ID = "eduardo"
_STORED_LIGA_URL = "https://www.ligamagic.com.br/?view=cards/card&card=Lightning+Bolt&show=1"
_STORED_FOIL_URL = "https://www.ligamagic.com.br/?view=cards/card&card=Lightning+Bolt+Foil&show=1"


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
        "extras": "",
        "created_at": datetime(2026, 1, 1),
    }
    defaults.update(overrides)
    row = MagicMock(spec=UserCollectionRow)
    for k, v in defaults.items():
        setattr(row, k, v)
    return row


def _make_card_row(**overrides) -> MagicMock:
    defaults = {
        "id": 42,
        "name": "Raio",
        "name_en": "Lightning Bolt",
        "set_code": "DMR",
    }
    defaults.update(overrides)
    row = MagicMock(spec=CardRow)
    for k, v in defaults.items():
        setattr(row, k, v)
    return row


def _make_price_obs(**overrides) -> MagicMock:
    defaults = {
        "id": 100,
        "source": "liga",
        "external_id": "liga_42",
        "observed_at": date(2026, 8, 20),
        "median_price": Decimal("8.50"),
        "tcg_price": None,
        "last_sold_price": None,
        "quantity_available": 5,
        "last_sold_meta": None,
        "currency": "BRL",
    }
    defaults.update(overrides)
    obs = MagicMock(spec=PriceObservationRow)
    for k, v in defaults.items():
        setattr(obs, k, v)
    return obs


def _setup_repo(mock_repo: MagicMock, entry_overrides: dict | None = None) -> None:
    """Wire up standard repo mock returns."""
    entry = _make_collection_row(**(entry_overrides or {}))
    mock_repo.get_collection_entry.return_value = entry
    mock_repo.get_card_by_id.return_value = _make_card_row()
    mock_repo.get_source_cards_for_card.return_value = []
    mock_repo.get_latest_prices_batch.return_value = {}


def _make_app(mock_repo: MagicMock) -> FastAPI:
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_db] = lambda: mock_repo
    app.dependency_overrides[require_auth_or_api_key] = lambda: _TEST_USER_ID
    return app


class TestCollectionDetailLigaUrl:
    """GET /collection/{entry_id} — Liga URL resolution."""

    def test_collection_detail_uses_stored_liga_url(self) -> None:
        """When a stored Liga URL exists for the card, it should be returned."""
        mock_repo = MagicMock()
        _setup_repo(mock_repo)
        mock_repo.get_liga_card_url.side_effect = (
            lambda ext_id: _STORED_LIGA_URL if ext_id == "liga_42" else None
        )

        client = TestClient(_make_app(mock_repo))
        resp = client.get("/collection/1")
        assert resp.status_code == 200

        data = resp.json()["data"]
        assert data["ligamagic_url"] == _STORED_LIGA_URL
        mock_repo.get_liga_card_url.assert_called()

    def test_collection_detail_foil_prefers_foil_url(self) -> None:
        """Foil entries should try the foil external_id first."""
        mock_repo = MagicMock()
        _setup_repo(mock_repo, entry_overrides={"extras": "Foil"})

        def _lookup(ext_id: str) -> str | None:
            if ext_id == "liga_42_foil":
                return _STORED_FOIL_URL
            if ext_id == "liga_42":
                return _STORED_LIGA_URL
            return None

        mock_repo.get_liga_card_url.side_effect = _lookup

        client = TestClient(_make_app(mock_repo))
        resp = client.get("/collection/1")
        assert resp.status_code == 200

        data = resp.json()["data"]
        # Should prefer the foil URL
        assert data["ligamagic_url"] == _STORED_FOIL_URL

    def test_collection_detail_unlinked_entry_uses_name_fallback(self) -> None:
        """Entries without a card_id should fall back to name-based URL."""
        mock_repo = MagicMock()
        _setup_repo(mock_repo, entry_overrides={"card_id": None})
        # No card row lookup for unlinked entries
        mock_repo.get_card_by_id.return_value = None

        client = TestClient(_make_app(mock_repo))
        resp = client.get("/collection/1")
        assert resp.status_code == 200

        data = resp.json()["data"]
        # Should build a name-based URL since card_id is None
        assert data["ligamagic_url"] is not None
        assert "Lightning+Bolt" in data["ligamagic_url"]
        assert "view=cards/card" in data["ligamagic_url"]
        # get_liga_card_url should NOT have been called (no card_id to look up)
        mock_repo.get_liga_card_url.assert_not_called()

    def test_collection_detail_no_name_no_url_returns_none(self) -> None:
        """Entry with no card_id and no name should yield no Liga URL."""
        mock_repo = MagicMock()
        _setup_repo(
            mock_repo,
            entry_overrides={
                "card_id": None,
                "name_en": None,
                "name_pt": None,
            },
        )
        mock_repo.get_card_by_id.return_value = None

        client = TestClient(_make_app(mock_repo))
        resp = client.get("/collection/1")
        assert resp.status_code == 200

        data = resp.json()["data"]
        assert data["ligamagic_url"] is None
