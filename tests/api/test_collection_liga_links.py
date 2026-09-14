"""Tests for Liga Magic link generation in collection detail endpoint.

Per F124 (ADR 0012 — Liga fetched-URL persistence): the collection detail
endpoint serves the stored Liga URL recorded during the price fetch
(`liga_{card_id}` / `liga_{card_id}_foil`) rather than rebuilding one from
the (possibly stale/drifted) canonical card name. When no valid stored URL
exists, it falls back to a URL built from the same name used for the price
fetch (`entry.name_en`/`entry.name_pt`), matching what the sweep searched
for — even if that name has drifted from the linked CardRow.
"""

from __future__ import annotations

from datetime import datetime
from unittest.mock import MagicMock

from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.api.deps import get_db, require_auth_or_api_key
from src.api.routers.collection import router
from src.database.models import UserCollectionRow

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


def _make_app(mock_repo: MagicMock) -> FastAPI:
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_db] = lambda: mock_repo
    app.dependency_overrides[require_auth_or_api_key] = lambda: _TEST_USER_ID
    return app


def _base_repo(**collection_overrides) -> MagicMock:
    """A MagicMock repo with no stored Liga URL and no price data."""
    mock_repo = MagicMock()
    mock_repo.get_collection_entry.return_value = _make_collection_row(**collection_overrides)
    mock_repo.get_liga_card_url.return_value = None
    mock_repo.get_source_cards_for_card.return_value = []
    mock_repo.get_latest_prices_batch.return_value = {}
    return mock_repo


class TestLigaMagicLinkStoredUrl:
    def test_stored_url_served_verbatim(self) -> None:
        mock_repo = _base_repo(name_en="Arcane Signet", extras=None)
        mock_repo.get_liga_card_url.return_value = (
            "https://www.ligamagic.com.br/?view=cards/card&card=42&show=1"
        )

        client = TestClient(_make_app(mock_repo))
        resp = client.get("/collection/1")
        data = resp.json()["data"]

        assert data["ligamagic_url"] == (
            "https://www.ligamagic.com.br/?view=cards/card&card=42&show=1"
        )
        mock_repo.get_liga_card_url.assert_called_with("liga_42")

    def test_foil_entry_prefers_foil_stored_url(self) -> None:
        mock_repo = _base_repo(extras='{"foil": true}')

        def _get_liga_card_url(key: str) -> str | None:
            urls = {
                "liga_42_foil": "https://www.ligamagic.com.br/?view=cards/card&card=42f&show=1",
                "liga_42": "https://www.ligamagic.com.br/?view=cards/card&card=42&show=1",
            }
            return urls.get(key)

        mock_repo.get_liga_card_url.side_effect = _get_liga_card_url

        client = TestClient(_make_app(mock_repo))
        resp = client.get("/collection/1")
        data = resp.json()["data"]

        assert data["ligamagic_url"] == (
            "https://www.ligamagic.com.br/?view=cards/card&card=42f&show=1"
        )

    def test_foil_entry_falls_back_to_non_foil_stored_url(self) -> None:
        mock_repo = _base_repo(extras='{"foil": true}')

        def _get_liga_card_url(key: str) -> str | None:
            urls = {
                "liga_42": "https://www.ligamagic.com.br/?view=cards/card&card=42&show=1",
            }
            return urls.get(key)

        mock_repo.get_liga_card_url.side_effect = _get_liga_card_url

        client = TestClient(_make_app(mock_repo))
        resp = client.get("/collection/1")
        data = resp.json()["data"]

        assert data["ligamagic_url"] == (
            "https://www.ligamagic.com.br/?view=cards/card&card=42&show=1"
        )

    def test_foil_entry_falls_back_to_name_when_no_stored_url(self) -> None:
        mock_repo = _base_repo(extras='{"foil": true}', name_en="Sol Ring")

        client = TestClient(_make_app(mock_repo))
        resp = client.get("/collection/1")
        data = resp.json()["data"]

        assert "Sol+Ring" in data["ligamagic_url"]

    def test_stored_invalid_url_is_never_served(self) -> None:
        mock_repo = _base_repo(name_en="Arcane Signet")
        mock_repo.get_liga_card_url.return_value = "https://evil.com/?view=cards/card"

        client = TestClient(_make_app(mock_repo))
        resp = client.get("/collection/1")
        data = resp.json()["data"]

        assert "evil.com" not in data["ligamagic_url"]
        assert "Arcane+Signet" in data["ligamagic_url"]


class TestLigaMagicLinkNameFallback:
    def test_drifted_entry_name_used_over_card_row_name(self) -> None:
        """Even when card_id is linked, fallback uses entry name (same as price fetch)."""
        mock_repo = _base_repo(name_en="Arcane Signet")

        client = TestClient(_make_app(mock_repo))
        resp = client.get("/collection/1")
        data = resp.json()["data"]

        assert "Arcane+Signet" in data["ligamagic_url"]
        # get_card_by_id (canonical name lookup) is no longer used for Liga
        mock_repo.get_card_by_id.assert_not_called()

    def test_no_card_id_uses_entry_name_without_repo_lookup(self) -> None:
        mock_repo = _base_repo(card_id=None, name_en="Sol Ring")

        client = TestClient(_make_app(mock_repo))
        resp = client.get("/collection/1")
        data = resp.json()["data"]

        assert "Sol+Ring" in data["ligamagic_url"]
        assert "&show=1" in data["ligamagic_url"]
        mock_repo.get_liga_card_url.assert_not_called()

    def test_falls_back_to_name_pt_when_name_en_missing(self) -> None:
        mock_repo = _base_repo(name_en=None, name_pt="Anel Solar")

        client = TestClient(_make_app(mock_repo))
        resp = client.get("/collection/1")
        data = resp.json()["data"]

        assert "Anel+Solar" in data["ligamagic_url"]

    def test_no_names_yields_null_ligamagic_url(self) -> None:
        mock_repo = _base_repo(card_id=None, name_en=None, name_pt=None)

        client = TestClient(_make_app(mock_repo))
        resp = client.get("/collection/1")
        data = resp.json()["data"]

        assert data["ligamagic_url"] is None

    def test_special_chars_encoded(self) -> None:
        mock_repo = _base_repo(name_en="Dain, Dwarven King")

        client = TestClient(_make_app(mock_repo))
        resp = client.get("/collection/1")
        data = resp.json()["data"]

        assert "Dain%2C+Dwarven+King" in data["ligamagic_url"]

    def test_scryfall_url_still_uses_entry_name(self) -> None:
        mock_repo = _base_repo(name_en="Arcane Signet")

        client = TestClient(_make_app(mock_repo))
        resp = client.get("/collection/1")
        data = resp.json()["data"]

        assert "Arcane+Signet" in data["scryfall_url"]
