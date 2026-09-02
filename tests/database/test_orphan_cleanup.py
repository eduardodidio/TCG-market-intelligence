"""Tests for orphan reference cleanup (F99-T01)."""

from __future__ import annotations

from datetime import datetime

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from src.database.cleanup import OrphanCleanupResult, cleanup_orphan_references
from src.database.models import (
    CardLegalityRow,
    CardRow,
    CreditBalanceRow,
    CreditTransactionRow,
    DeckCardRow,
    DeckRow,
    EvaluationEntryRow,
    LegalityHistoryRow,
    SourceCardRow,
    UserCollectionRow,
    UserRow,
)
from src.database.repository import Repository


@pytest.fixture()
def repo(tmp_path):
    """Create a Repository backed by a temp SQLite DB."""
    db_path = tmp_path / "test_orphan.db"
    db_url = f"sqlite:///{db_path}"
    return Repository(db_url=db_url)


@pytest.fixture()
def db_url(tmp_path):
    db_path = tmp_path / "test_orphan.db"
    return f"sqlite:///{db_path}"


@pytest.fixture()
def seeded_repo(tmp_path):
    """Create a repo with orphan records in multiple tables."""
    db_path = tmp_path / "test_orphan_seeded.db"
    db_url = f"sqlite:///{db_path}"
    repo = Repository(db_url=db_url)
    engine = repo.engine

    with Session(engine) as session:
        # Create a valid card
        card = CardRow(game="magic", name_en="Lightning Bolt", set_code="2xm", collector_number="1")
        session.add(card)
        session.flush()
        valid_card_id = card.id

        # Create a valid user
        user = UserRow(
            email="test@example.com",
            auth_provider="email",
            password_hash="hash",
        )
        session.add(user)
        session.flush()
        valid_user_id = user.id

        # Create a valid deck
        deck = DeckRow(user_id=str(valid_user_id), name="Test Deck")
        session.add(deck)
        session.flush()
        valid_deck_id = deck.id

        # --- Orphans ---

        # 1. source_card with orphan card_id
        session.add(
            SourceCardRow(
                source="myp",
                external_id="orphan1",
                card_id=99999,
                url="http://example.com/orphan1",
            )
        )
        # valid source_card
        session.add(
            SourceCardRow(
                source="myp",
                external_id="valid1",
                card_id=valid_card_id,
                url="http://example.com/valid1",
            )
        )

        # 2. user_collection with orphan card_id
        session.add(
            UserCollectionRow(
                user_id=str(valid_user_id),
                card_id=99999,
                set_code="xxx",
                collector_number="1",
            )
        )
        # valid collection entry
        session.add(
            UserCollectionRow(
                user_id=str(valid_user_id),
                card_id=valid_card_id,
                set_code="2xm",
                collector_number="1",
            )
        )

        # 3. deck_card with orphan card_id
        session.add(
            DeckCardRow(
                deck_id=valid_deck_id,
                card_id=88888,
                name_en="Orphan Card",
            )
        )
        # valid deck_card
        session.add(
            DeckCardRow(
                deck_id=valid_deck_id,
                card_id=valid_card_id,
                name_en="Lightning Bolt",
            )
        )

        # 4. card_legality with orphan card_id
        session.add(CardLegalityRow(card_id=77777, format="commander", status="legal"))
        # valid legality
        session.add(CardLegalityRow(card_id=valid_card_id, format="commander", status="legal"))

        # 5. legality_history with orphan card_id
        session.add(
            LegalityHistoryRow(
                card_id=66666,
                format="commander",
                new_status="banned",
                changed_at=datetime.now(),
            )
        )

        # 6. evaluation_entry with orphan card_id
        session.add(
            EvaluationEntryRow(
                user_id=valid_user_id,
                card_name="Orphan Eval",
                card_id=55555,
            )
        )

        # 7. deck_card with orphan deck_id
        session.add(DeckCardRow(deck_id=44444, card_id=None, name_en="No Deck Card"))

        # 8. credit_balance with orphan user_id
        session.add(CreditBalanceRow(user_id=33333, balance=100))

        # 9. credit_transaction with orphan user_id
        session.add(CreditTransactionRow(user_id=33333, amount=50, reason="test"))

        session.commit()

    return db_url, repo


class TestOrphanCleanupDryRun:
    def test_dry_run_returns_correct_counts(self, seeded_repo):
        db_url, repo = seeded_repo
        result = cleanup_orphan_references(db_url, dry_run=True, skip_backup=True)

        assert result.dry_run is True
        assert result.source_cards_unlinked == 1
        assert result.user_collection_unlinked == 1
        assert result.deck_cards_unlinked == 1
        assert result.card_legalities_deleted == 1
        assert result.legality_history_deleted == 1
        assert result.evaluation_entries_unlinked == 1
        assert result.deck_cards_no_deck_deleted == 1
        assert result.credit_balances_deleted == 1
        assert result.credit_transactions_deleted == 1
        assert result.total == 9

    def test_dry_run_does_not_modify_data(self, seeded_repo):
        db_url, repo = seeded_repo
        cleanup_orphan_references(db_url, dry_run=True, skip_backup=True)

        # Verify orphan source_card still has card_id=99999
        with Session(repo.engine) as session:
            sc = session.execute(
                select(SourceCardRow).where(SourceCardRow.external_id == "orphan1")
            ).scalar_one()
            assert sc.card_id == 99999


class TestOrphanCleanupExecute:
    def test_execute_cleans_all_orphans(self, seeded_repo):
        db_url, repo = seeded_repo
        result = cleanup_orphan_references(db_url, dry_run=False, skip_backup=True)

        assert result.dry_run is False
        assert result.total == 9

        with Session(repo.engine) as session:
            # source_card orphan should have card_id=NULL
            sc = session.execute(
                select(SourceCardRow).where(SourceCardRow.external_id == "orphan1")
            ).scalar_one()
            assert sc.card_id is None

            # Valid source_card should still be linked
            sc_valid = session.execute(
                select(SourceCardRow).where(SourceCardRow.external_id == "valid1")
            ).scalar_one()
            assert sc_valid.card_id is not None

            # Orphan card_legality should be deleted
            leg_count = session.execute(
                select(func.count())
                .select_from(CardLegalityRow)
                .where(CardLegalityRow.card_id == 77777)
            ).scalar()
            assert leg_count == 0

            # Valid legality still exists
            valid_leg = session.execute(select(func.count()).select_from(CardLegalityRow)).scalar()
            assert valid_leg == 1

            # Orphan legality_history deleted
            lh_count = session.execute(
                select(func.count())
                .select_from(LegalityHistoryRow)
                .where(LegalityHistoryRow.card_id == 66666)
            ).scalar()
            assert lh_count == 0

            # deck_card with orphan deck_id deleted
            no_deck = session.execute(
                select(func.count()).select_from(DeckCardRow).where(DeckCardRow.deck_id == 44444)
            ).scalar()
            assert no_deck == 0

            # Valid deck_card still exists
            valid_dc = session.execute(
                select(func.count())
                .select_from(DeckCardRow)
                .where(DeckCardRow.name_en == "Lightning Bolt")
            ).scalar()
            assert valid_dc == 1

            # credit_balance orphan deleted
            cb_count = session.execute(
                select(func.count())
                .select_from(CreditBalanceRow)
                .where(CreditBalanceRow.user_id == 33333)
            ).scalar()
            assert cb_count == 0

            # credit_transaction orphan deleted
            ct_count = session.execute(
                select(func.count())
                .select_from(CreditTransactionRow)
                .where(CreditTransactionRow.user_id == 33333)
            ).scalar()
            assert ct_count == 0


class TestOrphanCleanupEdgeCases:
    def test_empty_database_returns_zero_counts(self, tmp_path):
        db_path = tmp_path / "empty.db"
        db_url = f"sqlite:///{db_path}"
        Repository(db_url=db_url)  # create tables

        result = cleanup_orphan_references(db_url, dry_run=True, skip_backup=True)
        assert result.total == 0

    def test_no_orphans_returns_zero_counts(self, tmp_path):
        db_path = tmp_path / "clean.db"
        db_url = f"sqlite:///{db_path}"
        repo = Repository(db_url=db_url)

        with Session(repo.engine) as session:
            card = CardRow(game="magic", name_en="Bolt", set_code="2xm", collector_number="1")
            session.add(card)
            session.flush()
            session.add(
                SourceCardRow(
                    source="myp",
                    external_id="valid",
                    card_id=card.id,
                    url="http://example.com",
                )
            )
            session.commit()

        result = cleanup_orphan_references(db_url, dry_run=True, skip_backup=True)
        assert result.total == 0

    def test_total_property(self):
        result = OrphanCleanupResult(
            source_cards_unlinked=1,
            user_collection_unlinked=2,
            deck_cards_unlinked=3,
        )
        assert result.total == 6
