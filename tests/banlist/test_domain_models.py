"""Tests for F41 banlist domain models."""

from datetime import date, datetime

from src.domain.models import (
    BanlistSyncSummary,
    CardLegality,
    LegalityChange,
    LegalityStatus,
)


class TestLegalityStatus:
    def test_values_match_scryfall(self):
        assert LegalityStatus.LEGAL.value == "legal"
        assert LegalityStatus.NOT_LEGAL.value == "not_legal"
        assert LegalityStatus.BANNED.value == "banned"
        assert LegalityStatus.RESTRICTED.value == "restricted"

    def test_all_four_values(self):
        assert len(LegalityStatus) == 4

    def test_is_str_enum(self):
        assert isinstance(LegalityStatus.LEGAL, str)
        assert LegalityStatus.BANNED == "banned"


class TestCardLegality:
    def test_basic_creation(self):
        leg = CardLegality(card_id=1, format="standard", status="legal")
        assert leg.card_id == 1
        assert leg.format == "standard"
        assert leg.status == "legal"
        assert leg.effective_date is None

    def test_with_effective_date(self):
        d = date(2026, 8, 1)
        leg = CardLegality(card_id=42, format="modern", status="banned", effective_date=d)
        assert leg.effective_date == d


class TestLegalityChange:
    def test_basic_creation(self):
        change = LegalityChange(
            card_id=1,
            format="standard",
            old_status="legal",
            new_status="banned",
        )
        assert change.card_id == 1
        assert change.old_status == "legal"
        assert change.new_status == "banned"
        assert change.source == "scryfall_sync"
        assert isinstance(change.changed_at, datetime)

    def test_initial_ban_no_old_status(self):
        change = LegalityChange(
            card_id=1,
            format="standard",
            old_status=None,
            new_status="banned",
        )
        assert change.old_status is None


class TestBanlistSyncSummary:
    def test_defaults(self):
        summary = BanlistSyncSummary()
        assert summary.cards_processed == 0
        assert summary.legalities_upserted == 0
        assert summary.changes_detected == 0
        assert summary.errors == 0
        assert isinstance(summary.started_at, datetime)
        assert summary.finished_at is None
