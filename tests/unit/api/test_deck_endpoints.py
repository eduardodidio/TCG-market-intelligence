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


# ---------------------------------------------------------------------------
# GET /decks/{deck_id}/evaluate — F133-T03
# ---------------------------------------------------------------------------


def _mock_deck_card(card_id=1, name="Lightning Bolt", qty=4):
    """Create a mock DeckCardRow."""
    dc = MagicMock()
    dc.card_id = card_id
    dc.name_en = name
    dc.quantity = qty
    return dc


def _mock_card_row(card_id=1, name="Lightning Bolt"):
    """Create a mock CardRow with standard attributes."""
    cr = MagicMock()
    cr.id = card_id
    cr.name_en = name
    cr.mana_cost = "{R}"
    cr.type_line = "Instant"
    cr.color_identity = "R"
    cr.rarity = "common"
    return cr


class TestEvaluateDeck:
    def test_evaluate_returns_valid_data(self):
        app = _make_app()
        mock_repo = app.state.mock_repo
        mock_repo.get_deck.return_value = _mock_deck(1)

        dc1 = _mock_deck_card(card_id=10, name="Lightning Bolt", qty=4)
        dc2 = _mock_deck_card(card_id=20, name="Mountain", qty=36)
        mock_repo.get_deck_cards.return_value = [dc1, dc2]

        cr_bolt = _mock_card_row(10, "Lightning Bolt")
        cr_bolt.mana_cost = "{R}"
        cr_bolt.type_line = "Instant"

        cr_mountain = _mock_card_row(20, "Mountain")
        cr_mountain.mana_cost = None
        cr_mountain.type_line = "Basic Land"
        cr_mountain.color_identity = None

        mock_repo.get_card_by_id.side_effect = lambda cid: {
            10: cr_bolt,
            20: cr_mountain,
        }.get(cid)

        mock_repo.get_latest_prices_batch.return_value = {}
        mock_repo.get_legalities_for_cards_batch.return_value = {}

        client = TestClient(app)
        resp = client.get("/decks/1/evaluate")
        assert resp.status_code == 200
        body = resp.json()["data"]
        assert body["deck_id"] == 1
        assert body["total_cards"] == 40
        assert body["land_count"] == 36
        assert body["nonland_count"] == 4
        assert isinstance(body["mana_curve"], list)
        assert isinstance(body["type_distribution"], list)
        assert isinstance(body["color_distribution"], list)

    def test_evaluate_not_found(self):
        app = _make_app()
        mock_repo = app.state.mock_repo
        mock_repo.get_deck.return_value = None

        client = TestClient(app)
        resp = client.get("/decks/999/evaluate")
        assert resp.status_code == 404

    def test_evaluate_wrong_user(self):
        app = _make_app(user_id="user1")
        mock_repo = app.state.mock_repo
        mock_repo.get_deck.return_value = _mock_deck(1, user_id="user2")

        client = TestClient(app)
        resp = client.get("/decks/1/evaluate")
        assert resp.status_code == 404

    def test_evaluate_empty_deck(self):
        app = _make_app()
        mock_repo = app.state.mock_repo
        mock_repo.get_deck.return_value = _mock_deck(1)
        mock_repo.get_deck_cards.return_value = []
        mock_repo.get_latest_prices_batch.return_value = {}
        mock_repo.get_legalities_for_cards_batch.return_value = {}

        client = TestClient(app)
        resp = client.get("/decks/1/evaluate")
        assert resp.status_code == 200
        body = resp.json()["data"]
        assert body["total_cards"] == 0
        assert body["avg_cmc"] == 0.0

    def test_evaluate_with_format_legality(self):
        app = _make_app()
        mock_repo = app.state.mock_repo
        mock_repo.get_deck.return_value = _mock_deck(1)

        dc1 = _mock_deck_card(card_id=10, name="Sol Ring", qty=1)
        mock_repo.get_deck_cards.return_value = [dc1]

        cr = _mock_card_row(10, "Sol Ring")
        cr.mana_cost = "{1}"
        cr.type_line = "Artifact"
        cr.color_identity = None
        mock_repo.get_card_by_id.return_value = cr

        mock_repo.get_latest_prices_batch.return_value = {}
        mock_repo.get_legalities_for_cards_batch.return_value = {
            10: [{"format": "commander", "status": "legal"}],
        }

        client = TestClient(app)
        resp = client.get("/decks/1/evaluate?format=commander")
        assert resp.status_code == 200
        body = resp.json()["data"]
        assert body["legality"] is not None
        assert body["legality"]["format"] == "commander"

    def test_evaluate_no_format_legality_is_none(self):
        app = _make_app()
        mock_repo = app.state.mock_repo
        mock_repo.get_deck.return_value = _mock_deck(1)
        mock_repo.get_deck_cards.return_value = []
        mock_repo.get_latest_prices_batch.return_value = {}
        mock_repo.get_legalities_for_cards_batch.return_value = {}

        client = TestClient(app)
        resp = client.get("/decks/1/evaluate")
        assert resp.status_code == 200
        body = resp.json()["data"]
        assert body["legality"] is None

    def test_evaluate_with_budget(self):
        app = _make_app()
        mock_repo = app.state.mock_repo
        mock_repo.get_deck.return_value = _mock_deck(1)

        dc1 = _mock_deck_card(card_id=10, name="Sol Ring", qty=1)
        mock_repo.get_deck_cards.return_value = [dc1]

        cr = _mock_card_row(10, "Sol Ring")
        cr.mana_cost = "{1}"
        cr.type_line = "Artifact"
        cr.color_identity = None
        mock_repo.get_card_by_id.return_value = cr

        obs = MagicMock()
        obs.median_price = 25.0
        mock_repo.get_latest_prices_batch.return_value = {10: obs}
        mock_repo.get_legalities_for_cards_batch.return_value = {}

        client = TestClient(app)
        resp = client.get("/decks/1/evaluate")
        assert resp.status_code == 200
        body = resp.json()["data"]
        assert body["budget"] is not None
        assert body["budget"]["total_value"] == 25.0
        assert len(body["budget"]["most_expensive"]) == 1

    def test_evaluate_unlinked_cards_warning(self):
        app = _make_app()
        mock_repo = app.state.mock_repo
        mock_repo.get_deck.return_value = _mock_deck(1)

        dc1 = _mock_deck_card(card_id=None, name="Unknown Card", qty=1)
        mock_repo.get_deck_cards.return_value = [dc1]
        mock_repo.get_latest_prices_batch.return_value = {}
        mock_repo.get_legalities_for_cards_batch.return_value = {}

        client = TestClient(app)
        resp = client.get("/decks/1/evaluate")
        assert resp.status_code == 200
        body = resp.json()["data"]
        assert len(body["suggestions"]) > 0
        assert "not linked" in body["suggestions"][0].lower()


# ---------------------------------------------------------------------------
# POST /decks/generate — F133-T04
# ---------------------------------------------------------------------------


class TestGenerateDeck:
    @patch("src.decks.builder.generate_deck")
    def test_generate_valid_commander(self, mock_gen):
        from src.domain.models import GeneratedDeck

        mock_gen.return_value = GeneratedDeck(
            cards=[
                {
                    "card_id": 1,
                    "name_en": "Sol Ring",
                    "set_code": "cmr",
                    "collector_number": "472",
                    "quantity": 1,
                    "mana_cost": "{1}",
                    "type_line": "Artifact",
                    "rarity": "uncommon",
                    "image_uri": None,
                    "price": 10.0,
                    "is_owned": False,
                },
            ],
            format_name="commander",
            archetype="control",
            colors=["U", "W"],
            total_value=None,
            land_count=37,
            nonland_count=62,
            warnings=[],
        )

        app = _make_app()
        mock_repo = app.state.mock_repo

        # Commander validation
        commander = MagicMock()
        commander.name_en = "Atraxa"
        commander.type_line = "Legendary Creature"
        mock_repo.get_card_by_id.return_value = commander

        saved_deck = _mock_deck(42)
        mock_repo.create_deck.return_value = saved_deck
        mock_repo.add_deck_cards.return_value = 1

        client = TestClient(app)
        resp = client.post(
            "/decks/generate",
            json={
                "format_name": "commander",
                "commander_card_id": 100,
                "colors": ["W", "U"],
                "archetype": "control",
            },
        )
        assert resp.status_code == 200
        body = resp.json()["data"]
        assert body["deck_id"] == 42
        assert body["format_name"] == "commander"
        assert len(body["cards"]) == 1
        mock_gen.assert_called_once()

    def test_generate_invalid_format(self):
        app = _make_app()
        client = TestClient(app)
        resp = client.post(
            "/decks/generate",
            json={"format_name": "invalid_format"},
        )
        assert resp.status_code == 400

    def test_generate_invalid_commander_not_legendary(self):
        app = _make_app()
        mock_repo = app.state.mock_repo

        card = MagicMock()
        card.name_en = "Lightning Bolt"
        card.type_line = "Instant"
        mock_repo.get_card_by_id.return_value = card

        client = TestClient(app)
        resp = client.post(
            "/decks/generate",
            json={
                "format_name": "commander",
                "commander_card_id": 999,
            },
        )
        assert resp.status_code == 400
        assert "Legendary Creature" in resp.json()["detail"]["message"]

    def test_generate_commander_not_found(self):
        app = _make_app()
        mock_repo = app.state.mock_repo
        mock_repo.get_card_by_id.return_value = None

        client = TestClient(app)
        resp = client.post(
            "/decks/generate",
            json={
                "format_name": "commander",
                "commander_card_id": 9999,
            },
        )
        assert resp.status_code == 400

    @patch("src.decks.builder.generate_deck")
    def test_generate_standard_format(self, mock_gen):
        from src.domain.models import GeneratedDeck

        mock_gen.return_value = GeneratedDeck(
            cards=[],
            format_name="standard",
            archetype=None,
            colors=["R"],
            total_value=None,
            land_count=24,
            nonland_count=36,
            warnings=[],
        )

        app = _make_app()
        mock_repo = app.state.mock_repo
        saved_deck = _mock_deck(10)
        mock_repo.create_deck.return_value = saved_deck
        mock_repo.add_deck_cards.return_value = 0

        client = TestClient(app)
        resp = client.post(
            "/decks/generate",
            json={"format_name": "standard", "colors": ["R"]},
        )
        assert resp.status_code == 200
        body = resp.json()["data"]
        assert body["format_name"] == "standard"


# ---------------------------------------------------------------------------
# GET /decks/commanders — F133-T04
# ---------------------------------------------------------------------------


class TestCommanderSearch:
    @patch("src.decks.builder.get_commander_candidates")
    def test_search_commanders(self, mock_search):
        mock_search.return_value = [
            {
                "card_id": 1,
                "name_en": "Atraxa, Praetors' Voice",
                "set_code": "cm2",
                "collector_number": "10",
                "color_identity": "WUBG",
                "mana_cost": "{G}{W}{U}{B}",
                "type_line": "Legendary Creature",
                "rarity": "mythic",
                "image_uri": None,
            }
        ]

        app = _make_app()
        client = TestClient(app)
        resp = client.get("/decks/commanders?q=atraxa")
        assert resp.status_code == 200
        body = resp.json()["data"]
        assert len(body) == 1
        assert body[0]["name_en"] == "Atraxa, Praetors' Voice"

    @patch("src.decks.builder.get_commander_candidates")
    def test_search_commanders_with_colors(self, mock_search):
        mock_search.return_value = []

        app = _make_app()
        client = TestClient(app)
        resp = client.get("/decks/commanders?q=&colors=W,U")
        assert resp.status_code == 200
        # Verify color list was passed correctly
        call_args = mock_search.call_args
        assert call_args.kwargs["colors"] == ["W", "U"]

    @patch("src.decks.builder.get_commander_candidates")
    def test_search_commanders_empty_query(self, mock_search):
        mock_search.return_value = []

        app = _make_app()
        client = TestClient(app)
        resp = client.get("/decks/commanders")
        assert resp.status_code == 200
        assert resp.json()["data"] == []

    @patch("src.decks.builder.get_commander_candidates")
    def test_search_commanders_returns_name_pt(self, mock_search):
        """F172-T02: name_pt is exposed in the CommanderCandidate schema."""
        mock_search.return_value = [
            {
                "card_id": 1,
                "name_en": "Atraxa, Praetors' Voice",
                "name_pt": "Atraxa, Voz dos Pretores",
                "type_line": "Legendary Creature",
            },
            {"card_id": 2, "name_en": "Krenko, Mob Boss", "type_line": "Legendary Creature"},
        ]

        client = TestClient(_make_app())
        resp = client.get("/decks/commanders?q=voz dos")
        assert resp.status_code == 200
        body = resp.json()["data"]
        assert body[0]["name_pt"] == "Atraxa, Voz dos Pretores"
        assert body[1]["name_pt"] is None
