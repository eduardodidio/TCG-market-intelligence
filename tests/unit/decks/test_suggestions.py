"""Tests for deck suggestion engine — T05."""

from __future__ import annotations

from src.decks.suggestions import (
    ARCHETYPE_TEMPLATES,
    _in_range,
    generate_suggestions,
)
from src.domain.models import DeckEvaluation


def _make_evaluation(**overrides) -> DeckEvaluation:
    """Create a DeckEvaluation with sensible defaults, overridable."""
    defaults = {
        "mana_curve": {1: 10, 2: 15, 3: 12, 4: 8, 5: 5, 6: 2, 7: 1},
        "color_distribution": {"W": 15, "U": 15, "B": 15},
        "type_distribution": {
            "Creature": 25,
            "Instant": 10,
            "Sorcery": 8,
            "Enchantment": 6,
            "Artifact": 10,
            "Land": 37,
            "Planeswalker": 2,
            "Other": 2,
        },
        "land_count": 37,
        "nonland_count": 63,
        "total_cards": 100,
        "avg_cmc": 3.0,
        "color_identity": {"W", "U", "B"},
        "legality_check": None,
        "budget": None,
        "suggestions": [],
    }
    defaults.update(overrides)
    return DeckEvaluation(**defaults)


# ---------------------------------------------------------------------------
# _in_range helper
# ---------------------------------------------------------------------------


class TestInRange:
    def test_value_below_range(self):
        assert _in_range(5, (10, 20)) == "low"

    def test_value_above_range(self):
        assert _in_range(25, (10, 20)) == "high"

    def test_value_in_range(self):
        assert _in_range(15, (10, 20)) is None

    def test_value_at_lower_bound(self):
        assert _in_range(10, (10, 20)) is None

    def test_value_at_upper_bound(self):
        assert _in_range(20, (10, 20)) is None

    def test_float_values(self):
        assert _in_range(2.5, (2.0, 3.2)) is None
        assert _in_range(1.5, (2.0, 3.2)) == "low"
        assert _in_range(4.0, (2.0, 3.2)) == "high"


# ---------------------------------------------------------------------------
# ARCHETYPE_TEMPLATES structure
# ---------------------------------------------------------------------------


class TestArchetypeTemplates:
    def test_commander_archetypes_exist(self):
        assert "commander" in ARCHETYPE_TEMPLATES
        cmd = ARCHETYPE_TEMPLATES["commander"]
        for arch in ("aggro", "control", "midrange", "combo", "tempo"):
            assert arch in cmd, f"Missing archetype: {arch}"

    def test_template_has_required_keys(self):
        template = ARCHETYPE_TEMPLATES["commander"]["aggro"]
        required_keys = [
            "land_range",
            "creature_range",
            "instant_range",
            "sorcery_range",
            "enchantment_range",
            "artifact_range",
            "removal_min",
            "card_draw_min",
            "ramp_min",
            "avg_cmc_range",
        ]
        for key in required_keys:
            assert key in template, f"Missing key: {key}"

    def test_land_ranges_are_tuples(self):
        for fmt, archetypes in ARCHETYPE_TEMPLATES.items():
            for arch, template in archetypes.items():
                land_range = template["land_range"]
                assert isinstance(land_range, tuple) and len(land_range) == 2
                assert land_range[0] <= land_range[1]


# ---------------------------------------------------------------------------
# Card count suggestions
# ---------------------------------------------------------------------------


class TestCardCountSuggestions:
    def test_correct_card_count_no_suggestion(self):
        ev = _make_evaluation(total_cards=100)
        suggestions = generate_suggestions(ev, format_name="commander")
        card_count_msgs = [s for s in suggestions if "expected" in s]
        assert len(card_count_msgs) == 0

    def test_too_few_cards(self):
        ev = _make_evaluation(total_cards=85)
        suggestions = generate_suggestions(ev, format_name="commander")
        card_count_msgs = [s for s in suggestions if "expected" in s]
        assert len(card_count_msgs) == 1
        assert "85 cards" in card_count_msgs[0]
        assert "100" in card_count_msgs[0]

    def test_too_many_cards(self):
        ev = _make_evaluation(total_cards=105)
        suggestions = generate_suggestions(ev, format_name="commander")
        card_count_msgs = [s for s in suggestions if "expected" in s]
        assert len(card_count_msgs) == 1
        assert "105 cards" in card_count_msgs[0]

    def test_no_format_no_card_count_check(self):
        ev = _make_evaluation(total_cards=50)
        suggestions = generate_suggestions(ev, format_name=None)
        card_count_msgs = [s for s in suggestions if "expected" in s]
        assert len(card_count_msgs) == 0

    def test_60_card_format(self):
        ev = _make_evaluation(total_cards=55)
        suggestions = generate_suggestions(ev, format_name="standard")
        card_count_msgs = [s for s in suggestions if "expected" in s]
        assert len(card_count_msgs) == 1
        assert "60" in card_count_msgs[0]


# ---------------------------------------------------------------------------
# Land count suggestions
# ---------------------------------------------------------------------------


class TestLandCountSuggestions:
    def test_too_few_lands_with_template(self):
        ev = _make_evaluation(land_count=30)
        suggestions = generate_suggestions(
            ev,
            archetype="aggro",
            format_name="commander",
        )
        land_msgs = [s for s in suggestions if "more lands" in s]
        assert len(land_msgs) == 1
        assert "aggro" in land_msgs[0].lower()

    def test_too_many_lands_with_template(self):
        ev = _make_evaluation(land_count=45)
        suggestions = generate_suggestions(
            ev,
            archetype="aggro",
            format_name="commander",
        )
        land_msgs = [s for s in suggestions if "cutting" in s.lower()]
        assert len(land_msgs) == 1

    def test_lands_in_range_no_suggestion(self):
        ev = _make_evaluation(land_count=36)
        suggestions = generate_suggestions(
            ev,
            archetype="aggro",
            format_name="commander",
        )
        land_msgs = [
            s for s in suggestions if "lands" in s.lower() and ("more" in s or "cutting" in s)
        ]
        assert len(land_msgs) == 0

    def test_generic_land_check_no_archetype(self):
        ev = _make_evaluation(land_count=25)
        suggestions = generate_suggestions(ev, format_name="commander")
        land_msgs = [s for s in suggestions if "more lands" in s]
        assert len(land_msgs) == 1

    def test_generic_too_many_lands(self):
        ev = _make_evaluation(land_count=45)
        suggestions = generate_suggestions(ev, format_name="commander")
        land_msgs = [s for s in suggestions if "cutting" in s.lower()]
        assert len(land_msgs) == 1


# ---------------------------------------------------------------------------
# Creature count suggestions
# ---------------------------------------------------------------------------


class TestCreatureCountSuggestions:
    def test_too_few_creatures(self):
        ev = _make_evaluation(
            type_distribution={"Creature": 10, "Instant": 20, "Land": 37},
        )
        suggestions = generate_suggestions(
            ev,
            archetype="aggro",
            format_name="commander",
        )
        creature_msgs = [s for s in suggestions if "creatures" in s.lower()]
        assert len(creature_msgs) == 1
        assert "more creatures" in creature_msgs[0].lower()

    def test_too_many_creatures(self):
        ev = _make_evaluation(
            type_distribution={"Creature": 40, "Instant": 5, "Land": 37},
        )
        suggestions = generate_suggestions(
            ev,
            archetype="aggro",
            format_name="commander",
        )
        creature_msgs = [
            s for s in suggestions if "creatures" in s.lower() and "cutting" in s.lower()
        ]
        assert len(creature_msgs) == 1

    def test_creature_count_no_archetype_no_check(self):
        """Without archetype template, creature count is not checked."""
        ev = _make_evaluation(
            type_distribution={"Creature": 5, "Instant": 20, "Land": 37},
        )
        suggestions = generate_suggestions(ev, format_name="commander")
        creature_msgs = [s for s in suggestions if "creatures" in s.lower()]
        assert len(creature_msgs) == 0


# ---------------------------------------------------------------------------
# Average CMC suggestions
# ---------------------------------------------------------------------------


class TestAvgCmcSuggestions:
    def test_cmc_too_high_with_template(self):
        ev = _make_evaluation(avg_cmc=4.0, nonland_count=60)
        suggestions = generate_suggestions(
            ev,
            archetype="aggro",
            format_name="commander",
        )
        cmc_msgs = [s for s in suggestions if "mana cost" in s.lower()]
        assert len(cmc_msgs) == 1
        assert "high" in cmc_msgs[0].lower()

    def test_cmc_too_low_with_template(self):
        ev = _make_evaluation(avg_cmc=1.5, nonland_count=60)
        suggestions = generate_suggestions(
            ev,
            archetype="aggro",
            format_name="commander",
        )
        cmc_msgs = [s for s in suggestions if "mana cost" in s.lower()]
        assert len(cmc_msgs) == 1
        assert "higher-impact" in cmc_msgs[0].lower()

    def test_cmc_in_range_no_suggestion(self):
        ev = _make_evaluation(avg_cmc=2.5, nonland_count=60)
        suggestions = generate_suggestions(
            ev,
            archetype="aggro",
            format_name="commander",
        )
        cmc_msgs = [s for s in suggestions if "mana cost" in s.lower()]
        assert len(cmc_msgs) == 0

    def test_generic_cmc_high(self):
        ev = _make_evaluation(avg_cmc=4.0, nonland_count=60)
        suggestions = generate_suggestions(ev, format_name="commander")
        cmc_msgs = [s for s in suggestions if "mana cost" in s.lower()]
        assert len(cmc_msgs) == 1

    def test_no_nonland_cards_no_cmc_check(self):
        ev = _make_evaluation(avg_cmc=0.0, nonland_count=0)
        suggestions = generate_suggestions(ev, format_name="commander")
        cmc_msgs = [s for s in suggestions if "mana cost" in s.lower()]
        assert len(cmc_msgs) == 0


# ---------------------------------------------------------------------------
# Color balance suggestions
# ---------------------------------------------------------------------------


class TestColorBalanceSuggestions:
    def test_balanced_colors_no_suggestion(self):
        ev = _make_evaluation(
            color_distribution={"W": 15, "U": 15, "B": 15},
        )
        suggestions = generate_suggestions(ev, format_name="commander")
        color_msgs = [s for s in suggestions if "Color" in s]
        assert len(color_msgs) == 0

    def test_one_color_underrepresented(self):
        ev = _make_evaluation(
            color_distribution={"W": 30, "U": 30, "B": 1},
        )
        suggestions = generate_suggestions(ev, format_name="commander")
        color_msgs = [s for s in suggestions if "Black" in s]
        assert len(color_msgs) == 1
        assert "very few" in color_msgs[0].lower()

    def test_two_colors_no_balance_check(self):
        """Color balance only triggers for 3+ colors."""
        ev = _make_evaluation(
            color_distribution={"W": 50, "U": 1},
        )
        suggestions = generate_suggestions(ev, format_name="commander")
        color_msgs = [s for s in suggestions if "Color" in s and "few" in s]
        assert len(color_msgs) == 0

    def test_five_colors_one_weak(self):
        ev = _make_evaluation(
            color_distribution={"W": 20, "U": 20, "B": 20, "R": 20, "G": 1},
        )
        suggestions = generate_suggestions(ev, format_name="commander")
        color_msgs = [s for s in suggestions if "Green" in s]
        assert len(color_msgs) == 1


# ---------------------------------------------------------------------------
# Interaction (instant count) suggestions
# ---------------------------------------------------------------------------


class TestInteractionSuggestions:
    def test_few_instants_triggers_suggestion(self):
        ev = _make_evaluation(
            type_distribution={"Creature": 50, "Instant": 2, "Land": 37},
            total_cards=100,
        )
        suggestions = generate_suggestions(ev, format_name="commander")
        instant_msgs = [s for s in suggestions if "instant-speed" in s.lower()]
        assert len(instant_msgs) == 1

    def test_enough_instants_no_suggestion(self):
        ev = _make_evaluation(
            type_distribution={"Creature": 40, "Instant": 10, "Land": 37},
            total_cards=100,
        )
        suggestions = generate_suggestions(ev, format_name="commander")
        instant_msgs = [s for s in suggestions if "instant-speed" in s.lower()]
        assert len(instant_msgs) == 0

    def test_small_deck_no_instant_check(self):
        """Decks with < 20 cards skip the instant check."""
        ev = _make_evaluation(
            type_distribution={"Creature": 5, "Instant": 0, "Land": 5},
            total_cards=10,
        )
        suggestions = generate_suggestions(ev, format_name=None)
        instant_msgs = [s for s in suggestions if "instant-speed" in s.lower()]
        assert len(instant_msgs) == 0


# ---------------------------------------------------------------------------
# Legality suggestions
# ---------------------------------------------------------------------------


class TestLegalitySuggestions:
    def test_illegal_cards_listed(self):
        ev = _make_evaluation(
            legality_check={
                "format": "commander",
                "is_legal": False,
                "illegal_cards": [
                    {"name_en": "Banned Card", "status": "banned"},
                    {"name_en": "Not Legal Card", "status": "not_legal"},
                ],
                "singleton_violations": [],
                "card_count_valid": True,
            },
        )
        suggestions = generate_suggestions(ev, format_name="commander")
        illegal_msgs = [s for s in suggestions if "not legal" in s.lower()]
        assert len(illegal_msgs) == 1
        assert "2 card(s)" in illegal_msgs[0]
        assert "Banned Card" in illegal_msgs[0]

    def test_singleton_violations_listed(self):
        ev = _make_evaluation(
            legality_check={
                "format": "commander",
                "is_legal": False,
                "illegal_cards": [],
                "singleton_violations": ["Sol Ring", "Lightning Bolt"],
                "card_count_valid": True,
            },
        )
        suggestions = generate_suggestions(ev, format_name="commander")
        singleton_msgs = [s for s in suggestions if "singleton" in s.lower()]
        assert len(singleton_msgs) == 1
        assert "Sol Ring" in singleton_msgs[0]

    def test_no_legality_check_no_suggestions(self):
        ev = _make_evaluation(legality_check=None)
        suggestions = generate_suggestions(ev, format_name="commander")
        legal_msgs = [s for s in suggestions if "legal" in s.lower() or "singleton" in s.lower()]
        assert len(legal_msgs) == 0


# ---------------------------------------------------------------------------
# Unknown archetype / format
# ---------------------------------------------------------------------------


class TestUnknownArchetypeFormat:
    def test_unknown_archetype_falls_back_to_generic(self):
        ev = _make_evaluation(land_count=25)
        suggestions = generate_suggestions(
            ev,
            archetype="unknown_type",
            format_name="commander",
        )
        # Should still get generic land suggestion, not template-specific
        land_msgs = [s for s in suggestions if "more lands" in s]
        assert len(land_msgs) == 1
        # Should NOT mention archetype template name
        assert "unknown_type" not in land_msgs[0]

    def test_unknown_format_no_template(self):
        ev = _make_evaluation(land_count=25)
        suggestions = generate_suggestions(
            ev,
            archetype="aggro",
            format_name="unknown_format",
        )
        # No template match, but card count check may not trigger (unknown format)
        # Land check should not use template-specific ranges
        land_msgs = [
            s for s in suggestions if "lands" in s.lower() and ("more" in s or "cutting" in s)
        ]
        assert len(land_msgs) == 0  # No generic range for unknown format

    def test_no_archetype_no_format(self):
        ev = _make_evaluation()
        suggestions = generate_suggestions(ev)
        # Only generic checks: CMC (if high), color balance, interaction
        # With defaults, everything is in range -> few or no suggestions
        assert isinstance(suggestions, list)


# ---------------------------------------------------------------------------
# Perfect deck — no suggestions
# ---------------------------------------------------------------------------


class TestPerfectDeck:
    def test_well_balanced_deck_no_suggestions(self):
        """A deck within all archetype ranges should return empty suggestions."""
        ev = _make_evaluation(
            total_cards=100,
            land_count=36,
            nonland_count=64,
            avg_cmc=2.8,
            type_distribution={
                "Creature": 30,
                "Instant": 8,
                "Sorcery": 6,
                "Enchantment": 5,
                "Artifact": 10,
                "Land": 36,
                "Planeswalker": 2,
                "Other": 3,
            },
            color_distribution={"W": 15, "U": 15, "B": 15},
            legality_check=None,
        )
        suggestions = generate_suggestions(
            ev,
            archetype="aggro",
            format_name="commander",
        )
        assert suggestions == []


# ---------------------------------------------------------------------------
# Integration with evaluate_deck
# ---------------------------------------------------------------------------


class TestEvaluatorIntegration:
    def test_evaluate_deck_populates_suggestions(self):
        """evaluate_deck should populate the suggestions field."""
        from src.decks.evaluator import evaluate_deck

        # Build a 10-card deck (too few for commander)
        cards = [
            {
                "card_id": 1,
                "name_en": "Lightning Bolt",
                "mana_cost": "{R}",
                "type_line": "Instant",
                "color_identity": "R",
                "rarity": "common",
                "quantity": 4,
            },
            {
                "card_id": 2,
                "name_en": "Plains",
                "mana_cost": None,
                "type_line": "Basic Land",
                "color_identity": "",
                "rarity": "common",
                "quantity": 6,
            },
        ]
        result = evaluate_deck(
            cards,
            format_name="commander",
            archetype="aggro",
        )
        # Should have suggestions about card count, land count, etc.
        assert len(result.suggestions) > 0
        # Card count suggestion should be first (critical)
        assert "expected" in result.suggestions[0].lower()

    def test_evaluate_deck_no_format_minimal_suggestions(self):
        """Without format, only generic checks run."""
        from src.decks.evaluator import evaluate_deck

        cards = [
            {
                "card_id": 1,
                "name_en": "Creature",
                "mana_cost": "{2}",
                "type_line": "Creature",
                "color_identity": "W",
                "rarity": "common",
                "quantity": 10,
            },
        ]
        result = evaluate_deck(cards)
        # With only 10 cards, instant check won't trigger (< 20 cards)
        assert isinstance(result.suggestions, list)

    def test_evaluate_deck_suggestions_field_is_list(self):
        """Suggestions field should always be a list."""
        from src.decks.evaluator import evaluate_deck

        result = evaluate_deck([])
        assert isinstance(result.suggestions, list)


# ---------------------------------------------------------------------------
# Severity ordering
# ---------------------------------------------------------------------------


class TestSeverityOrdering:
    def test_critical_before_warnings(self):
        """Card count / legality issues should appear before land/CMC suggestions."""
        ev = _make_evaluation(
            total_cards=85,  # Wrong card count (critical)
            land_count=25,  # Too few lands (warning)
            avg_cmc=4.5,  # Too high CMC (warning)
            nonland_count=60,
            legality_check={
                "format": "commander",
                "is_legal": False,
                "illegal_cards": [{"name_en": "Bad Card", "status": "banned"}],
                "singleton_violations": [],
                "card_count_valid": False,
            },
        )
        suggestions = generate_suggestions(
            ev,
            archetype="aggro",
            format_name="commander",
        )
        # Card count and legality should come first
        assert any("expected" in s for s in suggestions[:3])
        assert any("not legal" in s.lower() for s in suggestions[:3])

    def test_info_comes_last(self):
        """Color balance and interaction suggestions come after warnings."""
        ev = _make_evaluation(
            total_cards=100,
            land_count=30,  # Too few (warning)
            avg_cmc=2.5,
            nonland_count=70,
            type_distribution={"Creature": 50, "Instant": 2, "Land": 30},
            color_distribution={"W": 30, "U": 30, "B": 1},
        )
        suggestions = generate_suggestions(
            ev,
            archetype="aggro",
            format_name="commander",
        )
        # The instant-speed and color balance msgs should be after land msgs
        if len(suggestions) >= 2:
            land_idx = next(
                (i for i, s in enumerate(suggestions) if "lands" in s.lower()),
                -1,
            )
            instant_idx = next(
                (i for i, s in enumerate(suggestions) if "instant-speed" in s.lower()),
                -1,
            )
            if land_idx >= 0 and instant_idx >= 0:
                assert land_idx < instant_idx
