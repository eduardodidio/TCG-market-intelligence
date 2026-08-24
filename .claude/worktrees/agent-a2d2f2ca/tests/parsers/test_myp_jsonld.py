"""Tests for parse_jsonld_price() parser function."""

from __future__ import annotations

import json
from decimal import Decimal

from src.domain.models import JsonLdPrice
from src.parsers.myp import parse_jsonld_price

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _wrap_jsonld(data: dict | list | str, extra_scripts: str = "") -> str:
    """Wrap a JSON-LD object in a minimal HTML page."""
    if isinstance(data, str):
        payload = data
    else:
        payload = json.dumps(data)
    return (
        "<html><head>"
        f"{extra_scripts}"
        f'<script type="application/ld+json">{payload}</script>'
        "</head><body></body></html>"
    )


def _product_jsonld(
    price: str | int | float | None = "12.50",
    currency: str = "BRL",
    availability: str = "https://schema.org/InStock",
    include_offers: bool = True,
    product_id: str = "179334",
) -> dict:
    """Build a minimal Product JSON-LD dict."""
    product: dict = {
        "@context": "https://schema.org/",
        "@type": "Product",
        "name": "Tutor Esclarecido / Enlightened Tutor",
        "productID": product_id,
    }
    if include_offers:
        offers: dict = {"@type": "Offer", "priceCurrency": currency}
        if price is not None:
            offers["price"] = str(price) if not isinstance(price, str) else price
        if availability:
            offers["availability"] = availability
        product["offers"] = offers
    return product


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------


class TestParseJsonldPriceHappyPath:
    """U10: Valid Product JSON-LD with price, currency, and availability."""

    def test_instock_valid_price(self):
        html = _wrap_jsonld(_product_jsonld(price="12.50"))
        result = parse_jsonld_price(html)

        assert result is not None
        assert isinstance(result, JsonLdPrice)
        assert result.price == Decimal("12.50")
        assert result.currency == "BRL"
        assert result.availability == "InStock"

    def test_outofstock_card(self):
        """U11: OutOfStock card with valid price."""
        html = _wrap_jsonld(
            _product_jsonld(
                price="5.00",
                availability="https://schema.org/OutOfStock",
            )
        )
        result = parse_jsonld_price(html)

        assert result is not None
        assert result.price == Decimal("5.00")
        assert result.currency == "BRL"
        assert result.availability == "OutOfStock"

    def test_price_as_integer_string(self):
        """U21: Price as integer string."""
        html = _wrap_jsonld(_product_jsonld(price="10"))
        result = parse_jsonld_price(html)

        assert result is not None
        assert result.price == Decimal("10")

    def test_price_with_comma_decimal(self):
        """U18: Brazilian format with comma separator."""
        html = _wrap_jsonld(_product_jsonld(price="12,50"))
        result = parse_jsonld_price(html)

        assert result is not None
        assert result.price == Decimal("12.50")

    def test_price_as_float_rounds_to_decimal(self):
        """Price as float (0.44999...) converts to Decimal correctly."""
        product = _product_jsonld()
        product["offers"]["price"] = 0.45
        html = _wrap_jsonld(product)
        result = parse_jsonld_price(html)

        assert result is not None
        assert result.price == Decimal("0.45")


# ---------------------------------------------------------------------------
# Zero price normalization
# ---------------------------------------------------------------------------


class TestParseJsonldPriceZero:
    """U12: Zero price is normalized to None."""

    def test_price_zero_string(self):
        html = _wrap_jsonld(_product_jsonld(price="0"))
        result = parse_jsonld_price(html)

        assert result is not None
        assert result.price is None
        assert result.currency == "BRL"
        assert result.availability == "InStock"

    def test_price_zero_int(self):
        product = _product_jsonld()
        product["offers"]["price"] = 0
        html = _wrap_jsonld(product)
        result = parse_jsonld_price(html)

        assert result is not None
        assert result.price is None

    def test_price_zero_decimal_string(self):
        html = _wrap_jsonld(_product_jsonld(price="0.00"))
        result = parse_jsonld_price(html)

        assert result is not None
        assert result.price is None


# ---------------------------------------------------------------------------
# Missing / absent fields
# ---------------------------------------------------------------------------


class TestParseJsonldPriceMissing:
    """U13, U14, U16: Missing price, offers, or JSON-LD blocks."""

    def test_missing_price_field(self):
        """U13: Offers block exists but has no 'price' key."""
        product = _product_jsonld()
        del product["offers"]["price"]
        html = _wrap_jsonld(product)
        result = parse_jsonld_price(html)

        assert result is not None
        assert result.price is None
        assert result.currency == "BRL"

    def test_missing_offers_block(self):
        """U16: Product JSON-LD without offers key."""
        html = _wrap_jsonld(_product_jsonld(include_offers=False))
        result = parse_jsonld_price(html)

        assert result is not None
        assert result.price is None
        assert result.currency == "BRL"
        assert result.availability == "Unknown"


# ---------------------------------------------------------------------------
# No JSON-LD / no Product type
# ---------------------------------------------------------------------------


class TestParseJsonldPriceNoJsonLd:
    """U14, U15: No JSON-LD blocks or no Product type."""

    def test_no_jsonld_tags(self):
        """U14: Plain HTML without JSON-LD script tags."""
        html = "<html><head><title>Test</title></head><body><p>Hello</p></body></html>"
        result = parse_jsonld_price(html)

        assert result is None

    def test_empty_html(self):
        """Empty HTML string."""
        result = parse_jsonld_price("")

        assert result is None

    def test_none_input(self):
        """None input (defensive)."""
        result = parse_jsonld_price(None)  # type: ignore[arg-type]

        assert result is None

    def test_no_product_type(self):
        """JSON-LD exists but is not Product type (e.g., Organization, WebSite)."""
        org = {"@type": "Organization", "name": "MYP Cards"}
        website = {"@type": "WebSite", "name": "MYP Cards"}
        html = _wrap_jsonld(
            org,
            extra_scripts=(f'<script type="application/ld+json">{json.dumps(website)}</script>'),
        )
        result = parse_jsonld_price(html)

        assert result is None


# ---------------------------------------------------------------------------
# Malformed JSON
# ---------------------------------------------------------------------------


class TestParseJsonldPriceMalformed:
    """U15: Malformed JSON in script tag."""

    def test_broken_json(self):
        html = (
            '<html><head><script type="application/ld+json">'
            "{broken json</script></head><body></body></html>"
        )
        result = parse_jsonld_price(html)

        assert result is None

    def test_malformed_first_valid_product_second(self):
        """Malformed first block, valid Product second -- picks the Product."""
        broken = '<script type="application/ld+json">{not valid</script>'
        product = _product_jsonld(price="7.99")
        html = (
            f"<html><head>{broken}"
            f'<script type="application/ld+json">{json.dumps(product)}</script>'
            "</head><body></body></html>"
        )
        result = parse_jsonld_price(html)

        assert result is not None
        assert result.price == Decimal("7.99")


# ---------------------------------------------------------------------------
# Multiple JSON-LD blocks
# ---------------------------------------------------------------------------


class TestParseJsonldPriceMultipleBlocks:
    """U17: Multiple JSON-LD blocks, only one is Product."""

    def test_breadcrumb_first_product_second(self):
        breadcrumb = {
            "@type": "BreadcrumbList",
            "itemListElement": [
                {"@type": "ListItem", "position": 1, "name": "Home"},
            ],
        }
        product = _product_jsonld(price="25.00")
        html = (
            "<html><head>"
            f'<script type="application/ld+json">{json.dumps(breadcrumb)}</script>'
            f'<script type="application/ld+json">{json.dumps(product)}</script>'
            "</head><body></body></html>"
        )
        result = parse_jsonld_price(html)

        assert result is not None
        assert result.price == Decimal("25.00")
        assert result.availability == "InStock"


# ---------------------------------------------------------------------------
# Availability edge cases
# ---------------------------------------------------------------------------


class TestParseJsonldPriceAvailability:
    """U19, U20: Availability field edge cases."""

    def test_availability_plain_string_no_url(self):
        """U19: Availability is already short form without URL prefix."""
        product = _product_jsonld()
        product["offers"]["availability"] = "InStock"
        html = _wrap_jsonld(product)
        result = parse_jsonld_price(html)

        assert result is not None
        assert result.availability == "InStock"

    def test_availability_empty_string(self):
        """U20: Empty availability string."""
        product = _product_jsonld()
        product["offers"]["availability"] = ""
        html = _wrap_jsonld(product)
        result = parse_jsonld_price(html)

        assert result is not None
        assert result.availability == "Unknown"

    def test_availability_missing_key(self):
        """Availability key not present in offers."""
        product = _product_jsonld()
        del product["offers"]["availability"]
        html = _wrap_jsonld(product)
        result = parse_jsonld_price(html)

        assert result is not None
        assert result.availability == "Unknown"
