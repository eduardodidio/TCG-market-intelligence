"""Tests for compute_card_analytics() with period_days parameter — F34."""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

from src.analytics.indicators import compute_card_analytics
from src.domain.models import HistoricalPrice


def _hp(d: date, price: Decimal) -> HistoricalPrice:
    return HistoricalPrice(
        source="test",
        external_id="1",
        observed_at=d,
        median_price=price,
    )


def _generate_prices(n: int = 30) -> list[HistoricalPrice]:
    today = date.today()
    return [_hp(today - timedelta(days=n - i), Decimal("10") + Decimal(str(i))) for i in range(n)]


class TestComputeCardAnalyticsExtended:
    def test_period_days_none_backward_compat(self) -> None:
        """When period_days is None, performance and period_comparison are None."""
        prices = _generate_prices(30)
        result = compute_card_analytics(prices, "test", "1", period_days=None)
        assert result.performance is None
        assert result.period_comparison is None
        # Volatility/momentum still computed with defaults
        assert result.volatility is not None
        assert result.momentum is not None

    def test_period_days_set_populates_new_fields(self) -> None:
        """When period_days is set, performance and comparison are populated."""
        prices = _generate_prices(60)
        result = compute_card_analytics(prices, "test", "1", period_days=30)
        # With 60 data points and period=30, both should be populated
        assert result.performance is not None
        assert result.performance.period_days == 30
        assert result.period_comparison is not None
        assert result.period_comparison.period_days == 30

    def test_period_days_affects_volatility_period(self) -> None:
        """Volatility should use the provided period_days."""
        prices = _generate_prices(60)
        result = compute_card_analytics(prices, "test", "1", period_days=14)
        assert result.volatility is not None
        assert result.volatility.period_days == 14

    def test_period_days_affects_momentum_period(self) -> None:
        """Momentum should use the provided period_days."""
        prices = _generate_prices(60)
        result = compute_card_analytics(prices, "test", "1", period_days=14)
        assert result.momentum is not None
        assert result.momentum.period_days == 14

    def test_extremes_always_full_dataset(self) -> None:
        """Extremes should always be computed over full dataset."""
        today = date.today()
        # Old data with extreme values
        old = [_hp(today - timedelta(days=100), Decimal("1"))]
        recent = _generate_prices(30)
        prices = old + recent

        result = compute_card_analytics(prices, "test", "1", period_days=7)
        assert result.extremes is not None
        # ATL should be from the old data point
        assert result.extremes.atl_price == Decimal("1")

    def test_moving_averages_always_computed(self) -> None:
        """Moving averages are always computed regardless of period_days."""
        prices = _generate_prices(30)
        result = compute_card_analytics(prices, "test", "1", period_days=7)
        assert len(result.moving_averages) > 0

    def test_insufficient_data_for_new_fields(self) -> None:
        """With only 2 points, performance returns None."""
        today = date.today()
        prices = [
            _hp(today - timedelta(days=1), Decimal("10")),
            _hp(today, Decimal("11")),
        ]
        result = compute_card_analytics(prices, "test", "1", period_days=7)
        assert result.performance is None
