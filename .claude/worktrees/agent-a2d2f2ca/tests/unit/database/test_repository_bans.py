"""Tests for Repository ban engine (F42) query methods."""

from __future__ import annotations

from datetime import datetime, timedelta

import pytest
from sqlalchemy.orm import Session

from src.database.models import (
    CardLegalityRow,
    CardRow,
    LegalityHistoryRow,
    UserCollectionRow,
)
from src.database.repository import Repository


@pytest.fixture()
def repo(tmp_path):
    db_path = tmp_path / "test.db"
    return Repository(f"sqlite:///{db_path}")


@pytest.fixture()
def seeded_repo(repo):
    """Seed repo with collection + legality data for ban engine tests."""
    engine = repo.engine
    with Session(engine) as session:
        # Create canonical cards
        card1 = CardRow(
            id=1, game="magic", name_en="Counterspell", set_code="DMR", collector_number="10"
        )
        card2 = CardRow(
            id=2, game="magic", name_en="Lightning Bolt", set_code="2XM", collector_number="5"
        )
        card3 = CardRow(
            id=3, game="magic", name_en="Aether Vial", set_code="MH2", collector_number="1"
        )
        session.add_all([card1, card2, card3])
        session.flush()

        # Collection entries
        uc1 = UserCollectionRow(
            user_id="u1",
            card_id=1,
            set_code="DMR",
            collector_number="10",
            name_en="Counterspell",
            quantity=2,
        )
        uc2 = UserCollectionRow(
            user_id="u1",
            card_id=2,
            set_code="2XM",
            collector_number="5",
            name_en="Lightning Bolt",
            quantity=1,
        )
        uc3 = UserCollectionRow(
            user_id="u1",
            card_id=3,
            set_code="MH2",
            collector_number="1",
            name_en="Aether Vial",
            quantity=1,
        )
        # Unlinked card (card_id=None)
        uc4 = UserCollectionRow(
            user_id="u1",
            card_id=None,
            set_code="LEA",
            collector_number="99",
            name_en="Unlinked Card",
            quantity=1,
        )
        # Other user's card
        uc5 = UserCollectionRow(
            user_id="u2",
            card_id=1,
            set_code="DMR",
            collector_number="10",
            name_en="Counterspell",
            quantity=1,
        )
        session.add_all([uc1, uc2, uc3, uc4, uc5])
        session.flush()

        # Legalities
        # Counterspell: banned in standard, legal in modern
        leg1 = CardLegalityRow(card_id=1, format="standard", status="banned")
        leg2 = CardLegalityRow(card_id=1, format="modern", status="legal")
        # Lightning Bolt: restricted in vintage
        leg3 = CardLegalityRow(card_id=2, format="vintage", status="restricted")
        leg4 = CardLegalityRow(card_id=2, format="modern", status="legal")
        # Aether Vial: legal everywhere
        leg5 = CardLegalityRow(card_id=3, format="modern", status="legal")
        leg6 = CardLegalityRow(card_id=3, format="standard", status="not_legal")
        session.add_all([leg1, leg2, leg3, leg4, leg5, leg6])

        # Recent legality history: Counterspell was recently banned in standard
        hist1 = LegalityHistoryRow(
            card_id=1,
            format="standard",
            old_status="legal",
            new_status="banned",
            changed_at=datetime.now() - timedelta(days=3),
        )
        # Old change for Lightning Bolt (outside window)
        hist2 = LegalityHistoryRow(
            card_id=2,
            format="vintage",
            old_status="legal",
            new_status="restricted",
            changed_at=datetime.now() - timedelta(days=60),
        )
        session.add_all([hist1, hist2])
        session.commit()

    return repo


class TestGetBannedCollectionCards:
    def test_returns_banned_and_restricted(self, seeded_repo):
        results = seeded_repo.get_banned_collection_cards("u1")
        assert len(results) == 2
        statuses = {r["status"] for r in results}
        assert "banned" in statuses
        assert "restricted" in statuses

    def test_format_filter_narrows_results(self, seeded_repo):
        results = seeded_repo.get_banned_collection_cards("u1", format_filter="standard")
        assert len(results) == 1
        assert results[0]["format"] == "standard"
        assert results[0]["status"] == "banned"

    def test_format_filter_no_match(self, seeded_repo):
        results = seeded_repo.get_banned_collection_cards("u1", format_filter="legacy")
        assert len(results) == 0

    def test_excludes_unlinked_cards(self, seeded_repo):
        results = seeded_repo.get_banned_collection_cards("u1")
        card_ids = {r["card_id"] for r in results}
        assert None not in card_ids

    def test_user_isolation(self, seeded_repo):
        results_u1 = seeded_repo.get_banned_collection_cards("u1")
        results_u2 = seeded_repo.get_banned_collection_cards("u2")
        assert len(results_u1) == 2
        assert len(results_u2) == 1  # u2 owns Counterspell (banned in standard)

    def test_returns_expected_fields(self, seeded_repo):
        results = seeded_repo.get_banned_collection_cards("u1")
        row = results[0]
        assert "entry_id" in row
        assert "card_id" in row
        assert "name_en" in row
        assert "set_code" in row
        assert "quantity" in row
        assert "format" in row
        assert "status" in row


class TestGetCollectionBanSummary:
    def test_returns_correct_counts(self, seeded_repo):
        result = seeded_repo.get_collection_ban_summary("u1")
        assert result["banned_count"] == 1  # 1 distinct card banned
        assert result["restricted_count"] == 1  # 1 distinct card restricted

    def test_no_banned_cards(self, seeded_repo):
        result = seeded_repo.get_collection_ban_summary("nonexistent")
        assert result["banned_count"] == 0
        assert result["restricted_count"] == 0


class TestGetCardLegalitiesWithHistory:
    def test_returns_legalities_with_change_info(self, seeded_repo):
        results = seeded_repo.get_card_legalities_with_history(1, days=30)
        assert len(results) == 2
        # Standard should be recently changed
        standard = next(r for r in results if r["format"] == "standard")
        assert standard["recently_changed"] is True
        assert standard["old_status"] == "legal"

    def test_no_recent_changes(self, seeded_repo):
        results = seeded_repo.get_card_legalities_with_history(2, days=30)
        # Vintage change was 60 days ago, outside 30-day window
        vintage = next(r for r in results if r["format"] == "vintage")
        assert vintage["recently_changed"] is False

    def test_wider_window_shows_changes(self, seeded_repo):
        results = seeded_repo.get_card_legalities_with_history(2, days=90)
        vintage = next(r for r in results if r["format"] == "vintage")
        assert vintage["recently_changed"] is True

    def test_nonexistent_card(self, seeded_repo):
        results = seeded_repo.get_card_legalities_with_history(999, days=30)
        assert results == []


class TestGetRecentlyChangedCardIds:
    def test_returns_recently_changed(self, seeded_repo):
        result = seeded_repo.get_recently_changed_card_ids("u1", days=7)
        assert 1 in result  # Counterspell changed 3 days ago
        assert 2 not in result  # Lightning Bolt changed 60 days ago

    def test_wider_window(self, seeded_repo):
        result = seeded_repo.get_recently_changed_card_ids("u1", days=90)
        assert 1 in result
        assert 2 in result

    def test_other_user(self, seeded_repo):
        result = seeded_repo.get_recently_changed_card_ids("u2", days=7)
        assert 1 in result  # u2 also owns Counterspell
