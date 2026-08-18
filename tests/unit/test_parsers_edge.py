"""Edge-case tests for MYP parsers — covers uncovered branches."""

from decimal import Decimal

from src.parsers.myp import (
    _extract_stat_price,
    _extract_tcg_price,
    _parse_date,
    _to_decimal,
    parse_card_page,
    parse_json_ld_product,
    parse_price_history,
    parse_price_snapshot,
    parse_set_links,
)

# --- parse_json_ld_product edge cases ---


class TestParseJsonLdProductEdge:
    def test_empty_html(self):
        assert parse_json_ld_product("") is None

    def test_no_script_tags(self):
        assert parse_json_ld_product("<html><body>hello</body></html>") is None

    def test_malformed_json_in_ld(self):
        html = '<script type="application/ld+json">{not valid json}</script>'
        assert parse_json_ld_product(html) is None

    def test_json_ld_not_product(self):
        html = '<script type="application/ld+json">{"@type": "BreadcrumbList"}</script>'
        assert parse_json_ld_product(html) is None

    def test_json_ld_with_non_dict(self):
        """Covers the AttributeError branch when JSON-LD is a list."""
        html = '<script type="application/ld+json">[1, 2, 3]</script>'
        assert parse_json_ld_product(html) is None

    def test_multiple_ld_blocks_first_malformed(self):
        """First block is malformed, second is a valid Product."""
        html = (
            '<script type="application/ld+json">{broken</script>'
            '<script type="application/ld+json">'
            '{"@type": "Product", "sku": "magic_dmr_001", "name": "Test"}'
            "</script>"
        )
        result = parse_json_ld_product(html)
        assert result is not None
        assert result["@type"] == "Product"


# --- parse_card_page edge cases ---


class TestParseCardPageEdge:
    def test_no_product_returns_none(self):
        assert parse_card_page("<html></html>", "123", "test") is None

    def test_empty_sku(self):
        html = (
            '<script type="application/ld+json">'
            '{"@type": "Product", "sku": "", "name": "TestCard", "image": ""}'
            "</script>"
        )
        card = parse_card_page(html, "100", "test-card")
        assert card is not None
        assert card.identity.set_code is None
        assert card.identity.collector_number is None

    def test_breadcrumb_different_name(self):
        """When breadcrumb last item name differs from JSON-LD name."""
        html = (
            '<script type="application/ld+json">'
            '{"@type": "Product", "sku": "magic_ltr_451", '
            '"name": "O Um Anel", "image": ""}'
            "</script>"
            '<script type="application/ld+json">'
            '{"@type": "BreadcrumbList", "itemListElement": ['
            '{"name": "Home"}, {"name": "Magic"}, '
            '{"name": "LTR"}, {"name": "The One Ring"}'
            "]}"
            "</script>"
        )
        card = parse_card_page(html, "190887", "o-um-anel")
        assert card is not None
        assert card.identity.name_en == "The One Ring"
        assert card.identity.name_pt == "O Um Anel"

    def test_breadcrumb_malformed_json(self):
        """Covers except branch in breadcrumb parsing (lines 99-100)."""
        html = (
            '<script type="application/ld+json">'
            '{"@type": "Product", "sku": "magic_ltr_451", '
            '"name": "TestCard", "image": ""}'
            "</script>"
            '<script type="application/ld+json">{broken breadcrumb</script>'
        )
        card = parse_card_page(html, "100", "test")
        assert card is not None
        assert card.identity.name_en == "TestCard"

    def test_breadcrumb_non_dict(self):
        """Covers AttributeError branch in breadcrumb parsing."""
        html = (
            '<script type="application/ld+json">'
            '{"@type": "Product", "sku": "magic_ltr_451", '
            '"name": "TestCard", "image": ""}'
            "</script>"
            '<script type="application/ld+json">[1, 2, 3]</script>'
        )
        card = parse_card_page(html, "100", "test")
        assert card is not None

    def test_en_image_url_sets_name_pt(self):
        """When image URL contains _en. and no breadcrumb, name_pt gets set (line 119)."""
        html = (
            '<script type="application/ld+json">'
            '{"@type": "Product", "sku": "magic_ltr_451", '
            '"name": "O Um Anel", '
            '"image": "https://cdn.myp.com/magic_ltr_451_en.jpg"}'
            "</script>"
        )
        card = parse_card_page(html, "190887", "o-um-anel")
        assert card is not None
        assert card.identity.name_pt == "O Um Anel"


# --- parse_price_snapshot edge cases ---


class TestParsePriceSnapshotEdge:
    def test_no_product_returns_none(self):
        assert parse_price_snapshot("<html></html>", "123") is None

    def test_no_price_in_offers(self):
        html = (
            '<script type="application/ld+json">'
            '{"@type": "Product", "sku": "magic_test_1", '
            '"name": "Test", "offers": {}}'
            "</script>"
        )
        snap = parse_price_snapshot(html, "100")
        assert snap is not None
        assert snap.min_price is None

    def test_no_offers_key(self):
        html = (
            '<script type="application/ld+json">'
            '{"@type": "Product", "sku": "magic_test_1", "name": "Test"}'
            "</script>"
        )
        snap = parse_price_snapshot(html, "100")
        assert snap is not None
        assert snap.min_price is None


# --- parse_price_history edge cases ---


class TestParsePriceHistoryEdge:
    def test_no_chart_config(self):
        assert parse_price_history("<html>no chart here</html>", "123") == []

    def test_malformed_chart_config_json(self):
        html = "window.precoChartConfig = {not valid json};"
        assert parse_price_history(html, "123") == []

    def test_invalid_date_label_skipped(self):
        """Date that can't be parsed should be skipped (line 194)."""
        html = (
            'window.precoChartConfig = {"labels": ["not-a-date", "01/01/2024"], '
            '"series": [{"key": "mediana", "dados": [10.0, 20.0]}]};'
        )
        prices = parse_price_history(html, "100")
        assert len(prices) == 1
        assert prices[0].median_price == Decimal("20.0")

    def test_empty_labels(self):
        html = 'window.precoChartConfig = {"labels": [], "series": []};'
        assert parse_price_history(html, "100") == []

    def test_series_shorter_than_labels(self):
        """When series data is shorter than labels, missing entries get None."""
        html = (
            'window.precoChartConfig = {"labels": ["01/01/2024", "02/01/2024"], '
            '"series": [{"key": "mediana", "dados": [10.0]}]};'
        )
        prices = parse_price_history(html, "100")
        assert len(prices) == 2
        assert prices[0].median_price == Decimal("10.0")
        assert prices[1].median_price is None


# --- parse_set_links edge cases ---


class TestParseSetLinksEdge:
    def test_empty_html(self):
        assert parse_set_links("") == []

    def test_no_matching_links(self):
        html = '<a href="/other/page">Link</a>'
        assert parse_set_links(html) == []

    def test_excluded_slugs_filtered(self):
        html = (
            '<a href="/magic/edicoes">Editions</a>'
            '<a href="/magic/produto">Product</a>'
            '<a href="/magic/preco">Price</a>'
        )
        assert parse_set_links(html) == []


# --- Helper function edge cases ---


class TestToDecimalEdge:
    def test_none_returns_none(self):
        assert _to_decimal(None) is None

    def test_invalid_string(self):
        assert _to_decimal("not-a-number") is None

    def test_empty_string(self):
        assert _to_decimal("") is None

    def test_whitespace_only(self):
        assert _to_decimal("   ") is None

    def test_integer_input(self):
        assert _to_decimal(42) == Decimal("42")

    def test_float_input(self):
        assert _to_decimal(3.14) == Decimal("3.14")

    def test_comma_decimal_separator(self):
        assert _to_decimal("10,50") == Decimal("10.50")


class TestParseDateEdge:
    def test_valid_date(self):
        from datetime import date

        assert _parse_date("15/03/2024") == date(2024, 3, 15)

    def test_invalid_date_returns_none(self):
        assert _parse_date("not-a-date") is None

    def test_empty_string(self):
        assert _parse_date("") is None

    def test_wrong_format(self):
        assert _parse_date("2024-03-15") is None


class TestExtractStatPrice:
    def test_finds_price(self):
        html = '<div class="stat-media">Mediana: R$ 25,50</div>'
        result = _extract_stat_price(html, "stat-media")
        assert result == Decimal("25.50")

    def test_no_match_returns_none(self):
        html = "<div>No price here</div>"
        assert _extract_stat_price(html, "stat-media") is None


class TestExtractTcgPrice:
    def test_no_match_returns_none(self):
        html = "<div>No TCG price</div>"
        assert _extract_tcg_price(html) is None

    def test_finds_tcg_price(self):
        html = '<span class="estat-tcg other">TCG: R$ 15,00</span>'
        result = _extract_tcg_price(html)
        assert result == Decimal("15.00")
