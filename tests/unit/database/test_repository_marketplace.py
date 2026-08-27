"""Tests for marketplace repository methods (F69-T01).

Covers: SharedCollectionRow, TradeInterestRow, TradeAgreementRow CRUD,
        list_shared_collections anonymization, share_code uniqueness.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

import pytest

from src.database.models import SharedCollectionRow, TradeAgreementRow, TradeInterestRow
from src.database.repository import Repository


@pytest.fixture()
def repo(tmp_path):
    db_path = tmp_path / "test_marketplace.db"
    db_url = f"sqlite:///{db_path}"
    return Repository(db_url=db_url)


# ── SharedCollection CRUD ────────────────────────────────────────────


class TestSharedCollectionCRUD:
    def test_get_shared_collection_returns_none_for_new_user(self, repo):
        assert repo.get_shared_collection(user_id=999) is None

    def test_set_sharing_creates_row_on_first_call(self, repo):
        row = repo.set_sharing(user_id=1, is_shared=True)
        assert isinstance(row, SharedCollectionRow)
        assert row.user_id == 1
        assert row.is_shared == 1
        assert row.share_code is not None
        assert len(row.share_code) > 0
        assert row.shared_at is not None

    def test_set_sharing_false_creates_private_row(self, repo):
        row = repo.set_sharing(user_id=1, is_shared=False)
        assert row.is_shared == 0
        assert row.shared_at is None

    def test_set_sharing_toggle_on_then_off(self, repo):
        row_on = repo.set_sharing(user_id=1, is_shared=True)
        code = row_on.share_code
        assert row_on.is_shared == 1

        row_off = repo.set_sharing(user_id=1, is_shared=False)
        assert row_off.is_shared == 0
        # share_code should be preserved
        assert row_off.share_code == code

    def test_set_sharing_toggle_off_then_on(self, repo):
        repo.set_sharing(user_id=1, is_shared=False)
        row_on = repo.set_sharing(user_id=1, is_shared=True)
        assert row_on.is_shared == 1
        assert row_on.shared_at is not None

    def test_get_shared_collection_returns_row_after_create(self, repo):
        repo.set_sharing(user_id=42, is_shared=True)
        row = repo.get_shared_collection(user_id=42)
        assert row is not None
        assert row.user_id == 42
        assert row.is_shared == 1

    def test_share_code_is_unique_per_user(self, repo):
        row1 = repo.set_sharing(user_id=1, is_shared=True)
        row2 = repo.set_sharing(user_id=2, is_shared=True)
        assert row1.share_code != row2.share_code

    def test_share_code_auto_generated_length(self, repo):
        row = repo.set_sharing(user_id=1, is_shared=True)
        # token_urlsafe(12)[:16] should produce 16-char code
        assert len(row.share_code) == 16

    def test_shared_at_not_overwritten_on_re_enable(self, repo):
        row1 = repo.set_sharing(user_id=1, is_shared=True)
        original_shared_at = row1.shared_at

        # Disable then re-enable
        repo.set_sharing(user_id=1, is_shared=False)
        row2 = repo.set_sharing(user_id=1, is_shared=True)

        # shared_at should NOT be overwritten since it was already set
        assert row2.shared_at == original_shared_at


class TestGetSharedCollectionByCode:
    def test_returns_none_for_unknown_code(self, repo):
        assert repo.get_shared_collection_by_code("nonexistent") is None

    def test_returns_row_for_valid_shared_code(self, repo):
        row = repo.set_sharing(user_id=1, is_shared=True)
        found = repo.get_shared_collection_by_code(row.share_code)
        assert found is not None
        assert found.user_id == 1

    def test_returns_none_for_private_collection_code(self, repo):
        row = repo.set_sharing(user_id=1, is_shared=True)
        code = row.share_code
        repo.set_sharing(user_id=1, is_shared=False)

        # Code exists but collection is not shared
        assert repo.get_shared_collection_by_code(code) is None


class TestListSharedCollections:
    def test_returns_empty_when_no_shared(self, repo):
        assert repo.list_shared_collections() == []

    def test_returns_only_shared_collections(self, repo):
        repo.set_sharing(user_id=1, is_shared=True)
        repo.set_sharing(user_id=2, is_shared=False)
        repo.set_sharing(user_id=3, is_shared=True)

        result = repo.list_shared_collections()
        assert len(result) == 2

    def test_does_not_include_user_id(self, repo):
        repo.set_sharing(user_id=1, is_shared=True)
        result = repo.list_shared_collections()
        assert len(result) == 1
        assert "user_id" not in result[0]

    def test_does_not_include_email(self, repo):
        repo.set_sharing(user_id=1, is_shared=True)
        result = repo.list_shared_collections()
        assert "email" not in result[0]

    def test_returns_correct_fields(self, repo):
        repo.set_sharing(user_id=1, is_shared=True)
        result = repo.list_shared_collections()
        entry = result[0]
        assert "id" in entry
        assert "share_code" in entry
        assert "shared_at" in entry
        assert "updated_at" in entry

    def test_pagination_limit(self, repo):
        for i in range(5):
            repo.set_sharing(user_id=i + 1, is_shared=True)

        result = repo.list_shared_collections(limit=2)
        assert len(result) == 2

    def test_pagination_offset(self, repo):
        for i in range(5):
            repo.set_sharing(user_id=i + 1, is_shared=True)

        page1 = repo.list_shared_collections(limit=2, offset=0)
        page2 = repo.list_shared_collections(limit=2, offset=2)

        codes1 = {e["share_code"] for e in page1}
        codes2 = {e["share_code"] for e in page2}
        assert codes1.isdisjoint(codes2)


# ── TradeInterest CRUD ───────────────────────────────────────────────


class TestTradeInterestCRUD:
    def test_create_trade_interest_defaults(self, repo):
        row = repo.create_trade_interest(
            buyer_user_id=1,
            seller_user_id=2,
            collection_entry_id=100,
        )
        assert isinstance(row, TradeInterestRow)
        assert row.buyer_user_id == 1
        assert row.seller_user_id == 2
        assert row.collection_entry_id == 100
        assert row.status == "pending"
        assert row.estimated_fee == 2
        assert row.message is None
        assert row.card_price_at_interest is None
        assert row.created_at is not None

    def test_create_trade_interest_with_all_fields(self, repo):
        row = repo.create_trade_interest(
            buyer_user_id=1,
            seller_user_id=2,
            collection_entry_id=100,
            message="I want this card!",
            estimated_fee=5,
            card_price_at_interest=Decimal("12.50"),
        )
        assert row.message == "I want this card!"
        assert row.estimated_fee == 5
        assert row.card_price_at_interest == Decimal("12.50")

    def test_get_trade_interest_returns_none_for_unknown(self, repo):
        assert repo.get_trade_interest(999) is None

    def test_get_trade_interest_returns_created_row(self, repo):
        created = repo.create_trade_interest(
            buyer_user_id=1, seller_user_id=2, collection_entry_id=100
        )
        fetched = repo.get_trade_interest(created.id)
        assert fetched is not None
        assert fetched.id == created.id
        assert fetched.buyer_user_id == 1

    def test_update_trade_interest_status_accepted(self, repo):
        row = repo.create_trade_interest(buyer_user_id=1, seller_user_id=2, collection_entry_id=100)
        updated = repo.update_trade_interest_status(row.id, "accepted")
        assert updated is not None
        assert updated.status == "accepted"

    def test_update_trade_interest_status_rejected(self, repo):
        row = repo.create_trade_interest(buyer_user_id=1, seller_user_id=2, collection_entry_id=100)
        updated = repo.update_trade_interest_status(row.id, "rejected")
        assert updated.status == "rejected"

    def test_update_trade_interest_status_completed(self, repo):
        row = repo.create_trade_interest(buyer_user_id=1, seller_user_id=2, collection_entry_id=100)
        repo.update_trade_interest_status(row.id, "accepted")
        updated = repo.update_trade_interest_status(row.id, "completed")
        assert updated.status == "completed"

    def test_update_trade_interest_status_cancelled(self, repo):
        row = repo.create_trade_interest(buyer_user_id=1, seller_user_id=2, collection_entry_id=100)
        updated = repo.update_trade_interest_status(row.id, "cancelled")
        assert updated.status == "cancelled"

    def test_update_trade_interest_status_invalid_raises(self, repo):
        row = repo.create_trade_interest(buyer_user_id=1, seller_user_id=2, collection_entry_id=100)
        with pytest.raises(ValueError, match="Invalid trade interest status"):
            repo.update_trade_interest_status(row.id, "invalid_status")

    def test_update_trade_interest_status_not_found(self, repo):
        result = repo.update_trade_interest_status(999, "accepted")
        assert result is None


class TestGetUserTrades:
    def test_returns_empty_for_no_trades(self, repo):
        result = repo.get_user_trades(user_id=1)
        assert result == []

    def test_returns_trades_as_buyer(self, repo):
        repo.create_trade_interest(buyer_user_id=1, seller_user_id=2, collection_entry_id=100)
        result = repo.get_user_trades(user_id=1)
        assert len(result) == 1
        assert result[0].buyer_user_id == 1

    def test_returns_trades_as_seller(self, repo):
        repo.create_trade_interest(buyer_user_id=2, seller_user_id=1, collection_entry_id=100)
        result = repo.get_user_trades(user_id=1)
        assert len(result) == 1
        assert result[0].seller_user_id == 1

    def test_returns_both_buyer_and_seller_trades(self, repo):
        repo.create_trade_interest(buyer_user_id=1, seller_user_id=2, collection_entry_id=100)
        repo.create_trade_interest(buyer_user_id=3, seller_user_id=1, collection_entry_id=200)
        result = repo.get_user_trades(user_id=1)
        assert len(result) == 2

    def test_does_not_return_other_users_trades(self, repo):
        repo.create_trade_interest(buyer_user_id=2, seller_user_id=3, collection_entry_id=100)
        result = repo.get_user_trades(user_id=1)
        assert result == []

    def test_pagination(self, repo):
        for i in range(5):
            repo.create_trade_interest(
                buyer_user_id=1, seller_user_id=2, collection_entry_id=100 + i
            )
        page1 = repo.get_user_trades(user_id=1, limit=2, offset=0)
        page2 = repo.get_user_trades(user_id=1, limit=2, offset=2)
        assert len(page1) == 2
        assert len(page2) == 2
        ids1 = {t.id for t in page1}
        ids2 = {t.id for t in page2}
        assert ids1.isdisjoint(ids2)

    def test_ordered_newest_first(self, repo):
        t1 = repo.create_trade_interest(buyer_user_id=1, seller_user_id=2, collection_entry_id=100)
        t2 = repo.create_trade_interest(buyer_user_id=1, seller_user_id=3, collection_entry_id=200)
        result = repo.get_user_trades(user_id=1)
        assert result[0].id == t2.id
        assert result[1].id == t1.id


# ── TradeAgreement CRUD ──────────────────────────────────────────────


class TestTradeAgreementCRUD:
    def test_create_trade_agreement(self, repo):
        interest = repo.create_trade_interest(
            buyer_user_id=1, seller_user_id=2, collection_entry_id=100
        )
        agreement = repo.create_trade_agreement(interest.id)
        assert isinstance(agreement, TradeAgreementRow)
        assert agreement.trade_interest_id == interest.id
        assert agreement.buyer_confirmed == 0
        assert agreement.seller_confirmed == 0
        assert agreement.buyer_fee_charged == 0
        assert agreement.seller_fee_charged == 0
        assert agreement.completed_at is None
        assert agreement.created_at is not None

    def test_get_trade_agreement_returns_none_for_unknown(self, repo):
        assert repo.get_trade_agreement(999) is None

    def test_get_trade_agreement_returns_created(self, repo):
        interest = repo.create_trade_interest(
            buyer_user_id=1, seller_user_id=2, collection_entry_id=100
        )
        created = repo.create_trade_agreement(interest.id)
        fetched = repo.get_trade_agreement(created.id)
        assert fetched is not None
        assert fetched.id == created.id

    def test_get_trade_agreement_by_interest(self, repo):
        interest = repo.create_trade_interest(
            buyer_user_id=1, seller_user_id=2, collection_entry_id=100
        )
        repo.create_trade_agreement(interest.id)
        found = repo.get_trade_agreement_by_interest(interest.id)
        assert found is not None
        assert found.trade_interest_id == interest.id

    def test_get_trade_agreement_by_interest_not_found(self, repo):
        assert repo.get_trade_agreement_by_interest(999) is None

    def test_update_trade_agreement_buyer_confirmed(self, repo):
        interest = repo.create_trade_interest(
            buyer_user_id=1, seller_user_id=2, collection_entry_id=100
        )
        agreement = repo.create_trade_agreement(interest.id)
        updated = repo.update_trade_agreement(agreement.id, buyer_confirmed=1)
        assert updated is not None
        assert updated.buyer_confirmed == 1
        assert updated.seller_confirmed == 0

    def test_update_trade_agreement_seller_confirmed(self, repo):
        interest = repo.create_trade_interest(
            buyer_user_id=1, seller_user_id=2, collection_entry_id=100
        )
        agreement = repo.create_trade_agreement(interest.id)
        updated = repo.update_trade_agreement(agreement.id, seller_confirmed=1)
        assert updated.seller_confirmed == 1

    def test_update_trade_agreement_fees_and_completion(self, repo):
        interest = repo.create_trade_interest(
            buyer_user_id=1, seller_user_id=2, collection_entry_id=100
        )
        agreement = repo.create_trade_agreement(interest.id)
        now = datetime.now()
        updated = repo.update_trade_agreement(
            agreement.id,
            buyer_confirmed=1,
            seller_confirmed=1,
            buyer_fee_charged=2,
            seller_fee_charged=2,
            completed_at=now,
        )
        assert updated.buyer_confirmed == 1
        assert updated.seller_confirmed == 1
        assert updated.buyer_fee_charged == 2
        assert updated.seller_fee_charged == 2
        assert updated.completed_at is not None

    def test_update_trade_agreement_not_found(self, repo):
        result = repo.update_trade_agreement(999, buyer_confirmed=1)
        assert result is None

    def test_update_trade_agreement_ignores_unknown_fields(self, repo):
        interest = repo.create_trade_interest(
            buyer_user_id=1, seller_user_id=2, collection_entry_id=100
        )
        agreement = repo.create_trade_agreement(interest.id)
        # Should not raise, just ignore the unknown field
        updated = repo.update_trade_agreement(
            agreement.id, nonexistent_field="value", buyer_confirmed=1
        )
        assert updated.buyer_confirmed == 1


# ── Domain model tests ───────────────────────────────────────────────


class TestDomainModels:
    def test_shared_collection_dataclass(self):
        from src.domain.models import SharedCollection

        sc = SharedCollection(
            user_id=1,
            is_shared=True,
            share_code="abc123",
            shared_at=datetime(2026, 1, 1),
        )
        assert sc.user_id == 1
        assert sc.is_shared is True
        assert sc.share_code == "abc123"
        assert sc.shared_at == datetime(2026, 1, 1)

    def test_shared_collection_shared_at_none(self):
        from src.domain.models import SharedCollection

        sc = SharedCollection(user_id=1, is_shared=False, share_code="x", shared_at=None)
        assert sc.shared_at is None

    def test_trade_interest_dataclass(self):
        from src.domain.models import TradeInterest

        ti = TradeInterest(
            id=1,
            buyer_user_id=10,
            seller_user_id=20,
            collection_entry_id=100,
            status="pending",
            message="want this",
            estimated_fee=2,
            card_price_at_interest=Decimal("5.00"),
            created_at=datetime(2026, 1, 1),
        )
        assert ti.id == 1
        assert ti.status == "pending"
        assert ti.card_price_at_interest == Decimal("5.00")

    def test_trade_interest_optional_fields(self):
        from src.domain.models import TradeInterest

        ti = TradeInterest(
            id=1,
            buyer_user_id=10,
            seller_user_id=20,
            collection_entry_id=100,
            status="pending",
            message=None,
            estimated_fee=2,
            card_price_at_interest=None,
            created_at=datetime(2026, 1, 1),
        )
        assert ti.message is None
        assert ti.card_price_at_interest is None

    def test_trade_agreement_dataclass(self):
        from src.domain.models import TradeAgreement

        ta = TradeAgreement(
            id=1,
            trade_interest_id=10,
            buyer_confirmed=True,
            seller_confirmed=False,
            buyer_fee_charged=2,
            seller_fee_charged=0,
            completed_at=None,
        )
        assert ta.id == 1
        assert ta.buyer_confirmed is True
        assert ta.seller_confirmed is False
        assert ta.completed_at is None

    def test_trade_agreement_completed(self):
        from src.domain.models import TradeAgreement

        now = datetime(2026, 6, 15)
        ta = TradeAgreement(
            id=1,
            trade_interest_id=10,
            buyer_confirmed=True,
            seller_confirmed=True,
            buyer_fee_charged=2,
            seller_fee_charged=2,
            completed_at=now,
        )
        assert ta.completed_at == now
        assert ta.buyer_fee_charged == 2
        assert ta.seller_fee_charged == 2
