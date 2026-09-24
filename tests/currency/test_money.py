"""Tests for src.currency.money."""

from decimal import Decimal

import pytest

from src.currency.money import detect_symbol, number_format_hint, parse_money


class TestDetectSymbol:
    @pytest.mark.parametrize(
        "text,expected",
        [
            ("R$ 9,75", "BRL"),
            ("r$ 9,75", "BRL"),
            ("BRL 9,75", "BRL"),
            ("US$ 3.10", "USD"),
            ("U$ 3.10", "USD"),
            ("USD 3.10", "USD"),
            ("$3.10", "USD"),
            ("€ 3,00", "EUR"),
            ("EUR 3,00", "EUR"),
            ("3,10", None),
            ("3.10", None),
            ("no symbol here", None),
            ("", None),
        ],
    )
    def test_detect(self, text, expected):
        assert detect_symbol(text) == expected


class TestParseMoneyHappyPath:
    @pytest.mark.parametrize(
        "text,expected",
        [
            ("R$ 9,75", (Decimal("9.75"), "BRL")),
            ("R$9,75", (Decimal("9.75"), "BRL")),
            ("BRL 9,75", (Decimal("9.75"), "BRL")),
            ("US$ 3.10", (Decimal("3.10"), "USD")),
            ("U$ 3.10", (Decimal("3.10"), "USD")),
            ("USD 3.10", (Decimal("3.10"), "USD")),
            ("$3.10", (Decimal("3.10"), "USD")),
            ("$0.50", (Decimal("0.50"), "USD")),
            ("3,10", (Decimal("3.10"), None)),
            ("3.10", (Decimal("3.10"), None)),
        ],
    )
    def test_happy_path(self, text, expected):
        assert parse_money(text) == expected

    def test_r_1234_56(self):
        assert parse_money("R$ 1.234,56") == (Decimal("1234.56"), "BRL")

    def test_us_1234_56(self):
        assert parse_money("US$ 1,234.56") == (Decimal("1234.56"), "USD")

    def test_bare_12_50(self):
        assert parse_money("12,50") == (Decimal("12.50"), None)
        assert parse_money("12.50") == (Decimal("12.50"), None)


class TestParseMoneyEdgeCases:
    def test_nbsp_between_symbol_and_number(self):
        assert parse_money("R$\xa09,75") == (Decimal("9.75"), "BRL")

    def test_unid_suffix(self):
        assert parse_money("R$ 1.234,56 (unid.)") == (Decimal("1234.56"), "BRL")

    def test_dot_thousands_comma_decimal_over_million_is_none(self):
        amount, symbol = parse_money("1.234.567,89")
        assert amount is None
        assert symbol is None

    def test_comma_thousands_dot_decimal_over_million_is_none(self):
        amount, symbol = parse_money("1,234,567.89")
        assert amount is None
        assert symbol is None

    def test_leading_trailing_spaces(self):
        assert parse_money("  R$ 9,75  ") == (Decimal("9.75"), "BRL")

    def test_lowercase_symbol(self):
        assert parse_money("r$ 9,75") == (Decimal("9.75"), "BRL")


class TestParseMoneyAmbiguity:
    def test_dot_thousands_with_brl_hint(self):
        assert parse_money("1.234", hint="BRL") == (Decimal("1234.00"), None)

    def test_dot_ambiguous_with_usd_hint(self):
        assert parse_money("1.234", hint="USD") == (Decimal("1.23"), None)

    def test_dot_ambiguous_no_hint(self):
        assert parse_money("1.234") == (Decimal("1.23"), None)

    def test_comma_thousands_with_usd_hint(self):
        assert parse_money("1,234", hint="USD") == (Decimal("1234.00"), None)

    def test_comma_ambiguous_with_brl_hint(self):
        assert parse_money("1,234", hint="BRL") == (Decimal("1.23"), None)

    def test_comma_ambiguous_no_hint(self):
        assert parse_money("1,234") == (Decimal("1.23"), None)


class TestParseMoneyErrors:
    def test_empty_string(self):
        assert parse_money("") == (None, None)

    def test_none(self):
        assert parse_money(None) == (None, None)

    def test_garbage_text(self):
        assert parse_money("abc") == (None, None)

    def test_symbol_only(self):
        amount, symbol = parse_money("R$")
        assert amount is None
        assert symbol == "BRL"

    def test_double_dash(self):
        assert parse_money("--") == (None, None)

    def test_negative(self):
        assert parse_money("-5") == (None, None)

    def test_scientific_notation(self):
        assert parse_money("1e5") == (None, None)


class TestParseMoneyBoundary:
    def test_zero(self):
        assert parse_money("0,00") == (Decimal("0.00"), None)

    def test_one_million_valid(self):
        assert parse_money("1000000,00") == (Decimal("1000000.00"), None)

    def test_over_one_million_invalid(self):
        assert parse_money("1000000,01") == (None, None)

    def test_half_up_rounding(self):
        assert parse_money("0,005") == (Decimal("0.01"), None)

    def test_plain_integer_no_separators(self):
        assert parse_money("1234") == (Decimal("1234.00"), None)

    def test_multiple_dots_thousands(self):
        assert parse_money("1.234.567") == (None, None)

    def test_multiple_commas_thousands(self):
        assert parse_money("1,234,567") == (None, None)

    def test_mixed_separators_invalid_decimal(self):
        assert parse_money("1.2,3,4") == (None, None)


class TestNumberFormatHint:
    @pytest.mark.parametrize(
        "text,expected",
        [
            ("12,50", "BRL"),
            ("1.234,56", "BRL"),
            ("12.50", "USD"),
            ("1,234.56", "USD"),
            ("12", None),
        ],
    )
    def test_hint(self, text, expected):
        assert number_format_hint(text) == expected

    def test_empty_string(self):
        assert number_format_hint("") is None
