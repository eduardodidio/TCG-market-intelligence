"""Tests for LigaMagic HTML parser -- pure function tests with fixture HTML."""

from __future__ import annotations

from decimal import Decimal
from pathlib import Path

import pytest

from src.providers.liga.parser import (
    _parse_brl,
    parse_card_name_from_page,
    parse_card_prices,
)

FIXTURES = Path(__file__).parent.parent / "fixtures"


def _load_html(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# _parse_brl helper
# ---------------------------------------------------------------------------


class TestParseBrl:
    def test_standard_format(self):
        assert _parse_brl("R$ 1.234,56") == Decimal("1234.56")

    def test_no_thousands_separator(self):
        assert _parse_brl("R$ 45,00") == Decimal("45.00")

    def test_no_prefix(self):
        assert _parse_brl("1.234,56") == Decimal("1234.56")

    def test_no_space_after_prefix(self):
        assert _parse_brl("R$12,90") == Decimal("12.90")

    def test_empty_string(self):
        assert _parse_brl("") is None

    def test_none(self):
        assert _parse_brl(None) is None

    def test_just_prefix(self):
        assert _parse_brl("R$ ") is None

    def test_invalid_text(self):
        assert _parse_brl("abc") is None

    def test_large_number(self):
        assert _parse_brl("R$ 10.500,00") == Decimal("10500.00")

    def test_cents_only(self):
        assert _parse_brl("R$ 0,50") == Decimal("0.50")


# ---------------------------------------------------------------------------
# parse_card_prices -- fixture-based tests
# ---------------------------------------------------------------------------


class TestParseCardPricesWithBolt:
    @pytest.fixture
    def prices(self):
        html = _load_html("liga_card_bolt.html")
        return parse_card_prices(html, "Lightning Bolt")

    def test_card_name(self, prices):
        assert prices["card_name"] == "Lightning Bolt"

    def test_normal_low(self, prices):
        assert prices["normal"]["low"] == Decimal("45.00")

    def test_normal_high(self, prices):
        assert prices["normal"]["high"] == Decimal("2500.00")

    def test_normal_mid_is_between(self, prices):
        mid = prices["normal"]["mid"]
        assert mid is not None
        assert Decimal("45.00") <= mid <= Decimal("2500.00")

    def test_foil_prices_extracted(self, prices):
        # Foil section should have some prices
        foil = prices["foil"]
        has_foil = any(v is not None for v in foil.values())
        assert has_foil


class TestParseCardPricesNoPrices:
    def test_empty_html(self):
        result = parse_card_prices("", "Test Card")
        assert result["card_name"] == "Test Card"
        assert result["normal"]["low"] is None
        assert result["normal"]["mid"] is None
        assert result["normal"]["high"] is None

    def test_no_prices_page(self):
        html = _load_html("liga_card_no_prices.html")
        result = parse_card_prices(html, "Nonexistent Card")
        assert result["normal"]["low"] is None
        assert result["normal"]["mid"] is None
        assert result["normal"]["high"] is None

    def test_whitespace_only_html(self):
        result = parse_card_prices("   \n\t  ", "Test")
        assert result["normal"]["low"] is None


class TestParseCardPricesSinglePrice:
    def test_single_price_goes_to_mid(self):
        html = _load_html("liga_card_single_price.html")
        result = parse_card_prices(html, "Sol Ring")
        assert result["normal"]["mid"] == Decimal("12.90")
        # With only one unique price, low and high are None
        assert result["normal"]["low"] is None
        assert result["normal"]["high"] is None


class TestParseCardPricesFoilOnly:
    def test_foil_section_parsed(self):
        html = _load_html("liga_card_foil_only.html")
        result = parse_card_prices(html, "Promo Card")
        foil = result["foil"]
        has_foil = any(v is not None for v in foil.values())
        assert has_foil

    def test_foil_low_and_high(self):
        html = _load_html("liga_card_foil_only.html")
        result = parse_card_prices(html, "Promo Card")
        foil = result["foil"]
        if foil["low"] is not None and foil["high"] is not None:
            assert foil["low"] <= foil["high"]


# ---------------------------------------------------------------------------
# parse_card_name_from_page
# ---------------------------------------------------------------------------


class TestParseCardNameFromPage:
    def test_extracts_name_from_title(self):
        html = _load_html("liga_card_bolt.html")
        name = parse_card_name_from_page(html)
        assert name == "Lightning Bolt"

    def test_strips_ligamagic_suffix(self):
        html = "<html><head><title>Sol Ring - LigaMagic</title></head><body></body></html>"
        name = parse_card_name_from_page(html)
        assert name == "Sol Ring"

    def test_no_title_returns_none(self):
        html = "<html><head></head><body>No title here</body></html>"
        name = parse_card_name_from_page(html)
        assert name is None

    def test_empty_html(self):
        assert parse_card_name_from_page("") is None
