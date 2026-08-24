"""Tests for deck ranking and value detail endpoints."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from unittest.mock import MagicMock

from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.api.deps import get_currency_converter_dep, get_db, require_auth_or_api_key
from src.api.routers.decks import router

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_app(user_id: str = "user1") -> FastAPI:
    app = FastAPI()
    app.include_router(router)

    mock_repo = MagicMock()
    mock_converter = MagicMock()
    mock_converter.convert.side_effect = lambda v, d, c: v  # identity conversion

    app.dependency_overrides[get_db] = lambda: mock_repo
    app.dependency_overrides[require_auth_or_api_key] = lambda: user_id
    app.dependency_overrides[get_currency_converter_dep] = lambda: mock_converter

    app.state.mock_repo = mock_repo
    app.state.mock_converter = mock_converter
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


def _mock_deck_card(card_id=1, quantity=1):
    dc = MagicMock()
    dc.card_id = card_id
    dc.quantity = quantity
    return dc


def _mock_price_obs(median_price=Decimal("10.00")):
    obs = MagicMock()
    obs.median_price = median_price
    obs.observed_at = datetime(2026, 8, 21)
    return obs


# ---------------------------------------------------------------------------
# GET /ranking
# ---------------------------------------------------------------------------


class TestGetDeckRanking:
    def test_empty_decks(self):
        app = _make_app()
        repo = app.state.mock_repo
        repo.list_decks.return_value = []

        client = TestClient(app)
        resp = client.get("/decks/ranking")
        assert resp.status_code == 200
        body = resp.json()
        assert body["data"]["decks"] == []
        assert body["data"]["total"] == 0

    def test_ranking_with_decks(self):
        app = _make_app()
        repo = app.state.mock_repo

        deck1 = _mock_deck(deck_id=1, name="Expensive")
        deck2 = _mock_deck(deck_id=2, name="Cheap")
        repo.list_decks.return_value = [deck1, deck2]

        # deck1 has 2 cards, deck2 has 1 card
        repo.get_deck_cards.side_effect = lambda did: (
            [_mock_deck_card(card_id=10, quantity=4)]
            if did == 1
            else [_mock_deck_card(card_id=20, quantity=1)]
        )

        repo.get_latest_prices_batch.return_value = {
            10: _mock_price_obs(Decimal("25.00")),
            20: _mock_price_obs(Decimal("5.00")),
        }
        repo.get_price_series_batch.return_value = {}
        repo.get_deck_summary.return_value = {
            "total_cards": 4,
            "unique_cards": 1,
            "owned_cards": 1,
            "ownership_pct": 100.0,
        }

        client = TestClient(app)
        resp = client.get("/decks/ranking")
        assert resp.status_code == 200
        body = resp.json()
        assert body["data"]["total"] == 2

        # Default sort is by total_value desc
        decks = body["data"]["decks"]
        assert decks[0]["name"] == "Expensive"
        assert decks[0]["total_value"] == 100.0  # 25*4
        assert decks[1]["name"] == "Cheap"
        assert decks[1]["total_value"] == 5.0

    def test_sort_order_asc(self):
        app = _make_app()
        repo = app.state.mock_repo

        deck1 = _mock_deck(deck_id=1, name="Expensive")
        deck2 = _mock_deck(deck_id=2, name="Cheap")
        repo.list_decks.return_value = [deck1, deck2]

        repo.get_deck_cards.side_effect = lambda did: (
            [_mock_deck_card(card_id=10, quantity=1)]
            if did == 1
            else [_mock_deck_card(card_id=20, quantity=1)]
        )

        repo.get_latest_prices_batch.return_value = {
            10: _mock_price_obs(Decimal("100.00")),
            20: _mock_price_obs(Decimal("5.00")),
        }
        repo.get_price_series_batch.return_value = {}
        repo.get_deck_summary.return_value = {
            "total_cards": 1,
            "unique_cards": 1,
            "owned_cards": 1,
            "ownership_pct": 100.0,
        }

        client = TestClient(app)
        resp = client.get("/decks/ranking?sort_order=asc")
        body = resp.json()
        decks = body["data"]["decks"]
        assert decks[0]["name"] == "Cheap"

    def test_min_value_filter(self):
        app = _make_app()
        repo = app.state.mock_repo

        deck1 = _mock_deck(deck_id=1, name="Expensive")
        deck2 = _mock_deck(deck_id=2, name="Cheap")
        repo.list_decks.return_value = [deck1, deck2]

        repo.get_deck_cards.side_effect = lambda did: (
            [_mock_deck_card(card_id=10, quantity=1)]
            if did == 1
            else [_mock_deck_card(card_id=20, quantity=1)]
        )

        repo.get_latest_prices_batch.return_value = {
            10: _mock_price_obs(Decimal("100.00")),
            20: _mock_price_obs(Decimal("5.00")),
        }
        repo.get_price_series_batch.return_value = {}
        repo.get_deck_summary.return_value = {
            "total_cards": 1,
            "unique_cards": 1,
            "owned_cards": 1,
            "ownership_pct": 100.0,
        }

        client = TestClient(app)
        resp = client.get("/decks/ranking?min_value=50")
        body = resp.json()
        assert body["data"]["total"] == 1
        assert body["data"]["decks"][0]["name"] == "Expensive"

    def test_max_value_filter(self):
        app = _make_app()
        repo = app.state.mock_repo

        deck1 = _mock_deck(deck_id=1, name="Expensive")
        deck2 = _mock_deck(deck_id=2, name="Cheap")
        repo.list_decks.return_value = [deck1, deck2]

        repo.get_deck_cards.side_effect = lambda did: (
            [_mock_deck_card(card_id=10, quantity=1)]
            if did == 1
            else [_mock_deck_card(card_id=20, quantity=1)]
        )

        repo.get_latest_prices_batch.return_value = {
            10: _mock_price_obs(Decimal("100.00")),
            20: _mock_price_obs(Decimal("5.00")),
        }
        repo.get_price_series_batch.return_value = {}
        repo.get_deck_summary.return_value = {
            "total_cards": 1,
            "unique_cards": 1,
            "owned_cards": 1,
            "ownership_pct": 100.0,
        }

        client = TestClient(app)
        resp = client.get("/decks/ranking?max_value=50")
        body = resp.json()
        assert body["data"]["total"] == 1
        assert body["data"]["decks"][0]["name"] == "Cheap"

    def test_pagination(self):
        app = _make_app()
        repo = app.state.mock_repo

        decks = [_mock_deck(deck_id=i, name=f"Deck{i}") for i in range(1, 6)]
        repo.list_decks.return_value = decks

        repo.get_deck_cards.return_value = [_mock_deck_card(card_id=10, quantity=1)]
        repo.get_latest_prices_batch.return_value = {10: _mock_price_obs(Decimal("10.00"))}
        repo.get_price_series_batch.return_value = {}
        repo.get_deck_summary.return_value = {
            "total_cards": 1,
            "unique_cards": 1,
            "owned_cards": 1,
            "ownership_pct": 100.0,
        }

        client = TestClient(app)
        resp = client.get("/decks/ranking?limit=2&offset=0")
        body = resp.json()
        assert len(body["data"]["decks"]) == 2
        assert body["data"]["total"] == 5

        resp2 = client.get("/decks/ranking?limit=2&offset=2")
        body2 = resp2.json()
        assert len(body2["data"]["decks"]) == 2

    def test_only_returns_user_decks(self):
        """Ranking only returns decks belonging to the authenticated user."""
        app = _make_app(user_id="user1")
        repo = app.state.mock_repo

        # list_decks is called with user_id and only returns that user's decks
        repo.list_decks.return_value = [_mock_deck(deck_id=1, user_id="user1")]
        repo.get_deck_cards.return_value = [_mock_deck_card(card_id=10)]
        repo.get_latest_prices_batch.return_value = {10: _mock_price_obs(Decimal("10.00"))}
        repo.get_price_series_batch.return_value = {}
        repo.get_deck_summary.return_value = {
            "total_cards": 1,
            "unique_cards": 1,
            "owned_cards": 1,
            "ownership_pct": 100.0,
        }

        client = TestClient(app)
        resp = client.get("/decks/ranking")
        assert resp.status_code == 200
        # Verify list_decks was called with the correct user_id
        repo.list_decks.assert_called_with("user1")


# ---------------------------------------------------------------------------
# GET /{deck_id}/value
# ---------------------------------------------------------------------------


class TestGetDeckValue:
    def test_value_detail_success(self):
        app = _make_app()
        repo = app.state.mock_repo

        deck = _mock_deck(deck_id=1)
        repo.get_deck.return_value = deck
        repo.get_deck_cards.return_value = [_mock_deck_card(card_id=10, quantity=2)]
        repo.get_latest_prices_batch.return_value = {10: _mock_price_obs(Decimal("15.00"))}
        repo.get_price_series_batch.return_value = {}

        client = TestClient(app)
        resp = client.get("/decks/1/value")
        assert resp.status_code == 200
        body = resp.json()
        assert body["data"]["deck_id"] == 1
        assert body["data"]["total_value"] == 30.0  # 15*2
        assert body["data"]["priced_cards"] == 1

    def test_value_detail_not_found(self):
        app = _make_app()
        repo = app.state.mock_repo
        repo.get_deck.return_value = None

        client = TestClient(app)
        resp = client.get("/decks/999/value")
        assert resp.status_code == 404

    def test_value_detail_wrong_user(self):
        app = _make_app(user_id="user1")
        repo = app.state.mock_repo
        repo.get_deck.return_value = _mock_deck(deck_id=1, user_id="other_user")

        client = TestClient(app)
        resp = client.get("/decks/1/value")
        assert resp.status_code == 404

    def test_value_detail_with_period(self):
        app = _make_app()
        repo = app.state.mock_repo

        deck = _mock_deck(deck_id=1)
        repo.get_deck.return_value = deck
        repo.get_deck_cards.return_value = [_mock_deck_card(card_id=10, quantity=1)]
        repo.get_latest_prices_batch.return_value = {10: _mock_price_obs(Decimal("10.00"))}
        repo.get_price_series_batch.return_value = {}

        client = TestClient(app)
        resp = client.get("/decks/1/value?period=7d")
        assert resp.status_code == 200
        body = resp.json()
        assert body["data"]["period"] == "7d"
