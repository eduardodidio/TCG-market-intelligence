"""Tests for synergy metrics in the deck evaluator."""

from __future__ import annotations

from src.decks.evaluator import evaluate_deck


def _make_card(
    name: str = "Test",
    type_line: str = "Creature",
    oracle_text: str = "",
    mana_cost: str = "{1}",
    card_id: int | None = None,
    quantity: int = 1,
    color_identity: str = "",
    rarity: str = "C",
) -> dict:
    return {
        "card_id": card_id,
        "name_en": name,
        "type_line": type_line,
        "oracle_text": oracle_text,
        "mana_cost": mana_cost,
        "quantity": quantity,
        "color_identity": color_identity,
        "rarity": rarity,
    }


class TestEvaluatorSynergyScore:
    def test_synergy_score_computed_with_commander(self):
        cards = [
            _make_card(
                name="Elf Commander",
                type_line="Legendary Creature \u2014 Elf Druid",
                oracle_text="Whenever another Elf enters, draw a card.",
            ),
            _make_card(
                name="Llanowar Elves",
                type_line="Creature \u2014 Elf Druid",
                oracle_text="{T}: Add {G}.",
            ),
            _make_card(
                name="Plains",
                type_line="Basic Land",
                oracle_text="",
            ),
        ]
        result = evaluate_deck(cards)
        assert result.synergy_score is not None
        assert 0.0 <= result.synergy_score <= 1.0

    def test_no_commander_no_synergy_score(self):
        cards = [
            _make_card(name="Goblin", type_line="Creature \u2014 Goblin"),
        ]
        result = evaluate_deck(cards)
        assert result.synergy_score is None

    def test_tribal_density_computed(self):
        cards = [
            _make_card(
                name="Commander",
                type_line="Legendary Creature \u2014 Elf",
                oracle_text="",
            ),
            _make_card(
                name="Elf1",
                type_line="Creature \u2014 Elf",
            ),
            _make_card(
                name="Elf2",
                type_line="Creature \u2014 Elf Warrior",
            ),
            _make_card(
                name="Human",
                type_line="Creature \u2014 Human",
            ),
        ]
        result = evaluate_deck(cards)
        # Commander + 2 elves out of 4 creatures = 3/4 = 0.75
        assert result.tribal_density is not None
        assert result.tribal_density == 0.75

    def test_tribal_density_none_without_commander(self):
        cards = [
            _make_card(name="Goblin", type_line="Creature \u2014 Goblin"),
        ]
        result = evaluate_deck(cards)
        assert result.tribal_density is None


class TestEvaluatorRoleCoverage:
    def test_role_coverage_populated(self):
        cards = [
            _make_card(
                name="Commander",
                type_line="Legendary Creature \u2014 Elf",
                oracle_text="Draw a card.",
            ),
            _make_card(
                name="Bolt",
                type_line="Instant",
                oracle_text="Lightning Bolt deals 3 damage to any target.",
            ),
            _make_card(
                name="Rampant",
                type_line="Sorcery",
                oracle_text="Search your library for a basic land card.",
            ),
        ]
        result = evaluate_deck(cards)
        assert result.role_coverage is not None
        assert "draw" in result.role_coverage
        assert "removal" in result.role_coverage
        assert "ramp" in result.role_coverage

    def test_role_coverage_none_without_oracle_text(self):
        cards = [
            _make_card(name="Card", type_line="Creature", oracle_text=""),
        ]
        result = evaluate_deck(cards)
        # No oracle_text on any card -> no roles detected -> None
        assert result.role_coverage is None

    def test_role_coverage_quantity_weighted(self):
        cards = [
            _make_card(
                name="Draw Card",
                type_line="Instant",
                oracle_text="Draw a card.",
                quantity=3,
            ),
        ]
        result = evaluate_deck(cards)
        assert result.role_coverage is not None
        assert result.role_coverage["draw"] == 3
