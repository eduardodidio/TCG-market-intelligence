"""Tests for MYP Cards parsers using saved HTML fixtures."""

from pathlib import Path

import pytest

from src.parsers.myp import (
    parse_card_links,
    parse_card_page,
    parse_json_ld_product,
    parse_pagination_max,
    parse_price_history,
    parse_price_snapshot,
    parse_set_links,
    parse_sku,
)

FIXTURES = Path(__file__).parent.parent / "fixtures"


def _load(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


# --- SKU parsing ---


class TestParseSku:
    def test_standard_sku(self):
        set_code, num = parse_sku("magic_ltr_748")
        assert set_code == "ltr"
        assert num == "748"

    def test_three_letter_set(self):
        set_code, num = parse_sku("magic_dmr_045")
        assert set_code == "dmr"
        assert num == "045"

    def test_invalid_sku(self):
        assert parse_sku("invalid") == (None, None)

    def test_empty_sku(self):
        assert parse_sku("") == (None, None)


# --- Editions page ---


class TestParseSetLinks:
    @pytest.fixture
    def editions_html(self):
        return _load("editions_page_1.html")

    def test_finds_sets(self, editions_html):
        slugs = parse_set_links(editions_html)
        assert len(slugs) > 10
        # Should contain known sets
        assert any("reality-fracture" in s or "foundations" in s for s in slugs)

    def test_excludes_produto_links(self, editions_html):
        slugs = parse_set_links(editions_html)
        assert "produto" not in slugs
        assert "edicoes" not in slugs


# --- Set card listing ---


class TestParseCardLinks:
    @pytest.fixture
    def set_html(self):
        return _load("set_page_dmr.html")

    def test_finds_cards(self, set_html):
        cards = parse_card_links(set_html)
        assert len(cards) >= 20
        # Each card is (id, slug) tuple
        for card_id, slug in cards:
            assert card_id.isdigit()
            assert len(slug) > 0

    def test_cards_are_unique(self, set_html):
        cards = parse_card_links(set_html)
        ids = [c[0] for c in cards]
        assert len(ids) == len(set(ids))


# --- Card page ---


class TestParseCardPage:
    @pytest.fixture
    def card_html(self):
        return _load("card_page_one_ring.html")

    def test_parses_json_ld(self, card_html):
        product = parse_json_ld_product(card_html)
        assert product is not None
        assert product["@type"] == "Product"
        assert "productID" in product
        assert product["sku"].startswith("magic_")

    def test_parses_card(self, card_html):
        card = parse_card_page(card_html, "190887", "o-um-anel")
        assert card is not None
        assert card.source == "myp"
        assert card.external_id == "190887"
        assert card.sku == "magic_ltr_451"
        assert card.identity is not None
        assert card.identity.game == "magic"
        assert card.identity.set_code == "ltr"
        assert card.identity.collector_number == "451"

    def test_card_has_url(self, card_html):
        card = parse_card_page(card_html, "190887", "o-um-anel")
        assert "190887" in card.url
        assert "o-um-anel" in card.url


class TestParsePriceSnapshot:
    @pytest.fixture
    def card_html(self):
        return _load("card_page_one_ring.html")

    def test_extracts_price(self, card_html):
        snap = parse_price_snapshot(card_html, "190887")
        assert snap is not None
        assert snap.source == "myp"
        assert snap.min_price is not None
        assert snap.min_price > 0
        assert snap.currency == "BRL"


# --- Price history ---


class TestParsePriceHistory:
    @pytest.fixture
    def history_html(self):
        return _load("price_history_one_ring.html")

    def test_parses_history(self, history_html):
        prices = parse_price_history(history_html, "190887")
        assert len(prices) > 0

    def test_history_has_dates(self, history_html):
        prices = parse_price_history(history_html, "190887")
        for p in prices:
            assert p.observed_at is not None
            assert p.source == "myp"
            assert p.external_id == "190887"

    def test_history_has_prices(self, history_html):
        prices = parse_price_history(history_html, "190887")
        has_median = any(p.median_price is not None for p in prices)
        assert has_median

    def test_history_chronological(self, history_html):
        prices = parse_price_history(history_html, "190887")
        dates = [p.observed_at for p in prices]
        assert dates == sorted(dates)

    def test_no_duplicate_dates(self, history_html):
        prices = parse_price_history(history_html, "190887")
        dates = [p.observed_at for p in prices]
        assert len(dates) == len(set(dates))


# --- Pagination ---


class TestParsePaginationMax:
    def test_finds_max_page(self):
        html = '<a href="?page=1">1</a> <a href="?page=5">5</a> <a href="?page=48">48</a>'
        assert parse_pagination_max(html) == 48

    def test_single_page(self):
        html = '<a href="?page=1">1</a>'
        assert parse_pagination_max(html) == 1

    def test_no_pagination(self):
        html = "<p>No pages</p>"
        assert parse_pagination_max(html) == 1
