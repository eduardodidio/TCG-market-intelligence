"""Tests for portfolio backfill — synthetic snapshot generation (F112-T02)."""

from __future__ import annotations

from datetime import date, datetime, timedelta
from decimal import Decimal
from unittest.mock import MagicMock, patch

from src.collectors.portfolio_backfill import (
    _build_price_index,
    _find_best_price,
    backfill_portfolio_snapshots,
)

# ── Helpers ──────────────────────────────────────────────────────


def _make_collection_entry(
    card_id: int | None,
    quantity: int = 1,
    created_at: datetime | None = None,
):
    """Create a mock UserCollectionRow."""
    entry = MagicMock()
    entry.card_id = card_id
    entry.quantity = quantity
    entry.created_at = created_at or datetime(2026, 8, 1)
    return entry


def _make_session_context(
    collection_entries: list | None = None,
    source_card_rows: list | None = None,
    price_obs_rows: list | None = None,
    existing_snapshot_dates: list | None = None,
):
    """Build a mock Session that returns canned query results.

    The Session is used as a context manager and execute() is called
    multiple times in sequence:
      1. existing snapshot dates
      2. collection entries
      3. source card (card_id, external_id) rows
      4. price observation rows
    """
    session = MagicMock()

    call_results = []

    # 1 — existing snapshot dates
    snap_scalars = MagicMock()
    snap_scalars.all.return_value = existing_snapshot_dates or []
    snap_result = MagicMock()
    snap_result.scalars.return_value = snap_scalars
    call_results.append(snap_result)

    # 2 — collection entries
    coll_scalars = MagicMock()
    coll_scalars.all.return_value = collection_entries or []
    coll_result = MagicMock()
    coll_result.scalars.return_value = coll_scalars
    call_results.append(coll_result)

    # 3 — source card rows (card_id, external_id)
    src_result = MagicMock()
    src_result.all.return_value = source_card_rows or []
    call_results.append(src_result)

    # 4 — price observations
    price_result = MagicMock()
    price_result.all.return_value = price_obs_rows or []
    call_results.append(price_result)

    session.execute = MagicMock(side_effect=call_results)

    ctx = MagicMock()
    ctx.__enter__ = MagicMock(return_value=session)
    ctx.__exit__ = MagicMock(return_value=False)

    return ctx


# ── Forward-fill tests ──────────────────────────────────────────


class TestForwardFill:
    """Price from earlier date carries forward when no new observation exists."""

    def test_price_carries_forward(self):
        """If a price exists on day 1 but not day 2, day 2 uses day 1 price."""
        price_index = {
            "ext_1": (
                [date(2026, 8, 1)],
                [Decimal("10.00")],
            ),
        }
        # Day after the observation — should carry forward.
        result = _find_best_price(price_index, ["ext_1"], date(2026, 8, 5))
        assert result == Decimal("10.00")

    def test_price_on_exact_date(self):
        price_index = {
            "ext_1": (
                [date(2026, 8, 1), date(2026, 8, 3)],
                [Decimal("10.00"), Decimal("15.00")],
            ),
        }
        result = _find_best_price(price_index, ["ext_1"], date(2026, 8, 3))
        assert result == Decimal("15.00")

    def test_no_price_before_target_date(self):
        price_index = {
            "ext_1": (
                [date(2026, 8, 5)],
                [Decimal("10.00")],
            ),
        }
        result = _find_best_price(price_index, ["ext_1"], date(2026, 8, 1))
        assert result is None

    def test_multiple_external_ids_most_recent_wins(self):
        price_index = {
            "ext_1": (
                [date(2026, 8, 1)],
                [Decimal("10.00")],
            ),
            "ext_2": (
                [date(2026, 8, 3)],
                [Decimal("20.00")],
            ),
        }
        result = _find_best_price(price_index, ["ext_1", "ext_2"], date(2026, 8, 5))
        assert result == Decimal("20.00")

    def test_no_external_ids(self):
        result = _find_best_price({}, [], date(2026, 8, 1))
        assert result is None


# ── Build price index ────────────────────────────────────────────


class TestBuildPriceIndex:
    def test_empty_external_ids(self):
        session = MagicMock()
        result = _build_price_index(session, set())
        assert result == {}


# ── Backfill integration (mocked DB) ────────────────────────────


class TestBackfillPortfolioSnapshots:
    @patch("src.collectors.portfolio_backfill.Session")
    def test_skips_existing_snapshots(self, mock_session_cls):
        """Dates with existing snapshots are not overwritten."""
        today = date.today()
        yesterday = today - timedelta(days=1)

        entry = _make_collection_entry(card_id=1, quantity=2)

        ctx = _make_session_context(
            collection_entries=[entry],
            source_card_rows=[(1, "ext_1")],
            price_obs_rows=[("ext_1", yesterday, Decimal("5.00"), None, None)],
            existing_snapshot_dates=[yesterday],
        )
        mock_session_cls.return_value = ctx

        repo = MagicMock()
        repo.engine = MagicMock()

        result = backfill_portfolio_snapshots(repo, "user1", days=1)

        # yesterday is skipped (existing), today is filled
        assert result["days_skipped"] == 1
        assert result["days_filled"] == 1

    @patch("src.collectors.portfolio_backfill.Session")
    def test_entries_created_after_target_excluded(self, mock_session_cls):
        """Collection entries created after the target date are excluded."""
        today = date.today()
        yesterday = today - timedelta(days=1)

        # Entry created today — should NOT count for yesterday.
        entry = _make_collection_entry(
            card_id=1,
            quantity=3,
            created_at=datetime.combine(today, datetime.min.time()),
        )

        ctx = _make_session_context(
            collection_entries=[entry],
            source_card_rows=[(1, "ext_1")],
            price_obs_rows=[("ext_1", yesterday, Decimal("10.00"), None, None)],
            existing_snapshot_dates=[],
        )
        mock_session_cls.return_value = ctx

        repo = MagicMock()
        repo.engine = MagicMock()

        result = backfill_portfolio_snapshots(repo, "user1", days=1)

        # Both yesterday and today should be filled.
        assert result["days_filled"] == 2

        # Check the call for yesterday — should have total_card_count=0
        # because the entry was created today.
        calls = repo.upsert_portfolio_snapshot.call_args_list
        yesterday_call = [c for c in calls if c.kwargs.get("snapshot_date") == yesterday]
        assert len(yesterday_call) == 1
        assert yesterday_call[0].kwargs["total_card_count"] == 0
        assert yesterday_call[0].kwargs["total_value_brl"] == Decimal("0")

        # Today should include the entry.
        today_call = [c for c in calls if c.kwargs.get("snapshot_date") == today]
        assert len(today_call) == 1
        assert today_call[0].kwargs["total_card_count"] == 3

    @patch("src.collectors.portfolio_backfill.Session")
    def test_empty_collection_returns_zero(self, mock_session_cls):
        """User with no collection entries gets zero days filled."""
        ctx = _make_session_context(collection_entries=[])
        mock_session_cls.return_value = ctx

        repo = MagicMock()
        repo.engine = MagicMock()

        result = backfill_portfolio_snapshots(repo, "user1", days=5)

        assert result == {"days_filled": 0, "days_skipped": 0}
        repo.upsert_portfolio_snapshot.assert_not_called()

    @patch("src.collectors.portfolio_backfill.Session")
    def test_summary_counts(self, mock_session_cls):
        """Verify days_filled and days_skipped add up correctly."""
        today = date.today()
        day_minus_2 = today - timedelta(days=2)
        day_minus_1 = today - timedelta(days=1)

        entry = _make_collection_entry(card_id=1, quantity=1)

        ctx = _make_session_context(
            collection_entries=[entry],
            source_card_rows=[(1, "ext_1")],
            price_obs_rows=[
                ("ext_1", day_minus_2, Decimal("8.00"), None, None),
            ],
            existing_snapshot_dates=[day_minus_1],
        )
        mock_session_cls.return_value = ctx

        repo = MagicMock()
        repo.engine = MagicMock()

        result = backfill_portfolio_snapshots(repo, "user1", days=2)

        # 3 days total (d-2, d-1, d-0), 1 skipped (d-1)
        assert result["days_filled"] == 2
        assert result["days_skipped"] == 1

    @patch("src.collectors.portfolio_backfill.Session")
    def test_forward_fill_across_days(self, mock_session_cls):
        """Price from day-2 carries forward to day-1 and today when no new observation."""
        today = date.today()
        day_minus_2 = today - timedelta(days=2)

        entry = _make_collection_entry(card_id=1, quantity=2)

        ctx = _make_session_context(
            collection_entries=[entry],
            source_card_rows=[(1, "ext_1")],
            price_obs_rows=[
                ("ext_1", day_minus_2, Decimal("5.00"), None, None),
            ],
            existing_snapshot_dates=[],
        )
        mock_session_cls.return_value = ctx

        repo = MagicMock()
        repo.engine = MagicMock()

        backfill_portfolio_snapshots(repo, "user1", days=2)

        calls = repo.upsert_portfolio_snapshot.call_args_list
        # All 3 days should use the price from day_minus_2: 5.00 * 2 = 10.00
        for call in calls:
            assert call.kwargs["total_value_brl"] == Decimal("10.00")
            assert call.kwargs["priced_card_count"] == 1
            assert call.kwargs["total_card_count"] == 2

    @patch("src.collectors.portfolio_backfill.Session")
    def test_unlinked_card_counted_but_not_priced(self, mock_session_cls):
        """Entries with card_id=None are counted but not priced."""
        entry = _make_collection_entry(card_id=None, quantity=4)

        ctx = _make_session_context(
            collection_entries=[entry],
            source_card_rows=[],
            price_obs_rows=[],
            existing_snapshot_dates=[],
        )
        mock_session_cls.return_value = ctx

        repo = MagicMock()
        repo.engine = MagicMock()

        backfill_portfolio_snapshots(repo, "user1", days=0)

        call = repo.upsert_portfolio_snapshot.call_args
        assert call.kwargs["total_card_count"] == 4
        assert call.kwargs["priced_card_count"] == 0
        assert call.kwargs["total_value_brl"] == Decimal("0")
