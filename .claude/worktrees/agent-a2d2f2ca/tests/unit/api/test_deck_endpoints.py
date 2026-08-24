"""Tests for the decks API router."""

from __future__ import annotations

from datetime import datetime
from unittest.mock import MagicMock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.api.deps import get_db, require_auth_or_api_key
from src.api.routers.decks import router

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_app(user_id: str = "user1") -> FastAPI:
    app = FastAPI()
    app.include_router(router)

    mock_repo = MagicMock()
    app.dependency_overrides[get_db] = lambda: mock_repo
    app.dependency_overrides[require_auth_or_api_key] = lambda: user_id

    # Store mock_repo for access in tests
    app.state.mock_repo = mock_repo
    return app


def _mock_deck(deck_id=1, user_id="user1", name="Test Deck", description=None):
    deck = MagicMock()
    deck.id = deck_id
    deck.user_id = user_id
    deck.name = name
    deck.description = description
    deck.created_at = datetime(2026, 8, 21, 12, 0, 0)
    deck.updated_at = datetime(2026, 8, 21, 12, 0, 0)
    return deck


# ---------------------------------------------------------------------------
# POST /decks — import
# ---------------------------------------------------------------------------


class TestImportDeck:
    @patch("src.decks.importer.import_deck_from_text")
    def test_import_text_deck(self, mock_import):
        mock_import.return_value = {
            "deck_id": 1,
            "name": "My Deck",
            "cards_imported": 4,
            "cards_linked": 2,
        }

        app = _make_app()
        client = TestClient(app)

        resp = client.post(
            "/decks",
            json={"name": "My Deck", "content": "4 Lightning Bolt"},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["data"]["deck_id"] == 1
        assert body["data"]["cards_imported"] == 4
        mock_import.assert_called_once()

    @patch("src.decks.importer.import_deck_from_csv")
    def test_import_csv_deck(self, mock_import):
        mock_import.return_value = {
            "deck_id": 2,
            "name": "CSV Deck",
            "cards_imported": 3,
            "cards_linked": 1,
        }

        app = _make_app()
        client = TestClient(app)

        resp = client.post(
            "/decks",
            json={
                "name": "CSV Deck",
                "format": "csv",
                "content": "Card (EN),Quantidade\nBolt,4",
            },
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["data"]["deck_id"] == 2
        mock_import.assert_called_once()

    def test_import_empty_name_fails(self):
        app = _make_app()
        client = TestClient(app)

        resp = client.post("/decks", json={"name": "", "content": "4 Bolt"})
        assert resp.status_code == 422

    def test_import_empty_content_fails(self):
        app = _make_app()
        client = TestClient(app)

        resp = client.post("/decks", json={"name": "Deck", "content": ""})
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# GET /decks — list
# ---------------------------------------------------------------------------


class TestListDecks:
    def test_list_decks(self):
        app = _make_app()
        mock_repo = app.state.mock_repo
        mock_repo.list_decks.return_value = [_mock_deck(1), _mock_deck(2, name="Deck 2")]
        mock_repo.get_deck_summary.return_value = {
            "total_cards": 60,
            "unique_cards": 15,
            "owned_cards": 10,
            "ownership_pct": 66.67,
        }

        client = TestClient(app)
        resp = client.get("/decks")
        assert resp.status_code == 200
        body = resp.json()
        assert len(body["data"]) == 2
        assert body["data"][0]["total_cards"] == 60

    def test_list_empty(self):
        app = _make_app()
        mock_repo = app.state.mock_repo
        mock_repo.list_decks.return_value = []

        client = TestClient(app)
        resp = client.get("/decks")
        assert resp.status_code == 200
        assert resp.json()["data"] == []


# ---------------------------------------------------------------------------
# GET /decks/{deck_id} — detail
# ---------------------------------------------------------------------------


class TestGetDeck:
    def _setup_get_deck(self, app):
        from src.api.deps import get_currency_converter_dep

        mock_converter = MagicMock()
        mock_converter.convert.return_value = None
        app.dependency_overrides[get_currency_converter_dep] = lambda: mock_converter

        mock_repo = app.state.mock_repo
        mock_repo.get_deck.return_value = _mock_deck(1)
        mock_repo.get_deck_cards_with_ownership.return_value = [
            {
                "id": 1,
                "deck_id": 1,
                "name_en": "Lightning Bolt",
                "set_code": "lea",
                "collector_number": "161",
                "quantity": 4,
                "card_id": None,
                "in_collection": True,
                "owned_quantity": 3,
                "collection_entry_id": 100,
            }
        ]
        mock_repo.get_deck_summary.return_value = {
            "total_cards": 4,
            "unique_cards": 1,
            "owned_cards": 1,
            "ownership_pct": 100.0,
        }
        mock_repo.get_latest_prices_batch.return_value = {}
        return mock_repo

    def test_get_deck(self):
        app = _make_app()
        self._setup_get_deck(app)

        client = TestClient(app)
        resp = client.get("/decks/1")
        assert resp.status_code == 200
        body = resp.json()
        assert body["data"]["id"] == 1
        assert body["data"]["name"] == "Test Deck"
        assert len(body["data"]["cards"]) == 1
        assert body["data"]["cards"][0]["in_collection"] is True

    def test_get_deck_not_found(self):
        app = _make_app()
        from src.api.deps import get_currency_converter_dep

        app.dependency_overrides[get_currency_converter_dep] = lambda: MagicMock()
        app.state.mock_repo.get_deck.return_value = None

        client = TestClient(app)
        resp = client.get("/decks/999")
        assert resp.status_code == 404

    def test_get_deck_wrong_user(self):
        app = _make_app(user_id="user1")
        from src.api.deps import get_currency_converter_dep

        app.dependency_overrides[get_currency_converter_dep] = lambda: MagicMock()
        app.state.mock_repo.get_deck.return_value = _mock_deck(1, user_id="user2")

        client = TestClient(app)
        resp = client.get("/decks/1")
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# DELETE /decks/{deck_id}
# ---------------------------------------------------------------------------


class TestDeleteDeck:
    def test_delete_deck(self):
        app = _make_app()
        app.state.mock_repo.delete_deck.return_value = True

        client = TestClient(app)
        resp = client.delete("/decks/1")
        assert resp.status_code == 204

    def test_delete_deck_not_found(self):
        app = _make_app()
        app.state.mock_repo.delete_deck.return_value = False

        client = TestClient(app)
        resp = client.delete("/decks/999")
        assert resp.status_code == 404
