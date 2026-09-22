"""Tests for F168-T01: Daily Price Snapshot Service."""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

import pytest
from sqlalchemy.orm import Session

from src.collectors.price_snapshot import (
    MAX_BACKFILL_DAYS,
    SNAPSHOT_SOURCE,
    backfill_snapshots,
    run_daily_snapshot,
)
from src.database.models import Base, PriceObservationRow
from src.database.repository import Repository


@pytest.fixture
def repo():
    r = Repository(db_url="sqlite:///:memory:")
    Base.metadata.create_all(r.engine)
    return r


def _insert_observation(
    repo: Repository,
    *,
    source: str,
    external_id: str,
    observed_at: date,
    median_price: Decimal | None = None,
) -> None:
    """Helper to insert a raw price observation."""
    with Session(repo.engine) as session:
        row = PriceObservationRow(
            source=source,
            external_id=external_id,
            observed_at=observed_at,
            median_price=median_price,
        )
        session.add(row)
        session.commit()


class TestRunDailySnapshot:
    """Tests for run_daily_snapshot()."""

    def test_happy_path_creates_observations(self, repo):
        """DB with 3 cards having prices -> snapshot creates 3 observations."""
        today = date.today()
        yesterday = today - timedelta(days=1)

        _insert_observation(
            repo,
            source="liga",
            external_id="liga_1",
            observed_at=yesterday,
            median_price=Decimal("10.00"),
        )
        _insert_observation(
            repo,
            source="liga",
            external_id="liga_2",
            observed_at=yesterday,
            median_price=Decimal("20.00"),
        )
        _insert_observation(
            repo,
            source="myp",
            external_id="myp_3",
            observed_at=yesterday,
            median_price=Decimal("30.00"),
        )

        count = run_daily_snapshot(repo)

        assert count == 3

        # Verify the observations were created with correct source and date
        with Session(repo.engine) as session:
            snapshots = (
                session.query(PriceObservationRow)
                .filter(PriceObservationRow.source == SNAPSHOT_SOURCE)
                .all()
            )
            assert len(snapshots) == 3
            for snap in snapshots:
                assert snap.observed_at == today
                assert snap.source == SNAPSHOT_SOURCE
                assert snap.median_price is not None
                # Only median_price should be set
                assert snap.tcg_price is None
                assert snap.last_sold_price is None
                assert snap.quantity_available is None

    def test_idempotency_second_run_returns_zero(self, repo):
        """Running twice on the same day -> second run returns 0."""
        yesterday = date.today() - timedelta(days=1)

        _insert_observation(
            repo,
            source="liga",
            external_id="liga_1",
            observed_at=yesterday,
            median_price=Decimal("10.00"),
        )
        _insert_observation(
            repo,
            source="liga",
            external_id="liga_2",
            observed_at=yesterday,
            median_price=Decimal("25.00"),
        )

        first_count = run_daily_snapshot(repo)
        assert first_count == 2

        second_count = run_daily_snapshot(repo)
        assert second_count == 0

    def test_no_prices_returns_zero(self, repo):
        """Empty DB -> returns 0, no errors."""
        count = run_daily_snapshot(repo)
        assert count == 0

    def test_mixed_prices_only_priced_cards_get_snapshots(self, repo):
        """Cards with null median_price should NOT get snapshots."""
        yesterday = date.today() - timedelta(days=1)

        # Card with price
        _insert_observation(
            repo,
            source="liga",
            external_id="liga_1",
            observed_at=yesterday,
            median_price=Decimal("15.00"),
        )
        # Card without price (null median_price)
        _insert_observation(
            repo, source="liga", external_id="liga_2", observed_at=yesterday, median_price=None
        )

        count = run_daily_snapshot(repo)

        assert count == 1

        with Session(repo.engine) as session:
            snapshots = (
                session.query(PriceObservationRow)
                .filter(PriceObservationRow.source == SNAPSHOT_SOURCE)
                .all()
            )
            assert len(snapshots) == 1
            assert snapshots[0].external_id == "liga_1"
            assert snapshots[0].median_price == Decimal("15.00")

    def test_multiple_sources_picks_latest_by_date(self, repo):
        """Card with observations from different sources and dates -> picks latest."""
        today = date.today()
        two_days_ago = today - timedelta(days=2)
        yesterday = today - timedelta(days=1)

        # Older observation from liga
        _insert_observation(
            repo,
            source="liga",
            external_id="card_1",
            observed_at=two_days_ago,
            median_price=Decimal("10.00"),
        )
        # Newer observation from myp (same external_id)
        _insert_observation(
            repo,
            source="myp",
            external_id="card_1",
            observed_at=yesterday,
            median_price=Decimal("12.50"),
        )

        count = run_daily_snapshot(repo)
        assert count == 1

        with Session(repo.engine) as session:
            snap = (
                session.query(PriceObservationRow)
                .filter(PriceObservationRow.source == SNAPSHOT_SOURCE)
                .one()
            )
            # Should use the latest price (12.50 from yesterday, not 10.00 from two days ago)
            assert snap.median_price == Decimal("12.50")
            assert snap.external_id == "card_1"


class TestGetAllLatestPrices:
    """Tests for Repository.get_all_latest_prices()."""

    def test_returns_latest_price_per_external_id(self, repo):
        """Multiple observations for same card -> returns the latest."""
        today = date.today()
        yesterday = today - timedelta(days=1)

        _insert_observation(
            repo,
            source="liga",
            external_id="liga_1",
            observed_at=yesterday,
            median_price=Decimal("10.00"),
        )
        _insert_observation(
            repo,
            source="liga",
            external_id="liga_1",
            observed_at=today,
            median_price=Decimal("12.00"),
        )

        results = repo.get_all_latest_prices()

        assert len(results) == 1
        source, ext_id, price = results[0]
        assert ext_id == "liga_1"
        assert price == Decimal("12.00")

    def test_excludes_null_median_price(self, repo):
        """Observations with null median_price are excluded."""
        yesterday = date.today() - timedelta(days=1)

        _insert_observation(
            repo, source="liga", external_id="liga_1", observed_at=yesterday, median_price=None
        )

        results = repo.get_all_latest_prices()
        assert results == []

    def test_empty_db_returns_empty_list(self, repo):
        """No observations -> empty list."""
        results = repo.get_all_latest_prices()
        assert results == []


class TestBackfillSnapshots:
    """Tests for backfill_snapshots()."""

    def test_happy_path_creates_observations(self, repo):
        """Cards with prices but no snapshots -> creates observations."""
        yesterday = date.today() - timedelta(days=1)

        for i in range(1, 6):
            _insert_observation(
                repo,
                source="liga",
                external_id=f"liga_{i}",
                observed_at=yesterday,
                median_price=Decimal(f"{i * 10}.00"),
            )

        count = backfill_snapshots(repo, days=1)
        assert count == 5

        with Session(repo.engine) as session:
            snapshots = (
                session.query(PriceObservationRow)
                .filter(PriceObservationRow.source == SNAPSHOT_SOURCE)
                .all()
            )
            assert len(snapshots) == 5
            for snap in snapshots:
                assert snap.observed_at == date.today()

    def test_partial_backfill_skips_existing(self, repo):
        """Cards that already have snapshots are skipped."""
        yesterday = date.today() - timedelta(days=1)

        for i in range(1, 6):
            _insert_observation(
                repo,
                source="liga",
                external_id=f"liga_{i}",
                observed_at=yesterday,
                median_price=Decimal(f"{i * 10}.00"),
            )

        # Pre-create snapshots for 2 cards
        _insert_observation(
            repo,
            source=SNAPSHOT_SOURCE,
            external_id="liga_1",
            observed_at=date.today(),
            median_price=Decimal("10.00"),
        )
        _insert_observation(
            repo,
            source=SNAPSHOT_SOURCE,
            external_id="liga_2",
            observed_at=date.today(),
            median_price=Decimal("20.00"),
        )

        count = backfill_snapshots(repo, days=1)
        assert count == 3

    def test_multi_day_creates_multiple_per_card(self, repo):
        """days=3 creates 3 observations per card."""
        yesterday = date.today() - timedelta(days=1)

        _insert_observation(
            repo,
            source="liga",
            external_id="liga_1",
            observed_at=yesterday,
            median_price=Decimal("10.00"),
        )
        _insert_observation(
            repo,
            source="liga",
            external_id="liga_2",
            observed_at=yesterday,
            median_price=Decimal("20.00"),
        )

        count = backfill_snapshots(repo, days=3)
        assert count == 6  # 2 cards x 3 days

        today = date.today()
        with Session(repo.engine) as session:
            snapshots = (
                session.query(PriceObservationRow)
                .filter(PriceObservationRow.source == SNAPSHOT_SOURCE)
                .order_by(
                    PriceObservationRow.external_id,
                    PriceObservationRow.observed_at,
                )
                .all()
            )
            assert len(snapshots) == 6

            # Verify dates: today, today-1, today-2 for each card
            expected_dates = {today - timedelta(days=d) for d in range(3)}
            liga_1_dates = {s.observed_at for s in snapshots if s.external_id == "liga_1"}
            liga_2_dates = {s.observed_at for s in snapshots if s.external_id == "liga_2"}
            assert liga_1_dates == expected_dates
            assert liga_2_dates == expected_dates

    def test_days_capped_at_max(self, repo, caplog):
        """days > MAX_BACKFILL_DAYS gets capped with a warning."""
        import logging

        yesterday = date.today() - timedelta(days=1)
        _insert_observation(
            repo,
            source="liga",
            external_id="liga_1",
            observed_at=yesterday,
            median_price=Decimal("10.00"),
        )

        with caplog.at_level(logging.WARNING, logger="src.collectors.price_snapshot"):
            count = backfill_snapshots(repo, days=100)

        # Should have capped at MAX_BACKFILL_DAYS
        assert count == MAX_BACKFILL_DAYS  # 1 card x 90 days
        assert "capping" in caplog.text.lower() or "exceeds" in caplog.text.lower()

    def test_idempotency_second_run_zero(self, repo):
        """Running backfill twice -> second run creates 0."""
        yesterday = date.today() - timedelta(days=1)

        _insert_observation(
            repo,
            source="liga",
            external_id="liga_1",
            observed_at=yesterday,
            median_price=Decimal("10.00"),
        )

        first = backfill_snapshots(repo, days=1)
        assert first == 1

        second = backfill_snapshots(repo, days=1)
        assert second == 0

    def test_no_priced_cards_returns_zero(self, repo):
        """Empty DB -> returns 0."""
        count = backfill_snapshots(repo, days=1)
        assert count == 0


class TestGetExternalIdsWithSource:
    """Tests for Repository.get_external_ids_with_source()."""

    def test_returns_matching_external_ids(self, repo):
        """Returns external_ids that have observations for the given source."""
        yesterday = date.today() - timedelta(days=1)

        _insert_observation(
            repo,
            source="daily_snapshot",
            external_id="card_1",
            observed_at=yesterday,
            median_price=Decimal("10.00"),
        )
        _insert_observation(
            repo,
            source="daily_snapshot",
            external_id="card_2",
            observed_at=yesterday,
            median_price=Decimal("20.00"),
        )
        _insert_observation(
            repo,
            source="liga",
            external_id="card_3",
            observed_at=yesterday,
            median_price=Decimal("30.00"),
        )

        result = repo.get_external_ids_with_source("daily_snapshot")
        assert result == {"card_1", "card_2"}

    def test_empty_for_nonexistent_source(self, repo):
        """No observations for the source -> empty set."""
        result = repo.get_external_ids_with_source("nonexistent")
        assert result == set()
