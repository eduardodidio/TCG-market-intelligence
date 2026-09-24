"""Tests for src/metagame/valuation.py — pure metagame deck valuation."""

from __future__ import annotations

import ast
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace

import pytest

from src.metagame import valuation as valuation_module
from src.metagame.valuation import BASIC_LANDS, MetaDeckValuation, value_meta_deck


def card(card_id, qty, name="Card", board="main"):
    return SimpleNamespace(card_id=card_id, quantity=qty, card_name=name, board=board)


PRICES = {1: Decimal("10"), 2: Decimal("5")}


class TestHappyPath:
    def test_values_owned_and_missing(self):
        deck = [card(1, 4, "A"), card(2, 2, "B")]
        result = value_meta_deck(deck, PRICES, {1: 4})

        assert result == MetaDeckValuation(
            total_value_brl=Decimal("50.00"),
            priced_pct=Decimal("100.0"),
            owned_pct=Decimal("66.7"),
            missing_value_brl=Decimal("10.00"),
            total_copies=6,
        )

    def test_nothing_owned_missing_equals_total(self):
        deck = [card(1, 4, "A"), card(2, 2, "B")]
        result = value_meta_deck(deck, PRICES, {})
        assert result.owned_pct == Decimal("0.0")
        assert result.missing_value_brl == Decimal("50.00")

    def test_fully_owned_missing_zero(self):
        result = value_meta_deck([card(1, 4, "A")], PRICES, {1: 4})
        assert result.owned_pct == Decimal("100.0")
        assert result.missing_value_brl == Decimal("0.00")

    def test_accepts_generator(self):
        result = value_meta_deck((c for c in [card(1, 1)]), PRICES, None)
        assert result.total_value_brl == Decimal("10.00")


class TestOwnership:
    def test_owned_more_than_deck_counts_deck_quantity(self):
        result = value_meta_deck([card(1, 4, "A")], PRICES, {1: 10})
        assert result.owned_pct == Decimal("100.0")
        assert result.missing_value_brl == Decimal("0.00")

    def test_partial_ownership(self):
        result = value_meta_deck([card(1, 4, "A")], PRICES, {1: 1})
        assert result.owned_pct == Decimal("25.0")
        assert result.missing_value_brl == Decimal("30.00")

    def test_negative_owned_is_clamped(self):
        result = value_meta_deck([card(1, 4, "A")], PRICES, {1: -3})
        assert result.owned_pct == Decimal("0.0")
        assert result.missing_value_brl == Decimal("40.00")

    def test_owned_unpriced_card_counts_as_owned_not_in_missing(self):
        deck = [card(1, 1, "A"), card(99, 1, "Unpriced")]
        result = value_meta_deck(deck, PRICES, {99: 1})
        assert result.owned_pct == Decimal("50.0")
        assert result.missing_value_brl == Decimal("10.00")
        assert result.priced_pct == Decimal("50.0")

    def test_anonymous_user(self):
        result = value_meta_deck([card(1, 4, "A")], PRICES, None)
        assert result.owned_pct is None
        assert result.missing_value_brl is None
        assert result.total_value_brl == Decimal("40.00")


class TestUnlinkedAndUnpriced:
    def test_card_id_none_is_unpriced_and_unowned(self):
        deck = [card(1, 1, "A"), card(None, 1, "Mystery")]
        result = value_meta_deck(deck, PRICES, {1: 1})
        assert result.total_value_brl == Decimal("10.00")
        assert result.priced_pct == Decimal("50.0")
        assert result.owned_pct == Decimal("50.0")
        assert result.total_copies == 2

    def test_all_prices_none(self):
        deck = [card(1, 2, "A"), card(2, 2, "B")]
        result = value_meta_deck(deck, {1: None, 2: None}, {1: 2})
        assert result.total_value_brl is None
        assert result.priced_pct == Decimal("0.0")
        assert result.missing_value_brl is None
        assert result.owned_pct == Decimal("50.0")

    def test_all_unpriced_with_basics_counts_basics_only(self):
        deck = [card(1, 3, "A"), card(None, 1, "Island")]
        result = value_meta_deck(deck, {}, {})
        assert result.total_value_brl is None
        assert result.priced_pct == Decimal("25.0")
        assert result.missing_value_brl is None


class TestBasicLands:
    def test_only_basics(self):
        result = value_meta_deck([card(None, 20, "Island")], {}, {})
        assert result.total_value_brl == Decimal("0.00")
        assert result.priced_pct == Decimal("100.0")
        assert result.owned_pct == Decimal("100.0")
        assert result.missing_value_brl == Decimal("0.00")
        assert result.total_copies == 20

    def test_basic_ignores_its_card_price(self):
        result = value_meta_deck([card(7, 10, "Forest")], {7: Decimal("3")}, None)
        assert result.total_value_brl == Decimal("0.00")
        assert result.owned_pct is None

    def test_basics_mixed_with_spells(self):
        deck = [card(1, 2, "A"), card(None, 2, "Snow-Covered Swamp")]
        result = value_meta_deck(deck, PRICES, {})
        assert result.total_value_brl == Decimal("20.00")
        assert result.owned_pct == Decimal("50.0")
        assert result.missing_value_brl == Decimal("20.00")

    def test_name_attribute_fallback(self):
        dto = SimpleNamespace(card_id=None, quantity=5, name="Wastes", board="main")
        result = value_meta_deck([dto], {}, {})
        assert result.owned_pct == Decimal("100.0")

    @pytest.mark.parametrize("name", sorted(BASIC_LANDS))
    def test_all_basic_names(self, name):
        assert value_meta_deck([card(None, 1, name)], {}, {}).owned_pct == Decimal("100.0")

    def test_basic_lands_constant(self):
        assert len(BASIC_LANDS) == 12
        assert "Snow-Covered Wastes" in BASIC_LANDS

    def test_non_string_name_is_not_basic(self):
        weird = SimpleNamespace(card_id=None, quantity=1, card_name=None, name=None)
        result = value_meta_deck([weird], {}, {})
        assert result.owned_pct == Decimal("0.0")


class TestBoards:
    def test_sideboard_ignored_by_default(self):
        deck = [card(1, 1, "A"), card(2, 3, "B", board="side")]
        result = value_meta_deck(deck, PRICES, None)
        assert result.total_copies == 1
        assert result.total_value_brl == Decimal("10.00")

    @pytest.mark.parametrize("board", ["side", "sideboard", "SIDE"])
    def test_sideboard_included_with_flag(self, board):
        deck = [card(1, 1, "A"), card(2, 3, "B", board=board)]
        result = value_meta_deck(deck, PRICES, None, include_sideboard=True)
        assert result.total_copies == 4
        assert result.total_value_brl == Decimal("25.00")

    def test_commander_board_included(self):
        result = value_meta_deck([card(1, 1, "Cmd", board="commander")], PRICES, None)
        assert result.total_value_brl == Decimal("10.00")

    def test_missing_board_defaults_to_main(self):
        obj = SimpleNamespace(card_id=1, quantity=2, card_name="A")
        assert value_meta_deck([obj], PRICES, None).total_copies == 2

    def test_unknown_board_ignored(self):
        result = value_meta_deck([card(1, 1, "A", board="maybe")], PRICES, None)
        assert result.total_copies == 0


class TestBoundaries:
    def test_empty_deck(self):
        result = value_meta_deck([], PRICES, {})
        assert result == MetaDeckValuation(
            total_value_brl=None,
            priced_pct=Decimal("0.0"),
            owned_pct=Decimal("0.0"),
            missing_value_brl=None,
            total_copies=0,
        )

    def test_empty_deck_anonymous(self):
        result = value_meta_deck([], PRICES, None)
        assert result.owned_pct is None
        assert result.missing_value_brl is None

    def test_zero_or_none_quantity_skipped(self):
        deck = [card(1, 0, "A"), card(2, None, "B")]
        assert value_meta_deck(deck, PRICES, {}).total_copies == 0

    def test_missing_quantity_defaults_to_one(self):
        obj = SimpleNamespace(card_id=1, card_name="A", board="main")
        assert value_meta_deck([obj], PRICES, None).total_value_brl == Decimal("10.00")

    def test_rounding_two_thirds(self):
        deck = [card(1, 2, "A"), card(99, 1, "C")]
        assert value_meta_deck(deck, PRICES, None).priced_pct == Decimal("66.7")

    def test_brl_round_half_up(self):
        result = value_meta_deck([card(1, 1, "A")], {1: Decimal("1.005")}, None)
        assert result.total_value_brl == Decimal("1.01")

    def test_result_is_frozen(self):
        result = value_meta_deck([], {}, None)
        with pytest.raises(AttributeError):
            result.total_copies = 5  # type: ignore[misc]


def test_module_has_no_database_imports():
    tree = ast.parse(Path(valuation_module.__file__).read_text(encoding="utf-8"))
    modules = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            modules.add(node.module)
    assert not any(m.startswith(("src.database", "sqlalchemy")) for m in modules)
