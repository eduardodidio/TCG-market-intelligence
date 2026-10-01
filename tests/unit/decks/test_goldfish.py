"""Tests for goldfish simulator — pure functions, no DB."""

from __future__ import annotations

import random

import pytest

from src.decks.goldfish import (
    SampleHand,
    SingleGameResult,
    _evaluate_opening_hand,
    _is_land,
    _parse_cmc_simple,
    _simulate_single_game,
    simulate_goldfish,
)

# ---------------------------------------------------------------------------
# _is_land
# ---------------------------------------------------------------------------


class TestIsLand:
    def test_basic_land(self):
        assert _is_land("Basic Land — Forest") is True

    def test_legendary_land(self):
        assert _is_land("Legendary Land — Desert") is True

    def test_land_simple(self):
        assert _is_land("Land") is True

    def test_creature(self):
        assert _is_land("Creature — Elf Warrior") is False

    def test_none(self):
        assert _is_land(None) is False

    def test_empty_string(self):
        assert _is_land("") is False

    def test_artifact_land(self):
        assert _is_land("Artifact Land") is True

    def test_enchantment(self):
        assert _is_land("Enchantment") is False

    def test_case_insensitive(self):
        assert _is_land("basic land") is True

    def test_landfall_not_land(self):
        # "Landfall" contains "Land" but is not a land type
        # Our regex uses word boundary, so this should be False
        assert _is_land("Creature — Landfall Elemental") is False

    def test_snow_covered_land(self):
        assert _is_land("Basic Snow Land — Island") is True


# ---------------------------------------------------------------------------
# _parse_cmc_simple
# ---------------------------------------------------------------------------


class TestParseCmcSimple:
    def test_generic_plus_colors(self):
        assert _parse_cmc_simple("{3}{U}{U}") == 5

    def test_x_cost_counts_as_zero(self):
        assert _parse_cmc_simple("{X}{R}") == 1

    def test_none_returns_zero(self):
        assert _parse_cmc_simple(None) == 0

    def test_empty_string_returns_zero(self):
        assert _parse_cmc_simple("") == 0

    def test_hybrid_mana(self):
        assert _parse_cmc_simple("{W/U}{W/U}") == 2

    def test_phyrexian_mana(self):
        assert _parse_cmc_simple("{W/P}") == 1

    def test_pure_numeric(self):
        assert _parse_cmc_simple("{5}") == 5

    def test_zero_mana(self):
        assert _parse_cmc_simple("{0}") == 0

    def test_all_colors(self):
        assert _parse_cmc_simple("{W}{U}{B}{R}{G}") == 5

    def test_colorless_pip(self):
        assert _parse_cmc_simple("{C}{C}") == 2

    def test_split_card_front_face(self):
        assert _parse_cmc_simple("{3}{U} // {1}{R}") == 4

    def test_hybrid_with_generic(self):
        # {2/W} should use the higher cost (2)
        assert _parse_cmc_simple("{2/W}") == 2

    def test_double_x(self):
        assert _parse_cmc_simple("{X}{X}{R}") == 1

    def test_complex_mana_cost(self):
        assert _parse_cmc_simple("{1}{W}{W}{U}") == 4


# ---------------------------------------------------------------------------
# _evaluate_opening_hand
# ---------------------------------------------------------------------------


def _make_card(name: str, type_line: str = "Creature", mana_cost: str = "{1}") -> dict:
    return {"name_en": name, "type_line": type_line, "mana_cost": mana_cost}


def _make_land(name: str = "Plains") -> dict:
    return {"name_en": name, "type_line": "Basic Land — Plains", "mana_cost": None}


class TestEvaluateOpeningHand:
    def test_zero_lands_returns_zero(self):
        # Use CMC >= 3 spells so the low-CMC bonus does not apply
        hand = [_make_card(f"Spell{i}", mana_cost="{3}") for i in range(7)]
        assert _evaluate_opening_hand(hand) == 0.0

    def test_zero_lands_with_low_cmc_gets_bonus(self):
        # CMC 1 spells trigger +0.1 bonus even with 0 lands
        hand = [_make_card(f"Spell{i}", mana_cost="{1}") for i in range(7)]
        assert _evaluate_opening_hand(hand) == pytest.approx(0.1)

    def test_one_land(self):
        hand = [_make_land()] + [_make_card(f"Spell{i}", mana_cost="{3}") for i in range(6)]
        # 1 land = 0.3, no low-cmc spell (all are CMC 3)
        assert _evaluate_opening_hand(hand) == 0.3

    def test_one_land_with_low_cmc_bonus(self):
        hand = (
            [_make_land()]
            + [_make_card("Bolt", mana_cost="{R}")]
            + [_make_card(f"Spell{i}", mana_cost="{3}") for i in range(5)]
        )
        # 1 land = 0.3, + 0.1 bonus for Bolt (CMC 1)
        assert _evaluate_opening_hand(hand) == pytest.approx(0.4)

    def test_two_lands(self):
        hand = [_make_land() for _ in range(2)] + [
            _make_card(f"Spell{i}", mana_cost="{3}") for i in range(5)
        ]
        assert _evaluate_opening_hand(hand) == 0.9

    def test_three_lands(self):
        hand = [_make_land() for _ in range(3)] + [
            _make_card(f"Spell{i}", mana_cost="{3}") for i in range(4)
        ]
        assert _evaluate_opening_hand(hand) == 1.0

    def test_three_lands_with_bonus_capped(self):
        hand = (
            [_make_land() for _ in range(3)]
            + [
                _make_card("Bolt", mana_cost="{R}"),
            ]
            + [_make_card(f"Spell{i}", mana_cost="{3}") for i in range(3)]
        )
        # 3 lands = 1.0, bonus would bring to 1.1 but capped at 1.0
        assert _evaluate_opening_hand(hand) == 1.0

    def test_four_lands(self):
        hand = [_make_land() for _ in range(4)] + [
            _make_card(f"Spell{i}", mana_cost="{3}") for i in range(3)
        ]
        assert _evaluate_opening_hand(hand) == 0.7

    def test_five_lands(self):
        hand = [_make_land() for _ in range(5)] + [
            _make_card(f"Spell{i}", mana_cost="{3}") for i in range(2)
        ]
        assert _evaluate_opening_hand(hand) == 0.3

    def test_six_lands(self):
        hand = [_make_land() for _ in range(6)] + [_make_card("Spell", mana_cost="{3}")]
        assert _evaluate_opening_hand(hand) == 0.1

    def test_seven_lands(self):
        hand = [_make_land() for _ in range(7)]
        # 7 lands = 0.1 (clamped to last entry in table)
        assert _evaluate_opening_hand(hand) == 0.1

    def test_empty_hand(self):
        assert _evaluate_opening_hand([]) == 0.0

    def test_bonus_requires_cmc_at_least_1(self):
        # A spell with CMC 0 (like Mox) should NOT trigger the bonus
        hand = (
            [_make_land() for _ in range(2)]
            + [
                _make_card("Mox", mana_cost="{0}"),
            ]
            + [_make_card(f"Spell{i}", mana_cost="{4}") for i in range(4)]
        )
        # 2 lands = 0.9, no bonus (Mox CMC is 0, other spells are CMC 4)
        assert _evaluate_opening_hand(hand) == 0.9


# ---------------------------------------------------------------------------
# _simulate_single_game
# ---------------------------------------------------------------------------


class TestSimulateSingleGame:
    def test_basic_game(self):
        deck = [_make_land() for _ in range(24)] + [
            _make_card(f"Spell{i}", mana_cost="{2}") for i in range(36)
        ]
        rng = random.Random(42)
        result = _simulate_single_game(deck, turns=7, rng=rng)

        assert isinstance(result, SingleGameResult)
        assert len(result.turns) == 7
        assert result.opening_hand_lands >= 0
        assert 0.0 <= result.opening_hand_quality <= 1.0
        assert len(result.opening_hand_names) <= 7

    def test_all_lands_game(self):
        deck = [_make_land() for _ in range(20)]
        rng = random.Random(42)
        result = _simulate_single_game(deck, turns=5, rng=rng)

        # Should have all lands in hand, play one per turn
        for td in result.turns:
            assert td.spells_cast == 0
            assert td.spells_castable == 0

    def test_no_lands_game(self):
        deck = [_make_card(f"Spell{i}", mana_cost="{1}") for i in range(20)]
        rng = random.Random(42)
        result = _simulate_single_game(deck, turns=5, rng=rng)

        for td in result.turns:
            assert td.lands_in_play == 0

    def test_small_deck(self):
        deck = [_make_land(), _make_card("Bolt", mana_cost="{R}")]
        rng = random.Random(42)
        result = _simulate_single_game(deck, turns=3, rng=rng)

        assert len(result.turns) == 3
        assert len(result.opening_hand_names) == 2  # only 2 cards in deck

    def test_lands_monotonically_non_decreasing(self):
        deck = [_make_land() for _ in range(20)] + [
            _make_card(f"Spell{i}", mana_cost="{2}") for i in range(40)
        ]
        rng = random.Random(42)
        result = _simulate_single_game(deck, turns=10, rng=rng)

        for i in range(1, len(result.turns)):
            assert result.turns[i].lands_in_play >= result.turns[i - 1].lands_in_play


# ---------------------------------------------------------------------------
# simulate_goldfish
# ---------------------------------------------------------------------------


class TestSimulateGoldfish:
    def test_all_lands_flood_rate(self):
        cards = [
            {
                "name_en": "Plains",
                "quantity": 40,
                "type_line": "Basic Land — Plains",
                "mana_cost": None,
            }
        ]
        result = simulate_goldfish(cards, num_simulations=50, turns=7, rng=random.Random(42))

        assert result.mana_flood_rate == 1.0
        assert result.total_simulations == 50

    def test_no_lands_screw_rate(self):
        cards = [{"name_en": "Bolt", "quantity": 40, "type_line": "Instant", "mana_cost": "{R}"}]
        result = simulate_goldfish(cards, num_simulations=50, turns=7, rng=random.Random(42))

        assert result.mana_screw_rate == 1.0
        assert result.total_simulations == 50

    def test_sample_hands_count(self):
        cards = [
            {
                "name_en": "Plains",
                "quantity": 24,
                "type_line": "Basic Land — Plains",
                "mana_cost": None,
            },
            {"name_en": "Bolt", "quantity": 36, "type_line": "Instant", "mana_cost": "{R}"},
        ]
        result = simulate_goldfish(cards, num_simulations=50, turns=7, rng=random.Random(42))

        assert len(result.sample_hands) == 3
        for sh in result.sample_hands:
            assert isinstance(sh, SampleHand)
            assert len(sh.cards) <= 7
            assert sh.land_count >= 0

    def test_deterministic_rng(self):
        cards = [
            {
                "name_en": "Plains",
                "quantity": 24,
                "type_line": "Basic Land — Plains",
                "mana_cost": None,
            },
            {"name_en": "Bolt", "quantity": 36, "type_line": "Instant", "mana_cost": "{R}"},
        ]
        result1 = simulate_goldfish(cards, num_simulations=50, turns=7, rng=random.Random(123))
        result2 = simulate_goldfish(cards, num_simulations=50, turns=7, rng=random.Random(123))

        assert result1.opening_hand_quality == result2.opening_hand_quality
        assert result1.mana_screw_rate == result2.mana_screw_rate
        assert result1.mana_flood_rate == result2.mana_flood_rate
        assert result1.avg_mana_by_turn == result2.avg_mana_by_turn
        assert result1.avg_spells_cast_by_turn == result2.avg_spells_cast_by_turn

    def test_normal_deck_reasonable_rates(self):
        cards = [
            {
                "name_en": "Plains",
                "quantity": 24,
                "type_line": "Basic Land — Plains",
                "mana_cost": None,
            },
            {"name_en": "Bolt", "quantity": 16, "type_line": "Instant", "mana_cost": "{R}"},
            {
                "name_en": "Knight",
                "quantity": 12,
                "type_line": "Creature — Knight",
                "mana_cost": "{1}{W}",
            },
            {
                "name_en": "Angel",
                "quantity": 8,
                "type_line": "Creature — Angel",
                "mana_cost": "{3}{W}{W}",
            },
        ]
        result = simulate_goldfish(cards, num_simulations=200, turns=7, rng=random.Random(42))

        # A balanced 60-card deck should have moderate rates
        assert result.mana_screw_rate < 0.5
        assert result.mana_flood_rate < 0.5
        assert result.total_simulations == 200
        assert result.total_turns == 7

    def test_avg_mana_by_turn_monotonic(self):
        cards = [
            {
                "name_en": "Plains",
                "quantity": 24,
                "type_line": "Basic Land — Plains",
                "mana_cost": None,
            },
            {"name_en": "Bolt", "quantity": 36, "type_line": "Instant", "mana_cost": "{R}"},
        ]
        result = simulate_goldfish(cards, num_simulations=100, turns=10, rng=random.Random(42))

        # Average mana by turn should be monotonically non-decreasing
        assert len(result.avg_mana_by_turn) == 10
        for i in range(1, len(result.avg_mana_by_turn)):
            assert result.avg_mana_by_turn[i] >= result.avg_mana_by_turn[i - 1]

    def test_empty_card_list(self):
        result = simulate_goldfish([], num_simulations=10, turns=5)

        assert result.total_simulations == 0
        assert result.mana_screw_rate == 1.0
        assert result.mana_flood_rate == 0.0
        assert result.sample_hands == []
        assert len(result.avg_mana_by_turn) == 5

    def test_cards_with_no_type_line(self):
        """Cards without type_line should be treated as non-land, CMC 0."""
        cards = [
            {"name_en": "Mystery", "quantity": 30, "type_line": None, "mana_cost": None},
            {
                "name_en": "Plains",
                "quantity": 30,
                "type_line": "Basic Land — Plains",
                "mana_cost": None,
            },
        ]
        result = simulate_goldfish(cards, num_simulations=50, turns=7, rng=random.Random(42))

        assert result.total_simulations == 50
        # Should not crash; unknown cards treated as non-land

    def test_sample_hands_ordered(self):
        """Sample hands should be worst, median, best quality."""
        cards = [
            {
                "name_en": "Plains",
                "quantity": 24,
                "type_line": "Basic Land — Plains",
                "mana_cost": None,
            },
            {"name_en": "Bolt", "quantity": 36, "type_line": "Instant", "mana_cost": "{R}"},
        ]
        result = simulate_goldfish(cards, num_simulations=100, turns=7, rng=random.Random(42))

        assert len(result.sample_hands) == 3
        worst, median, best = result.sample_hands
        assert worst.quality <= median.quality
        assert median.quality <= best.quality

    def test_spells_cast_by_turn(self):
        """avg_spells_cast_by_turn should have correct length."""
        cards = [
            {
                "name_en": "Plains",
                "quantity": 20,
                "type_line": "Basic Land — Plains",
                "mana_cost": None,
            },
            {"name_en": "Bolt", "quantity": 40, "type_line": "Instant", "mana_cost": "{R}"},
        ]
        result = simulate_goldfish(cards, num_simulations=50, turns=5, rng=random.Random(42))

        assert len(result.avg_spells_cast_by_turn) == 5
        # Early turns with lands should cast some spells
        # (with 40 bolts and 20 lands, by turn 2-3 there should be casts)

    def test_total_turns_matches(self):
        cards = [
            {
                "name_en": "Plains",
                "quantity": 20,
                "type_line": "Basic Land — Plains",
                "mana_cost": None,
            },
            {"name_en": "Bolt", "quantity": 40, "type_line": "Instant", "mana_cost": "{R}"},
        ]
        result = simulate_goldfish(cards, num_simulations=10, turns=5, rng=random.Random(42))
        assert result.total_turns == 5

    def test_quantity_expansion(self):
        """Cards should be expanded by quantity before simulation."""
        cards = [
            {
                "name_en": "Plains",
                "quantity": 40,
                "type_line": "Basic Land — Plains",
                "mana_cost": None,
            },
        ]
        # 40 copies total deck size = 40, all lands
        result = simulate_goldfish(cards, num_simulations=10, turns=7, rng=random.Random(42))
        assert result.total_simulations == 10
        # All cards are lands, so flood rate should be 1.0
        assert result.mana_flood_rate == 1.0


# ---------------------------------------------------------------------------
# API endpoint integration tests
# ---------------------------------------------------------------------------


class TestGoldfishEndpoint:
    """Integration tests for POST /decks/{id}/goldfish using TestClient."""

    def _make_app(self, user_id: str = "user1"):
        from unittest.mock import MagicMock

        from fastapi import FastAPI
        from fastapi.testclient import TestClient

        from src.api.deps import get_db, require_auth_or_api_key
        from src.api.routers.decks import router

        app = FastAPI()
        app.include_router(router)

        mock_repo = MagicMock()
        app.dependency_overrides[get_db] = lambda: mock_repo
        app.dependency_overrides[require_auth_or_api_key] = lambda: user_id

        return app, mock_repo, TestClient(app)

    def _mock_deck(self, deck_id=1, user_id="user1"):
        from datetime import datetime
        from unittest.mock import MagicMock

        deck = MagicMock()
        deck.id = deck_id
        deck.user_id = user_id
        deck.name = "Test Deck"
        deck.description = None
        deck.created_at = datetime(2026, 8, 21, 12, 0, 0)
        deck.updated_at = datetime(2026, 8, 21, 12, 0, 0)
        return deck

    def _mock_deck_card(self, card_id=1, name="Lightning Bolt", qty=4):
        from unittest.mock import MagicMock

        dc = MagicMock()
        dc.card_id = card_id
        dc.name_en = name
        dc.quantity = qty
        return dc

    def _mock_card_row(self, type_line="Instant", mana_cost="{R}"):
        from unittest.mock import MagicMock

        cr = MagicMock()
        cr.type_line = type_line
        cr.mana_cost = mana_cost
        return cr

    def test_goldfish_returns_200(self):
        app, mock_repo, client = self._make_app()

        mock_repo.get_deck.return_value = self._mock_deck()
        mock_repo.get_deck_cards.return_value = [
            self._mock_deck_card(card_id=1, name="Lightning Bolt", qty=20),
            self._mock_deck_card(card_id=2, name="Plains", qty=20),
        ]
        mock_repo.get_card_by_id.side_effect = lambda cid: {
            1: self._mock_card_row(type_line="Instant", mana_cost="{R}"),
            2: self._mock_card_row(type_line="Basic Land — Plains", mana_cost=None),
        }.get(cid)

        resp = client.post("/decks/1/goldfish?num_simulations=10&turns=5")
        assert resp.status_code == 200
        body = resp.json()
        data = body["data"]
        assert data["deck_id"] == 1
        assert data["total_simulations"] == 10
        assert data["total_turns"] == 5
        assert len(data["avg_mana_by_turn"]) == 5
        assert len(data["sample_hands"]) == 3

    def test_goldfish_nonexistent_deck_404(self):
        app, mock_repo, client = self._make_app()
        mock_repo.get_deck.return_value = None

        resp = client.post("/decks/999/goldfish")
        assert resp.status_code == 404

    def test_goldfish_other_user_deck_404(self):
        app, mock_repo, client = self._make_app(user_id="user1")
        mock_repo.get_deck.return_value = self._mock_deck(user_id="user2")

        resp = client.post("/decks/1/goldfish")
        assert resp.status_code == 404

    def test_goldfish_empty_deck_400(self):
        app, mock_repo, client = self._make_app()
        mock_repo.get_deck.return_value = self._mock_deck()
        mock_repo.get_deck_cards.return_value = []

        resp = client.post("/decks/1/goldfish")
        assert resp.status_code == 400

    def test_goldfish_query_params_respected(self):
        app, mock_repo, client = self._make_app()

        mock_repo.get_deck.return_value = self._mock_deck()
        mock_repo.get_deck_cards.return_value = [
            self._mock_deck_card(card_id=1, name="Lightning Bolt", qty=30),
            self._mock_deck_card(card_id=2, name="Plains", qty=30),
        ]
        mock_repo.get_card_by_id.side_effect = lambda cid: {
            1: self._mock_card_row(type_line="Instant", mana_cost="{R}"),
            2: self._mock_card_row(type_line="Basic Land — Plains", mana_cost=None),
        }.get(cid)

        resp = client.post("/decks/1/goldfish?num_simulations=15&turns=3")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["total_simulations"] == 15
        assert data["total_turns"] == 3
        assert len(data["avg_mana_by_turn"]) == 3
