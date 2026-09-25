"""Tests for the batched legality writer (F177-T03)."""

from datetime import date, datetime

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from src.database.legality_writer import bulk_insert_legality_changes, bulk_upsert_legalities
from src.database.models import Base, CardLegalityRow, CardRow, LegalityHistoryRow
from src.database.repository import Repository
from src.domain.models import CardLegality, LegalityChange


@pytest.fixture
def repo(tmp_path):
    r = Repository(db_url=f"sqlite:///{tmp_path}/t.db")
    Base.metadata.create_all(r.engine)
    return r


def _make_cards(repo: Repository, count: int) -> list[int]:
    with Session(repo.engine) as session:
        cards = [
            CardRow(game="magic", name_en=f"Card {i}", set_code="lea", collector_number=str(i))
            for i in range(count)
        ]
        session.add_all(cards)
        session.commit()
        return [c.id for c in cards]


class TestBulkUpsertLegalities:
    def test_empty_list_no_db_access(self, repo, monkeypatch):
        called = False

        original_execute = Session.execute

        def spy(self, *args, **kwargs):
            nonlocal called
            called = True
            return original_execute(self, *args, **kwargs)

        monkeypatch.setattr(Session, "execute", spy)
        assert bulk_upsert_legalities(repo.engine, []) == 0
        assert called is False

    def test_insert_happy_path(self, repo):
        card_ids = _make_cards(repo, 2)
        legalities = [
            CardLegality(card_id=card_ids[0], format="standard", status="legal"),
            CardLegality(card_id=card_ids[0], format="modern", status="legal"),
            CardLegality(card_id=card_ids[1], format="standard", status="banned"),
        ]
        count = bulk_upsert_legalities(repo.engine, legalities)
        assert count == 3
        with Session(repo.engine) as session:
            rows = session.query(CardLegalityRow).all()
            assert len(rows) == 3

    def test_chunking_1201_rows_three_statements(self, repo, monkeypatch):
        card_ids = _make_cards(repo, 1201)
        legalities = [
            CardLegality(card_id=cid, format="standard", status="legal") for cid in card_ids
        ]

        calls = []
        original_execute = Session.execute

        def spy(self, stmt, *args, **kwargs):
            calls.append(stmt)
            return original_execute(self, stmt, *args, **kwargs)

        monkeypatch.setattr(Session, "execute", spy)
        count = bulk_upsert_legalities(repo.engine, legalities)
        assert count == 1201
        assert len(calls) == 3
        with Session(repo.engine) as session:
            assert session.query(CardLegalityRow).count() == 1201

    def test_boundary_chunk_size_two_five_rows_three_executes(self, repo, monkeypatch):
        card_ids = _make_cards(repo, 5)
        legalities = [
            CardLegality(card_id=cid, format="standard", status="legal") for cid in card_ids
        ]

        calls = []
        original_execute = Session.execute

        def spy(self, stmt, *args, **kwargs):
            calls.append(stmt)
            return original_execute(self, stmt, *args, **kwargs)

        monkeypatch.setattr(Session, "execute", spy)
        count = bulk_upsert_legalities(repo.engine, legalities, chunk_size=2)
        assert count == 5
        assert len(calls) == 3
        with Session(repo.engine) as session:
            assert session.query(CardLegalityRow).count() == 5

    def test_update_keeps_previous_effective_date_when_none(self, repo):
        card_ids = _make_cards(repo, 1)
        card_id = card_ids[0]
        bulk_upsert_legalities(
            repo.engine,
            [
                CardLegality(
                    card_id=card_id,
                    format="standard",
                    status="banned",
                    effective_date=date(2026, 1, 1),
                )
            ],
        )
        bulk_upsert_legalities(
            repo.engine,
            [CardLegality(card_id=card_id, format="standard", status="restricted")],
        )
        with Session(repo.engine) as session:
            row = session.query(CardLegalityRow).filter_by(card_id=card_id, format="standard").one()
            assert row.status == "restricted"
            assert row.effective_date == date(2026, 1, 1)

    def test_update_status_and_updated_at(self, repo):
        card_ids = _make_cards(repo, 1)
        card_id = card_ids[0]
        bulk_upsert_legalities(
            repo.engine, [CardLegality(card_id=card_id, format="standard", status="legal")]
        )
        with Session(repo.engine) as session:
            before = (
                session.query(CardLegalityRow).filter_by(card_id=card_id, format="standard").one()
            )
            before_updated_at = before.updated_at

        bulk_upsert_legalities(
            repo.engine, [CardLegality(card_id=card_id, format="standard", status="banned")]
        )
        with Session(repo.engine) as session:
            after = (
                session.query(CardLegalityRow).filter_by(card_id=card_id, format="standard").one()
            )
            assert after.status == "banned"
            assert after.updated_at >= before_updated_at

    def test_duplicate_keys_in_same_call_last_wins(self, repo):
        card_ids = _make_cards(repo, 1)
        card_id = card_ids[0]
        legalities = [
            CardLegality(card_id=card_id, format="standard", status="legal"),
            CardLegality(card_id=card_id, format="standard", status="banned"),
        ]
        count = bulk_upsert_legalities(repo.engine, legalities)
        assert count == 1
        with Session(repo.engine) as session:
            rows = (
                session.query(CardLegalityRow)
                .filter_by(card_id=card_id, format="standard")
                .all()
            )
            assert len(rows) == 1
            assert rows[0].status == "banned"

    def test_fk_violation_raises_and_rolls_back(self, repo):
        card_ids = _make_cards(repo, 1)
        legalities = [
            CardLegality(card_id=card_ids[0], format="standard", status="legal"),
            CardLegality(card_id=99999, format="standard", status="legal"),
        ]
        with pytest.raises(IntegrityError):
            bulk_upsert_legalities(repo.engine, legalities, chunk_size=1)
        with Session(repo.engine) as session:
            rows = session.query(CardLegalityRow).all()
            assert len(rows) == 0


class TestBulkInsertLegalityChanges:
    def test_empty_list_no_db_access(self, repo, monkeypatch):
        called = False
        original_execute = Session.execute

        def spy(self, *args, **kwargs):
            nonlocal called
            called = True
            return original_execute(self, *args, **kwargs)

        monkeypatch.setattr(Session, "execute", spy)
        assert bulk_insert_legality_changes(repo.engine, []) == 0
        assert called is False

    def test_insert_happy_path_preserves_source(self, repo):
        card_ids = _make_cards(repo, 2)
        changes = [
            LegalityChange(
                card_id=card_ids[0],
                format="standard",
                old_status=None,
                new_status="banned",
                changed_at=datetime.now(),
                source="scryfall_baseline",
            ),
            LegalityChange(
                card_id=card_ids[1],
                format="modern",
                old_status="legal",
                new_status="banned",
                changed_at=datetime.now(),
                source="scryfall_baseline",
            ),
        ]
        count = bulk_insert_legality_changes(repo.engine, changes)
        assert count == 2
        with Session(repo.engine) as session:
            rows = session.query(LegalityHistoryRow).all()
            assert len(rows) == 2
            assert all(r.source == "scryfall_baseline" for r in rows)

    def test_boundary_chunk_size_two_five_rows_three_executes(self, repo, monkeypatch):
        card_ids = _make_cards(repo, 5)
        changes = [
            LegalityChange(
                card_id=cid, format="standard", old_status=None, new_status="banned"
            )
            for cid in card_ids
        ]

        calls = []
        original_execute = Session.execute

        def spy(self, stmt, *args, **kwargs):
            calls.append(stmt)
            return original_execute(self, stmt, *args, **kwargs)

        monkeypatch.setattr(Session, "execute", spy)
        count = bulk_insert_legality_changes(repo.engine, changes, chunk_size=2)
        assert count == 5
        assert len(calls) == 3
        with Session(repo.engine) as session:
            assert session.query(LegalityHistoryRow).count() == 5

    def test_fk_violation_raises_and_rolls_back(self, repo):
        changes = [
            LegalityChange(card_id=99999, format="standard", old_status=None, new_status="banned")
        ]
        with pytest.raises(IntegrityError):
            bulk_insert_legality_changes(repo.engine, changes)
        with Session(repo.engine) as session:
            assert session.query(LegalityHistoryRow).count() == 0
