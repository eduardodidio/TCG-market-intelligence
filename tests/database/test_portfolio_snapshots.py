"""Tests for portfolio snapshot repository methods (F80-T01)."""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

import pytest

from src.database.repository import Repository


@pytest.fixture()
def repo(tmp_path):
    db_path = tmp_path / "test_portfolio.db"
    return Repository(db_url=f"sqlite:///{db_path}")


class TestUpsertPortfolioSnapshot:
    def test_insert_new_snapshot(self, repo):
        row_id = repo.upsert_portfolio_snapshot(
            user_id="1",
            snapshot_date=date(2026, 8, 27),
            total_value_brl=Decimal("1234.56"),
            priced_card_count=300,
            total_card_count=349,
        )
        assert row_id > 0

        snapshots = repo.get_portfolio_snapshots("1", days=30)
        assert len(snapshots) == 1
        assert snapshots[0].total_value_brl == Decimal("1234.56")
        assert snapshots[0].priced_card_count == 300
        assert snapshots[0].total_card_count == 349

    def test_upsert_same_date_updates_value(self, repo):
        repo.upsert_portfolio_snapshot(
            user_id="1",
            snapshot_date=date(2026, 8, 27),
            total_value_brl=Decimal("1000.00"),
            priced_card_count=200,
            total_card_count=300,
        )
        repo.upsert_portfolio_snapshot(
            user_id="1",
            snapshot_date=date(2026, 8, 27),
            total_value_brl=Decimal("1500.00"),
            priced_card_count=250,
            total_card_count=300,
        )

        snapshots = repo.get_portfolio_snapshots("1", days=30)
        assert len(snapshots) == 1
        assert snapshots[0].total_value_brl == Decimal("1500.00")
        assert snapshots[0].priced_card_count == 250

    def test_different_users_separate_snapshots(self, repo):
        repo.upsert_portfolio_snapshot(
            user_id="1",
            snapshot_date=date(2026, 8, 27),
            total_value_brl=Decimal("1000.00"),
            priced_card_count=100,
            total_card_count=200,
        )
        repo.upsert_portfolio_snapshot(
            user_id="2",
            snapshot_date=date(2026, 8, 27),
            total_value_brl=Decimal("2000.00"),
            priced_card_count=150,
            total_card_count=250,
        )

        s1 = repo.get_portfolio_snapshots("1", days=30)
        s2 = repo.get_portfolio_snapshots("2", days=30)
        assert len(s1) == 1
        assert len(s2) == 1
        assert s1[0].total_value_brl == Decimal("1000.00")
        assert s2[0].total_value_brl == Decimal("2000.00")

    def test_zero_value_snapshot(self, repo):
        repo.upsert_portfolio_snapshot(
            user_id="1",
            snapshot_date=date(2026, 8, 27),
            total_value_brl=Decimal("0"),
            priced_card_count=0,
            total_card_count=100,
        )
        snapshots = repo.get_portfolio_snapshots("1", days=30)
        assert len(snapshots) == 1
        assert snapshots[0].total_value_brl == Decimal("0")


class TestGetPortfolioSnapshots:
    def test_ordered_by_date_desc(self, repo):
        for i in range(5):
            repo.upsert_portfolio_snapshot(
                user_id="1",
                snapshot_date=date(2026, 8, 23) + timedelta(days=i),
                total_value_brl=Decimal(str(1000 + i * 10)),
                priced_card_count=100,
                total_card_count=200,
            )

        snapshots = repo.get_portfolio_snapshots("1", days=30)
        assert len(snapshots) == 5
        dates = [s.snapshot_date for s in snapshots]
        assert dates == sorted(dates, reverse=True)

    def test_respects_days_filter(self, repo):
        today = date.today()
        # Insert snapshot from 40 days ago — should be excluded with days=30
        repo.upsert_portfolio_snapshot(
            user_id="1",
            snapshot_date=today - timedelta(days=40),
            total_value_brl=Decimal("500.00"),
            priced_card_count=50,
            total_card_count=100,
        )
        repo.upsert_portfolio_snapshot(
            user_id="1",
            snapshot_date=today,
            total_value_brl=Decimal("1000.00"),
            priced_card_count=100,
            total_card_count=200,
        )

        snapshots = repo.get_portfolio_snapshots("1", days=30)
        assert len(snapshots) == 1
        assert snapshots[0].snapshot_date == today

        # But with days=60 we get both
        snapshots_all = repo.get_portfolio_snapshots("1", days=60)
        assert len(snapshots_all) == 2

    def test_empty_for_unknown_user(self, repo):
        snapshots = repo.get_portfolio_snapshots("nonexistent", days=30)
        assert snapshots == []

    def test_only_returns_requested_user(self, repo):
        repo.upsert_portfolio_snapshot(
            user_id="1",
            snapshot_date=date(2026, 8, 27),
            total_value_brl=Decimal("1000.00"),
            priced_card_count=100,
            total_card_count=200,
        )
        repo.upsert_portfolio_snapshot(
            user_id="2",
            snapshot_date=date(2026, 8, 27),
            total_value_brl=Decimal("2000.00"),
            priced_card_count=150,
            total_card_count=250,
        )

        snapshots = repo.get_portfolio_snapshots("1", days=30)
        assert len(snapshots) == 1
        assert all(s.user_id == "1" for s in snapshots)
