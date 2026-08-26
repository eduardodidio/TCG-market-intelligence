"""Tests for credit system database models and repository methods (F65-T01)."""

from __future__ import annotations

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from src.database.models import (
    CreditBalanceRow,
    CreditTransactionRow,
)
from src.database.repository import Repository
from src.domain.models import CreditBalance, CreditTransaction, User


@pytest.fixture
def repo(tmp_path):
    """Create an in-memory repository for testing."""
    db_path = tmp_path / "test.db"
    db_url = f"sqlite:///{db_path}"
    return Repository(db_url=db_url)


@pytest.fixture
def user(repo):
    """Create a test user and return the UserRow."""
    return repo.create_user(
        email="test@example.com",
        display_name="Test User",
        auth_provider="email",
        password_hash="fakehash",
    )


# --- Model creation tests ---


class TestCreditBalanceRow:
    def test_create_credit_balance_row(self, repo, user):
        """CreditBalanceRow can be created via SQLAlchemy."""
        with Session(repo.engine) as session:
            row = CreditBalanceRow(user_id=user.id, balance=100)
            session.add(row)
            session.commit()
            session.refresh(row)

            assert row.id is not None
            assert row.user_id == user.id
            assert row.balance == 100
            assert row.last_bonus_at is None
            assert row.updated_at is not None

    def test_credit_balance_default_zero(self, repo, user):
        """CreditBalanceRow defaults balance to 0."""
        with Session(repo.engine) as session:
            row = CreditBalanceRow(user_id=user.id)
            session.add(row)
            session.commit()
            session.refresh(row)

            assert row.balance == 0


class TestCreditTransactionRow:
    def test_create_credit_transaction_row(self, repo, user):
        """CreditTransactionRow can be created via SQLAlchemy."""
        with Session(repo.engine) as session:
            row = CreditTransactionRow(
                user_id=user.id,
                amount=50,
                reason="initial_credits",
                reference_id="seed",
            )
            session.add(row)
            session.commit()
            session.refresh(row)

            assert row.id is not None
            assert row.user_id == user.id
            assert row.amount == 50
            assert row.reason == "initial_credits"
            assert row.reference_id == "seed"
            assert row.created_at is not None

    def test_transaction_negative_amount(self, repo, user):
        """CreditTransactionRow supports negative amounts (debits)."""
        with Session(repo.engine) as session:
            row = CreditTransactionRow(
                user_id=user.id,
                amount=-10,
                reason="card_refresh",
            )
            session.add(row)
            session.commit()
            session.refresh(row)

            assert row.amount == -10


# --- Repository method tests ---


class TestEnsureCreditBalance:
    def test_creates_balance_if_missing(self, repo, user):
        """ensure_credit_balance creates a row with balance=0 if missing."""
        balance = repo.ensure_credit_balance(user.id)
        assert balance.user_id == user.id
        assert balance.balance == 0

    def test_returns_existing_balance(self, repo, user):
        """ensure_credit_balance returns existing row if present."""
        repo.update_credit_balance(user.id, 25, "admin_grant")
        balance = repo.ensure_credit_balance(user.id)
        assert balance.balance == 25

    def test_idempotent(self, repo, user):
        """Calling ensure_credit_balance twice returns same row."""
        b1 = repo.ensure_credit_balance(user.id)
        b2 = repo.ensure_credit_balance(user.id)
        assert b1.id == b2.id


class TestGetCreditBalance:
    def test_returns_none_if_no_balance(self, repo, user):
        """get_credit_balance returns None for user without balance."""
        assert repo.get_credit_balance(user.id) is None

    def test_returns_balance_after_creation(self, repo, user):
        """get_credit_balance returns row after ensure creates it."""
        repo.ensure_credit_balance(user.id)
        balance = repo.get_credit_balance(user.id)
        assert balance is not None
        assert balance.balance == 0


class TestUpdateCreditBalance:
    def test_positive_delta(self, repo, user):
        """update_credit_balance adds positive delta and logs transaction."""
        result = repo.update_credit_balance(user.id, 50, "initial_credits")
        assert result.balance == 50

        txs = repo.get_credit_transactions(user.id)
        assert len(txs) == 1
        assert txs[0].amount == 50
        assert txs[0].reason == "initial_credits"

    def test_negative_delta(self, repo, user):
        """update_credit_balance subtracts negative delta."""
        repo.update_credit_balance(user.id, 100, "admin_grant")
        result = repo.update_credit_balance(user.id, -30, "card_refresh", "card_42")
        assert result.balance == 70

        txs = repo.get_credit_transactions(user.id)
        assert len(txs) == 2
        assert txs[0].amount == -30  # newest first
        assert txs[0].reason == "card_refresh"
        assert txs[0].reference_id == "card_42"

    def test_negative_delta_exceeding_balance_raises(self, repo, user):
        """update_credit_balance raises ValueError when delta would go negative."""
        repo.update_credit_balance(user.id, 10, "admin_grant")
        with pytest.raises(ValueError, match="Insufficient credits"):
            repo.update_credit_balance(user.id, -20, "card_refresh")

        # Balance should be unchanged
        balance = repo.get_credit_balance(user.id)
        assert balance.balance == 10

    def test_exact_zero_balance_allowed(self, repo, user):
        """Spending exact balance (resulting in 0) is allowed."""
        repo.update_credit_balance(user.id, 10, "admin_grant")
        result = repo.update_credit_balance(user.id, -10, "card_refresh")
        assert result.balance == 0

    def test_creates_balance_if_missing(self, repo, user):
        """update_credit_balance auto-creates balance row if missing."""
        result = repo.update_credit_balance(user.id, 50, "initial_credits")
        assert result.balance == 50


class TestGetCreditTransactions:
    def test_ordered_by_created_at_desc(self, repo, user):
        """Transactions are returned newest first."""
        repo.update_credit_balance(user.id, 10, "bonus_claim")
        repo.update_credit_balance(user.id, 20, "admin_grant")
        repo.update_credit_balance(user.id, -5, "card_refresh")

        txs = repo.get_credit_transactions(user.id)
        assert len(txs) == 3
        assert txs[0].reason == "card_refresh"
        assert txs[1].reason == "admin_grant"
        assert txs[2].reason == "bonus_claim"

    def test_respects_limit(self, repo, user):
        """get_credit_transactions respects limit parameter."""
        for i in range(5):
            repo.update_credit_balance(user.id, 1, f"tx_{i}")

        txs = repo.get_credit_transactions(user.id, limit=3)
        assert len(txs) == 3

    def test_respects_offset(self, repo, user):
        """get_credit_transactions respects offset parameter."""
        for i in range(5):
            repo.update_credit_balance(user.id, 1, f"tx_{i}")

        txs = repo.get_credit_transactions(user.id, limit=2, offset=2)
        assert len(txs) == 2
        # offset=2 skips the 2 newest
        assert txs[0].reason == "tx_2"
        assert txs[1].reason == "tx_1"

    def test_empty_for_unknown_user(self, repo):
        """get_credit_transactions returns empty list for unknown user."""
        txs = repo.get_credit_transactions(999)
        assert txs == []


# --- UserRow is_admin tests ---


class TestIsAdmin:
    def test_user_default_not_admin(self, repo):
        """New users have is_admin=0 by default."""
        user = repo.create_user(
            email="nonadmin@example.com",
            auth_provider="email",
            password_hash="hash",
        )
        assert user.is_admin == 0

    def test_user_set_admin(self, repo):
        """is_admin can be set via update_user."""
        user = repo.create_user(
            email="admin@example.com",
            auth_provider="email",
            password_hash="hash",
        )
        updated = repo.update_user(user.id, is_admin=1)
        assert updated.is_admin == 1

    def test_no_credit_balance_for_regular_user(self, repo):
        """Regular user has no credit balance row until first interaction."""
        user = repo.create_user(
            email="regular@example.com",
            auth_provider="email",
            password_hash="hash",
        )
        assert repo.get_credit_balance(user.id) is None


# --- Domain model tests ---


class TestDomainModels:
    def test_user_is_admin_defaults_false(self):
        """User domain model has is_admin=False by default."""
        user = User(id=1, email="test@example.com")
        assert user.is_admin is False

    def test_user_is_admin_true(self):
        """User domain model can be created with is_admin=True."""
        user = User(id=1, email="test@example.com", is_admin=True)
        assert user.is_admin is True

    def test_credit_balance_dataclass(self):
        """CreditBalance dataclass can be instantiated."""
        cb = CreditBalance(user_id=1, balance=50, last_bonus_at=None)
        assert cb.user_id == 1
        assert cb.balance == 50
        assert cb.last_bonus_at is None

    def test_credit_transaction_dataclass(self):
        """CreditTransaction dataclass can be instantiated."""
        from datetime import datetime

        now = datetime.now()
        ct = CreditTransaction(
            id=1,
            user_id=1,
            amount=50,
            reason="initial_credits",
            reference_id=None,
            created_at=now,
        )
        assert ct.id == 1
        assert ct.amount == 50
        assert ct.reason == "initial_credits"
        assert ct.created_at == now


# --- Seed user simulation tests ---


class TestSeedUserCredits:
    def test_seed_user_gets_admin_and_credits(self, repo):
        """Simulates seed-users: user gets is_admin=1 and 50 initial credits."""
        user = repo.create_user(
            email="seed@example.com",
            display_name="Seed User",
            auth_provider="email",
            password_hash="hash",
        )
        repo.update_user(user.id, is_admin=1)

        # Grant initial 50 credits
        balance = repo.update_credit_balance(
            user_id=user.id,
            delta=50,
            reason="initial_credits",
        )

        # Verify admin
        updated_user = repo.get_user_by_id(user.id)
        assert updated_user.is_admin == 1

        # Verify credits
        assert balance.balance == 50

        # Verify transaction logged
        txs = repo.get_credit_transactions(user.id)
        assert len(txs) == 1
        assert txs[0].amount == 50
        assert txs[0].reason == "initial_credits"


# --- Ensure _ensure_columns migration ---


class TestEnsureColumns:
    def test_is_admin_column_added_on_init(self, tmp_path):
        """Repository._ensure_columns adds is_admin to existing users table."""
        db_path = tmp_path / "migrate.db"
        db_url = f"sqlite:///{db_path}"

        # Create DB without is_admin (simulate old schema)
        from sqlalchemy import Column, Integer, String, text
        from sqlalchemy.orm import DeclarativeBase

        class OldBase(DeclarativeBase):
            pass

        class OldUserRow(OldBase):
            __tablename__ = "users"
            id = Column(Integer, primary_key=True)
            email = Column(String(320), unique=True, nullable=False)
            auth_provider = Column(String(20), nullable=False, default="email")
            is_active = Column(Integer, default=1)
            preferred_language = Column(String(10), default="en")

        engine = create_engine(db_url)
        OldBase.metadata.create_all(engine)

        # Insert a user without is_admin
        with engine.begin() as conn:
            conn.execute(
                text(
                    "INSERT INTO users (email, auth_provider, is_active) "
                    "VALUES ('old@example.com', 'email', 1)"
                )
            )

        # Now create a Repository — should add is_admin column
        Repository(db_url=db_url)

        # Verify the column exists and defaults to 0
        with engine.begin() as conn:
            result = conn.execute(text("SELECT is_admin FROM users WHERE email='old@example.com'"))
            row = result.fetchone()
            assert row[0] == 0 or row[0] is None  # SQLite ALTER ADD defaults may be NULL
