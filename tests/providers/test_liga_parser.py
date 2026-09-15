"""Tests for LigaMagic HTML parser -- pure function tests with fixture HTML."""

from __future__ import annotations

from decimal import Decimal
from pathlib import Path

import pytest

from src.providers.liga.parser import (
    _parse_brl,
    _parse_price_mkp,
    parse_card_name_from_page,
    parse_card_prices,
    parse_edition_options,
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


class TestParseCardPricesNbsp:
    """Ensure parser handles R$ with &nbsp; (non-breaking space) correctly."""

    @pytest.fixture
    def prices(self):
        html = _load_html("liga_card_nbsp_prices.html")
        return parse_card_prices(html, "Demonic Tutor")

    def test_card_name(self, prices):
        assert prices["card_name"] == "Demonic Tutor"

    def test_normal_low(self, prices):
        assert prices["normal"]["low"] == Decimal("55.90")

    def test_normal_high(self, prices):
        assert prices["normal"]["high"] == Decimal("350.00")

    def test_normal_mid_is_between(self, prices):
        mid = prices["normal"]["mid"]
        assert mid is not None
        assert Decimal("55.90") <= mid <= Decimal("350.00")


class TestParseBrlNbsp:
    """_parse_brl handles &nbsp; and \\xa0 between R$ and digits."""

    def test_nbsp_entity(self):
        assert _parse_brl("R$&nbsp;75,00") == Decimal("75.00")

    def test_unicode_nbsp(self):
        assert _parse_brl("R$\xa075,00") == Decimal("75.00")

    def test_no_space(self):
        assert _parse_brl("R$75,00") == Decimal("75.00")


# ---------------------------------------------------------------------------
# Parametrized regression tests across all fixtures
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "fixture_file, card_name, expect_normal, expect_foil",
    [
        pytest.param(
            "liga_card_bolt.html",
            "Lightning Bolt",
            True,
            True,
            id="bolt-normal-and-foil",
        ),
        pytest.param(
            "liga_card_no_prices.html",
            "Nonexistent Card",
            False,
            False,
            id="no-prices",
        ),
        pytest.param(
            "liga_card_single_price.html",
            "Sol Ring",
            True,
            False,
            id="single-price",
        ),
        pytest.param(
            "liga_card_foil_only.html",
            "Promo Card",
            True,  # foil prices also appear in the full-page regex scan
            True,
            id="foil-only",
        ),
        pytest.param(
            "liga_card_nbsp_prices.html",
            "Demonic Tutor",
            True,
            False,
            id="nbsp-prices",
        ),
    ],
)
class TestParseCardPricesParametrized:
    def test_has_expected_normal_prices(self, fixture_file, card_name, expect_normal, expect_foil):
        html = _load_html(fixture_file)
        result = parse_card_prices(html, card_name)
        normal = result["normal"]
        has_normal = any(v is not None for v in normal.values())
        assert has_normal == expect_normal

    def test_has_expected_foil_prices(self, fixture_file, card_name, expect_normal, expect_foil):
        html = _load_html(fixture_file)
        result = parse_card_prices(html, card_name)
        foil = result["foil"]
        has_foil = any(v is not None for v in foil.values())
        assert has_foil == expect_foil

    def test_card_name_preserved(self, fixture_file, card_name, expect_normal, expect_foil):
        html = _load_html(fixture_file)
        result = parse_card_prices(html, card_name)
        assert result["card_name"] == card_name

    def test_prices_are_positive_decimals(
        self, fixture_file, card_name, expect_normal, expect_foil
    ):
        html = _load_html(fixture_file)
        result = parse_card_prices(html, card_name)
        for section in ("normal", "foil"):
            for key in ("low", "mid", "high"):
                val = result[section][key]
                if val is not None:
                    assert isinstance(val, Decimal)
                    assert val > 0


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


# ---------------------------------------------------------------------------
# _parse_price_mkp -- structured price extraction
# ---------------------------------------------------------------------------


class TestParsePriceMkp:
    def test_extracts_min_medium_max(self):
        html = _load_html("liga_card_price_mkp.html")
        mkp = _parse_price_mkp(html)
        assert mkp is not None
        assert mkp["low"] == Decimal("6.84")
        assert mkp["mid"] == Decimal("8.50")
        assert mkp["high"] == Decimal("12.00")

    def test_returns_none_for_no_mkp(self):
        html = _load_html("liga_card_bolt.html")
        assert _parse_price_mkp(html) is None

    def test_returns_none_for_empty_html(self):
        assert _parse_price_mkp("") is None


class TestParseCardPricesWithPriceMkp:
    """Verify that price-mkp is preferred over all-page-scan fallback."""

    @pytest.fixture
    def prices(self):
        html = _load_html("liga_card_price_mkp.html")
        return parse_card_prices(html, "Arcane Signet")

    def test_uses_price_mkp_not_marketplace(self, prices):
        """Must NOT pick up R$248, R$1250 from marketplace listings."""
        assert prices["normal"]["low"] == Decimal("6.84")
        assert prices["normal"]["mid"] == Decimal("8.50")
        assert prices["normal"]["high"] == Decimal("12.00")

    def test_card_name(self, prices):
        assert prices["card_name"] == "Arcane Signet"

    def test_no_foil_on_normal_page(self, prices):
        foil = prices["foil"]
        assert all(v is None for v in foil.values())


class TestParseCardPricesMkpFoil:
    """Verify foil price-mkp extraction."""

    @pytest.fixture
    def prices(self):
        html = _load_html("liga_card_price_mkp_foil.html")
        return parse_card_prices(html, "Lightning Bolt")

    def test_normal_prices(self, prices):
        assert prices["normal"]["low"] == Decimal("3.50")
        assert prices["normal"]["mid"] == Decimal("5.00")
        assert prices["normal"]["high"] == Decimal("8.90")

    def test_foil_prices(self, prices):
        assert prices["foil"]["low"] == Decimal("25.00")
        assert prices["foil"]["mid"] == Decimal("45.00")
        assert prices["foil"]["high"] == Decimal("120.00")


# ---------------------------------------------------------------------------
# parse_edition_options
# ---------------------------------------------------------------------------


class TestParseEditionOptions:
    def test_extracts_editions(self):
        html = _load_html("liga_card_price_mkp.html")
        editions = parse_edition_options(html)
        assert len(editions) == 3
        values = [v for v, _ in editions]
        assert "480612_1" in values
        assert "480263_367" in values
        assert "479771_331" in values

    def test_collector_numbers(self):
        html = _load_html("liga_card_price_mkp.html")
        editions = parse_edition_options(html)
        collector_nums = {cn for _, cn in editions}
        assert collector_nums == {"1", "367", "331"}

    def test_empty_html(self):
        assert parse_edition_options("") == []

    def test_no_edition_options(self):
        html = _load_html("liga_card_no_prices.html")
        assert parse_edition_options(html) == []
