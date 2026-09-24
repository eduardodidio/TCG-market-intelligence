"""Tests for src.currency.import_conversion."""

from datetime import date
from decimal import Decimal
from unittest.mock import Mock

from src.currency.import_conversion import (
    ConversionResult,
    rate_lookup_from_converter,
    to_brl,
)

TODAY = date(2026, 9, 24)


def _fake_rate_lookup(rate: Decimal | None):
    return lambda _on_date: rate


class TestToBrlHappyPath:
    def test_usd_times_rate(self):
        result = to_brl(Decimal("2.00"), "USD", TODAY, _fake_rate_lookup(Decimal("5.40")))
        assert result.brl == Decimal("10.80")
        assert result.rate == Decimal("5.40")
        assert result.warning is None
        assert result.original_amount == Decimal("2.00")
        assert result.original_currency == "USD"

    def test_brl_identity(self):
        result = to_brl(Decimal("10.00"), "BRL", TODAY, _fake_rate_lookup(None))
        assert result.brl == Decimal("10.00")
        assert result.rate is None
        assert result.warning is None

    def test_lowercase_usd(self):
        result = to_brl(Decimal("1.00"), "usd", TODAY, _fake_rate_lookup(Decimal("5.00")))
        assert result.brl == Decimal("5.00")
        assert result.original_currency == "USD"

    def test_currency_with_whitespace(self):
        result = to_brl(Decimal("1.00"), " usd ", TODAY, _fake_rate_lookup(Decimal("5.00")))
        assert result.original_currency == "USD"
        assert result.brl == Decimal("5.00")


class TestToBrlEdgeCases:
    def test_amount_zero(self):
        result = to_brl(Decimal("0"), "USD", TODAY, _fake_rate_lookup(Decimal("5.00")))
        assert result.brl == Decimal("0.00")

    def test_rounding_half_up(self):
        result = to_brl(Decimal("0.335"), "USD", TODAY, _fake_rate_lookup(Decimal("5.00")))
        assert result.brl == Decimal("1.68")

    def test_rate_with_four_decimals(self):
        result = to_brl(Decimal("2.00"), "USD", TODAY, _fake_rate_lookup(Decimal("5.4321")))
        assert result.brl == (Decimal("2.00") * Decimal("5.4321")).quantize(Decimal("0.01"))
        assert result.rate == Decimal("5.4321")


class TestToBrlErrors:
    def test_rate_none(self):
        result = to_brl(Decimal("2.00"), "USD", TODAY, _fake_rate_lookup(None))
        assert result.brl is None
        assert result.warning == "no_rate"
        assert result.rate is None

    def test_rate_zero(self):
        result = to_brl(Decimal("2.00"), "USD", TODAY, _fake_rate_lookup(Decimal("0")))
        assert result.brl is None
        assert result.warning == "no_rate"

    def test_rate_negative(self):
        result = to_brl(Decimal("2.00"), "USD", TODAY, _fake_rate_lookup(Decimal("-1")))
        assert result.brl is None
        assert result.warning == "no_rate"

    def test_eur_unsupported(self):
        result = to_brl(Decimal("2.00"), "EUR", TODAY, _fake_rate_lookup(Decimal("5.00")))
        assert result.brl is None
        assert result.warning == "unsupported_currency"
        assert result.original_currency == "EUR"

    def test_empty_currency_unsupported(self):
        result = to_brl(Decimal("2.00"), "", TODAY, _fake_rate_lookup(Decimal("5.00")))
        assert result.brl is None
        assert result.warning == "unsupported_currency"


class TestToBrlBoundary:
    def test_on_date_passed_through_to_lookup(self):
        lookup = Mock(return_value=Decimal("5.00"))
        to_brl(Decimal("1.00"), "USD", TODAY, lookup)
        lookup.assert_called_once_with(TODAY)

    def test_conversion_result_is_dataclass(self):
        result = to_brl(Decimal("1.00"), "BRL", TODAY, _fake_rate_lookup(None))
        assert isinstance(result, ConversionResult)


class TestRateLookupFromConverter:
    def test_delegates_to_converter(self):
        converter = Mock()
        converter.get_display_rate.return_value = Decimal("5.25")

        lookup = rate_lookup_from_converter(converter)
        rate = lookup(TODAY)

        assert rate == Decimal("5.25")
        converter.get_display_rate.assert_called_once_with(TODAY)

    def test_none_rate_propagates(self):
        converter = Mock()
        converter.get_display_rate.return_value = None

        lookup = rate_lookup_from_converter(converter)

        assert lookup(TODAY) is None
