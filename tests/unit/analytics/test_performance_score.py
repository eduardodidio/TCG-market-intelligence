"""Tests for compute_performance_score() — F34."""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

from src.analytics.indicators import compute_performance_score
from src.domain.models import HistoricalPrice


def _hp(d: date, price: Decimal) -> HistoricalPrice:
    """Shortcut to build a HistoricalPrice."""
    return HistoricalPrice(
        source="test",
        external_id="1",
        observed_at=d,
        median_price=price,
    )


def _rising_prices(n: int = 10, start: Decimal = Decimal("10")) -> list[HistoricalPrice]:
    """Generate consistently rising prices over n days."""
    today = date.today()
    return [_hp(today - timedelta(days=n - i), start + Decimal(str(i))) for i in range(n)]


def _falling_prices(n: int = 10, start: Decimal = Decimal("20")) -> list[HistoricalPrice]:
    """Generate consistently falling prices over n days."""
    today = date.today()
    return [_hp(today - timedelta(days=n - i), start - Decimal(str(i))) for i in range(n)]


def _flat_prices(n: int = 10, price: Decimal = Decimal("10")) -> list[HistoricalPrice]:
    """Generate flat prices over n days."""
    today = date.today()
    return [_hp(today - timedelta(days=n - i), price) for i in range(n)]


class TestComputePerformanceScore:
    def test_returns_none_with_fewer_than_3_points(self) -> None:
        today = date.today()
        prices = [
            _hp(today - timedelta(days=1), Decimal("10")),
            _hp(today, Decimal("11")),
        ]
        result = compute_performance_score(prices, period_days=30)
        assert result is None

    def test_returns_none_with_empty_list(self) -> None:
        result = compute_performance_score([], period_days=30)
        assert result is None

    def test_score_in_valid_range(self) -> None:
        prices = _rising_prices(10)
        result = compute_performance_score(prices, period_days=30)
        assert result is not None
        assert 0 <= result.score <= 100

    def test_rising_prices_score_strong(self) -> None:
        prices = _rising_prices(15, start=Decimal("10"))
        result = compute_performance_score(prices, period_days=30)
        assert result is not None
        assert result.label == "strong"
        assert result.score >= 70

    def test_falling_prices_score_declining_or_weak(self) -> None:
        prices = _falling_prices(15, start=Decimal("30"))
        result = compute_performance_score(prices, period_days=30)
        assert result is not None
        assert result.label in ("declining", "weak")
        assert result.score < 45

    def test_flat_prices_score_moderate_or_weak(self) -> None:
        prices = _flat_prices(10)
        result = compute_performance_score(prices, period_days=30)
        assert result is not None
        # Flat: momentum ~50 (mapped from 0 roc), consistency 0 (no positive deltas),
        # ATH proximity 100 (at ATH). Score around 50.
        assert result.label in ("moderate", "weak")

    def test_period_filtering(self) -> None:
        """Only prices within the period window are used."""
        today = date.today()
        # Old data far in the past
        old = [_hp(today - timedelta(days=100 + i), Decimal("5")) for i in range(5)]
        # Recent rising data
        recent = _rising_prices(5, start=Decimal("10"))
        prices = old + recent
        result = compute_performance_score(prices, period_days=10)
        assert result is not None
        # Should reflect the recent rising trend, not old flat data
        assert result.score >= 45

    def test_different_price_field(self) -> None:
        today = date.today()
        prices = [
            HistoricalPrice(
                source="test",
                external_id="1",
                observed_at=today - timedelta(days=3 - i),
                median_price=None,
                tcg_price=Decimal("10") + Decimal(str(i)),
            )
            for i in range(4)
        ]
        result = compute_performance_score(prices, period_days=30, price_field="tcg_price")
        assert result is not None
        assert 0 <= result.score <= 100

    def test_all_same_price(self) -> None:
        """All same price: ATH proximity 100, momentum 50, consistency 0."""
        prices = _flat_prices(5, Decimal("15"))
        result = compute_performance_score(prices, period_days=30)
        assert result is not None
        assert result.price_field == "median_price"
        assert result.period_days == 30

    def test_label_strong_threshold(self) -> None:
        """Score >= 70 should be 'strong'."""
        prices = _rising_prices(20, start=Decimal("5"))
        result = compute_performance_score(prices, period_days=30)
        assert result is not None
        if result.score >= 70:
            assert result.label == "strong"

    def test_label_declining_threshold(self) -> None:
        """Score < 25 should be 'declining'."""
        # Steep decline
        today = date.today()
        prices = [
            _hp(today - timedelta(days=10 - i), Decimal("100") - Decimal(str(i * 10)))
            for i in range(10)
        ]
        result = compute_performance_score(prices, period_days=30)
        assert result is not None
        if result.score < 25:
            assert result.label == "declining"
