"""Tests for PRAGMA foreign_keys=ON (T03) and FK constraints (T04)."""

from __future__ import annotations

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from src.database.models import (
    CardLegalityRow,
    CardRow,
    CreditBalanceRow,
    DeckCardRow,
    DeckRow,
    SourceCardRow,
    UserRow,
)
from src.database.repository import Repository


@pytest.fixture()
def repo(tmp_path):
    db_path = tmp_path / "test_fk.db"
    db_url = f"sqlite:///{db_path}"
    return Repository(db_url=db_url)


@pytest.fixture()
def repo_with_card(repo):
    """Create a repo with a valid card and user for FK tests."""
    with Session(repo.engine) as session:
        card = CardRow(game="magic", name_en="Lightning Bolt", set_code="2xm", collector_number="1")
        session.add(card)
        session.flush()
        user = UserRow(email="test@fk.com", auth_provider="email", password_hash="hash")
        session.add(user)
        session.flush()
        deck = DeckRow(user_id=str(user.id), name="Test Deck")
        session.add(deck)
        session.commit()
    return repo


class TestPragmaForeignKeys:
    """T03: Verify PRAGMA foreign_keys is ON after engine creation."""

    def test_pragma_is_on(self, repo):
        with repo.engine.connect() as conn:
            result = conn.execute(text("PRAGMA foreign_keys")).scalar()
            assert result == 1

    def test_pragma_is_on_every_new_connection(self, repo):
        # First connection
        with repo.engine.connect() as conn:
            assert conn.execute(text("PRAGMA foreign_keys")).scalar() == 1

        # Second connection (from pool or new)
        with repo.engine.connect() as conn:
            assert conn.execute(text("PRAGMA foreign_keys")).scalar() == 1


class TestFKConstraintEnforcement:
    """T04: Verify FK constraints reject invalid references."""

    def test_source_card_invalid_card_id_rejected(self, repo):
        with Session(repo.engine) as session:
            session.add(
                SourceCardRow(
                    source="myp",
                    external_id="bad1",
                    card_id=99999,
                    url="http://example.com",
                )
            )
            with pytest.raises(IntegrityError):
                session.commit()

    def test_deck_card_invalid_deck_id_rejected(self, repo_with_card):
        with Session(repo_with_card.engine) as session:
            session.add(DeckCardRow(deck_id=99999, card_id=None, name_en="Bad Deck Card"))
            with pytest.raises(IntegrityError):
                session.commit()

    def test_deck_card_invalid_card_id_rejected(self, repo_with_card):
        with Session(repo_with_card.engine) as session:
            # Get valid deck_id
            deck = session.execute(text("SELECT id FROM decks LIMIT 1")).fetchone()
            session.add(DeckCardRow(deck_id=deck[0], card_id=99999, name_en="Bad Card Link"))
            with pytest.raises(IntegrityError):
                session.commit()

    def test_card_legality_invalid_card_id_rejected(self, repo):
        with Session(repo.engine) as session:
            session.add(CardLegalityRow(card_id=99999, format="commander", status="legal"))
            with pytest.raises(IntegrityError):
                session.commit()

    def test_credit_balance_invalid_user_id_rejected(self, repo):
        with Session(repo.engine) as session:
            session.add(CreditBalanceRow(user_id=99999, balance=100))
            with pytest.raises(IntegrityError):
                session.commit()

    def test_source_card_null_card_id_allowed(self, repo):
        with Session(repo.engine) as session:
            sc = SourceCardRow(
                source="myp",
                external_id="null_ok",
                card_id=None,
                url="http://example.com",
            )
            session.add(sc)
            session.commit()
            assert sc.id is not None

    def test_deck_card_null_card_id_allowed(self, repo_with_card):
        with Session(repo_with_card.engine) as session:
            deck = session.execute(text("SELECT id FROM decks LIMIT 1")).fetchone()
            dc = DeckCardRow(deck_id=deck[0], card_id=None, name_en="Unlinked")
            session.add(dc)
            session.commit()
            assert dc.id is not None


class TestFKConstraintsExistInSchema:
    """T04: Verify FK constraints are present via PRAGMA foreign_key_list."""

    def _get_fk_columns(self, repo, table_name: str) -> set[str]:
        with repo.engine.connect() as conn:
            rows = conn.execute(text(f"PRAGMA foreign_key_list({table_name})")).fetchall()
            return {row[3] for row in rows}  # column 3 = 'from'

    def test_source_cards_has_fk_on_card_id(self, repo):
        assert "card_id" in self._get_fk_columns(repo, "source_cards")

    def test_user_collection_has_fk_on_card_id(self, repo):
        assert "card_id" in self._get_fk_columns(repo, "user_collection")

    def test_deck_cards_has_fk_on_deck_id_and_card_id(self, repo):
        fk_cols = self._get_fk_columns(repo, "deck_cards")
        assert "deck_id" in fk_cols
        assert "card_id" in fk_cols

    def test_card_legalities_has_fk_on_card_id(self, repo):
        assert "card_id" in self._get_fk_columns(repo, "card_legalities")

    def test_legality_history_has_fk_on_card_id(self, repo):
        assert "card_id" in self._get_fk_columns(repo, "legality_history")

    def test_evaluation_entries_has_fk_on_card_id(self, repo):
        assert "card_id" in self._get_fk_columns(repo, "evaluation_entries")

    def test_credit_balances_has_fk_on_user_id(self, repo):
        assert "user_id" in self._get_fk_columns(repo, "credit_balances")

    def test_credit_transactions_has_fk_on_user_id(self, repo):
        assert "user_id" in self._get_fk_columns(repo, "credit_transactions")

    def test_shared_collections_has_fk_on_user_id(self, repo):
        assert "user_id" in self._get_fk_columns(repo, "shared_collections")

    def test_trade_interests_has_fks(self, repo):
        fk_cols = self._get_fk_columns(repo, "trade_interests")
        assert "buyer_user_id" in fk_cols
        assert "seller_user_id" in fk_cols
        assert "collection_entry_id" in fk_cols

    def test_trade_agreements_has_fk(self, repo):
        assert "trade_interest_id" in self._get_fk_columns(repo, "trade_agreements")


class TestFKConstraintCheckClean:
    """T04: Verify PRAGMA foreign_key_check returns empty on clean DB."""

    def test_foreign_key_check_returns_empty(self, repo):
        with repo.engine.connect() as conn:
            violations = conn.execute(text("PRAGMA foreign_key_check")).fetchall()
            assert len(violations) == 0
