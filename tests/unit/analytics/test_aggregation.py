"""Tests for src/analytics/aggregation.py — pure aggregation functions."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from src.analytics.aggregation import (
    PERIOD_MAP,
    aggregate_series,
    aggregate_weekly,
    compute_price_change_summary,
    determine_resolution,
)
from src.api.schemas.cards import PriceObservation

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _obs(
    d: date,
    median: Decimal | None = Decimal("10.00"),
    tcg: Decimal | None = None,
    last_sold: Decimal | None = None,
    qty: int | None = 5,
    currency: str = "BRL",
) -> PriceObservation:
    return PriceObservation(
        observed_at=d,
        median_price=median,
        tcg_price=tcg,
        last_sold_price=last_sold,
        quantity_available=qty,
        currency=currency,
    )


@pytest.fixture()
def two_weeks_observations() -> list[PriceObservation]:
    """14 daily observations spanning 2 ISO weeks (Mon-Sun each)."""
    # 2026-01-05 is a Monday (ISO week 2026-W02)
    return [_obs(date(2026, 1, 5 + i), median=Decimal(str(10 + i))) for i in range(14)]


# ---------------------------------------------------------------------------
# determine_resolution
# ---------------------------------------------------------------------------


class TestDetermineResolution:
    @pytest.mark.parametrize("period", ["24h", "7d", "30d", "90d"])
    def test_daily_for_short_periods(self, period: str) -> None:
        assert determine_resolution(period) == "daily"

    @pytest.mark.parametrize("period", ["180d", "1y"])
    def test_weekly_for_long_periods(self, period: str) -> None:
        assert determine_resolution(period) == "weekly"

    def test_unknown_period_returns_daily(self) -> None:
        assert determine_resolution("unknown") == "daily"


# ---------------------------------------------------------------------------
# aggregate_weekly
# ---------------------------------------------------------------------------


class TestAggregateWeekly:
    def test_groups_by_iso_week(self, two_weeks_observations) -> None:
        result = aggregate_weekly(two_weeks_observations)
        assert len(result) == 2

        # First week: days 0-6 (Mon Jan 5 - Sun Jan 11), prices 10-16
        # Average: (10+11+12+13+14+15+16)/7 = 13.0
        assert result[0].observed_at == date(2026, 1, 11)  # last date in week
        assert float(result[0].median_price) == pytest.approx(13.0, abs=0.01)

        # Second week: days 7-13 (Mon Jan 12 - Sun Jan 18), prices 17-23
        # Average: (17+18+19+20+21+22+23)/7 = 20.0
        assert result[1].observed_at == date(2026, 1, 18)
        assert float(result[1].median_price) == pytest.approx(20.0, abs=0.01)

    def test_handles_none_prices(self) -> None:
        observations = [
            _obs(date(2026, 1, 5), median=Decimal("10.00")),
            _obs(date(2026, 1, 6), median=None),
            _obs(date(2026, 1, 7), median=Decimal("20.00")),
        ]
        result = aggregate_weekly(observations)
        assert len(result) == 1
        # Average of non-None: (10 + 20) / 2 = 15
        assert float(result[0].median_price) == pytest.approx(15.0, abs=0.01)

    def test_all_none_prices(self) -> None:
        observations = [
            _obs(date(2026, 1, 5), median=None),
            _obs(date(2026, 1, 6), median=None),
        ]
        result = aggregate_weekly(observations)
        assert len(result) == 1
        assert result[0].median_price is None

    def test_empty_input(self) -> None:
        result = aggregate_weekly([])
        assert result == []

    def test_single_observation(self) -> None:
        observations = [_obs(date(2026, 1, 5))]
        result = aggregate_weekly(observations)
        assert len(result) == 1
        assert result[0].median_price == Decimal("10.00")
        assert result[0].observed_at == date(2026, 1, 5)

    def test_preserves_currency(self) -> None:
        observations = [
            _obs(date(2026, 1, 5), currency="USD"),
            _obs(date(2026, 1, 6), currency="USD"),
        ]
        result = aggregate_weekly(observations)
        assert result[0].currency == "USD"

    def test_quantity_uses_last_non_none(self) -> None:
        observations = [
            _obs(date(2026, 1, 5), qty=10),
            _obs(date(2026, 1, 6), qty=None),
            _obs(date(2026, 1, 7), qty=20),
        ]
        result = aggregate_weekly(observations)
        assert result[0].quantity_available == 20

    def test_quantity_all_none(self) -> None:
        observations = [
            _obs(date(2026, 1, 5), qty=None),
            _obs(date(2026, 1, 6), qty=None),
        ]
        result = aggregate_weekly(observations)
        assert result[0].quantity_available is None


# ---------------------------------------------------------------------------
# aggregate_series
# ---------------------------------------------------------------------------


class TestAggregateSeries:
    def test_daily_passthrough(self) -> None:
        observations = [_obs(date(2026, 1, 5)), _obs(date(2026, 1, 6))]
        result, resolution = aggregate_series(observations, "30d")
        assert resolution == "daily"
        assert result == observations  # Same objects, no transformation

    def test_weekly_for_long_period(self, two_weeks_observations) -> None:
        result, resolution = aggregate_series(two_weeks_observations, "180d")
        assert resolution == "weekly"
        assert len(result) == 2  # Two weeks aggregated

    def test_1y_triggers_weekly(self, two_weeks_observations) -> None:
        result, resolution = aggregate_series(two_weeks_observations, "1y")
        assert resolution == "weekly"


# ---------------------------------------------------------------------------
# compute_price_change_summary
# ---------------------------------------------------------------------------


class TestComputePriceChangeSummary:
    def test_positive_change(self) -> None:
        observations = [
            _obs(date(2026, 1, 5), median=Decimal("10.00")),
            _obs(date(2026, 1, 12), median=Decimal("15.00")),
        ]
        summary = compute_price_change_summary(observations, "7d", "daily")
        assert summary.period == "7d"
        assert summary.price_start == 10.00
        assert summary.price_end == 15.00
        assert summary.absolute_change == 5.00
        assert summary.percent_change == 50.00
        assert summary.data_points == 2
        assert summary.resolution == "daily"

    def test_negative_change(self) -> None:
        observations = [
            _obs(date(2026, 1, 5), median=Decimal("20.00")),
            _obs(date(2026, 1, 12), median=Decimal("15.00")),
        ]
        summary = compute_price_change_summary(observations, "7d", "daily")
        assert summary.absolute_change == -5.00
        assert summary.percent_change == -25.00

    def test_no_data(self) -> None:
        summary = compute_price_change_summary([], "30d", "daily")
        assert summary.price_start is None
        assert summary.price_end is None
        assert summary.absolute_change is None
        assert summary.percent_change is None
        assert summary.data_points == 0

    def test_single_point(self) -> None:
        observations = [_obs(date(2026, 1, 5), median=Decimal("10.00"))]
        summary = compute_price_change_summary(observations, "24h", "daily")
        assert summary.price_start == 10.00
        assert summary.price_end == 10.00
        assert summary.absolute_change == 0.00
        assert summary.percent_change == 0.00
        assert summary.data_points == 1

    def test_none_start_price(self) -> None:
        observations = [
            _obs(date(2026, 1, 5), median=None),
            _obs(date(2026, 1, 12), median=Decimal("15.00")),
        ]
        summary = compute_price_change_summary(observations, "7d", "daily")
        assert summary.price_start is None
        assert summary.price_end == 15.00
        assert summary.absolute_change is None
        assert summary.percent_change is None

    def test_none_end_price(self) -> None:
        observations = [
            _obs(date(2026, 1, 5), median=Decimal("10.00")),
            _obs(date(2026, 1, 12), median=None),
        ]
        summary = compute_price_change_summary(observations, "7d", "daily")
        assert summary.price_start == 10.00
        assert summary.price_end is None
        assert summary.absolute_change is None

    def test_zero_start_price(self) -> None:
        observations = [
            _obs(date(2026, 1, 5), median=Decimal("0.00")),
            _obs(date(2026, 1, 12), median=Decimal("15.00")),
        ]
        summary = compute_price_change_summary(observations, "7d", "daily")
        assert summary.absolute_change == 15.00
        assert summary.percent_change is None  # Cannot divide by zero

    def test_resolution_preserved(self) -> None:
        observations = [_obs(date(2026, 1, 5))]
        summary = compute_price_change_summary(observations, "180d", "weekly")
        assert summary.resolution == "weekly"


# ---------------------------------------------------------------------------
# PERIOD_MAP
# ---------------------------------------------------------------------------


class TestPeriodMap:
    def test_all_periods_present(self) -> None:
        expected = {"24h", "7d", "30d", "90d", "180d", "1y"}
        assert set(PERIOD_MAP.keys()) == expected

    def test_3y_not_present(self) -> None:
        assert "3y" not in PERIOD_MAP
