"""Tests for the pure synergy scoring engine — no DB, no framework."""

from __future__ import annotations

from src.decks.synergy import (
    CommanderKeywords,
    classify_card_role,
    extract_commander_keywords,
    extract_subtypes,
    score_synergy,
)

# ---------------------------------------------------------------------------
# extract_subtypes
# ---------------------------------------------------------------------------


class TestExtractSubtypes:
    def test_simple_creature(self):
        assert extract_subtypes("Creature \u2014 Elf Warrior") == ["Elf", "Warrior"]

    def test_legendary_creature(self):
        assert extract_subtypes("Legendary Creature \u2014 Human Wizard") == [
            "Human",
            "Wizard",
        ]

    def test_no_em_dash(self):
        assert extract_subtypes("Creature") == []

    def test_empty_string(self):
        assert extract_subtypes("") == []

    def test_artifact_creature(self):
        assert extract_subtypes("Artifact Creature \u2014 Golem") == ["Golem"]

    def test_dfc_uses_front_face(self):
        result = extract_subtypes(
            "Legendary Creature \u2014 Vampire // Legendary Creature \u2014 Bat"
        )
        assert result == ["Vampire"]

    def test_enchantment_creature(self):
        assert extract_subtypes("Enchantment Creature \u2014 God") == ["God"]

    def test_land_no_subtypes(self):
        assert extract_subtypes("Basic Land \u2014 Forest") == ["Forest"]

    def test_no_supertypes_or_types_without_dash(self):
        result = extract_subtypes("Sorcery")
        assert result == []


# ---------------------------------------------------------------------------
# extract_commander_keywords
# ---------------------------------------------------------------------------


class TestExtractCommanderKeywords:
    def test_tribal_commander(self):
        kw = extract_commander_keywords(
            oracle_text="Whenever another Elf enters the battlefield, draw a card.",
            type_line="Legendary Creature \u2014 Elf Druid",
        )
        assert "Elf" in kw.tribal_types
        assert "Druid" in kw.tribal_types
        assert "draw" in kw.mechanic_keywords

    def test_sacrifice_commander(self):
        kw = extract_commander_keywords(
            oracle_text="Whenever a creature you control dies, each opponent loses 1 life.",
            type_line="Legendary Creature \u2014 Demon",
        )
        assert "sacrifice" in kw.mechanic_keywords
        assert "Demon" in kw.tribal_types

    def test_lifegain_commander(self):
        kw = extract_commander_keywords(
            oracle_text="Lifelink. Whenever you gain life, put a +1/+1 counter on target creature.",
            type_line="Legendary Creature \u2014 Angel",
        )
        assert "lifegain" in kw.mechanic_keywords
        assert "counter" in kw.mechanic_keywords

    def test_empty_oracle_text(self):
        kw = extract_commander_keywords(
            oracle_text="",
            type_line="Legendary Creature \u2014 Dragon",
        )
        assert kw.mechanic_keywords == []
        assert "Dragon" in kw.tribal_types

    def test_referenced_types(self):
        kw = extract_commander_keywords(
            oracle_text="Whenever you cast an Enchantment spell, draw a card.",
            type_line="Legendary Creature \u2014 Human Druid",
        )
        assert "Enchantment" in kw.referenced_types

    def test_token_commander(self):
        kw = extract_commander_keywords(
            oracle_text="Whenever a nontoken creature enters the battlefield, create a 1/1 token.",
            type_line="Legendary Creature \u2014 Elf Noble",
        )
        assert "token" in kw.mechanic_keywords

    def test_graveyard_commander(self):
        kw = extract_commander_keywords(
            oracle_text="You may cast creature cards from your graveyard.",
            type_line="Legendary Creature \u2014 Spirit",
        )
        assert "graveyard" in kw.mechanic_keywords

    def test_equipment_commander(self):
        kw = extract_commander_keywords(
            oracle_text="Whenever equipped creature deals combat damage, draw a card. Equip {2}",
            type_line="Legendary Artifact Creature \u2014 Kor Knight",
        )
        assert "equipment" in kw.mechanic_keywords
        assert "draw" in kw.mechanic_keywords

    def test_flicker_commander(self):
        kw = extract_commander_keywords(
            oracle_text="Exile target creature, then return it to the battlefield under its owner's control.",  # noqa: E501
            type_line="Legendary Creature \u2014 Spirit",
        )
        assert "flicker" in kw.mechanic_keywords


# ---------------------------------------------------------------------------
# classify_card_role
# ---------------------------------------------------------------------------


class TestClassifyCardRole:
    def test_draw_role(self):
        roles = classify_card_role("Draw a card.")
        assert "draw" in roles

    def test_ramp_role(self):
        roles = classify_card_role("Search your library for a basic land card.")
        assert "ramp" in roles

    def test_removal_role(self):
        roles = classify_card_role("Destroy target creature.")
        assert "removal" in roles

    def test_multiple_roles(self):
        roles = classify_card_role("Exile target creature. Draw a card.")
        assert "removal" in roles
        assert "draw" in roles

    def test_no_match_returns_utility(self):
        roles = classify_card_role("This card has no keywords.")
        assert roles == ["utility"]

    def test_empty_text_returns_utility(self):
        roles = classify_card_role("")
        assert roles == ["utility"]

    def test_counter_role(self):
        roles = classify_card_role("Put a +1/+1 counter on target creature.")
        assert "counter" in roles

    def test_lifegain_role(self):
        roles = classify_card_role("You gain 3 life.")
        assert "lifegain" in roles

    def test_protection_role(self):
        roles = classify_card_role("Hexproof. Indestructible.")
        assert "protection" in roles

    def test_mill_is_graveyard(self):
        roles = classify_card_role("Target player mills three cards.")
        assert "graveyard" in roles


# ---------------------------------------------------------------------------
# score_synergy
# ---------------------------------------------------------------------------


class TestScoreSynergy:
    def _elf_commander(self) -> CommanderKeywords:
        return CommanderKeywords(
            tribal_types=["Elf", "Druid"],
            mechanic_keywords=["draw", "ramp"],
            referenced_types=[],
        )

    def test_perfect_tribal_match(self):
        kw = self._elf_commander()
        score = score_synergy(
            card_oracle_text="",
            card_type_line="Creature \u2014 Elf Warrior",
            commander_keywords=kw,
        )
        assert score >= 0.3  # at least one tribal match

    def test_no_match_returns_zero(self):
        kw = self._elf_commander()
        score = score_synergy(
            card_oracle_text="Flying.",
            card_type_line="Creature \u2014 Bird",
            commander_keywords=kw,
        )
        assert score == 0.0

    def test_mechanic_match_only(self):
        kw = self._elf_commander()
        score = score_synergy(
            card_oracle_text="Draw a card. Search your library for a basic land.",
            card_type_line="Sorcery",
            commander_keywords=kw,
        )
        # draw + ramp = 0.2 + 0.2 = 0.4
        assert score >= 0.4

    def test_tribal_plus_mechanic(self):
        kw = self._elf_commander()
        score = score_synergy(
            card_oracle_text="Draw a card.",
            card_type_line="Creature \u2014 Elf Shaman",
            commander_keywords=kw,
        )
        # Elf tribal (0.3) + draw mechanic (0.2) = 0.5
        assert score >= 0.5

    def test_capped_at_one(self):
        kw = CommanderKeywords(
            tribal_types=["Elf", "Druid", "Shaman"],
            mechanic_keywords=[
                "draw",
                "ramp",
                "removal",
                "token",
                "counter",
            ],
            referenced_types=[],
        )
        score = score_synergy(
            card_oracle_text=(
                "Draw a card. Search your library for a basic land. "
                "Destroy target creature. Create a 1/1 token. "
                "Put a +1/+1 counter on target creature."
            ),
            card_type_line="Creature \u2014 Elf Druid Shaman",
            commander_keywords=kw,
        )
        assert score == 1.0

    def test_empty_oracle_and_type(self):
        kw = self._elf_commander()
        score = score_synergy(
            card_oracle_text="",
            card_type_line="",
            commander_keywords=kw,
        )
        assert score == 0.0

    def test_double_tribal_match(self):
        kw = self._elf_commander()
        score = score_synergy(
            card_oracle_text="",
            card_type_line="Creature \u2014 Elf Druid",
            commander_keywords=kw,
        )
        # Two tribal matches: 0.3 + 0.3 = 0.6
        assert score == 0.6

    def test_score_range(self):
        kw = self._elf_commander()
        score = score_synergy(
            card_oracle_text="Add {G}.",
            card_type_line="Artifact",
            commander_keywords=kw,
        )
        assert 0.0 <= score <= 1.0
