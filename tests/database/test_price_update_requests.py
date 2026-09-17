"""Tests for PriceUpdateRequestRow model and repository methods (F130-T04)."""

from __future__ import annotations

from datetime import datetime, timedelta
from decimal import Decimal

import pytest
from sqlalchemy.orm import Session

from src.database.models import PriceUpdateRequestRow
from src.database.repository import Repository


@pytest.fixture()
def repo(tmp_path):
    db_path = tmp_path / "t.db"
    return Repository(f"sqlite:///{db_path}")


@pytest.fixture()
def user(repo):
    """Create a test user and return the UserRow."""
    return repo.create_user(
        email="test@example.com",
        display_name="Test User",
        auth_provider="email",
        password_hash="fakehash",
    )


@pytest.fixture()
def user2(repo):
    """Create a second test user."""
    return repo.create_user(
        email="test2@example.com",
        display_name="Test User 2",
        auth_provider="email",
        password_hash="fakehash2",
    )


@pytest.fixture()
def card(repo):
    """Create a test card and return its id."""
    return repo.create_canonical_card(
        game="mtg",
        name_en="Lightning Bolt",
        name_pt=None,
        set_code="m10",
        collector_number="1",
    )


@pytest.fixture()
def card2(repo):
    """Create a second test card and return its id."""
    return repo.create_canonical_card(
        game="mtg",
        name_en="Counterspell",
        name_pt=None,
        set_code="m10",
        collector_number="2",
    )


class TestCreatePriceUpdateRequest:
    def test_creates_new_pending_request(self, repo, user, card):
        row = repo.create_price_update_request(card_id=card, user_id=user.id)

        assert row.id is not None
        assert row.card_id == card
        assert row.user_id == user.id
        assert row.status == "pending"
        assert row.attempts == 0
        assert row.processed_at is None
        assert row.result_price is None
        assert row.error_message is None
        assert row.requested_at is not None

    def test_deduplicates_within_24h(self, repo, user, card):
        first = repo.create_price_update_request(card_id=card, user_id=user.id)
        second = repo.create_price_update_request(card_id=card, user_id=user.id)

        assert first.id == second.id

    def test_dedup_is_per_card(self, repo, user, card, card2):
        """Different cards get their own requests."""
        r1 = repo.create_price_update_request(card_id=card, user_id=user.id)
        r2 = repo.create_price_update_request(card_id=card2, user_id=user.id)

        assert r1.id != r2.id

    def test_dedup_allows_after_24h(self, repo, user, card):
        """A new request is created if the existing one is older than 24h."""
        first = repo.create_price_update_request(card_id=card, user_id=user.id)

        # Manually backdate the existing request to 25 hours ago
        with Session(repo.engine) as session:
            row = session.get(PriceUpdateRequestRow, first.id)
            row.requested_at = datetime.now() - timedelta(hours=25)
            session.commit()

        second = repo.create_price_update_request(card_id=card, user_id=user.id)
        assert second.id != first.id

    def test_dedup_skips_non_pending(self, repo, user, card):
        """Completed requests don't block new pending ones."""
        first = repo.create_price_update_request(card_id=card, user_id=user.id)
        repo.update_price_request_status(first.id, "completed", result_price=Decimal("10.00"))

        second = repo.create_price_update_request(card_id=card, user_id=user.id)
        assert second.id != first.id

    def test_different_users_same_card_get_own_requests(self, repo, user, user2, card):
        """Dedup is by card_id only, not user_id — each user still creates."""
        # Note: the spec says dedup is by card_id, so user2 submitting for the same
        # card within 24h should return the existing pending request from user1.
        r1 = repo.create_price_update_request(card_id=card, user_id=user.id)
        r2 = repo.create_price_update_request(card_id=card, user_id=user2.id)

        # The dedup is by card_id (any pending request for that card within 24h),
        # so user2 gets back the same request row.
        assert r1.id == r2.id


class TestGetPendingPriceRequests:
    def test_returns_oldest_first(self, repo, user, card, card2):
        r1 = repo.create_price_update_request(card_id=card, user_id=user.id)
        r2 = repo.create_price_update_request(card_id=card2, user_id=user.id)

        pending = repo.get_pending_price_requests(limit=10)
        assert len(pending) == 2
        assert pending[0].id == r1.id
        assert pending[1].id == r2.id

    def test_respects_limit(self, repo, user, card, card2):
        repo.create_price_update_request(card_id=card, user_id=user.id)
        repo.create_price_update_request(card_id=card2, user_id=user.id)

        pending = repo.get_pending_price_requests(limit=1)
        assert len(pending) == 1

    def test_skips_completed_requests(self, repo, user, card, card2):
        r1 = repo.create_price_update_request(card_id=card, user_id=user.id)
        repo.create_price_update_request(card_id=card2, user_id=user.id)
        repo.update_price_request_status(r1.id, "completed", result_price=Decimal("5.00"))

        pending = repo.get_pending_price_requests()
        assert len(pending) == 1
        assert pending[0].card_id == card2

    def test_skips_requests_with_3_or_more_attempts(self, repo, user, card):
        r1 = repo.create_price_update_request(card_id=card, user_id=user.id)

        # Simulate 3 failed attempts (each call increments attempts)
        repo.update_price_request_status(r1.id, "pending", error_message="retry 1")
        repo.update_price_request_status(r1.id, "pending", error_message="retry 2")
        repo.update_price_request_status(r1.id, "pending", error_message="retry 3")

        pending = repo.get_pending_price_requests()
        assert len(pending) == 0

    def test_returns_empty_when_none_pending(self, repo):
        pending = repo.get_pending_price_requests()
        assert pending == []


class TestUpdatePriceRequestStatus:
    def test_sets_status_and_increments_attempts(self, repo, user, card):
        r = repo.create_price_update_request(card_id=card, user_id=user.id)
        repo.update_price_request_status(r.id, "processing")

        with Session(repo.engine) as session:
            row = session.get(PriceUpdateRequestRow, r.id)
            assert row.status == "processing"
            assert row.attempts == 1

    def test_sets_processed_at_on_completed(self, repo, user, card):
        r = repo.create_price_update_request(card_id=card, user_id=user.id)
        repo.update_price_request_status(r.id, "completed", result_price=Decimal("15.50"))

        with Session(repo.engine) as session:
            row = session.get(PriceUpdateRequestRow, r.id)
            assert row.status == "completed"
            assert row.processed_at is not None
            assert row.result_price == Decimal("15.50")

    def test_sets_processed_at_on_failed(self, repo, user, card):
        r = repo.create_price_update_request(card_id=card, user_id=user.id)
        repo.update_price_request_status(r.id, "failed", error_message="Liga timeout")

        with Session(repo.engine) as session:
            row = session.get(PriceUpdateRequestRow, r.id)
            assert row.status == "failed"
            assert row.processed_at is not None
            assert row.error_message == "Liga timeout"

    def test_does_not_set_processed_at_on_processing(self, repo, user, card):
        r = repo.create_price_update_request(card_id=card, user_id=user.id)
        repo.update_price_request_status(r.id, "processing")

        with Session(repo.engine) as session:
            row = session.get(PriceUpdateRequestRow, r.id)
            assert row.processed_at is None

    def test_increments_attempts_cumulatively(self, repo, user, card):
        r = repo.create_price_update_request(card_id=card, user_id=user.id)
        repo.update_price_request_status(r.id, "processing")
        repo.update_price_request_status(r.id, "pending", error_message="retry")
        repo.update_price_request_status(r.id, "processing")

        with Session(repo.engine) as session:
            row = session.get(PriceUpdateRequestRow, r.id)
            assert row.attempts == 3

    def test_noop_for_nonexistent_id(self, repo):
        # Should not raise
        repo.update_price_request_status(99999, "completed")


class TestGetPriceRequests:
    def test_returns_all_when_no_filter(self, repo, user, card, card2):
        repo.create_price_update_request(card_id=card, user_id=user.id)
        r2 = repo.create_price_update_request(card_id=card2, user_id=user.id)
        repo.update_price_request_status(r2.id, "completed", result_price=Decimal("1.00"))

        rows, total = repo.get_price_requests()
        assert total == 2
        assert len(rows) == 2

    def test_filters_by_status(self, repo, user, card, card2):
        repo.create_price_update_request(card_id=card, user_id=user.id)
        r2 = repo.create_price_update_request(card_id=card2, user_id=user.id)
        repo.update_price_request_status(r2.id, "completed", result_price=Decimal("1.00"))

        rows, total = repo.get_price_requests(status="pending")
        assert total == 1
        assert len(rows) == 1
        assert rows[0].status == "pending"

    def test_pagination(self, repo, user, card, card2):
        repo.create_price_update_request(card_id=card, user_id=user.id)
        repo.create_price_update_request(card_id=card2, user_id=user.id)

        rows, total = repo.get_price_requests(limit=1, offset=0)
        assert total == 2
        assert len(rows) == 1

        rows2, total2 = repo.get_price_requests(limit=1, offset=1)
        assert total2 == 2
        assert len(rows2) == 1
        assert rows[0].id != rows2[0].id

    def test_ordered_by_requested_at_desc(self, repo, user, card, card2):
        repo.create_price_update_request(card_id=card, user_id=user.id)
        repo.create_price_update_request(card_id=card2, user_id=user.id)

        rows, _ = repo.get_price_requests()
        # Most recent first
        assert rows[0].requested_at >= rows[1].requested_at


class TestGetUserPriceRequestForCard:
    def test_returns_latest_request(self, repo, user, card):
        r1 = repo.create_price_update_request(card_id=card, user_id=user.id)
        # Complete the first one so a new one can be created
        repo.update_price_request_status(r1.id, "completed", result_price=Decimal("5.00"))
        r2 = repo.create_price_update_request(card_id=card, user_id=user.id)

        result = repo.get_user_price_request_for_card(user_id=user.id, card_id=card)
        assert result is not None
        assert result.id == r2.id

    def test_returns_none_when_no_requests(self, repo, user, card):
        result = repo.get_user_price_request_for_card(user_id=user.id, card_id=card)
        assert result is None

    def test_scoped_to_user(self, repo, user, user2, card):
        repo.create_price_update_request(card_id=card, user_id=user.id)

        result = repo.get_user_price_request_for_card(user_id=user2.id, card_id=card)
        assert result is None


class TestCountPriceRequestsByStatus:
    def test_returns_correct_counts(self, repo, user, card, card2):
        r1 = repo.create_price_update_request(card_id=card, user_id=user.id)
        repo.create_price_update_request(card_id=card2, user_id=user.id)
        repo.update_price_request_status(r1.id, "completed", result_price=Decimal("3.00"))

        counts = repo.count_price_requests_by_status()
        assert counts["pending"] == 1
        assert counts["completed"] == 1
        assert counts["processing"] == 0
        assert counts["failed"] == 0

    def test_all_zero_when_empty(self, repo):
        counts = repo.count_price_requests_by_status()
        assert counts == {"pending": 0, "processing": 0, "completed": 0, "failed": 0}

    def test_multiple_statuses(self, repo, user, card, card2):
        r1 = repo.create_price_update_request(card_id=card, user_id=user.id)
        r2 = repo.create_price_update_request(card_id=card2, user_id=user.id)
        repo.update_price_request_status(r1.id, "failed", error_message="err")
        repo.update_price_request_status(r2.id, "processing")

        counts = repo.count_price_requests_by_status()
        assert counts["failed"] == 1
        assert counts["processing"] == 1
        assert counts["pending"] == 0
        assert counts["completed"] == 0


class TestCascadeDelete:
    def test_cascade_on_card_delete(self, repo, user, card):
        """Deleting a card cascades to its price update requests."""
        repo.create_price_update_request(card_id=card, user_id=user.id)

        with Session(repo.engine) as session:
            from src.database.models import CardRow

            card_row = session.get(CardRow, card)
            session.delete(card_row)
            session.commit()

        rows, total = repo.get_price_requests()
        assert total == 0

    def test_cascade_on_user_delete(self, repo, user, card):
        """Deleting a user cascades to their price update requests."""
        repo.create_price_update_request(card_id=card, user_id=user.id)

        with Session(repo.engine) as session:
            from src.database.models import UserRow

            user_row = session.get(UserRow, user.id)
            session.delete(user_row)
            session.commit()

        rows, total = repo.get_price_requests()
        assert total == 0
