"""Tests for F176-T05: carry-forward limit + honest forward-fill backfill."""

from __future__ import annotations

import logging
from datetime import date, timedelta
from decimal import Decimal

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from src.collectors import price_snapshot
from src.collectors.price_snapshot import (
    BACKFILL_SOURCE,
    MAX_BACKFILL_DAYS,
    MAX_CARRY_FORWARD_DAYS,
    SNAPSHOT_SOURCE,
    _latest_real_prices,
    backfill_snapshots,
    run_daily_snapshot,
)
from src.database.models import Base, PriceObservationRow
from src.database.repository import Repository

TODAY = date(2026, 9, 24)


def _d(offset: int) -> date:
    return TODAY - timedelta(days=offset)


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
    with Session(repo.engine) as session:
        session.add(
            PriceObservationRow(
                source=source,
                external_id=external_id,
                observed_at=observed_at,
                median_price=median_price,
            )
        )
        session.commit()


def _rows(repo: Repository, source: str) -> list[tuple[str, date, Decimal]]:
    stmt = (
        select(
            PriceObservationRow.external_id,
            PriceObservationRow.observed_at,
            PriceObservationRow.median_price,
        )
        .where(PriceObservationRow.source == source)
        .order_by(PriceObservationRow.external_id, PriceObservationRow.observed_at)
    )
    with Session(repo.engine) as session:
        return [tuple(r) for r in session.execute(stmt).all()]


def _count_all(repo: Repository) -> int:
    with Session(repo.engine) as session:
        return session.query(PriceObservationRow).count()


# ── _latest_real_prices ────────────────────────────────────────────


class TestLatestRealPrices:
    def test_ignores_synthetic_sources_and_null_prices(self, repo):
        _insert_observation(
            repo,
            source="liga",
            external_id="liga_7",
            observed_at=_d(5),
            median_price=Decimal("5.00"),
        )
        _insert_observation(
            repo, source="liga", external_id="liga_7", observed_at=_d(3), median_price=None
        )
        _insert_observation(
            repo,
            source=SNAPSHOT_SOURCE,
            external_id="liga_7",
            observed_at=_d(1),
            median_price=Decimal("9.00"),
        )
        _insert_observation(
            repo,
            source=BACKFILL_SOURCE,
            external_id="liga_7",
            observed_at=_d(2),
            median_price=Decimal("8.00"),
        )

        assert _latest_real_prices(repo) == [("liga_7", _d(5), Decimal("5.00"))]

    def test_since_until_bounds(self, repo):
        _insert_observation(
            repo,
            source="liga",
            external_id="liga_1",
            observed_at=_d(40),
            median_price=Decimal("1.00"),
        )
        _insert_observation(
            repo,
            source="liga",
            external_id="liga_2",
            observed_at=TODAY + timedelta(days=1),
            median_price=Decimal("2.00"),
        )
        assert _latest_real_prices(repo, since=_d(30), until=TODAY) == []
        assert len(_latest_real_prices(repo)) == 2

    def test_empty_db(self, repo):
        assert _latest_real_prices(repo) == []


# ── run_daily_snapshot ─────────────────────────────────────────────


class TestRunDailySnapshotCarryForward:
    def test_happy_real_three_days_ago(self, repo):
        _insert_observation(
            repo,
            source="liga",
            external_id="liga_7",
            observed_at=_d(3),
            median_price=Decimal("12.34"),
        )

        assert run_daily_snapshot(repo, today=TODAY) == 1
        assert _rows(repo, SNAPSHOT_SOURCE) == [("liga_7", TODAY, Decimal("12.34"))]

    def test_real_31_days_ago_no_snapshot(self, repo):
        _insert_observation(
            repo,
            source="liga",
            external_id="liga_7",
            observed_at=_d(MAX_CARRY_FORWARD_DAYS + 1),
            median_price=Decimal("1.00"),
        )
        assert run_daily_snapshot(repo, today=TODAY) == 0
        assert _rows(repo, SNAPSHOT_SOURCE) == []

    def test_real_exactly_30_days_ago_boundary(self, repo):
        _insert_observation(
            repo,
            source="liga",
            external_id="liga_7",
            observed_at=_d(MAX_CARRY_FORWARD_DAYS),
            median_price=Decimal("1.00"),
        )
        assert run_daily_snapshot(repo, today=TODAY) == 1

    def test_previous_snapshot_is_not_real(self, repo):
        _insert_observation(
            repo,
            source="liga",
            external_id="liga_7",
            observed_at=_d(40),
            median_price=Decimal("1.00"),
        )
        _insert_observation(
            repo,
            source=SNAPSHOT_SOURCE,
            external_id="liga_7",
            observed_at=_d(1),
            median_price=Decimal("1.00"),
        )
        assert run_daily_snapshot(repo, today=TODAY) == 0

    def test_backfill_row_is_not_real(self, repo):
        _insert_observation(
            repo,
            source=BACKFILL_SOURCE,
            external_id="liga_7",
            observed_at=_d(1),
            median_price=Decimal("1.00"),
        )
        assert run_daily_snapshot(repo, today=TODAY) == 0

    def test_real_today_skips_snapshot(self, repo):
        _insert_observation(
            repo,
            source="liga",
            external_id="liga_7",
            observed_at=TODAY,
            median_price=Decimal("3.00"),
        )
        _insert_observation(
            repo,
            source="liga",
            external_id="liga_8",
            observed_at=_d(2),
            median_price=Decimal("4.00"),
        )
        assert run_daily_snapshot(repo, today=TODAY) == 1
        assert _rows(repo, SNAPSHOT_SOURCE) == [("liga_8", TODAY, Decimal("4.00"))]

    def test_twice_same_day_second_returns_zero(self, repo):
        _insert_observation(
            repo,
            source="liga",
            external_id="liga_7",
            observed_at=_d(1),
            median_price=Decimal("3.00"),
        )
        assert run_daily_snapshot(repo, today=TODAY) == 1
        assert run_daily_snapshot(repo, today=TODAY) == 0

    def test_null_price_real_ignored_uses_older_price(self, repo):
        _insert_observation(
            repo,
            source="liga",
            external_id="liga_7",
            observed_at=_d(5),
            median_price=Decimal("7.00"),
        )
        _insert_observation(
            repo, source="liga", external_id="liga_7", observed_at=_d(1), median_price=None
        )
        assert run_daily_snapshot(repo, today=TODAY) == 1
        assert _rows(repo, SNAPSHOT_SOURCE) == [("liga_7", TODAY, Decimal("7.00"))]

    def test_empty_db(self, repo):
        assert run_daily_snapshot(repo, today=TODAY) == 0

    def test_defaults_to_date_today(self, repo):
        _insert_observation(
            repo,
            source="liga",
            external_id="liga_7",
            observed_at=date.today() - timedelta(days=1),
            median_price=Decimal("1.00"),
        )
        assert run_daily_snapshot(repo) == 1
        assert _rows(repo, SNAPSHOT_SOURCE)[0][1] == date.today()


# ── backfill_snapshots ─────────────────────────────────────────────


class TestBackfillForwardFill:
    def test_forward_fill_uses_last_real_at_or_before_day(self, repo):
        _insert_observation(
            repo,
            source="liga",
            external_id="liga_7",
            observed_at=_d(10),
            median_price=Decimal("10.00"),
        )
        _insert_observation(
            repo,
            source="liga",
            external_id="liga_7",
            observed_at=_d(4),
            median_price=Decimal("20.00"),
        )

        count = backfill_snapshots(repo, days=15, today=TODAY)

        expected = [("liga_7", _d(o), Decimal("10.00")) for o in range(9, 4, -1)] + [
            ("liga_7", _d(o), Decimal("20.00")) for o in range(3, -1, -1)
        ]
        assert count == 9
        assert _rows(repo, BACKFILL_SOURCE) == expected
        # Nothing before the first real observation.
        assert all(d > _d(10) for _, d, _ in _rows(repo, BACKFILL_SOURCE))

    def test_backfill_rows_carry_marker_not_daily_snapshot(self, repo):
        """Governance: forward-filled rows are distinguishable from real snapshots."""
        _insert_observation(
            repo,
            source="liga",
            external_id="liga_7",
            observed_at=_d(2),
            median_price=Decimal("1.00"),
        )
        count = backfill_snapshots(repo, days=3, today=TODAY)

        assert count == 2
        assert BACKFILL_SOURCE == "daily_snapshot_backfill"
        assert _rows(repo, SNAPSHOT_SOURCE) == []
        assert {d for _, d, _ in _rows(repo, BACKFILL_SOURCE)} == {_d(1), TODAY}

    def test_id_with_old_daily_snapshot_still_filled(self, repo):
        """Regression H6: having any daily_snapshot no longer skips the id."""
        _insert_observation(
            repo,
            source="liga",
            external_id="liga_7",
            observed_at=_d(5),
            median_price=Decimal("5.00"),
        )
        _insert_observation(
            repo,
            source=SNAPSHOT_SOURCE,
            external_id="liga_7",
            observed_at=_d(3),
            median_price=Decimal("5.00"),
        )

        count = backfill_snapshots(repo, days=6, today=TODAY)

        # D-4, D-2, D-1, D (D-5 real, D-3 already has a snapshot).
        assert count == 4
        assert {d for _, d, _ in _rows(repo, BACKFILL_SOURCE)} == {_d(4), _d(2), _d(1), TODAY}

    def test_idempotent_second_run_zero(self, repo):
        _insert_observation(
            repo,
            source="liga",
            external_id="liga_7",
            observed_at=_d(5),
            median_price=Decimal("5.00"),
        )
        assert backfill_snapshots(repo, days=10, today=TODAY) == 5
        assert backfill_snapshots(repo, days=10, today=TODAY) == 0

    def test_dry_run_same_count_no_writes(self, repo):
        _insert_observation(
            repo,
            source="liga",
            external_id="liga_7",
            observed_at=_d(10),
            median_price=Decimal("10.00"),
        )
        _insert_observation(
            repo,
            source="myp",
            external_id="myp_1",
            observed_at=_d(3),
            median_price=Decimal("2.00"),
        )
        before = _count_all(repo)

        dry = backfill_snapshots(repo, days=15, dry_run=True, today=TODAY)

        assert _count_all(repo) == before
        assert dry == backfill_snapshots(repo, days=15, today=TODAY)
        assert dry == 10 + 3

    def test_respects_carry_forward_limit(self, repo):
        _insert_observation(
            repo,
            source="liga",
            external_id="liga_7",
            observed_at=_d(60),
            median_price=Decimal("6.00"),
        )

        count = backfill_snapshots(repo, days=90, today=TODAY)

        dates = [d for _, d, _ in _rows(repo, BACKFILL_SOURCE)]
        assert count == MAX_CARRY_FORWARD_DAYS
        assert min(dates) == _d(59)
        assert max(dates) == _d(30)

    def test_real_before_window_still_fills_start_of_window(self, repo):
        """The last real before the window is the price source for early days."""
        _insert_observation(
            repo,
            source="liga",
            external_id="liga_7",
            observed_at=_d(20),
            median_price=Decimal("3.00"),
        )
        count = backfill_snapshots(repo, days=5, today=TODAY)
        assert count == 5
        assert {p for _, _, p in _rows(repo, BACKFILL_SOURCE)} == {Decimal("3.00")}

    def test_real_too_old_for_window_ignored(self, repo):
        _insert_observation(
            repo,
            source="liga",
            external_id="liga_7",
            observed_at=_d(40),
            median_price=Decimal("3.00"),
        )
        assert backfill_snapshots(repo, days=5, today=TODAY) == 0

    def test_null_price_real_ignored(self, repo):
        _insert_observation(
            repo, source="liga", external_id="liga_7", observed_at=_d(3), median_price=None
        )
        _insert_observation(
            repo,
            source="liga",
            external_id="liga_8",
            observed_at=_d(6),
            median_price=Decimal("8.00"),
        )
        _insert_observation(
            repo, source="liga", external_id="liga_8", observed_at=_d(3), median_price=None
        )

        count = backfill_snapshots(repo, days=10, today=TODAY)

        rows = _rows(repo, BACKFILL_SOURCE)
        assert {e for e, _, _ in rows} == {"liga_8"}
        # D-3 already has an observation (null price) -> skipped; price stays 8.00.
        assert count == 5
        assert {p for _, _, p in rows} == {Decimal("8.00")}

    def test_snapshot_rows_never_used_as_price_source(self, repo):
        _insert_observation(
            repo,
            source=SNAPSHOT_SOURCE,
            external_id="liga_7",
            observed_at=_d(3),
            median_price=Decimal("1.00"),
        )
        assert backfill_snapshots(repo, days=10, today=TODAY) == 0

    def test_same_day_multiple_real_last_inserted_wins(self, repo):
        _insert_observation(
            repo,
            source="liga",
            external_id="card_1",
            observed_at=_d(2),
            median_price=Decimal("1.00"),
        )
        _insert_observation(
            repo,
            source="myp",
            external_id="card_1",
            observed_at=_d(2),
            median_price=Decimal("2.00"),
        )
        assert backfill_snapshots(repo, days=2, today=TODAY) == 2
        assert {p for _, _, p in _rows(repo, BACKFILL_SOURCE)} == {Decimal("2.00")}

    def test_paginates_external_ids(self, repo, monkeypatch):
        monkeypatch.setattr(price_snapshot, "BATCH_SIZE", 2)
        for i in range(5):
            _insert_observation(
                repo,
                source="liga",
                external_id=f"liga_{i}",
                observed_at=_d(1),
                median_price=Decimal("1.00"),
            )
        assert backfill_snapshots(repo, days=2, today=TODAY) == 5

    def test_days_zero_raises(self, repo):
        with pytest.raises(ValueError):
            backfill_snapshots(repo, days=0, today=TODAY)

    def test_days_negative_raises(self, repo):
        with pytest.raises(ValueError):
            backfill_snapshots(repo, days=-3, today=TODAY)

    def test_days_capped_with_warning(self, repo, caplog):
        _insert_observation(
            repo,
            source="liga",
            external_id="liga_7",
            observed_at=_d(100),
            median_price=Decimal("1.00"),
        )
        _insert_observation(
            repo,
            source="liga",
            external_id="liga_8",
            observed_at=_d(89),
            median_price=Decimal("1.00"),
        )
        with caplog.at_level(logging.WARNING, logger="src.collectors.price_snapshot"):
            count = backfill_snapshots(repo, days=120, today=TODAY)

        assert "capping" in caplog.text.lower()
        # Window capped to D-89..D: liga_7 (D-100) only reaches D-70 -> 20 days
        # inside the window (D-89..D-70); liga_8 fills D-88..D-59 -> 30 days.
        assert count == 20 + MAX_CARRY_FORWARD_DAYS
        assert min(d for _, d, _ in _rows(repo, BACKFILL_SOURCE)) >= _d(MAX_BACKFILL_DAYS - 1)

    def test_empty_db(self, repo):
        assert backfill_snapshots(repo, days=5, today=TODAY) == 0
        assert backfill_snapshots(repo, days=5, dry_run=True, today=TODAY) == 0

    def test_then_daily_snapshot_is_noop_today(self, repo):
        _insert_observation(
            repo,
            source="liga",
            external_id="liga_7",
            observed_at=_d(2),
            median_price=Decimal("1.00"),
        )
        backfill_snapshots(repo, days=3, today=TODAY)
        assert run_daily_snapshot(repo, today=TODAY) == 0
