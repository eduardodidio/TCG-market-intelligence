"""Tests for the Pila currency formatter (F19-T01)."""

from decimal import Decimal

from src.currency.pila_formatter import format_pila


class TestFormatPilaNone:
    def test_none_returns_dashes(self):
        assert format_pila(None) == "--"


class TestFormatPilaZero:
    def test_zero_int(self):
        assert format_pila(0) == "0 pilas"

    def test_zero_float(self):
        assert format_pila(0.0) == "0 pilas"

    def test_zero_decimal(self):
        assert format_pila(Decimal("0")) == "0 pilas"


class TestFormatPilaSingular:
    def test_one_pila_integer(self):
        assert format_pila(1.0) == "1 pila"

    def test_one_pila_decimal(self):
        assert format_pila(Decimal("1.00")) == "1 pila"

    def test_one_pila_one_centavo(self):
        assert format_pila(1.01) == "1 pila e 1 centavo"

    def test_one_pila_multiple_centavos(self):
        assert format_pila(1.50) == "1 pila e 50 centavos"


class TestFormatPilaPlural:
    def test_two_pilas(self):
        assert format_pila(2.0) == "2 pilas"

    def test_example_230_21(self):
        assert format_pila(230.21) == "230 pilas e 21 centavos"

    def test_ten_pilas(self):
        assert format_pila(10.0) == "10 pilas"

    def test_99_centavos(self):
        assert format_pila(0.99) == "0 pilas e 99 centavos"


class TestFormatPilaThousands:
    def test_thousand_separator(self):
        assert format_pila(1000.0) == "1.000 pilas"

    def test_millions(self):
        assert format_pila(1000000.0) == "1.000.000 pilas"

    def test_thousands_with_centavos(self):
        assert format_pila(1234.56) == "1.234 pilas e 56 centavos"

    def test_ten_thousand(self):
        assert format_pila(10000.0) == "10.000 pilas"

    def test_hundred(self):
        assert format_pila(100.0) == "100 pilas"


class TestFormatPilaRounding:
    def test_rounds_to_two_decimals(self):
        assert format_pila(1.005) == "1 pila e 1 centavo"

    def test_rounds_down(self):
        assert format_pila(1.004) == "1 pila"


class TestFormatPilaNegative:
    def test_negative_value(self):
        assert format_pila(-5.50) == "-5 pilas e 50 centavos"

    def test_negative_one(self):
        assert format_pila(-1.0) == "-1 pila"


class TestFormatPilaFromDecimal:
    def test_decimal_input(self):
        assert format_pila(Decimal("230.21")) == "230 pilas e 21 centavos"

    def test_decimal_zero_centavos(self):
        assert format_pila(Decimal("500.00")) == "500 pilas"


class TestFormatPilaEdgeCases:
    def test_very_small_amount(self):
        assert format_pila(0.01) == "0 pilas e 1 centavo"

    def test_large_amount(self):
        assert format_pila(999999.99) == "999.999 pilas e 99 centavos"
