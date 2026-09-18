"""Tests for src/analytics/indicators.py — all analytics indicator functions."""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

import pytest

from src.analytics.indicators import (
    compute_all_moving_averages,
    compute_card_analytics,
    compute_momentum,
    compute_moving_average,
    compute_price_extremes,
    compute_volatility,
)
from src.domain.models import (
    CardAnalytics,
    HistoricalPrice,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _hp(
    day_offset: int,
    median: Decimal | None = None,
    tcg: Decimal | None = None,
    last_sold: Decimal | None = None,
    qty: int | None = None,
    base_date: date | None = None,
) -> HistoricalPrice:
    """Build a HistoricalPrice with date = base_date + day_offset."""
    if base_date is None:
        base_date = date(2026, 1, 1)
    return HistoricalPrice(
        source="myp",
        external_id="123",
        observed_at=base_date + timedelta(days=day_offset),
        median_price=median,
        tcg_price=tcg,
        last_sold_price=last_sold,
        quantity_available=qty,
    )


def _make_prices(
    values: list[Decimal | None],
    base_date: date | None = None,
) -> list[HistoricalPrice]:
    """Build a list of HistoricalPrice with daily observations."""
    return [_hp(i, median=v, base_date=base_date) for i, v in enumerate(values)]


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def thirty_daily_prices() -> list[HistoricalPrice]:
    """30 daily prices: 10.00, 10.50, 11.00, ..., incrementing by 0.50."""
    return _make_prices([Decimal("10.00") + Decimal("0.50") * i for i in range(30)])


@pytest.fixture
def constant_prices() -> list[HistoricalPrice]:
    """10 daily prices all equal to 5.00."""
    return _make_prices([Decimal("5.00")] * 10)


@pytest.fixture
def prices_with_nones() -> list[HistoricalPrice]:
    """10 prices with some None values."""
    values: list[Decimal | None] = [
        Decimal("10.00"),
        None,
        Decimal("12.00"),
        None,
        Decimal("14.00"),
        Decimal("16.00"),
        None,
        Decimal("18.00"),
        Decimal("20.00"),
        Decimal("22.00"),
    ]
    return _make_prices(values)


@pytest.fixture
def empty_prices() -> list[HistoricalPrice]:
    return []


@pytest.fixture
def all_none_prices() -> list[HistoricalPrice]:
    """10 prices where all median_price are None."""
    return _make_prices([None] * 10)


@pytest.fixture
def single_price() -> list[HistoricalPrice]:
    return _make_prices([Decimal("5.00")])


# ---------------------------------------------------------------------------
# compute_moving_average
# ---------------------------------------------------------------------------


class TestComputeMovingAverage:
    def test_ma7_over_10_points(self, constant_prices: list[HistoricalPrice]):
        """MA(7) over 10 data points uses last 7 values."""
        result = compute_moving_average(constant_prices, period=7)
        assert result is not None
        assert result.period == 7
        assert result.value == Decimal("5.00")
        assert result.price_field == "median_price"

    def test_ma7_over_30_points(self, thirty_daily_prices: list[HistoricalPrice]):
        """MA(7) over 30 points uses the last 7."""
        result = compute_moving_average(thirty_daily_prices, period=7)
        assert result is not None
        # Last 7 values: 21.50, 22.00, 22.50, 23.00, 23.50, 24.00, 24.50
        # (indices 23-29 => 10 + 0.5*23=21.50 ... 10+0.5*29=24.50)
        expected = sum(Decimal("10.00") + Decimal("0.50") * i for i in range(23, 30)) / 7
        assert result.value == expected

    def test_ma30_over_30_points(self, thirty_daily_prices: list[HistoricalPrice]):
        """MA(30) over exactly 30 points uses all values."""
        result = compute_moving_average(thirty_daily_prices, period=30)
        assert result is not None
        expected = sum(Decimal("10.00") + Decimal("0.50") * i for i in range(30)) / 30
        assert result.value == expected

    def test_returns_none_insufficient_data(self, single_price: list[HistoricalPrice]):
        """MA returns None when fewer data points than period."""
        assert compute_moving_average(single_price, period=7) is None

    def test_returns_none_empty(self, empty_prices: list[HistoricalPrice]):
        assert compute_moving_average(empty_prices, period=7) is None

    def test_returns_none_all_none(self, all_none_prices: list[HistoricalPrice]):
        assert compute_moving_average(all_none_prices, period=7) is None

    def test_exactly_period_data_points(self):
        """Exactly `period` data points -> MA computable."""
        prices = _make_prices([Decimal("10.00")] * 7)
        result = compute_moving_average(prices, period=7)
        assert result is not None
        assert result.value == Decimal("10.00")

    def test_period_minus_one_returns_none(self):
        """period - 1 data points -> returns None."""
        prices = _make_prices([Decimal("10.00")] * 6)
        assert compute_moving_average(prices, period=7) is None

    def test_skips_none_values(self, prices_with_nones: list[HistoricalPrice]):
        """None values are skipped; only non-None count toward period."""
        # 7 non-None values exist, so MA(7) should work
        result = compute_moving_average(prices_with_nones, period=7)
        assert result is not None

    def test_alternative_price_field(self):
        """Works with tcg_price field."""
        prices = [_hp(i, tcg=Decimal("20.00")) for i in range(10)]
        result = compute_moving_average(prices, period=5, price_field="tcg_price")
        assert result is not None
        assert result.value == Decimal("20.00")
        assert result.price_field == "tcg_price"

    def test_calculated_at_is_last_date(self, thirty_daily_prices: list[HistoricalPrice]):
        result = compute_moving_average(thirty_daily_prices, period=7)
        assert result is not None
        assert result.calculated_at == thirty_daily_prices[-1].observed_at


# ---------------------------------------------------------------------------
# compute_all_moving_averages
# ---------------------------------------------------------------------------


class TestComputeAllMovingAverages:
    def test_default_periods(self, thirty_daily_prices: list[HistoricalPrice]):
        """Default periods [7, 30, 90]; 90 should be skipped (only 30 points)."""
        results = compute_all_moving_averages(thirty_daily_prices)
        assert len(results) == 2
        assert results[0].period == 7
        assert results[1].period == 30

    def test_custom_periods(self, thirty_daily_prices: list[HistoricalPrice]):
        results = compute_all_moving_averages(thirty_daily_prices, periods=[5, 10])
        assert len(results) == 2
        assert results[0].period == 5
        assert results[1].period == 10

    def test_empty_list(self, empty_prices: list[HistoricalPrice]):
        assert compute_all_moving_averages(empty_prices) == []

    def test_all_none(self, all_none_prices: list[HistoricalPrice]):
        assert compute_all_moving_averages(all_none_prices) == []


# ---------------------------------------------------------------------------
# compute_price_extremes
# ---------------------------------------------------------------------------


class TestComputePriceExtremes:
    def test_finds_ath_atl(self, thirty_daily_prices: list[HistoricalPrice]):
        result = compute_price_extremes(thirty_daily_prices)
        assert result is not None
        assert result.ath_price == Decimal("24.50")  # 10 + 0.5*29
        assert result.atl_price == Decimal("10.00")
        assert result.ath_date == date(2026, 1, 30)  # offset 29
        assert result.atl_date == date(2026, 1, 1)  # offset 0

    def test_constant_prices(self, constant_prices: list[HistoricalPrice]):
        """ATH == ATL when all prices are the same."""
        result = compute_price_extremes(constant_prices)
        assert result is not None
        assert result.ath_price == result.atl_price == Decimal("5.00")

    def test_empty_returns_none(self, empty_prices: list[HistoricalPrice]):
        assert compute_price_extremes(empty_prices) is None

    def test_all_none_returns_none(self, all_none_prices: list[HistoricalPrice]):
        assert compute_price_extremes(all_none_prices) is None

    def test_skips_none(self, prices_with_nones: list[HistoricalPrice]):
        result = compute_price_extremes(prices_with_nones)
        assert result is not None
        assert result.ath_price == Decimal("22.00")
        assert result.atl_price == Decimal("10.00")

    def test_alternative_price_field(self):
        prices = [
            _hp(0, tcg=Decimal("5.00")),
            _hp(1, tcg=Decimal("15.00")),
            _hp(2, tcg=Decimal("10.00")),
        ]
        result = compute_price_extremes(prices, price_field="tcg_price")
        assert result is not None
        assert result.ath_price == Decimal("15.00")
        assert result.atl_price == Decimal("5.00")
        assert result.price_field == "tcg_price"


# ---------------------------------------------------------------------------
# compute_volatility
# ---------------------------------------------------------------------------


class TestComputeVolatility:
    def test_known_std_dev(self):
        """Verify against hand-calculated population std_dev."""
        # Values: 2, 4, 4, 4, 5, 5, 7, 9
        # Mean = 5, Variance = 4, StdDev = 2
        values = [Decimal(v) for v in [2, 4, 4, 4, 5, 5, 7, 9]]
        prices = _make_prices(values)
        result = compute_volatility(prices)
        assert result is not None
        assert result.std_dev == Decimal("2")
        # CoV = 2 / 5 = 0.4
        assert result.coefficient_of_variation == Decimal("0.4")

    def test_constant_prices_zero_stddev(self, constant_prices: list[HistoricalPrice]):
        result = compute_volatility(constant_prices)
        assert result is not None
        assert result.std_dev == Decimal("0")
        assert result.coefficient_of_variation == Decimal("0")

    def test_returns_none_fewer_than_2(self, single_price: list[HistoricalPrice]):
        assert compute_volatility(single_price) is None

    def test_returns_none_empty(self, empty_prices: list[HistoricalPrice]):
        assert compute_volatility(empty_prices) is None

    def test_returns_none_all_none(self, all_none_prices: list[HistoricalPrice]):
        assert compute_volatility(all_none_prices) is None

    def test_period_days_filter(self):
        """Only uses data within last N days when period_days is set."""
        # 60 days of data, but only look at last 7
        prices = _make_prices([Decimal("10.00") + Decimal("0.50") * i for i in range(60)])
        result_all = compute_volatility(prices)
        result_7d = compute_volatility(prices, period_days=7)
        assert result_all is not None
        assert result_7d is not None
        # 7-day window should have lower std_dev than full range
        assert result_7d.std_dev < result_all.std_dev

    def test_skips_none(self, prices_with_nones: list[HistoricalPrice]):
        result = compute_volatility(prices_with_nones)
        assert result is not None
        # Should have computed over 7 non-None values
        assert result.std_dev > Decimal("0")

    def test_decimal_arithmetic_no_floats(self):
        """Ensure result types are Decimal, not float."""
        prices = _make_prices([Decimal("10.00"), Decimal("20.00"), Decimal("15.00")])
        result = compute_volatility(prices)
        assert result is not None
        assert isinstance(result.std_dev, Decimal)
        assert isinstance(result.coefficient_of_variation, Decimal)


# ---------------------------------------------------------------------------
# compute_momentum
# ---------------------------------------------------------------------------


class TestComputeMomentum:
    def test_positive_roc(self):
        """Price went from 10 to 12 over 7 days -> RoC = 20%, trend = up."""
        prices = [
            _hp(0, median=Decimal("10.00")),
            _hp(7, median=Decimal("12.00")),
        ]
        result = compute_momentum(prices, period_days=7)
        assert result is not None
        assert result.rate_of_change == Decimal("20.00000000000000000000000000")  # 20%
        assert result.trend_direction == "up"

    def test_negative_roc(self):
        """Price went from 10 to 8 -> RoC = -20%, trend = down."""
        prices = [
            _hp(0, median=Decimal("10.00")),
            _hp(7, median=Decimal("8.00")),
        ]
        result = compute_momentum(prices, period_days=7)
        assert result is not None
        assert result.trend_direction == "down"

    def test_constant_prices_flat(self, constant_prices: list[HistoricalPrice]):
        """Same price -> RoC = 0%, trend = flat."""
        result = compute_momentum(constant_prices, period_days=7)
        assert result is not None
        assert result.rate_of_change == Decimal("0")
        assert result.trend_direction == "flat"

    def test_roc_exactly_1_percent_is_flat(self):
        """RoC exactly 1% -> trend = flat (threshold exclusive)."""
        # past=100, current must be 101 for exactly 1%
        prices = [
            _hp(0, median=Decimal("100.00")),
            _hp(7, median=Decimal("101.00")),
        ]
        result = compute_momentum(prices, period_days=7)
        assert result is not None
        # RoC = (101-100)/100*100 = 1.0
        assert result.rate_of_change == Decimal("1.00")
        assert result.trend_direction == "flat"

    def test_roc_exactly_neg1_percent_is_flat(self):
        """RoC exactly -1% -> trend = flat."""
        prices = [
            _hp(0, median=Decimal("100.00")),
            _hp(7, median=Decimal("99.00")),
        ]
        result = compute_momentum(prices, period_days=7)
        assert result is not None
        assert result.trend_direction == "flat"

    def test_roc_just_above_1_is_up(self):
        """RoC just above 1% -> trend = up."""
        prices = [
            _hp(0, median=Decimal("100.00")),
            _hp(7, median=Decimal("101.01")),
        ]
        result = compute_momentum(prices, period_days=7)
        assert result is not None
        assert result.trend_direction == "up"

    def test_roc_just_below_neg1_is_down(self):
        """RoC just below -1% -> trend = down."""
        prices = [
            _hp(0, median=Decimal("100.00")),
            _hp(7, median=Decimal("98.99")),
        ]
        result = compute_momentum(prices, period_days=7)
        assert result is not None
        assert result.trend_direction == "down"

    def test_returns_none_single_price(self, single_price: list[HistoricalPrice]):
        assert compute_momentum(single_price) is None

    def test_returns_none_empty(self, empty_prices: list[HistoricalPrice]):
        assert compute_momentum(empty_prices) is None

    def test_returns_none_all_none(self, all_none_prices: list[HistoricalPrice]):
        assert compute_momentum(all_none_prices) is None

    def test_skips_none(self, prices_with_nones: list[HistoricalPrice]):
        result = compute_momentum(prices_with_nones, period_days=7)
        assert result is not None

    def test_finds_nearest_past_date(self):
        """When exact period_days ago doesn't exist, uses nearest."""
        prices = [
            _hp(0, median=Decimal("10.00")),
            _hp(3, median=Decimal("11.00")),
            _hp(6, median=Decimal("12.00")),
            _hp(10, median=Decimal("13.00")),
        ]
        # period_days=7, current=day10, target=day3
        # Nearest to day3: day3 (exact match)
        result = compute_momentum(prices, period_days=7)
        assert result is not None
        # (13 - 11) / 11 * 100
        expected_roc = (Decimal("13.00") - Decimal("11.00")) / Decimal("11.00") * Decimal("100")
        assert result.rate_of_change == expected_roc

    def test_past_price_zero_returns_none(self):
        """When past price is zero, returns None (division guard)."""
        prices = [
            _hp(0, median=Decimal("0.00")),
            _hp(7, median=Decimal("10.00")),
        ]
        result = compute_momentum(prices, period_days=7)
        assert result is None

    def test_invalid_price_field_returns_none(self):
        """Nonexistent price_field degrades gracefully to None."""
        prices = [
            _hp(0, median=Decimal("10.00")),
            _hp(7, median=Decimal("12.00")),
        ]
        result = compute_momentum(
            prices,
            period_days=7,
            price_field="nonexistent_field",
        )
        assert result is None

    def test_alternative_price_field(self):
        prices = [
            _hp(0, tcg=Decimal("10.00")),
            _hp(7, tcg=Decimal("15.00")),
        ]
        result = compute_momentum(prices, period_days=7, price_field="tcg_price")
        assert result is not None
        assert result.price_field == "tcg_price"
        assert result.trend_direction == "up"


# ---------------------------------------------------------------------------
# compute_card_analytics
# ---------------------------------------------------------------------------


class TestComputeCardAnalytics:
    def test_assembles_all_indicators(self, thirty_daily_prices: list[HistoricalPrice]):
        result = compute_card_analytics(thirty_daily_prices, source="myp", external_id="123")
        assert isinstance(result, CardAnalytics)
        assert result.source == "myp"
        assert result.external_id == "123"
        # MA: 7 and 30 should exist (90 not enough data)
        assert len(result.moving_averages) == 2
        assert result.moving_averages[0].period == 7
        assert result.moving_averages[1].period == 30
        # Extremes
        assert result.extremes is not None
        # Volatility (30d)
        assert result.volatility is not None
        # Momentum (7d)
        assert result.momentum is not None

    def test_empty_prices(self, empty_prices: list[HistoricalPrice]):
        result = compute_card_analytics(empty_prices, source="myp", external_id="456")
        assert result.moving_averages == []
        assert result.extremes is None
        assert result.volatility is None
        assert result.momentum is None

    def test_all_none_prices(self, all_none_prices: list[HistoricalPrice]):
        result = compute_card_analytics(all_none_prices, source="myp", external_id="789")
        assert result.moving_averages == []
        assert result.extremes is None
        assert result.volatility is None
        assert result.momentum is None

    def test_alternative_price_field(self):
        prices = [_hp(i, tcg=Decimal("10.00") + Decimal("0.50") * i) for i in range(30)]
        result = compute_card_analytics(
            prices, source="myp", external_id="abc", price_field="tcg_price"
        )
        assert len(result.moving_averages) == 2
        assert result.extremes is not None
        assert result.extremes.price_field == "tcg_price"

    def test_computed_at_set(self, thirty_daily_prices: list[HistoricalPrice]):
        result = compute_card_analytics(thirty_daily_prices, source="myp", external_id="123")
        assert result.computed_at is not None
