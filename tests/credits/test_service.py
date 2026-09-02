"""Tests for CreditService business logic."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from src.credits.constants import ADMIN_MONTHLY_GRANT, BONUS_AMOUNT, BONUS_INTERVAL_HOURS
from src.credits.exceptions import InsufficientCreditsError
from src.credits.service import CreditService
from src.database.repository import Repository


@pytest.fixture()
def repo(tmp_path):
    """Create a temporary SQLite repository with tables."""
    db_url = f"sqlite:///{tmp_path / 'test.db'}"
    r = Repository(db_url=db_url)
    # Create a user so FK constraints on credit_balances/transactions are satisfied
    r.create_user(email="test@example.com", auth_provider="email", password_hash="hash")
    return r


@pytest.fixture()
def service(repo):
    """Create a CreditService backed by the in-memory repo."""
    return CreditService(repo)


USER_ID = 1


class TestGetBalance:
    def test_new_user_gets_zero_balance(self, service):
        balance = service.get_balance(USER_ID)
        assert balance.user_id == USER_ID
        assert balance.balance == 0
        assert balance.last_bonus_at is None

    def test_idempotent_get_balance(self, service):
        b1 = service.get_balance(USER_ID)
        b2 = service.get_balance(USER_ID)
        assert b1.balance == b2.balance == 0


class TestCheckSufficient:
    def test_sufficient_returns_true(self, service):
        service.grant(USER_ID, 5, "seed")
        assert service.check_sufficient(USER_ID, 3) is True

    def test_exact_balance_returns_true(self, service):
        service.grant(USER_ID, 5, "seed")
        assert service.check_sufficient(USER_ID, 5) is True

    def test_insufficient_returns_false(self, service):
        service.grant(USER_ID, 2, "seed")
        assert service.check_sufficient(USER_ID, 3) is False

    def test_zero_balance_insufficient(self, service):
        assert service.check_sufficient(USER_ID, 1) is False

    def test_zero_cost_always_sufficient(self, service):
        assert service.check_sufficient(USER_ID, 0) is True


class TestDeduct:
    def test_deduct_reduces_balance(self, service):
        service.grant(USER_ID, 5, "seed")
        result = service.deduct(USER_ID, 1, "card_refresh")
        assert result.balance == 4

    def test_deduct_logs_transaction(self, service):
        service.grant(USER_ID, 5, "seed")
        service.deduct(USER_ID, 1, "card_refresh", reference_id="card_42")
        txs = service.get_transactions(USER_ID)
        deduct_tx = [t for t in txs if t.amount < 0]
        assert len(deduct_tx) == 1
        assert deduct_tx[0].amount == -1
        assert deduct_tx[0].reason == "card_refresh"
        assert deduct_tx[0].reference_id == "card_42"

    def test_deduct_insufficient_raises(self, service):
        # Balance is 0
        with pytest.raises(InsufficientCreditsError) as exc_info:
            service.deduct(USER_ID, 1, "card_refresh")
        assert exc_info.value.balance == 0
        assert exc_info.value.cost == 1

    def test_deduct_insufficient_preserves_balance(self, service):
        service.grant(USER_ID, 2, "seed")
        with pytest.raises(InsufficientCreditsError):
            service.deduct(USER_ID, 3, "card_refresh")
        assert service.get_balance(USER_ID).balance == 2

    def test_deduct_exact_balance(self, service):
        service.grant(USER_ID, 5, "seed")
        result = service.deduct(USER_ID, 5, "bulk_scan")
        assert result.balance == 0


class TestGrant:
    def test_grant_increases_balance(self, service):
        result = service.grant(USER_ID, 100, "admin_grant")
        assert result.balance == 100

    def test_grant_logs_transaction(self, service):
        service.grant(USER_ID, 100, "admin_grant", reference_id="admin_1")
        txs = service.get_transactions(USER_ID)
        assert len(txs) == 1
        assert txs[0].amount == 100
        assert txs[0].reason == "admin_grant"
        assert txs[0].reference_id == "admin_1"

    def test_grant_accumulates(self, service):
        service.grant(USER_ID, 10, "bonus")
        service.grant(USER_ID, 20, "bonus")
        assert service.get_balance(USER_ID).balance == 30


class TestClaimBonus:
    def test_first_claim_grants_bonus(self, service):
        balance, claimed = service.claim_bonus(USER_ID)
        assert claimed is True
        assert balance.balance == BONUS_AMOUNT
        assert balance.last_bonus_at is not None

    def test_second_claim_within_interval_denied(self, service):
        service.claim_bonus(USER_ID)
        balance, claimed = service.claim_bonus(USER_ID)
        assert claimed is False
        assert balance.balance == BONUS_AMOUNT  # unchanged

    def test_claim_after_interval_grants_again(self, service, repo):
        # First claim
        service.claim_bonus(USER_ID)

        # Move last_bonus_at back beyond the interval
        past = datetime.now(timezone.utc) - timedelta(hours=BONUS_INTERVAL_HOURS + 1)
        repo.update_last_bonus_at(USER_ID, past)

        balance, claimed = service.claim_bonus(USER_ID)
        assert claimed is True
        assert balance.balance == BONUS_AMOUNT * 2

    def test_claim_logs_transaction(self, service):
        service.claim_bonus(USER_ID)
        txs = service.get_transactions(USER_ID)
        bonus_txs = [t for t in txs if t.reason == "bonus_claim"]
        assert len(bonus_txs) == 1
        assert bonus_txs[0].amount == BONUS_AMOUNT


class TestGetBonusEligibility:
    def test_no_prior_claim_eligible(self, service):
        result = service.get_bonus_eligibility(USER_ID)
        assert result["eligible"] is True
        assert result["next_eligible_at"] is None
        assert result["amount"] == BONUS_AMOUNT

    def test_just_claimed_not_eligible(self, service):
        service.claim_bonus(USER_ID)
        result = service.get_bonus_eligibility(USER_ID)
        assert result["eligible"] is False
        assert result["next_eligible_at"] is not None

    def test_after_interval_eligible(self, service, repo):
        service.claim_bonus(USER_ID)
        past = datetime.now(timezone.utc) - timedelta(hours=BONUS_INTERVAL_HOURS + 1)
        repo.update_last_bonus_at(USER_ID, past)

        result = service.get_bonus_eligibility(USER_ID)
        assert result["eligible"] is True
        # next_eligible_at should be in the past
        assert result["next_eligible_at"] is not None

    def test_next_eligible_at_is_last_plus_interval(self, service, repo):
        service.claim_bonus(USER_ID)
        # Set a known time
        known_time = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        repo.update_last_bonus_at(USER_ID, known_time)

        result = service.get_bonus_eligibility(USER_ID)
        expected = known_time + timedelta(hours=BONUS_INTERVAL_HOURS)
        assert result["next_eligible_at"] == expected


class TestClaimMonthlyAdminGrant:
    def test_non_admin_gets_no_grant(self, service):
        balance, granted = service.claim_monthly_admin_grant(USER_ID, is_admin=False)
        assert granted is False
        assert balance.balance == 0

    def test_admin_first_call_grants_10k(self, service):
        balance, granted = service.claim_monthly_admin_grant(USER_ID, is_admin=True)
        assert granted is True
        assert balance.balance == ADMIN_MONTHLY_GRANT

    def test_admin_second_call_same_month_denied(self, service):
        service.claim_monthly_admin_grant(USER_ID, is_admin=True)
        balance, granted = service.claim_monthly_admin_grant(USER_ID, is_admin=True)
        assert granted is False
        assert balance.balance == ADMIN_MONTHLY_GRANT  # unchanged

    def test_admin_different_month_grants_again(self, service, repo):
        service.claim_monthly_admin_grant(USER_ID, is_admin=True)
        # Move last_monthly_grant_at to a previous month
        past = datetime(2026, 1, 15, 12, 0, 0, tzinfo=timezone.utc)
        repo.update_last_monthly_grant_at(USER_ID, past)

        balance, granted = service.claim_monthly_admin_grant(USER_ID, is_admin=True)
        assert granted is True
        assert balance.balance == ADMIN_MONTHLY_GRANT * 2

    def test_grant_logs_transaction(self, service):
        service.claim_monthly_admin_grant(USER_ID, is_admin=True)
        txs = service.get_transactions(USER_ID)
        grant_txs = [t for t in txs if t.reason == "admin_monthly_grant"]
        assert len(grant_txs) == 1
        assert grant_txs[0].amount == ADMIN_MONTHLY_GRANT

    def test_non_admin_balance_unchanged(self, service):
        service.grant(USER_ID, 50, "seed")
        balance, granted = service.claim_monthly_admin_grant(USER_ID, is_admin=False)
        assert granted is False
        assert balance.balance == 50


class TestGetTransactions:
    def test_empty_history(self, service):
        txs = service.get_transactions(USER_ID)
        assert txs == []

    def test_newest_first(self, service):
        service.grant(USER_ID, 10, "first")
        service.grant(USER_ID, 20, "second")
        service.grant(USER_ID, 30, "third")
        txs = service.get_transactions(USER_ID)
        assert len(txs) == 3
        assert txs[0].amount == 30
        assert txs[2].amount == 10

    def test_limit(self, service):
        for i in range(5):
            service.grant(USER_ID, i + 1, f"grant_{i}")
        txs = service.get_transactions(USER_ID, limit=2)
        assert len(txs) == 2

    def test_offset(self, service):
        for i in range(5):
            service.grant(USER_ID, i + 1, f"grant_{i}")
        txs = service.get_transactions(USER_ID, limit=2, offset=2)
        assert len(txs) == 2
        # offset=2 skips the 2 newest (amounts 5,4), returns 3,2
        assert txs[0].amount == 3
        assert txs[1].amount == 2

    def test_transactions_have_correct_fields(self, service):
        service.grant(USER_ID, 10, "admin_grant", reference_id="ref_1")
        txs = service.get_transactions(USER_ID)
        tx = txs[0]
        assert tx.user_id == USER_ID
        assert tx.amount == 10
        assert tx.reason == "admin_grant"
        assert tx.reference_id == "ref_1"
        assert tx.created_at is not None
        assert tx.id is not None
