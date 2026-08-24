"""Tests for exchange rate domain models (T03)."""

from datetime import date
from decimal import Decimal

from src.domain.models import ConvertedPrice, Currency, ExchangeRate


class TestCurrencyEnum:
    def test_brl(self):
        assert Currency.BRL == "BRL"
        assert Currency.BRL.value == "BRL"

    def test_usd(self):
        assert Currency.USD == "USD"
        assert Currency.USD.value == "USD"

    def test_is_str_enum(self):
        assert isinstance(Currency.BRL, str)


class TestExchangeRate:
    def test_defaults(self):
        rate = ExchangeRate(rate_date=date(2026, 8, 20))
        assert rate.from_currency == "USD"
        assert rate.to_currency == "BRL"
        assert rate.rate == Decimal("0")
        assert rate.source == "bcb_ptax"

    def test_with_values(self):
        rate = ExchangeRate(
            rate_date=date(2026, 8, 20),
            from_currency="USD",
            to_currency="BRL",
            rate=Decimal("5.25"),
            source="bcb_ptax",
        )
        assert rate.rate_date == date(2026, 8, 20)
        assert rate.rate == Decimal("5.25")


class TestConvertedPrice:
    def test_with_value(self):
        price = ConvertedPrice(
            value=Decimal("10.00"),
            currency="USD",
            exchange_rate=Decimal("5.25"),
            rate_date=date(2026, 8, 20),
        )
        assert price.value == Decimal("10.00")
        assert price.currency == "USD"
        assert price.exchange_rate == Decimal("5.25")

    def test_with_none_value(self):
        price = ConvertedPrice(value=None, currency="USD")
        assert price.value is None
        assert price.exchange_rate is None
        assert price.rate_date is None

    def test_defaults(self):
        price = ConvertedPrice(value=Decimal("1.00"), currency="BRL")
        assert price.exchange_rate is None
        assert price.rate_date is None
