"""Tests for Liga Magic link generation in collection detail endpoint.

Ensures that Liga URLs use the canonical card name from the cards table,
not the potentially stale name from user_collection.
"""

from __future__ import annotations

from datetime import datetime
from unittest.mock import MagicMock

from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.api.deps import get_db, require_auth_or_api_key
from src.api.routers.collection import router
from src.database.models import CardRow, UserCollectionRow

_TEST_USER_ID = "eduardo"


def _make_collection_row(**overrides) -> MagicMock:
    defaults = {
        "id": 1,
        "user_id": _TEST_USER_ID,
        "card_id": 42,
        "set_code": "DMR",
        "collector_number": "123",
        "name_en": "Arcane Signet",
        "name_pt": "Sinete Arcano",
        "set_name_en": "Dominaria Remastered",
        "quantity": 1,
        "quality": "NM",
        "language": "EN",
        "rarity": "R",
        "color": "C",
        "extras": None,
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
        "name": "Dain, Rei dos Anoes",
        "name_en": "Dain, Dwarven King",
        "set_code": "DMR",
    }
    defaults.update(overrides)
    row = MagicMock(spec=CardRow)
    for k, v in defaults.items():
        setattr(row, k, v)
    return row


def _make_app(mock_repo: MagicMock) -> FastAPI:
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_db] = lambda: mock_repo
    app.dependency_overrides[require_auth_or_api_key] = lambda: _TEST_USER_ID
    return app


class TestLigaMagicLinkFromCardsTable:
    """Liga Magic URL must use canonical name from cards table, not user_collection."""

    def test_liga_url_uses_cards_table_name(self) -> None:
        """When card_id points to a CardRow, ligamagic_url uses CardRow.name_en."""
        mock_repo = MagicMock()
        # entry.name_en = "Arcane Signet" (wrong/stale)
        mock_repo.get_collection_entry.return_value = _make_collection_row(
            name_en="Arcane Signet",
        )
        # CardRow.name_en = "Dain, Dwarven King" (correct)
        mock_repo.get_card_by_id.return_value = _make_card_row(
            name_en="Dain, Dwarven King",
        )
        mock_repo.get_source_cards_for_card.return_value = []
        mock_repo.get_latest_prices_batch.return_value = {}

        client = TestClient(_make_app(mock_repo))
        resp = client.get("/collection/1")
        data = resp.json()["data"]

        # Liga URL must use the canonical name, not "Arcane Signet"
        assert "Arcane+Signet" not in data["ligamagic_url"]
        assert "Dain%2C+Dwarven+King" in data["ligamagic_url"]
        assert "&show=1" in data["ligamagic_url"]

    def test_liga_url_encoding_special_chars(self) -> None:
        """Card names with commas, apostrophes, and spaces are URL-encoded."""
        mock_repo = MagicMock()
        mock_repo.get_collection_entry.return_value = _make_collection_row()
        mock_repo.get_card_by_id.return_value = _make_card_row(
            name_en="Thalia, Guardian of Thraben",
        )
        mock_repo.get_source_cards_for_card.return_value = []
        mock_repo.get_latest_prices_batch.return_value = {}

        client = TestClient(_make_app(mock_repo))
        resp = client.get("/collection/1")
        data = resp.json()["data"]

        assert "Thalia%2C+Guardian+of+Thraben" in data["ligamagic_url"]

    def test_liga_url_fallback_to_card_name_when_name_en_null(self) -> None:
        """When CardRow.name_en is None, fallback to CardRow.name (Portuguese)."""
        mock_repo = MagicMock()
        mock_repo.get_collection_entry.return_value = _make_collection_row()
        mock_repo.get_card_by_id.return_value = _make_card_row(
            name_en=None,
            name="Dain, Rei dos Anoes",
        )
        mock_repo.get_source_cards_for_card.return_value = []
        mock_repo.get_latest_prices_batch.return_value = {}

        client = TestClient(_make_app(mock_repo))
        resp = client.get("/collection/1")
        data = resp.json()["data"]

        assert "Dain%2C+Rei+dos+Anoes" in data["ligamagic_url"]

    def test_liga_url_fallback_to_entry_when_card_id_none(self) -> None:
        """When card_id is None (unlinked), use entry.name_en as fallback."""
        mock_repo = MagicMock()
        mock_repo.get_collection_entry.return_value = _make_collection_row(
            card_id=None,
            name_en="Sol Ring",
        )

        client = TestClient(_make_app(mock_repo))
        resp = client.get("/collection/1")
        data = resp.json()["data"]

        assert "Sol+Ring" in data["ligamagic_url"]
        assert "&show=1" in data["ligamagic_url"]
        # get_card_by_id should NOT be called when card_id is None
        mock_repo.get_card_by_id.assert_not_called()

    def test_liga_url_fallback_to_entry_name_pt_when_card_not_found(self) -> None:
        """When get_card_by_id returns None, use entry.name_pt."""
        mock_repo = MagicMock()
        mock_repo.get_collection_entry.return_value = _make_collection_row(
            name_en=None,
            name_pt="Anel Solar",
        )
        mock_repo.get_card_by_id.return_value = None
        mock_repo.get_source_cards_for_card.return_value = []
        mock_repo.get_latest_prices_batch.return_value = {}

        client = TestClient(_make_app(mock_repo))
        resp = client.get("/collection/1")
        data = resp.json()["data"]

        assert "Anel+Solar" in data["ligamagic_url"]

    def test_scryfall_url_still_uses_entry_name(self) -> None:
        """Scryfall URL should still use the entry's name_en (for set filtering)."""
        mock_repo = MagicMock()
        mock_repo.get_collection_entry.return_value = _make_collection_row(
            name_en="Arcane Signet",
        )
        mock_repo.get_card_by_id.return_value = _make_card_row(
            name_en="Dain, Dwarven King",
        )
        mock_repo.get_source_cards_for_card.return_value = []
        mock_repo.get_latest_prices_batch.return_value = {}

        client = TestClient(_make_app(mock_repo))
        resp = client.get("/collection/1")
        data = resp.json()["data"]

        # Scryfall uses entry name (for now), Liga uses canonical name
        assert "Arcane+Signet" in data["scryfall_url"]
        assert "Dain%2C+Dwarven+King" in data["ligamagic_url"]

    def test_apostrophe_in_card_name(self) -> None:
        """Card name with apostrophe is properly URL-encoded."""
        mock_repo = MagicMock()
        mock_repo.get_collection_entry.return_value = _make_collection_row()
        mock_repo.get_card_by_id.return_value = _make_card_row(
            name_en="Frodo's Ring",
        )
        mock_repo.get_source_cards_for_card.return_value = []
        mock_repo.get_latest_prices_batch.return_value = {}

        client = TestClient(_make_app(mock_repo))
        resp = client.get("/collection/1")
        data = resp.json()["data"]

        # quote_plus encodes apostrophe as %27
        assert "Frodo%27s+Ring" in data["ligamagic_url"]
