"""Tests for compute_period_comparison() — F34."""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

from src.analytics.indicators import compute_period_comparison
from src.domain.models import HistoricalPrice


def _hp(d: date, price: Decimal) -> HistoricalPrice:
    return HistoricalPrice(
        source="test",
        external_id="1",
        observed_at=d,
        median_price=price,
    )


class TestComputePeriodComparison:
    def test_returns_none_with_empty_list(self) -> None:
        result = compute_period_comparison([], period_days=7)
        assert result is None

    def test_returns_none_when_no_previous_period_data(self) -> None:
        """If all data is in the current period, previous is empty -> None."""
        today = date.today()
        prices = [_hp(today - timedelta(days=i), Decimal("10")) for i in range(5)]
        result = compute_period_comparison(prices, period_days=7)
        assert result is None

    def test_positive_delta(self) -> None:
        """Current period avg > previous period avg."""
        today = date.today()
        # Previous period: 14-7 days ago, avg = 10
        previous = [_hp(today - timedelta(days=14 - i), Decimal("10")) for i in range(7)]
        # Current period: last 7 days, avg = 15
        current = [_hp(today - timedelta(days=6 - i), Decimal("15")) for i in range(7)]
        prices = previous + current
        result = compute_period_comparison(prices, period_days=7)
        assert result is not None
        assert result.delta > 0
        assert result.delta_pct > 0
        assert result.current_avg == Decimal("15")
        assert result.previous_avg == Decimal("10")

    def test_negative_delta(self) -> None:
        """Current period avg < previous period avg."""
        today = date.today()
        previous = [_hp(today - timedelta(days=14 - i), Decimal("20")) for i in range(7)]
        current = [_hp(today - timedelta(days=6 - i), Decimal("12")) for i in range(7)]
        prices = previous + current
        result = compute_period_comparison(prices, period_days=7)
        assert result is not None
        assert result.delta < 0
        assert result.delta_pct < 0

    def test_delta_pct_calculation(self) -> None:
        """Verify delta_pct = (delta / previous_avg) * 100."""
        today = date.today()
        previous = [_hp(today - timedelta(days=14 - i), Decimal("10")) for i in range(7)]
        current = [_hp(today - timedelta(days=6 - i), Decimal("15")) for i in range(7)]
        prices = previous + current
        result = compute_period_comparison(prices, period_days=7)
        assert result is not None
        expected_pct = (result.delta / result.previous_avg) * Decimal("100")
        assert abs(result.delta_pct - expected_pct) < Decimal("0.01")

    def test_period_days_respected(self) -> None:
        today = date.today()
        # Data spread over 60 days
        prices = [
            _hp(today - timedelta(days=60 - i), Decimal("10") + Decimal(str(i % 5)))
            for i in range(60)
        ]
        result = compute_period_comparison(prices, period_days=30)
        assert result is not None
        assert result.period_days == 30

    def test_different_price_field(self) -> None:
        today = date.today()
        prices = [
            HistoricalPrice(
                source="test",
                external_id="1",
                observed_at=today - timedelta(days=20 - i),
                median_price=None,
                tcg_price=Decimal("10") + (Decimal("5") if i >= 10 else Decimal("0")),
            )
            for i in range(20)
        ]
        result = compute_period_comparison(prices, period_days=10, price_field="tcg_price")
        assert result is not None
        assert result.delta > 0

    def test_equal_averages(self) -> None:
        """When both periods have the same average, delta = 0."""
        today = date.today()
        prices = [_hp(today - timedelta(days=20 - i), Decimal("10")) for i in range(20)]
        result = compute_period_comparison(prices, period_days=10)
        assert result is not None
        assert result.delta == 0
        assert result.delta_pct == 0

    def test_returns_none_when_insufficient_previous(self) -> None:
        """Only 1 day of data -> no previous period."""
        today = date.today()
        prices = [_hp(today, Decimal("10"))]
        result = compute_period_comparison(prices, period_days=7)
        assert result is None

    def test_price_field_in_result(self) -> None:
        today = date.today()
        prices = [_hp(today - timedelta(days=20 - i), Decimal("10")) for i in range(20)]
        result = compute_period_comparison(prices, period_days=10)
        assert result is not None
        assert result.price_field == "median_price"
