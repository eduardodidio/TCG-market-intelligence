"""Tests for src.services.purchase_parser."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from src.services.purchase_parser import (
    _split_bilingual_name,
    parse_brl_price,
    parse_price_with_currency,
    parse_purchase_html,
)

# ---------------------------------------------------------------------------
# Price parsing
# ---------------------------------------------------------------------------


class TestParseBrlPrice:
    def test_simple_price(self):
        assert parse_brl_price("R$ 9,75") == Decimal("9.75")

    def test_price_with_unid_suffix(self):
        assert parse_brl_price("R$ 0,20 (unid.)") == Decimal("0.20")

    def test_price_with_thousands_separator(self):
        assert parse_brl_price("R$ 1.234,56") == Decimal("1234.56")

    def test_price_zero(self):
        assert parse_brl_price("R$ 0,00") == Decimal("0.00")

    def test_large_price(self):
        assert parse_brl_price("R$ 179,90 (unid.)") == Decimal("179.90")

    def test_invalid_price_returns_zero(self):
        assert parse_brl_price("free") == Decimal("0")

    def test_dot_decimal_is_not_thousands(self):
        """Regression: '12.50' must parse as 12.50, not 1250."""
        assert parse_brl_price("12.50") == Decimal("12.50")

    def test_bare_thousands_with_brl_hint(self):
        assert parse_brl_price("1.234") == Decimal("1234")

    def test_nbsp_price(self):
        assert parse_brl_price("R$\xa09,75") == Decimal("9.75")

    def test_empty_price_returns_zero(self):
        assert parse_brl_price("") == Decimal("0")

    def test_garbage_returns_zero_no_exception(self):
        assert parse_brl_price("—") == Decimal("0")

    def test_minimum_boundary(self):
        assert parse_brl_price("R$ 0,01") == Decimal("0.01")

    def test_maximum_boundary(self):
        assert parse_brl_price("R$ 999.999,99") == Decimal("999999.99")


class TestParsePriceWithCurrency:
    def test_usd_symbol(self):
        assert parse_price_with_currency("US$ 3.10") == (Decimal("3.10"), "USD")

    def test_brl_symbol(self):
        assert parse_price_with_currency("R$ 9,75") == (Decimal("9.75"), "BRL")

    def test_no_symbol_defaults_to_brl(self):
        assert parse_price_with_currency("12,50") == (Decimal("12.50"), "BRL")

    def test_empty_defaults_to_brl_zero(self):
        assert parse_price_with_currency("") == (Decimal("0"), "BRL")


# ---------------------------------------------------------------------------
# Bilingual name parsing
# ---------------------------------------------------------------------------


class TestSplitBilingualName:
    def test_bilingual(self):
        pt, en = _split_bilingual_name("Fogo do Dragão / Dragon's Fire")
        assert pt == "Fogo do Dragão"
        assert en == "Dragon's Fire"

    def test_english_only(self):
        pt, en = _split_bilingual_name("Terror of the Peaks")
        assert pt is None
        assert en == "Terror of the Peaks"

    def test_portuguese_only_with_accent(self):
        pt, en = _split_bilingual_name("Dragão Ancestral")
        assert pt == "Dragão Ancestral"
        assert en is None

    def test_english_only_no_accents(self):
        pt, en = _split_bilingual_name("Belladonna Took")
        assert pt is None
        assert en == "Belladonna Took"

    def test_bilingual_with_apostrophe(self):
        pt, en = _split_bilingual_name("Triunfo de Sarkhan / Sarkhan's Triumph")
        assert pt == "Triunfo de Sarkhan"
        assert en == "Sarkhan's Triumph"


# ---------------------------------------------------------------------------
# Nerdz Cards parser
# ---------------------------------------------------------------------------


NERDZ_SINGLE_CARD_HTML = """
<html>
<head><title>Pedido #9117259 | Nerdz Cards</title></head>
<body>
<div class="panel-body panel-order--number">
    <h3>#9117259</h3>
    <div align="center" style="color:#c3c9c4;"><i>25/08/2025 17:01</i></div>
</div>
<article class="panel-order--content layout-standard">
    <div class="row">
        <div class="col-xs-12 col-sm-6 col-md-6">
            <p>
                <span class="bold">3x</span> <a class="link-produto" href="#">
                    <span class="bold">Fogo do Dragão</span>  / Dragon's Fire
                    <font class="input-infoaux">(Código: AFR<b>139</b>)</font>
                </a>
            </p>
        </div>
        <div class="col-xs-6 col-sm-3 col-md-3">
            <p>R$ 0,20 (unid.)</p>
        </div>
    </div>
    <div class="row m-top-xs">
        <div class="col-xs-6 col-sm-3">
            <img src="AFR_C.gif" title="Adventures in the Forgotten Realms"
                 class="icon icon-edicao" height="21">
        </div>
        <div class="col-xs-3 col-sm-1">
            <img alt="Português" src="pt.svg" width="20" height="20">&nbsp;PT
        </div>
        <div class="col-xs-3 col-sm-1" title="Praticamente Nova (NM)">
            <div class="icon_qualid icon_qualid_2" title="Praticamente Nova (NM)">NM</div>
        </div>
    </div>
</article>
</body>
</html>
"""


class TestNerdzParser:
    def test_single_card(self):
        orders = parse_purchase_html(NERDZ_SINGLE_CARD_HTML, "test.html")
        assert len(orders) == 1
        order = orders[0]
        assert order.order_number == "#9117259"
        assert order.order_date == date(2025, 8, 25)
        assert order.store_name == "Nerdz Cards"
        assert len(order.items) == 1
        item = order.items[0]
        assert item.card_name_pt == "Fogo do Dragão"
        assert item.card_name_en == "Dragon's Fire"
        assert item.set_code == "AFR"
        assert item.collector_number == "139"
        assert item.quantity == 3
        assert item.unit_price == Decimal("0.20")
        assert item.language == "PT"
        assert item.quality == "NM"
        assert item.is_foil is False
        assert item.set_name == "Adventures in the Forgotten Realms"

    def test_order_date(self):
        orders = parse_purchase_html(NERDZ_SINGLE_CARD_HTML, "test.html")
        assert orders[0].order_date == date(2025, 8, 25)

    def test_quantity_parsing(self):
        orders = parse_purchase_html(NERDZ_SINGLE_CARD_HTML, "test.html")
        assert orders[0].items[0].quantity == 3


NERDZ_FOIL_HTML = """
<html>
<head><title>Pedido #9117260 | Nerdz Cards</title></head>
<body>
<div class="panel-body panel-order--number">
    <h3>#9117260</h3>
    <div align="center"><i>25/08/2025 17:01</i></div>
</div>
<article class="panel-order--content layout-standard">
    <div class="row">
        <div class="col-xs-12 col-sm-6 col-md-6">
            <p>
                <span class="bold">1x</span> <a class="link-produto" href="#">
                    <span class="bold">Fogo do Dragão</span>  / Dragon's Fire
                    <font class="input-infoaux">(Código: AFR<b>139</b>)</font>
                </a>
            </p>
        </div>
        <div class="col-xs-6 col-sm-3">
            <p>R$ 1,00 (unid.)</p>
        </div>
    </div>
    <div class="row m-top-xs">
        <div class="col-xs-12 col-sm-12">
            <span class="extras-pedido">
                <img src="alertR.png" width="15" height="15"> Foil
            </span>
        </div>
    </div>
</article>
</body>
</html>
"""


class TestNerdzFoil:
    def test_foil_detection(self):
        orders = parse_purchase_html(NERDZ_FOIL_HTML, "test.html")
        item = orders[0].items[0]
        assert item.is_foil is True
        assert "Foil" in item.extras


NERDZ_SEALED_HTML = """
<html>
<head><title>Pedido #5282134 | Nerdz Cards</title></head>
<body>
<div class="panel-body panel-order--number">
    <h3>#5282134</h3>
    <div align="center"><i>01/01/2025 10:00</i></div>
</div>
<article class="panel-order--content layout-standard">
    <div class="row">
        <div class="col-xs-12 col-sm-6 col-md-6">
            <p>
                <span class="bold">1x</span> <a class="link-produto" href="#">
                    <span class="bold">Kit Inicial - O Senhor dos Anéis</span>
                </a>
            </p>
        </div>
        <div class="col-xs-6 col-sm-3">
            <p>R$ 199,90 (unid.)</p>
        </div>
    </div>
</article>
</body>
</html>
"""


class TestNerdzSealed:
    def test_sealed_product_skipped(self):
        orders = parse_purchase_html(NERDZ_SEALED_HTML, "test.html")
        assert len(orders) == 1
        assert len(orders[0].items) == 0


NERDZ_EN_ONLY_HTML = """
<html>
<head><title>Pedido #9999 | Nerdz Cards</title></head>
<body>
<div class="panel-body panel-order--number">
    <h3>#9999</h3>
    <div align="center"><i>10/01/2025 12:00</i></div>
</div>
<article class="panel-order--content layout-standard">
    <div class="row">
        <div class="col-xs-12 col-sm-6 col-md-6">
            <p>
                <span class="bold">1x</span> <a class="link-produto" href="#">
                    <span class="bold">Terror of the Peaks</span>  / Terror dos Picos
                    <font class="input-infoaux">(Código: M21<b>164</b>)</font>
                </a>
            </p>
        </div>
        <div class="col-xs-6 col-sm-3">
            <p>R$ 179,90 (unid.)</p>
        </div>
    </div>
    <div class="row m-top-xs">
        <div class="col-xs-3 col-sm-1">
            <img alt="Inglês" src="en.svg" width="20" height="20">&nbsp;EN
        </div>
    </div>
</article>
</body>
</html>
"""


class TestNerdzEnOnly:
    def test_en_card_in_bold(self):
        """When the bold text IS the English name, parse correctly.

        The link text ``Terror of the Peaks / Terror dos Picos`` splits
        on `` / ``, producing pt="Terror of the Peaks" and en="Terror dos
        Picos".  The `` / `` convention in Nerdz is **bold = first name**
        (which may be EN or PT).  The matcher handles cross-language
        matching so both names are available regardless of which slot they
        land in.
        """
        orders = parse_purchase_html(NERDZ_EN_ONLY_HTML, "test.html")
        item = orders[0].items[0]
        # The " / " split produces first=PT slot, second=EN slot.
        assert item.card_name_pt == "Terror of the Peaks"
        assert item.card_name_en == "Terror dos Picos"
        assert item.language == "EN"


NERDZ_SET_CODE_PROMO_HTML = """
<html>
<head><title>Pedido #8888 | Nerdz Cards</title></head>
<body>
<div class="panel-body panel-order--number">
    <h3>#8888</h3>
    <div align="center"><i>10/01/2025 12:00</i></div>
</div>
<article class="panel-order--content layout-standard">
    <div class="row">
        <div class="col-xs-12 col-sm-6 col-md-6">
            <p>
                <span class="bold">1x</span> <a class="link-produto" href="#">
                    <span class="bold">Test Card</span>
                    <font class="input-infoaux">(Código: PRMID<b>390</b>)</font>
                </a>
            </p>
        </div>
        <div class="col-xs-6 col-sm-3">
            <p>R$ 5,00 (unid.)</p>
        </div>
    </div>
</article>
</body>
</html>
"""


class TestNerdzSetCode:
    def test_promo_set_code_extraction(self):
        """Set code 'PRMID' and collector number '390' extracted."""
        orders = parse_purchase_html(NERDZ_SET_CODE_PROMO_HTML, "test.html")
        item = orders[0].items[0]
        assert item.set_code == "PRMID"
        assert item.collector_number == "390"


# ---------------------------------------------------------------------------
# Auto-detection
# ---------------------------------------------------------------------------


class TestAutoDetection:
    def test_nerdz_detected(self):
        html = "<html><head><title>Pedido #123 | Nerdz Cards</title></head><body></body></html>"
        orders = parse_purchase_html(html, "nerdz.html")
        assert isinstance(orders, list)

    def test_unknown_format_raises(self):
        html = "<html><head><title>Unknown Store</title></head><body></body></html>"
        with pytest.raises(ValueError, match="Unrecognized HTML format"):
            parse_purchase_html(html, "unknown.html")


# ---------------------------------------------------------------------------
# Source file tracking
# ---------------------------------------------------------------------------


class TestSourceFile:
    def test_source_file_set(self):
        orders = parse_purchase_html(NERDZ_SINGLE_CARD_HTML, "myfile.html")
        assert orders[0].source_file == "myfile.html"
        assert orders[0].items[0].source_file == "myfile.html"


# ---------------------------------------------------------------------------
# Currency-aware prices (F171-T05)
# ---------------------------------------------------------------------------


class TestCurrencyAwarePrices:
    def test_default_currency_is_brl(self):
        orders = parse_purchase_html(NERDZ_SINGLE_CARD_HTML, "test.html")
        assert orders[0].items[0].currency == "BRL"
