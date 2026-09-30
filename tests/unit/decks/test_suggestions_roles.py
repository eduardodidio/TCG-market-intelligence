"""Tests for role-coverage-based suggestions in the suggestion engine."""

from __future__ import annotations

from src.decks.suggestions import generate_suggestions
from src.domain.models import DeckEvaluation


def _base_eval(**overrides) -> DeckEvaluation:
    """Create a base DeckEvaluation with sensible defaults."""
    defaults = {
        "mana_curve": {2: 20, 3: 15, 4: 10},
        "color_distribution": {"G": 30, "W": 10},
        "type_distribution": {"Creature": 30, "Instant": 10, "Land": 37},
        "land_count": 37,
        "nonland_count": 63,
        "total_cards": 100,
        "avg_cmc": 2.8,
        "color_identity": {"G", "W"},
        "legality_check": None,
        "budget": None,
        "suggestions": [],
        "synergy_score": None,
        "role_coverage": None,
        "tribal_density": None,
    }
    defaults.update(overrides)
    return DeckEvaluation(**defaults)


class TestRoleCoverageSuggestions:
    def test_low_removal_warning(self):
        eval_ = _base_eval(
            role_coverage={"removal": 3, "draw": 10, "ramp": 10},
        )
        suggestions = generate_suggestions(eval_, archetype="aggro", format_name="commander")
        removal_suggestions = [s for s in suggestions if "removal" in s.lower()]
        assert len(removal_suggestions) >= 1

    def test_low_draw_warning(self):
        eval_ = _base_eval(
            role_coverage={"removal": 10, "draw": 2, "ramp": 10},
        )
        suggestions = generate_suggestions(eval_, archetype="control", format_name="commander")
        draw_suggestions = [s for s in suggestions if "card-draw" in s.lower()]
        assert len(draw_suggestions) >= 1

    def test_low_ramp_warning(self):
        eval_ = _base_eval(
            role_coverage={"removal": 10, "draw": 10, "ramp": 1},
        )
        suggestions = generate_suggestions(eval_, archetype="midrange", format_name="commander")
        ramp_suggestions = [s for s in suggestions if "ramp" in s.lower()]
        assert len(ramp_suggestions) >= 1

    def test_no_warning_when_above_minimum(self):
        eval_ = _base_eval(
            role_coverage={"removal": 15, "draw": 15, "ramp": 15},
        )
        suggestions = generate_suggestions(eval_, archetype="aggro", format_name="commander")
        role_warnings = [
            s
            for s in suggestions
            if "removal" in s.lower() or "card-draw" in s.lower() or "ramp" in s.lower()
        ]
        assert len(role_warnings) == 0

    def test_no_role_coverage_no_warning(self):
        eval_ = _base_eval(role_coverage=None)
        suggestions = generate_suggestions(eval_, archetype="aggro", format_name="commander")
        role_warnings = [
            s
            for s in suggestions
            if "removal" in s.lower() or "card-draw" in s.lower() or "ramp" in s.lower()
        ]
        assert len(role_warnings) == 0


class TestSynergyScoreSuggestion:
    def test_low_synergy_warning(self):
        eval_ = _base_eval(synergy_score=0.05)
        suggestions = generate_suggestions(eval_, archetype="midrange", format_name="commander")
        syn_suggestions = [s for s in suggestions if "synergy" in s.lower()]
        assert len(syn_suggestions) >= 1

    def test_adequate_synergy_no_warning(self):
        eval_ = _base_eval(synergy_score=0.30)
        suggestions = generate_suggestions(eval_, archetype="midrange", format_name="commander")
        syn_suggestions = [s for s in suggestions if "synergy" in s.lower()]
        assert len(syn_suggestions) == 0

    def test_none_synergy_no_warning(self):
        eval_ = _base_eval(synergy_score=None)
        suggestions = generate_suggestions(eval_, archetype="midrange", format_name="commander")
        syn_suggestions = [s for s in suggestions if "synergy" in s.lower()]
        assert len(syn_suggestions) == 0
