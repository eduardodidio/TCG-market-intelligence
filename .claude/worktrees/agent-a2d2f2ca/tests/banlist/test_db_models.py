"""Tests for F41 banlist DB models."""

from datetime import date, datetime

from src.database.models import CardLegalityRow, LegalityHistoryRow


class TestCardLegalityRow:
    def test_instantiation(self):
        row = CardLegalityRow(
            card_id=1,
            format="standard",
            status="banned",
            effective_date=date(2026, 1, 1),
            updated_at=datetime.now(),
        )
        assert row.card_id == 1
        assert row.format == "standard"
        assert row.status == "banned"

    def test_unique_constraint_name(self):
        constraints = {
            c.name for c in CardLegalityRow.__table__.constraints if hasattr(c, "name") and c.name
        }
        assert "uq_card_legality" in constraints

    def test_tablename(self):
        assert CardLegalityRow.__tablename__ == "card_legalities"


class TestLegalityHistoryRow:
    def test_instantiation(self):
        row = LegalityHistoryRow(
            card_id=1,
            format="modern",
            old_status="legal",
            new_status="banned",
            changed_at=datetime.now(),
            source="scryfall_sync",
        )
        assert row.new_status == "banned"
        assert row.source == "scryfall_sync"

    def test_tablename(self):
        assert LegalityHistoryRow.__tablename__ == "legality_history"

    def test_old_status_nullable(self):
        row = LegalityHistoryRow(
            card_id=1,
            format="standard",
            old_status=None,
            new_status="legal",
            changed_at=datetime.now(),
        )
        assert row.old_status is None
