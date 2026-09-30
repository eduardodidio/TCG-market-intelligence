"""Tests for synergy integration in the deck builder."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from src.decks.builder import _rarity_bonus, _select_cards
from src.decks.synergy import CommanderKeywords


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
    oracle_text: str | None = None


class TestRarityBonus:
    def test_mythic(self):
        assert _rarity_bonus("M") == 1.0

    def test_rare(self):
        assert _rarity_bonus("R") == 0.75

    def test_uncommon(self):
        assert _rarity_bonus("U") == 0.5

    def test_common(self):
        assert _rarity_bonus("C") == 0.25

    def test_none_defaults(self):
        assert _rarity_bonus(None) == 0.25


class TestSelectCardsWithSynergy:
    def _elf_commander(self) -> CommanderKeywords:
        return CommanderKeywords(
            tribal_types=["Elf", "Druid"],
            mechanic_keywords=["draw", "ramp"],
            referenced_types=[],
        )

    def test_synergy_cards_get_score(self):
        cards = [
            FakeCardRow(
                id=1,
                name_en="Llanowar Elves",
                type_line="Creature \u2014 Elf Druid",
                oracle_text="{T}: Add {G}.",
            ),
            FakeCardRow(
                id=2,
                name_en="Giant Spider",
                type_line="Creature \u2014 Spider",
                oracle_text="Reach",
            ),
        ]
        selected = _select_cards(
            candidates=cards,
            target_count=2,
            singleton=True,
            budget_remaining=None,
            prices={},
            owned_ids=set(),
            prioritize_owned=False,
            commander_keywords=self._elf_commander(),
            synergy_weight=0.7,
        )
        assert len(selected) == 2
        # Llanowar Elves should have higher synergy_score
        llanowar = next(c for c in selected if c["name_en"] == "Llanowar Elves")
        spider = next(c for c in selected if c["name_en"] == "Giant Spider")
        assert llanowar["synergy_score"] > spider["synergy_score"]

    def test_synergy_score_present_in_output(self):
        cards = [
            FakeCardRow(id=1, name_en="Card A", oracle_text="Draw a card."),
        ]
        selected = _select_cards(
            candidates=cards,
            target_count=1,
            singleton=True,
            budget_remaining=None,
            prices={},
            owned_ids=set(),
            prioritize_owned=False,
            commander_keywords=self._elf_commander(),
            synergy_weight=0.5,
        )
        assert "synergy_score" in selected[0]
        assert isinstance(selected[0]["synergy_score"], float)

    def test_no_commander_keywords_zero_synergy(self):
        cards = [
            FakeCardRow(id=1, name_en="Card A", oracle_text="Draw a card."),
        ]
        selected = _select_cards(
            candidates=cards,
            target_count=1,
            singleton=True,
            budget_remaining=None,
            prices={},
            owned_ids=set(),
            prioritize_owned=False,
            commander_keywords=None,
            synergy_weight=0.0,
        )
        assert selected[0]["synergy_score"] == 0.0

    def test_synergy_prioritizes_matching_cards(self):
        # Elf should come first with synergy weight
        cards = [
            FakeCardRow(
                id=1,
                name_en="Random Dragon",
                type_line="Creature \u2014 Dragon",
                rarity="M",
                oracle_text="Flying.",
            ),
            FakeCardRow(
                id=2,
                name_en="Elvish Archdruid",
                type_line="Creature \u2014 Elf Druid",
                rarity="C",
                oracle_text="{T}: Add {G} for each Elf you control.",
            ),
        ]
        selected = _select_cards(
            candidates=cards,
            target_count=1,
            singleton=True,
            budget_remaining=None,
            prices={},
            owned_ids=set(),
            prioritize_owned=False,
            commander_keywords=self._elf_commander(),
            synergy_weight=0.9,  # high weight to synergy
        )
        # Should pick the Elf despite lower rarity
        assert selected[0]["name_en"] == "Elvish Archdruid"

    def test_budget_still_respected(self):
        cards = [
            FakeCardRow(id=1, name_en="Expensive Elf", oracle_text="Draw a card."),
        ]
        selected = _select_cards(
            candidates=cards,
            target_count=1,
            singleton=True,
            budget_remaining=Decimal("1"),
            prices={1: Decimal("100")},
            owned_ids=set(),
            prioritize_owned=False,
            commander_keywords=self._elf_commander(),
            synergy_weight=0.7,
        )
        assert len(selected) == 0
