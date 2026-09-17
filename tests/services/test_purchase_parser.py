"""Tests for src.services.purchase_parser."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from src.services.purchase_parser import (
    _split_bilingual_name,
    parse_brl_price,
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
# Liga Magic parser
# ---------------------------------------------------------------------------


LIGA_EXPANDED_HTML = """
<html>
<head><title>Meus Pedidos | LigaMagic</title></head>
<body>
<div class="boxshadow conteudo box-interna">
    <font class="titleorder">#MP1247013</font><br>
    <font class="titledate">(27 dias atrás - 21/08/2026 22:32)</font>
    <div class="venda-device" id="venda_mp_1247013">
        <div class="vendasheader"><b>Vendido e entregue por</b></div>
        <div class="row infovendas infovendas-prim" id="pedido_main_11752528">
            <div class="col-lg-2 venda-store">
                <label class="title">RED Jogos</label>
                <label class="aux"><a href="#" class="laranja">#11752528</a></label>
            </div>
            <div class="col-lg-2 venda-view" onclick="sale.showItens(11752528);">
                Visualizar Itens
            </div>
        </div>
        <div id="venda_11752528" class="infovenda-cards venda-selected">
            <div id="meucarrinho">
                <div class="row header hidden-xs">
                    <div class="col-lg-7">&nbsp;Card</div>
                </div>
                <div class="itens">
                    <div class="row">
                        <div class="col-lg-7 main-item">
                            <table>
                                <tr>
                                    <td>
                                        <p class="cardtitle" cardtitle="">
                                            <a href="?view=cards/card&card=Dragon+Tempest&ed=dtk"
                                               class="pretoG b">
                                                Tempestade Dragônica / Dragon Tempest
                                            </a>
                                        </p>
                                        <table id="carrinho-extras">
                                            <tr>
                                                <td editioncard="">
                                                    <a href="?view=cards/search&card=ed=DTK">
                                                        <img src="DTK_R.gif"
                                                             title="Dragões de Tarkir"
                                                             class="icon icon-edicao"
                                                             height="21">
                                                    </a>
                                                </td>
                                                <td class="label hidden-md">
                                                    <a href="#">Dragões de Tarkir</a>
                                                </td>
                                                <td class="icone" languagecard="">
                                                    <img alt="Inglês" src="en.svg" width="20">
                                                </td>
                                                <td class="label">EN</td>
                                                <td class="label" qualitycard="">
                                                    <a class="azul"
                                                       title="Praticamente Nova (NM)">NM</a>
                                                </td>
                                            </tr>
                                        </table>
                                    </td>
                                </tr>
                            </table>
                        </div>
                        <div class="col-lg-1 item-estoque">1 unid.</div>
                        <div class="col-lg-2 preco item-subpreco">R$ 9,75</div>
                        <div class="col-lg-2 item-xs-total">
                            <div class="preco-total item-total">R$ 9,75</div>
                        </div>
                    </div>
                    <div class="row zebra">
                        <div class="col-lg-7 main-item">
                            <table>
                                <tr>
                                    <td>
                                        <p class="cardtitle" cardtitle="">
                                            <a class="pretoG b"
                                               href="?view=cards/card&card=Sarkhan%27s+Triumph&ed=dtk">
                                                Triunfo de Sarkhan / Sarkhan's Triumph
                                            </a>
                                        </p>
                                        <table id="carrinho-extras">
                                            <tr>
                                                <td editioncard="">
                                                    <a href="?view=cards/search&card=ed=DTK">
                                                        <img src="DTK_U.gif"
                                                             title="Dragões de Tarkir"
                                                             class="icon icon-edicao"
                                                             height="21">
                                                    </a>
                                                </td>
                                                <td class="label hidden-md">
                                                    <a href="#">Dragões de Tarkir</a>
                                                </td>
                                                <td class="icone" languagecard="">
                                                    <img alt="Português" src="pt.svg" width="20">
                                                </td>
                                                <td class="label">PT</td>
                                                <td class="label" qualitycard="">
                                                    <a class="azul"
                                                       title="Praticamente Nova (NM)">NM</a>
                                                </td>
                                            </tr>
                                        </table>
                                    </td>
                                </tr>
                            </table>
                        </div>
                        <div class="col-lg-1 item-estoque">1 unid.</div>
                        <div class="col-lg-2 preco item-subpreco">R$ 9,50</div>
                        <div class="col-lg-2 item-xs-total">
                            <div class="preco-total item-total">R$ 9,50</div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>
</div>
</body>
</html>
"""


class TestLigaParser:
    def test_expanded_order(self):
        orders = parse_purchase_html(LIGA_EXPANDED_HTML, "liga.html")
        assert len(orders) == 1
        order = orders[0]
        assert order.store_name == "RED Jogos"
        assert order.order_date == date(2026, 8, 21)
        assert len(order.items) == 2

    def test_card_names(self):
        orders = parse_purchase_html(LIGA_EXPANDED_HTML, "liga.html")
        item = orders[0].items[0]
        assert item.card_name_pt == "Tempestade Dragônica"
        assert item.card_name_en == "Dragon Tempest"

    def test_card_set(self):
        orders = parse_purchase_html(LIGA_EXPANDED_HTML, "liga.html")
        item = orders[0].items[0]
        assert item.set_name == "Dragões de Tarkir"

    def test_card_price(self):
        orders = parse_purchase_html(LIGA_EXPANDED_HTML, "liga.html")
        assert orders[0].items[0].unit_price == Decimal("9.75")
        assert orders[0].items[1].unit_price == Decimal("9.50")

    def test_card_language(self):
        orders = parse_purchase_html(LIGA_EXPANDED_HTML, "liga.html")
        assert orders[0].items[0].language == "EN"
        assert orders[0].items[1].language == "PT"

    def test_card_quality(self):
        orders = parse_purchase_html(LIGA_EXPANDED_HTML, "liga.html")
        assert orders[0].items[0].quality == "NM"

    def test_card_quantity(self):
        orders = parse_purchase_html(LIGA_EXPANDED_HTML, "liga.html")
        assert orders[0].items[0].quantity == 1

    def test_order_date(self):
        orders = parse_purchase_html(LIGA_EXPANDED_HTML, "liga.html")
        assert orders[0].order_date == date(2026, 8, 21)


LIGA_UNEXPANDED_HTML = """
<html>
<head><title>Meus Pedidos | LigaMagic</title></head>
<body>
<div class="boxshadow conteudo box-interna">
    <font class="titleorder">#11722459</font><br>
    <font class="titledate">(30 dias atrás - 18/08/2026 22:01)</font>
    <div class="venda-device" id="venda_mp_e11722459">
        <div class="vendasheader"><b>Vendido e entregue por</b></div>
        <div class="row infovendas infovendas-prim" id="pedido_main_11722459">
            <div class="col-lg-2 venda-store">
                <label class="title">Nerdz Cards</label>
                <label class="aux"><a href="#" class="laranja">#11722459</a></label>
            </div>
        </div>
        <div id="venda_11722459" class="infovenda-cards" style="display:none;">
            <div align="center" class="loading-itens">
                <img src="loading-orange.gif" class="loading-mini">
            </div>
        </div>
    </div>
</div>
</body>
</html>
"""


class TestLigaUnexpanded:
    def test_unexpanded_order_skipped(self):
        orders = parse_purchase_html(LIGA_UNEXPANDED_HTML, "liga.html")
        assert len(orders) == 0


# ---------------------------------------------------------------------------
# Auto-detection
# ---------------------------------------------------------------------------


class TestAutoDetection:
    def test_nerdz_detected(self):
        html = "<html><head><title>Pedido #123 | Nerdz Cards</title></head><body></body></html>"
        orders = parse_purchase_html(html, "nerdz.html")
        assert isinstance(orders, list)

    def test_liga_detected(self):
        html = "<html><head><title>Meus Pedidos | LigaMagic</title></head><body></body></html>"
        orders = parse_purchase_html(html, "liga.html")
        assert isinstance(orders, list)

    def test_unknown_format_raises(self):
        html = "<html><head><title>Unknown Store</title></head><body></body></html>"
        with pytest.raises(ValueError, match="Unrecognized HTML format"):
            parse_purchase_html(html, "unknown.html")


# ---------------------------------------------------------------------------
# Multi-store Liga order
# ---------------------------------------------------------------------------


LIGA_MULTI_STORE_HTML = """
<html>
<head><title>Meus Pedidos | LigaMagic</title></head>
<body>
<div class="boxshadow conteudo box-interna">
    <font class="titleorder">#MP1239095</font><br>
    <font class="titledate">(32 dias atrás - 16/08/2026 22:00)</font>
    <div class="venda-device" id="venda_mp_1239095">
        <div class="vendasheader"><b>Vendido e entregue por</b></div>
        <div class="row infovendas infovendas-prim pedido-selected" id="pedido_main_11703922">
            <div class="col-lg-2 venda-store">
                <label class="title">Matuto Cards</label>
                <label class="aux"><a href="#" class="laranja">#11703922</a></label>
            </div>
        </div>
        <div id="venda_11703922" class="infovenda-cards venda-selected">
            <div id="meucarrinho">
                <div class="row header hidden-xs"><div>Card</div></div>
                <div class="itens">
                    <div class="row">
                        <div class="col-lg-7 main-item">
                            <table><tr><td>
                                <p class="cardtitle" cardtitle="">
                                    <a href="#" class="pretoG b">Card A / Card A EN</a>
                                </p>
                                <table id="carrinho-extras"><tr>
                                    <td editioncard=""><a href="?card=ed=MH3">
                                        <img src="MH3_R.gif" title="Modern Horizons 3"
                                             class="icon icon-edicao" height="21"></a></td>
                                    <td class="icone" languagecard="">
                                        <img alt="Português" src="pt.svg"></td>
                                    <td class="label">PT</td>
                                    <td class="label" qualitycard="">
                                        <a title="Praticamente Nova (NM)">NM</a></td>
                                </tr></table>
                            </td></tr></table>
                        </div>
                        <div class="col-lg-1 item-estoque">2 unid.</div>
                        <div class="col-lg-2 preco item-subpreco">R$ 5,00</div>
                        <div class="col-lg-2 item-xs-total">
                            <div class="preco-total item-total">R$ 10,00</div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
        <div class="row infovendas infovendas-ult pedido-selected" id="pedido_main_11703999">
            <div class="col-lg-2 venda-store">
                <label class="title">Another Store</label>
                <label class="aux"><a href="#" class="laranja">#11703999</a></label>
            </div>
        </div>
        <div id="venda_11703999" class="infovenda-cards venda-selected">
            <div id="meucarrinho">
                <div class="row header hidden-xs"><div>Card</div></div>
                <div class="itens">
                    <div class="row">
                        <div class="col-lg-7 main-item">
                            <table><tr><td>
                                <p class="cardtitle" cardtitle="">
                                    <a href="#" class="pretoG b">Card B / Card B EN</a>
                                </p>
                                <table id="carrinho-extras"><tr>
                                    <td editioncard=""><a href="?card=ed=FDN">
                                        <img src="FDN_C.gif" title="Foundations"
                                             class="icon icon-edicao" height="21"></a></td>
                                    <td class="icone" languagecard="">
                                        <img alt="Inglês" src="en.svg"></td>
                                    <td class="label">EN</td>
                                    <td class="label" qualitycard="">
                                        <a title="SP">SP</a></td>
                                </tr></table>
                            </td></tr></table>
                        </div>
                        <div class="col-lg-1 item-estoque">1 unid.</div>
                        <div class="col-lg-2 preco item-subpreco">R$ 15,50</div>
                        <div class="col-lg-2 item-xs-total">
                            <div class="preco-total item-total">R$ 15,50</div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>
</div>
</body>
</html>
"""


class TestLigaMultiStore:
    def test_multi_store_separate_orders(self):
        orders = parse_purchase_html(LIGA_MULTI_STORE_HTML, "liga.html")
        assert len(orders) == 2
        assert orders[0].store_name == "Matuto Cards"
        assert orders[1].store_name == "Another Store"

    def test_multi_store_items(self):
        orders = parse_purchase_html(LIGA_MULTI_STORE_HTML, "liga.html")
        assert len(orders[0].items) == 1
        assert orders[0].items[0].card_name_pt == "Card A"
        assert orders[0].items[0].card_name_en == "Card A EN"
        assert orders[0].items[0].quantity == 2
        assert orders[0].items[0].unit_price == Decimal("5.00")

        assert len(orders[1].items) == 1
        assert orders[1].items[0].card_name_pt == "Card B"
        assert orders[1].items[0].card_name_en == "Card B EN"
        assert orders[1].items[0].quality == "SP"


# ---------------------------------------------------------------------------
# Source file tracking
# ---------------------------------------------------------------------------


class TestSourceFile:
    def test_source_file_set(self):
        orders = parse_purchase_html(NERDZ_SINGLE_CARD_HTML, "myfile.html")
        assert orders[0].source_file == "myfile.html"
        assert orders[0].items[0].source_file == "myfile.html"
