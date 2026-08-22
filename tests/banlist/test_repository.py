"""Tests for F41 banlist repository methods."""

from datetime import date, datetime

import pytest

from src.database.models import Base, CardRow
from src.database.repository import Repository
from src.domain.models import CardLegality, LegalityChange


@pytest.fixture
def repo():
    r = Repository(db_url="sqlite:///:memory:")
    Base.metadata.create_all(r.engine)
    return r


@pytest.fixture
def repo_with_card(repo):
    from sqlalchemy.orm import Session

    with Session(repo.engine) as session:
        card = CardRow(
            game="magic",
            name_en="Lightning Bolt",
            name_pt="Raio",
            set_code="lea",
            collector_number="161",
        )
        session.add(card)
        session.commit()
        card_id = card.id
    return repo, card_id


class TestUpsertLegalities:
    def test_insert_new_rows(self, repo_with_card):
        repo, card_id = repo_with_card
        legalities = [
            CardLegality(card_id=card_id, format="standard", status="legal"),
            CardLegality(card_id=card_id, format="modern", status="legal"),
        ]
        count = repo.upsert_legalities(legalities)
        assert count == 2

    def test_update_existing_row(self, repo_with_card):
        repo, card_id = repo_with_card
        repo.upsert_legalities(
            [
                CardLegality(card_id=card_id, format="standard", status="legal"),
            ]
        )
        # Update status
        repo.upsert_legalities(
            [
                CardLegality(
                    card_id=card_id,
                    format="standard",
                    status="banned",
                    effective_date=date(2026, 8, 1),
                ),
            ]
        )
        result = repo.get_legalities_for_card(card_id)
        assert len(result) == 1
        assert result[0]["status"] == "banned"
        assert result[0]["effective_date"] == date(2026, 8, 1)

    def test_empty_list(self, repo):
        assert repo.upsert_legalities([]) == 0


class TestInsertLegalityChanges:
    def test_append_history(self, repo_with_card):
        repo, card_id = repo_with_card
        changes = [
            LegalityChange(
                card_id=card_id,
                format="standard",
                old_status=None,
                new_status="banned",
                changed_at=datetime.now(),
            ),
        ]
        count = repo.insert_legality_changes(changes)
        assert count == 1

    def test_empty_list(self, repo):
        assert repo.insert_legality_changes([]) == 0


class TestGetLegalitiesByFormat:
    def test_filter_by_format(self, repo_with_card):
        repo, card_id = repo_with_card
        repo.upsert_legalities(
            [
                CardLegality(card_id=card_id, format="standard", status="banned"),
                CardLegality(card_id=card_id, format="modern", status="legal"),
            ]
        )
        result = repo.get_legalities_by_format("standard")
        assert len(result) == 1
        assert result[0]["status"] == "banned"
        assert result[0]["name_en"] == "Lightning Bolt"

    def test_filter_by_status(self, repo_with_card):
        repo, card_id = repo_with_card
        repo.upsert_legalities(
            [
                CardLegality(card_id=card_id, format="standard", status="banned"),
            ]
        )
        # Filter for legal — should be empty
        result = repo.get_legalities_by_format("standard", status="legal")
        assert len(result) == 0
        # Filter for banned — should return 1
        result = repo.get_legalities_by_format("standard", status="banned")
        assert len(result) == 1

    def test_search_by_name(self, repo_with_card):
        repo, card_id = repo_with_card
        repo.upsert_legalities(
            [
                CardLegality(card_id=card_id, format="standard", status="banned"),
            ]
        )
        result = repo.get_legalities_by_format("standard", search="lightning")
        assert len(result) == 1
        result = repo.get_legalities_by_format("standard", search="nonexistent")
        assert len(result) == 0


class TestGetLegalitiesForCard:
    def test_returns_all_formats(self, repo_with_card):
        repo, card_id = repo_with_card
        repo.upsert_legalities(
            [
                CardLegality(card_id=card_id, format="standard", status="banned"),
                CardLegality(card_id=card_id, format="modern", status="legal"),
                CardLegality(card_id=card_id, format="vintage", status="restricted"),
            ]
        )
        result = repo.get_legalities_for_card(card_id)
        assert len(result) == 3
        formats = [r["format"] for r in result]
        assert formats == ["modern", "standard", "vintage"]  # sorted


class TestGetLegalityHistory:
    def test_filter_by_card_id(self, repo_with_card):
        repo, card_id = repo_with_card
        repo.insert_legality_changes(
            [
                LegalityChange(
                    card_id=card_id,
                    format="standard",
                    old_status=None,
                    new_status="banned",
                    changed_at=datetime(2026, 8, 1),
                ),
            ]
        )
        result = repo.get_legality_history(card_id=card_id)
        assert len(result) == 1
        assert result[0]["name_en"] == "Lightning Bolt"

    def test_filter_by_format(self, repo_with_card):
        repo, card_id = repo_with_card
        repo.insert_legality_changes(
            [
                LegalityChange(
                    card_id=card_id,
                    format="standard",
                    old_status=None,
                    new_status="banned",
                    changed_at=datetime(2026, 8, 1),
                ),
                LegalityChange(
                    card_id=card_id,
                    format="modern",
                    old_status=None,
                    new_status="legal",
                    changed_at=datetime(2026, 8, 1),
                ),
            ]
        )
        result = repo.get_legality_history(format="standard")
        assert len(result) == 1
        assert result[0]["format"] == "standard"


class TestGetKnownFormats:
    def test_returns_distinct_sorted(self, repo_with_card):
        repo, card_id = repo_with_card
        repo.upsert_legalities(
            [
                CardLegality(card_id=card_id, format="modern", status="legal"),
                CardLegality(card_id=card_id, format="standard", status="legal"),
                CardLegality(card_id=card_id, format="legacy", status="legal"),
            ]
        )
        formats = repo.get_known_formats()
        assert formats == ["legacy", "modern", "standard"]


class TestGetLegalitiesForCardsBatch:
    def test_batch_fetch(self, repo_with_card):
        repo, card_id = repo_with_card
        repo.upsert_legalities(
            [
                CardLegality(card_id=card_id, format="standard", status="banned"),
                CardLegality(card_id=card_id, format="modern", status="legal"),
            ]
        )
        result = repo.get_legalities_for_cards_batch([card_id])
        assert card_id in result
        assert len(result[card_id]) == 2

    def test_empty_input(self, repo):
        assert repo.get_legalities_for_cards_batch([]) == {}
