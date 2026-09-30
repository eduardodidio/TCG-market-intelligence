"""Tests for synergy-related schema additions in deck API schemas."""

from __future__ import annotations

from src.api.schemas.decks import (
    DeckEvaluationResponse,
    DeckGenerateRequest,
    DeckGenerateResponse,
    GeneratedCardSchema,
    RoleCoverageEntry,
)


class TestGeneratedCardSchemaSynergy:
    def test_synergy_score_field_exists(self):
        card = GeneratedCardSchema(name_en="Test Card")
        assert card.synergy_score is None

    def test_synergy_score_set(self):
        card = GeneratedCardSchema(name_en="Test Card", synergy_score=0.75)
        assert card.synergy_score == 0.75


class TestDeckGenerateRequestSynergy:
    def test_default_synergy_weight(self):
        req = DeckGenerateRequest(format_name="commander")
        assert req.synergy_weight == 0.7

    def test_custom_synergy_weight(self):
        req = DeckGenerateRequest(format_name="commander", synergy_weight=0.3)
        assert req.synergy_weight == 0.3

    def test_synergy_weight_clamped_max(self):
        import pytest

        with pytest.raises(Exception):
            DeckGenerateRequest(format_name="commander", synergy_weight=1.5)

    def test_synergy_weight_clamped_min(self):
        import pytest

        with pytest.raises(Exception):
            DeckGenerateRequest(format_name="commander", synergy_weight=-0.1)


class TestDeckGenerateResponseSynergy:
    def test_default_values(self):
        resp = DeckGenerateResponse(deck_id=1, name="Test", format_name="commander")
        assert resp.synergy_weight == 0.7
        assert resp.avg_synergy_score is None

    def test_custom_values(self):
        resp = DeckGenerateResponse(
            deck_id=1,
            name="Test",
            format_name="commander",
            synergy_weight=0.5,
            avg_synergy_score=0.35,
        )
        assert resp.synergy_weight == 0.5
        assert resp.avg_synergy_score == 0.35


class TestDeckEvaluationResponseSynergy:
    def test_synergy_fields_default(self):
        resp = DeckEvaluationResponse(deck_id=1)
        assert resp.synergy_score is None
        assert resp.role_coverage == []
        assert resp.tribal_density is None

    def test_synergy_fields_populated(self):
        resp = DeckEvaluationResponse(
            deck_id=1,
            synergy_score=0.42,
            role_coverage=[
                RoleCoverageEntry(role="draw", count=10),
                RoleCoverageEntry(role="removal", count=8),
            ],
            tribal_density=0.65,
        )
        assert resp.synergy_score == 0.42
        assert len(resp.role_coverage) == 2
        assert resp.role_coverage[0].role == "draw"
        assert resp.tribal_density == 0.65


class TestRoleCoverageEntry:
    def test_basic(self):
        entry = RoleCoverageEntry(role="ramp", count=5)
        assert entry.role == "ramp"
        assert entry.count == 5
