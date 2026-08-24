"""Tests for analytics domain models."""

from datetime import date, datetime
from decimal import Decimal

from src.domain.models import (
    CardAnalytics,
    Momentum,
    MovingAverage,
    PriceExtremes,
    Volatility,
)


class TestMovingAverage:
    def test_create(self):
        ma = MovingAverage(
            period=7,
            value=Decimal("123.45"),
            price_field="median_price",
            calculated_at=date(2026, 8, 18),
        )
        assert ma.period == 7
        assert ma.value == Decimal("123.45")
        assert ma.price_field == "median_price"
        assert ma.calculated_at == date(2026, 8, 18)

    def test_zero_value(self):
        ma = MovingAverage(
            period=30,
            value=Decimal("0.00"),
            price_field="tcg_price",
            calculated_at=date(2026, 1, 1),
        )
        assert ma.value == Decimal("0.00")


class TestPriceExtremes:
    def test_create(self):
        pe = PriceExtremes(
            ath_price=Decimal("500.00"),
            ath_date=date(2026, 6, 15),
            atl_price=Decimal("10.00"),
            atl_date=date(2026, 1, 1),
            price_field="median_price",
        )
        assert pe.ath_price == Decimal("500.00")
        assert pe.ath_date == date(2026, 6, 15)
        assert pe.atl_price == Decimal("10.00")
        assert pe.atl_date == date(2026, 1, 1)
        assert pe.price_field == "median_price"

    def test_zero_prices(self):
        pe = PriceExtremes(
            ath_price=Decimal("0.00"),
            ath_date=date(2026, 1, 1),
            atl_price=Decimal("0.00"),
            atl_date=date(2026, 1, 1),
            price_field="tcg_price",
        )
        assert pe.ath_price == Decimal("0.00")
        assert pe.atl_price == Decimal("0.00")


class TestVolatility:
    def test_create(self):
        v = Volatility(
            period_days=30,
            std_dev=Decimal("12.34"),
            coefficient_of_variation=Decimal("0.15"),
            price_field="median_price",
        )
        assert v.period_days == 30
        assert v.std_dev == Decimal("12.34")
        assert v.coefficient_of_variation == Decimal("0.15")
        assert v.price_field == "median_price"


class TestMomentum:
    def test_create_up(self):
        m = Momentum(
            period_days=7,
            rate_of_change=Decimal("5.25"),
            trend_direction="up",
            price_field="median_price",
        )
        assert m.period_days == 7
        assert m.rate_of_change == Decimal("5.25")
        assert m.trend_direction == "up"

    def test_negative_rate_of_change(self):
        m = Momentum(
            period_days=30,
            rate_of_change=Decimal("-10.50"),
            trend_direction="down",
            price_field="tcg_price",
        )
        assert m.rate_of_change == Decimal("-10.50")
        assert m.trend_direction == "down"

    def test_flat_trend(self):
        m = Momentum(
            period_days=7,
            rate_of_change=Decimal("0.00"),
            trend_direction="flat",
            price_field="median_price",
        )
        assert m.trend_direction == "flat"


class TestCardAnalytics:
    def test_create_with_defaults(self):
        ca = CardAnalytics(
            external_id="12345",
            source="myp",
        )
        assert ca.external_id == "12345"
        assert ca.source == "myp"
        assert ca.moving_averages == []
        assert ca.extremes is None
        assert ca.volatility is None
        assert ca.momentum is None
        assert isinstance(ca.computed_at, datetime)

    def test_create_with_empty_moving_averages(self):
        ca = CardAnalytics(
            external_id="12345",
            source="myp",
            moving_averages=[],
        )
        assert ca.moving_averages == []

    def test_create_full(self):
        ma = MovingAverage(
            period=7,
            value=Decimal("100.00"),
            price_field="median_price",
            calculated_at=date(2026, 8, 18),
        )
        extremes = PriceExtremes(
            ath_price=Decimal("200.00"),
            ath_date=date(2026, 6, 1),
            atl_price=Decimal("50.00"),
            atl_date=date(2026, 1, 1),
            price_field="median_price",
        )
        vol = Volatility(
            period_days=30,
            std_dev=Decimal("15.00"),
            coefficient_of_variation=Decimal("0.12"),
            price_field="median_price",
        )
        mom = Momentum(
            period_days=7,
            rate_of_change=Decimal("3.50"),
            trend_direction="up",
            price_field="median_price",
        )
        ca = CardAnalytics(
            external_id="12345",
            source="myp",
            moving_averages=[ma],
            extremes=extremes,
            volatility=vol,
            momentum=mom,
            computed_at=datetime(2026, 8, 18, 12, 0, 0),
        )
        assert len(ca.moving_averages) == 1
        assert ca.extremes.ath_price == Decimal("200.00")
        assert ca.volatility.std_dev == Decimal("15.00")
        assert ca.momentum.trend_direction == "up"
        assert ca.computed_at == datetime(2026, 8, 18, 12, 0, 0)
