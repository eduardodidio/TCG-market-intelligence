"""Tests for MarketplaceService (F69-T03).

Covers: toggle sharing, express interest, respond, confirm agreement,
        self-trade prevention, credit deduction, email reveal.
"""

from __future__ import annotations

import pytest

from src.credits.exceptions import InsufficientCreditsError
from src.credits.service import CreditService
from src.database.repository import Repository
from src.marketplace.service import MarketplaceService


@pytest.fixture()
def repo(tmp_path):
    db_path = tmp_path / "test_marketplace_svc.db"
    db_url = f"sqlite:///{db_path}"
    return Repository(db_url=db_url)


@pytest.fixture()
def credit_svc(repo):
    return CreditService(repo)


@pytest.fixture()
def svc(repo, credit_svc):
    return MarketplaceService(repo, credit_svc)


def _create_user(repo, user_id: int, email: str = "user@test.com"):
    """Create a user with credits for testing."""
    from sqlalchemy.orm import Session

    from src.database.models import UserRow

    with Session(repo.engine) as session:
        user = UserRow(
            id=user_id,
            email=email,
            auth_provider="email",
            password_hash="fakehash",
        )
        session.add(user)
        session.commit()
    # Give credits
    repo.ensure_credit_balance(user_id)
    repo.update_credit_balance(user_id, delta=100, reason="test_grant")


def _create_collection_entry(repo, user_id: int, name_en: str = "Lightning Bolt"):
    """Create a collection entry for testing."""
    from sqlalchemy.orm import Session

    from src.database.models import UserCollectionRow

    with Session(repo.engine) as session:
        entry = UserCollectionRow(
            user_id=str(user_id),
            name_en=name_en,
            set_code="lea",
            collector_number="161",
            rarity="C",
        )
        session.add(entry)
        session.commit()
        session.refresh(entry)
        entry_id = entry.id
    return entry_id


class TestToggleSharing:
    def test_toggle_on(self, svc, repo):
        _create_user(repo, 1, "user1@test.com")
        result = svc.toggle_sharing(1, True)
        assert result["is_shared"] is True
        assert result["share_code"] is not None

    def test_toggle_off(self, svc, repo):
        _create_user(repo, 1, "user1@test.com")
        svc.toggle_sharing(1, True)
        result = svc.toggle_sharing(1, False)
        assert result["is_shared"] is False

    def test_get_status_unshared(self, svc):
        result = svc.get_sharing_status(999)
        assert result["is_shared"] is False
        assert result["share_code"] is None

    def test_get_status_shared(self, svc, repo):
        _create_user(repo, 1, "user1@test.com")
        svc.toggle_sharing(1, True)
        result = svc.get_sharing_status(1)
        assert result["is_shared"] is True


class TestExpressInterest:
    def test_express_interest_success(self, svc, repo):
        _create_user(repo, 1, "seller@test.com")
        _create_user(repo, 2, "buyer@test.com")
        entry_id = _create_collection_entry(repo, 1)
        svc.toggle_sharing(1, True)
        status = svc.get_sharing_status(1)

        result = svc.express_interest(
            buyer_user_id=2,
            share_code=status["share_code"],
            entry_id=entry_id,
            message="I want this!",
        )
        assert result["status"] == "pending"
        assert result["estimated_fee"] == 2  # no price → minimum fee

    def test_self_trade_raises(self, svc, repo):
        _create_user(repo, 1, "user1@test.com")
        entry_id = _create_collection_entry(repo, 1)
        svc.toggle_sharing(1, True)
        status = svc.get_sharing_status(1)

        with pytest.raises(ValueError, match="Cannot trade with yourself"):
            svc.express_interest(
                buyer_user_id=1,
                share_code=status["share_code"],
                entry_id=entry_id,
            )

    def test_invalid_share_code_raises(self, svc, repo):
        _create_user(repo, 2)
        with pytest.raises(ValueError, match="not found"):
            svc.express_interest(
                buyer_user_id=2,
                share_code="nonexistent",
                entry_id=1,
            )

    def test_entry_not_found_raises(self, svc, repo):
        _create_user(repo, 1, "seller@test.com")
        _create_user(repo, 2, "buyer@test.com")
        svc.toggle_sharing(1, True)
        status = svc.get_sharing_status(1)

        with pytest.raises(ValueError, match="not found"):
            svc.express_interest(
                buyer_user_id=2,
                share_code=status["share_code"],
                entry_id=9999,
            )

    def test_entry_wrong_owner_raises(self, svc, repo):
        _create_user(repo, 1, "seller@test.com")
        _create_user(repo, 2, "buyer@test.com")
        _create_user(repo, 3, "other@test.com")
        entry_id = _create_collection_entry(repo, 3)  # belongs to user 3
        svc.toggle_sharing(1, True)
        status = svc.get_sharing_status(1)

        with pytest.raises(ValueError, match="does not belong"):
            svc.express_interest(
                buyer_user_id=2,
                share_code=status["share_code"],
                entry_id=entry_id,
            )


class TestRespondToInterest:
    def _setup_interest(self, svc, repo):
        _create_user(repo, 1, "seller@test.com")
        _create_user(repo, 2, "buyer@test.com")
        entry_id = _create_collection_entry(repo, 1)
        svc.toggle_sharing(1, True)
        status = svc.get_sharing_status(1)
        interest = svc.express_interest(
            buyer_user_id=2,
            share_code=status["share_code"],
            entry_id=entry_id,
        )
        return interest["id"]

    def test_accept(self, svc, repo):
        interest_id = self._setup_interest(svc, repo)
        result = svc.respond_to_interest(interest_id, user_id=1, action="accept")
        assert result["status"] == "accepted"
        assert "agreement_id" in result

    def test_reject(self, svc, repo):
        interest_id = self._setup_interest(svc, repo)
        result = svc.respond_to_interest(interest_id, user_id=1, action="reject")
        assert result["status"] == "rejected"

    def test_invalid_action_raises(self, svc, repo):
        interest_id = self._setup_interest(svc, repo)
        with pytest.raises(ValueError, match="accept.*reject"):
            svc.respond_to_interest(interest_id, user_id=1, action="maybe")

    def test_non_seller_cannot_respond(self, svc, repo):
        interest_id = self._setup_interest(svc, repo)
        with pytest.raises(PermissionError):
            svc.respond_to_interest(interest_id, user_id=2, action="accept")

    def test_respond_to_non_pending_raises(self, svc, repo):
        interest_id = self._setup_interest(svc, repo)
        svc.respond_to_interest(interest_id, user_id=1, action="reject")
        with pytest.raises(ValueError, match="Cannot respond"):
            svc.respond_to_interest(interest_id, user_id=1, action="accept")

    def test_respond_not_found_raises(self, svc, repo):
        with pytest.raises(ValueError, match="not found"):
            svc.respond_to_interest(9999, user_id=1, action="accept")


class TestConfirmAgreement:
    def _setup_accepted(self, svc, repo):
        _create_user(repo, 1, "seller@test.com")
        _create_user(repo, 2, "buyer@test.com")
        entry_id = _create_collection_entry(repo, 1)
        svc.toggle_sharing(1, True)
        status = svc.get_sharing_status(1)
        interest = svc.express_interest(
            buyer_user_id=2,
            share_code=status["share_code"],
            entry_id=entry_id,
        )
        svc.respond_to_interest(interest["id"], user_id=1, action="accept")
        return interest["id"]

    def test_buyer_confirms_first(self, svc, repo):
        interest_id = self._setup_accepted(svc, repo)
        result = svc.confirm_agreement(interest_id, user_id=2)
        assert result["my_confirmed"] is True
        assert result["both_confirmed"] is False

    def test_seller_confirms_first(self, svc, repo):
        interest_id = self._setup_accepted(svc, repo)
        result = svc.confirm_agreement(interest_id, user_id=1)
        assert result["my_confirmed"] is True
        assert result["both_confirmed"] is False

    def test_both_confirm_completes_trade(self, svc, repo):
        interest_id = self._setup_accepted(svc, repo)
        svc.confirm_agreement(interest_id, user_id=2)
        result = svc.confirm_agreement(interest_id, user_id=1)
        assert result["status"] == "completed"
        assert result["both_confirmed"] is True
        assert result["buyer_email"] == "buyer@test.com"
        assert result["seller_email"] == "seller@test.com"
        assert result["fee_charged"] == 2  # minimum fee (no price data)

    def test_both_confirm_deducts_credits(self, svc, repo, credit_svc):
        interest_id = self._setup_accepted(svc, repo)
        buyer_before = credit_svc.get_balance(2).balance
        seller_before = credit_svc.get_balance(1).balance

        svc.confirm_agreement(interest_id, user_id=2)
        svc.confirm_agreement(interest_id, user_id=1)

        buyer_after = credit_svc.get_balance(2).balance
        seller_after = credit_svc.get_balance(1).balance
        assert buyer_after == buyer_before - 2
        assert seller_after == seller_before - 2

    def test_insufficient_credits_raises(self, svc, repo):
        interest_id = self._setup_accepted(svc, repo)

        # Drain buyer credits
        repo.update_credit_balance(2, delta=-100, reason="drain")

        svc.confirm_agreement(interest_id, user_id=2)
        with pytest.raises(InsufficientCreditsError):
            svc.confirm_agreement(interest_id, user_id=1)

    def test_double_confirm_raises(self, svc, repo):
        interest_id = self._setup_accepted(svc, repo)
        svc.confirm_agreement(interest_id, user_id=2)
        with pytest.raises(ValueError, match="already confirmed"):
            svc.confirm_agreement(interest_id, user_id=2)

    def test_non_participant_raises(self, svc, repo):
        interest_id = self._setup_accepted(svc, repo)
        _create_user(repo, 3, "outsider@test.com")
        with pytest.raises(PermissionError):
            svc.confirm_agreement(interest_id, user_id=3)

    def test_confirm_non_accepted_raises(self, svc, repo):
        _create_user(repo, 1, "seller@test.com")
        _create_user(repo, 2, "buyer@test.com")
        entry_id = _create_collection_entry(repo, 1)
        svc.toggle_sharing(1, True)
        status = svc.get_sharing_status(1)
        interest = svc.express_interest(
            buyer_user_id=2,
            share_code=status["share_code"],
            entry_id=entry_id,
        )
        with pytest.raises(ValueError, match="Cannot confirm"):
            svc.confirm_agreement(interest["id"], user_id=2)

    def test_complete_trade_idempotent(self, svc, repo, credit_svc):
        """Calling _complete_trade twice should not double-charge (completed_at guard)."""
        interest_id = self._setup_accepted(svc, repo)
        buyer_before = credit_svc.get_balance(2).balance

        svc.confirm_agreement(interest_id, user_id=2)
        result = svc.confirm_agreement(interest_id, user_id=1)
        assert result["status"] == "completed"

        # Manually call _complete_trade again — should be idempotent
        interest = repo.get_trade_interest(interest_id)
        agreement = repo.get_trade_agreement_by_interest(interest_id)
        result2 = svc._complete_trade(interest, agreement)
        assert result2["status"] == "completed"

        # Balance should only be deducted once
        buyer_after = credit_svc.get_balance(2).balance
        assert buyer_after == buyer_before - 2

    def test_seller_insufficient_credits_refunds_buyer(self, svc, repo, credit_svc):
        """If seller deduction fails, buyer gets refunded."""
        interest_id = self._setup_accepted(svc, repo)
        buyer_before = credit_svc.get_balance(2).balance

        # Drain seller credits AFTER buyer confirms (so check_sufficient passes
        # but deduct will fail due to race window)
        svc.confirm_agreement(interest_id, user_id=2)

        # Drain seller to 0
        seller_bal = credit_svc.get_balance(1).balance
        repo.update_credit_balance(1, delta=-seller_bal, reason="drain")

        with pytest.raises(InsufficientCreditsError):
            svc.confirm_agreement(interest_id, user_id=1)

        # Buyer should be refunded
        buyer_after = credit_svc.get_balance(2).balance
        assert buyer_after == buyer_before


class TestGetMyTrades:
    def test_empty_trades(self, svc, repo):
        _create_user(repo, 1, "user1@test.com")
        result = svc.get_my_trades(1)
        assert result == []

    def test_buyer_sees_trade(self, svc, repo):
        _create_user(repo, 1, "seller@test.com")
        _create_user(repo, 2, "buyer@test.com")
        entry_id = _create_collection_entry(repo, 1)
        svc.toggle_sharing(1, True)
        status = svc.get_sharing_status(1)
        svc.express_interest(
            buyer_user_id=2,
            share_code=status["share_code"],
            entry_id=entry_id,
        )
        result = svc.get_my_trades(2)
        assert len(result) == 1
        assert result[0]["my_role"] == "buyer"
        assert result[0]["counterparty_email"] is None  # not yet completed

    def test_seller_sees_trade(self, svc, repo):
        _create_user(repo, 1, "seller@test.com")
        _create_user(repo, 2, "buyer@test.com")
        entry_id = _create_collection_entry(repo, 1)
        svc.toggle_sharing(1, True)
        status = svc.get_sharing_status(1)
        svc.express_interest(
            buyer_user_id=2,
            share_code=status["share_code"],
            entry_id=entry_id,
        )
        result = svc.get_my_trades(1)
        assert len(result) == 1
        assert result[0]["my_role"] == "seller"

    def test_completed_trade_reveals_email(self, svc, repo):
        _create_user(repo, 1, "seller@test.com")
        _create_user(repo, 2, "buyer@test.com")
        entry_id = _create_collection_entry(repo, 1)
        svc.toggle_sharing(1, True)
        status = svc.get_sharing_status(1)
        interest = svc.express_interest(
            buyer_user_id=2,
            share_code=status["share_code"],
            entry_id=entry_id,
        )
        svc.respond_to_interest(interest["id"], user_id=1, action="accept")
        svc.confirm_agreement(interest["id"], user_id=2)
        svc.confirm_agreement(interest["id"], user_id=1)

        buyer_trades = svc.get_my_trades(2)
        assert buyer_trades[0]["counterparty_email"] == "seller@test.com"

        seller_trades = svc.get_my_trades(1)
        assert seller_trades[0]["counterparty_email"] == "buyer@test.com"
