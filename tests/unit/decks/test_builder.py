"""Tests for deck builder service — uses mocked Repository."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from unittest.mock import MagicMock, patch

from src.decks.builder import (
    _add_basic_lands,
    _color_identity_matches,
    _get_target_composition,
    _select_cards,
    generate_deck,
)
from src.domain.models import DeckBuildParams

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


@dataclass
class FakeCardRow:
    """Minimal stand-in for CardRow in unit tests."""

    id: int
    game: str = "magic"
    name_en: str = "Test Card"
    name_pt: str | None = None
    set_code: str | None = "tst"
    collector_number: str | None = "1"
    rarity: str | None = "common"
    color_identity: str | None = ""
    mana_cost: str | None = "{1}"
    type_line: str | None = "Creature"
    image_uri: str | None = None


# ---------------------------------------------------------------------------
# _get_target_composition
# ---------------------------------------------------------------------------


class TestGetTargetComposition:
    def test_commander_sums_to_100(self):
        comp = _get_target_composition("commander", None)
        assert sum(comp.values()) == 100

    def test_standard_sums_to_60(self):
        comp = _get_target_composition("standard", None)
        assert sum(comp.values()) == 60

    def test_aggro_archetype_valid(self):
        comp = _get_target_composition("commander", "aggro")
        assert sum(comp.values()) == 100
        assert comp["Creature"] > comp.get("Planeswalker", 0)

    def test_control_archetype_valid(self):
        comp = _get_target_composition("commander", "control")
        assert sum(comp.values()) == 100
        assert comp.get("Planeswalker", 0) > 0

    def test_midrange_archetype_valid(self):
        comp = _get_target_composition("commander", "midrange")
        assert sum(comp.values()) == 100

    def test_combo_archetype_valid(self):
        comp = _get_target_composition("commander", "combo")
        assert sum(comp.values()) == 100

    def test_tempo_archetype_valid(self):
        comp = _get_target_composition("commander", "tempo")
        assert sum(comp.values()) == 100

    def test_modern_60_cards(self):
        comp = _get_target_composition("modern", "aggro")
        assert sum(comp.values()) == 60

    def test_unknown_archetype_uses_default(self):
        comp = _get_target_composition("commander", "unknown_archetype")
        # Falls back to None key (default)
        assert sum(comp.values()) == 100

    def test_all_types_present(self):
        comp = _get_target_composition("commander", None)
        assert "Land" in comp
        assert "Creature" in comp


# ---------------------------------------------------------------------------
# _color_identity_matches
# ---------------------------------------------------------------------------


class TestColorIdentityMatches:
    def test_colorless_always_allowed(self):
        assert _color_identity_matches("", {"W"}) is True
        assert _color_identity_matches("C", {"W"}) is True
        assert _color_identity_matches(None, {"W"}) is True

    def test_exact_match(self):
        assert _color_identity_matches("WU", {"W", "U"}) is True

    def test_subset_match(self):
        assert _color_identity_matches("W", {"W", "U", "B"}) is True

    def test_mismatch(self):
        assert _color_identity_matches("WU", {"W", "R"}) is False

    def test_single_color_in_five(self):
        assert _color_identity_matches("G", {"W", "U", "B", "R", "G"}) is True


# ---------------------------------------------------------------------------
# _select_cards
# ---------------------------------------------------------------------------


class TestSelectCards:
    def test_singleton_picks_one_each(self):
        candidates = [
            FakeCardRow(id=1, name_en="Alpha"),
            FakeCardRow(id=2, name_en="Beta"),
            FakeCardRow(id=3, name_en="Gamma"),
        ]
        result = _select_cards(
            candidates,
            3,
            singleton=True,
            budget_remaining=None,
            prices={},
            owned_ids=set(),
            prioritize_owned=False,
        )
        assert len(result) == 3
        for card in result:
            assert card["quantity"] == 1

    def test_non_singleton_picks_up_to_4(self):
        candidates = [
            FakeCardRow(id=1, name_en="Alpha"),
        ]
        result = _select_cards(
            candidates,
            4,
            singleton=False,
            budget_remaining=None,
            prices={},
            owned_ids=set(),
            prioritize_owned=False,
        )
        assert len(result) == 1
        assert result[0]["quantity"] == 4

    def test_budget_skips_expensive(self):
        candidates = [
            FakeCardRow(id=1, name_en="Cheap"),
            FakeCardRow(id=2, name_en="Expensive"),
        ]
        prices = {1: Decimal("1.00"), 2: Decimal("100.00")}
        result = _select_cards(
            candidates,
            2,
            singleton=True,
            budget_remaining=Decimal("5.00"),
            prices=prices,
            owned_ids=set(),
            prioritize_owned=False,
        )
        assert len(result) == 1
        assert result[0]["name_en"] == "Cheap"

    def test_owned_prioritized(self):
        candidates = [
            FakeCardRow(id=1, name_en="Not Owned"),
            FakeCardRow(id=2, name_en="Owned"),
        ]
        result = _select_cards(
            candidates,
            1,
            singleton=True,
            budget_remaining=None,
            prices={},
            owned_ids={2},
            prioritize_owned=True,
        )
        assert result[0]["name_en"] == "Owned"

    def test_respects_target_count(self):
        candidates = [FakeCardRow(id=i, name_en=f"Card {i}") for i in range(20)]
        result = _select_cards(
            candidates,
            5,
            singleton=True,
            budget_remaining=None,
            prices={},
            owned_ids=set(),
            prioritize_owned=False,
        )
        total_qty = sum(c["quantity"] for c in result)
        assert total_qty == 5

    def test_singleton_no_duplicate_names(self):
        candidates = [
            FakeCardRow(id=1, name_en="Same Name"),
            FakeCardRow(id=2, name_en="Same Name"),
            FakeCardRow(id=3, name_en="Different"),
        ]
        result = _select_cards(
            candidates,
            3,
            singleton=True,
            budget_remaining=None,
            prices={},
            owned_ids=set(),
            prioritize_owned=False,
        )
        names = [c["name_en"] for c in result]
        assert names.count("Same Name") == 1


# ---------------------------------------------------------------------------
# _add_basic_lands
# ---------------------------------------------------------------------------


class TestAddBasicLands:
    def test_distributes_proportionally(self):
        lands = _add_basic_lands({"W", "U"}, land_count=10, existing_land_count=0)
        total = sum(land["quantity"] for land in lands)
        assert total == 10

    def test_no_lands_needed(self):
        lands = _add_basic_lands({"W"}, land_count=5, existing_land_count=5)
        assert lands == []

    def test_empty_colors(self):
        lands = _add_basic_lands(set(), land_count=5, existing_land_count=0)
        assert lands == []

    def test_all_basic_land_types(self):
        lands = _add_basic_lands({"W", "U", "B", "R", "G"}, land_count=10, existing_land_count=0)
        total = sum(land["quantity"] for land in lands)
        assert total == 10
        names = {land["name_en"] for land in lands}
        assert names == {"Plains", "Island", "Swamp", "Mountain", "Forest"}


# ---------------------------------------------------------------------------
# generate_deck — integration with mock repo
# ---------------------------------------------------------------------------


class TestGenerateDeck:
    def _make_mock_repo(self, cards=None, commander=None, collection_cards=None):
        """Create a mock repo that returns predefined cards."""
        repo = MagicMock()

        if commander:
            repo.get_card_by_id.return_value = commander
        else:
            repo.get_card_by_id.return_value = None

        # Mock engine + Session for queries
        mock_engine = MagicMock()
        repo.engine = mock_engine

        return repo

    def test_generate_returns_generated_deck(self):
        """Smoke test: generate_deck returns a GeneratedDeck."""
        repo = self._make_mock_repo()
        params = DeckBuildParams(
            format_name="casual",
            colors=["W", "U"],
        )

        # Mock Session context to return empty results
        mock_session = MagicMock()
        mock_execute = MagicMock()
        mock_execute.scalars.return_value.all.return_value = []
        mock_execute.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_execute
        mock_session.__enter__ = MagicMock(return_value=mock_session)
        mock_session.__exit__ = MagicMock(return_value=False)

        with patch("src.decks.builder.Session", return_value=mock_session):
            result = generate_deck(repo, params)

        assert result.format_name == "casual"
        assert isinstance(result.cards, list)
        assert sorted(result.colors) == ["U", "W"]

    def test_no_colors_uses_all_five(self):
        repo = self._make_mock_repo()
        params = DeckBuildParams(format_name="casual")

        mock_session = MagicMock()
        mock_execute = MagicMock()
        mock_execute.scalars.return_value.all.return_value = []
        mock_execute.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_execute
        mock_session.__enter__ = MagicMock(return_value=mock_session)
        mock_session.__exit__ = MagicMock(return_value=False)

        with patch("src.decks.builder.Session", return_value=mock_session):
            result = generate_deck(repo, params)

        assert set(result.colors) == {"W", "U", "B", "R", "G"}
        assert any("No colors" in w for w in result.warnings)

    def test_commander_sets_colors_from_card(self):
        commander = FakeCardRow(
            id=99,
            name_en="Test Commander",
            color_identity="WU",
            type_line="Legendary Creature \u2014 Human",
            mana_cost="{W}{U}",
            rarity="mythic",
        )
        repo = self._make_mock_repo(commander=commander)
        params = DeckBuildParams(
            format_name="commander",
            commander_card_id=99,
        )

        mock_session = MagicMock()
        mock_execute = MagicMock()
        mock_execute.scalars.return_value.all.return_value = []
        mock_execute.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_execute
        mock_session.__enter__ = MagicMock(return_value=mock_session)
        mock_session.__exit__ = MagicMock(return_value=False)

        with patch("src.decks.builder.Session", return_value=mock_session):
            result = generate_deck(repo, params)

        assert set(result.colors) == {"W", "U"}

    def test_warnings_when_not_enough_cards(self):
        repo = self._make_mock_repo()
        params = DeckBuildParams(format_name="standard", colors=["W"])

        mock_session = MagicMock()
        mock_execute = MagicMock()
        mock_execute.scalars.return_value.all.return_value = []
        mock_execute.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_execute
        mock_session.__enter__ = MagicMock(return_value=mock_session)
        mock_session.__exit__ = MagicMock(return_value=False)

        with patch("src.decks.builder.Session", return_value=mock_session):
            result = generate_deck(repo, params)

        # Should have warnings about missing cards (empty catalog)
        assert len(result.warnings) > 0

    def test_exclude_card_ids(self):
        repo = self._make_mock_repo()
        params = DeckBuildParams(
            format_name="casual",
            colors=["W"],
            exclude_card_ids=[1, 2, 3],
        )

        mock_session = MagicMock()
        mock_execute = MagicMock()
        mock_execute.scalars.return_value.all.return_value = []
        mock_execute.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_execute
        mock_session.__enter__ = MagicMock(return_value=mock_session)
        mock_session.__exit__ = MagicMock(return_value=False)

        with patch("src.decks.builder.Session", return_value=mock_session):
            result = generate_deck(repo, params)

        # Excluded cards should not appear
        card_ids = [c["card_id"] for c in result.cards if c["card_id"] is not None]
        assert 1 not in card_ids
        assert 2 not in card_ids
        assert 3 not in card_ids
