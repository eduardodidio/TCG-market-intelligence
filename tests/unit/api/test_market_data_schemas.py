"""Tests for shared market data schemas (F44-T02)."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from src.api.schemas.market_data import (
    CardPriceInfo,
    MarketCardSummary,
    MarketSummary,
    MoverInfo,
    MoversResult,
)


class TestCardPriceInfo:
    def test_serialization(self):
        info = CardPriceInfo(
            card_id=1,
            latest_price=Decimal("15.50"),
            price_date=date(2026, 8, 20),
            currency="BRL",
        )
        data = info.model_dump()
        assert data["card_id"] == 1
        assert data["latest_price"] == Decimal("15.50")
        assert data["currency"] == "BRL"

    def test_defaults(self):
        info = CardPriceInfo(card_id=1)
        assert info.latest_price is None
        assert info.price_date is None
        assert info.currency == "BRL"


class TestMarketCardSummary:
    def test_with_price(self):
        price = CardPriceInfo(card_id=1, latest_price=Decimal("10.00"))
        summary = MarketCardSummary(
            card_id=1,
            name_en="Sol Ring",
            name_pt="Anel Solar",
            set_code="dmr",
            collector_number="001",
            image_url="https://example.com/sol-ring.jpg",
            price=price,
        )
        data = summary.model_dump()
        assert data["price"]["latest_price"] == Decimal("10.00")
        assert data["name_en"] == "Sol Ring"

    def test_without_price(self):
        summary = MarketCardSummary(card_id=1, name_en="Card")
        assert summary.price is None
        assert summary.set_code is None


class TestMoverInfo:
    def test_decimal_fields(self):
        mover = MoverInfo(
            card_id=1,
            name_en="Rising Star",
            price_start=Decimal("10.00"),
            price_end=Decimal("15.00"),
            change_pct=Decimal("50.00"),
        )
        data = mover.model_dump()
        assert isinstance(data["price_start"], Decimal)
        assert isinstance(data["change_pct"], Decimal)

    def test_defaults(self):
        mover = MoverInfo(card_id=1, name_en="Card")
        assert mover.price_start is None
        assert mover.currency == "BRL"


class TestMarketSummary:
    def test_optional_fields(self):
        summary = MarketSummary(total_cards=0, total_observations=0)
        assert summary.avg_price is None
        assert summary.date_range_start is None
        assert summary.computed_at is None
        assert summary.currency == "BRL"

    def test_full_fields(self):
        now = datetime(2026, 8, 20, 12, 0)
        summary = MarketSummary(
            total_cards=100,
            total_observations=500,
            avg_price=Decimal("15.50"),
            date_range_start=date(2026, 1, 1),
            date_range_end=date(2026, 8, 20),
            currency="USD",
            computed_at=now,
        )
        assert summary.total_cards == 100
        assert summary.currency == "USD"


class TestMoversResult:
    def test_defaults(self):
        result = MoversResult()
        assert result.gainers == []
        assert result.losers == []
        assert result.period == "30d"
        assert result.currency == "BRL"
        assert result.computed_at is None

    def test_with_movers(self):
        gainer = MoverInfo(card_id=1, name_en="Up", change_pct=Decimal("50"))
        result = MoversResult(
            gainers=[gainer],
            period="7d",
            currency="USD",
        )
        assert len(result.gainers) == 1
        assert result.period == "7d"
