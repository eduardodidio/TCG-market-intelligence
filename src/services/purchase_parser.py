"""Parse purchase HTML files from Nerdz Cards and Liga Magic.

Extracts card purchase data (name, set, quantity, unit price, order date)
from saved HTML files.  Two formats are supported:

1. **Nerdz Cards** -- individual order pages (``Pedido #XXXXXXX``).
2. **Liga Magic "Meus Pedidos"** -- aggregate page with multiple orders.

The public entry point is :func:`parse_purchase_html` which auto-detects
the format and returns a list of :class:`ParsedOrder`.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal

from bs4 import BeautifulSoup, Tag

from src.currency.money import parse_money

# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class ParsedPurchaseItem:
    """A single card extracted from a purchase order."""

    card_name_pt: str | None
    card_name_en: str | None
    set_name: str | None
    set_code: str | None
    collector_number: str | None
    language: str | None  # "PT" or "EN"
    quality: str | None  # "NM", "SP", etc.
    quantity: int
    unit_price: Decimal
    is_foil: bool
    extras: list[str]
    order_number: str
    order_date: date | None
    store_name: str
    source_file: str
    currency: str = "BRL"


@dataclass
class ParsedOrder:
    """One purchase order containing multiple items."""

    order_number: str
    order_date: date | None
    store_name: str
    items: list[ParsedPurchaseItem] = field(default_factory=list)
    source_file: str = ""


# ---------------------------------------------------------------------------
# Price parsing
# ---------------------------------------------------------------------------


def parse_brl_price(text: str) -> Decimal:
    """Parse ``R$ 1.234,56`` or ``R$ 9,75`` into a :class:`Decimal`.

    Thin wrapper over :func:`src.currency.money.parse_money` with a BRL
    hint so bare dot-decimal amounts like ``"12.50"`` are not mistaken
    for a thousands-separated ``1250``.
    """
    amount, _ = parse_money(text, hint="BRL")
    return amount if amount is not None else Decimal("0")


def parse_price_with_currency(text: str) -> tuple[Decimal, str]:
    """Parse a price and its currency, defaulting to BRL when no symbol.

    Liga Magic and Nerdz Cards are Brazilian stores, so the absence of a
    currency symbol means BRL; a detected ``USD``/``EUR`` symbol is kept.
    """
    amount, symbol = parse_money(text, hint="BRL")
    return (amount if amount is not None else Decimal("0")), (symbol or "BRL")


# ---------------------------------------------------------------------------
# Bilingual name parsing
# ---------------------------------------------------------------------------

_ACCENTED_RE = re.compile(r"[àáâãäåèéêëìíîïòóôõöùúûüçñ]", re.IGNORECASE)


def _split_bilingual_name(raw: str) -> tuple[str | None, str | None]:
    """Split ``"PT Name / EN Name"`` into ``(pt, en)`` tuple.

    If there is no `` / `` separator the function uses a heuristic:
    names with Portuguese diacritics are treated as PT; otherwise EN.
    """
    raw = raw.strip()
    if " / " in raw:
        parts = raw.split(" / ", 1)
        return parts[0].strip(), parts[1].strip()

    if _ACCENTED_RE.search(raw):
        return raw, None
    return None, raw


# ---------------------------------------------------------------------------
# Quality parsing
# ---------------------------------------------------------------------------

_QUALITY_PARENS_RE = re.compile(r"\((\w+)\)")


def _extract_quality_code(text: str) -> str | None:
    """Extract quality code like ``NM`` from ``Praticamente Nova (NM)``."""
    m = _QUALITY_PARENS_RE.search(text)
    if m:
        return m.group(1)
    text = text.strip()
    if text in {"NM", "SP", "MP", "HP", "D", "L"}:
        return text
    return text if text else None


# ---------------------------------------------------------------------------
# Nerdz Cards parser
# ---------------------------------------------------------------------------

_CODIGO_RE = re.compile(
    r"\(C[oó]digo:\s*([A-Za-z0-9]+?)(\d+[a-z]?)\)",
    re.IGNORECASE,
)


def _parse_nerdz_article(
    article: Tag,
    order_number: str,
    order_date: date | None,
    store_name: str,
    source_file: str,
) -> ParsedPurchaseItem | None:
    """Parse a single ``<article class="panel-order--content">`` element."""
    # --- Skip summary articles (no link-produto) ---
    link = article.select_one("a.link-produto")
    if link is None:
        return None

    # --- Detect sealed products: no (Codigo: ...) ---
    info_font = link.select_one("font.input-infoaux")
    if info_font is None:
        return None

    codigo_text = info_font.get_text()
    codigo_match = _CODIGO_RE.search(codigo_text)
    if not codigo_match:
        return None

    set_code = codigo_match.group(1).upper()
    collector_number = codigo_match.group(2)

    # --- Quantity ---
    # The quantity span appears before the link:  <span class="bold">3x</span>
    qty_span = article.select_one("p > span.bold")
    quantity = 1
    if qty_span:
        qty_text = qty_span.get_text(strip=True)
        m = re.match(r"(\d+)\s*x", qty_text, re.IGNORECASE)
        if m:
            quantity = int(m.group(1))

    # --- Card name (bilingual) ---
    # The link contains <span class="bold">PT Name</span> / EN Name
    # Remove the font.input-infoaux before extracting text
    link_copy = BeautifulSoup(str(link), "html.parser").select_one("a")
    if link_copy is None:
        return None
    for font_tag in link_copy.select("font.input-infoaux"):
        font_tag.decompose()
    raw_name = re.sub(r"\s+", " ", link_copy.get_text()).strip()
    card_name_pt, card_name_en = _split_bilingual_name(raw_name)

    # --- Set name ---
    set_name: str | None = None
    icon_img = article.select_one("img.icon-edicao")
    if icon_img:
        set_name = icon_img.get("title")

    # --- Unit price ---
    unit_price = Decimal("0")
    currency = "BRL"
    price_divs = article.select("div.col-xs-6.col-sm-3 p, div.col-xs-6.col-md-3 p")
    for p_tag in price_divs:
        p_text = p_tag.get_text(strip=True)
        if "(unid.)" in p_text or "unid" in p_text:
            unit_price, currency = parse_price_with_currency(p_text)
            break
    # Fallback: look for any <p> with R$ and (unid.)
    if unit_price == Decimal("0"):
        for p_tag in article.select("p"):
            p_text = p_tag.get_text(strip=True)
            if "R$" in p_text and "(unid.)" in p_text:
                unit_price, currency = parse_price_with_currency(p_text)
                break

    # --- Language ---
    language: str | None = None
    lang_img = article.select_one("img[alt='Português'], img[alt='Portugues']")
    if lang_img:
        language = "PT"
    else:
        lang_img = article.select_one("img[alt='Inglês'], img[alt='Ingles']")
        if lang_img:
            language = "EN"
    # Also check for PT/EN text sibling
    if language is None:
        for div_el in article.select("div"):
            txt = div_el.get_text(strip=True)
            if txt in ("PT", "EN"):
                language = txt
                break

    # --- Quality ---
    quality: str | None = None
    qual_div = article.select_one("div.icon_qualid")
    if qual_div:
        quality = _extract_quality_code(qual_div.get("title", ""))

    # --- Extras / foil ---
    extras: list[str] = []
    is_foil = False
    for extra_span in article.select("span.extras-pedido"):
        extra_text = extra_span.get_text(strip=True)
        if extra_text:
            extras.append(extra_text)
            if "foil" in extra_text.lower():
                is_foil = True

    return ParsedPurchaseItem(
        card_name_pt=card_name_pt,
        card_name_en=card_name_en,
        set_name=set_name,
        set_code=set_code,
        collector_number=collector_number,
        language=language,
        quality=quality,
        quantity=quantity,
        unit_price=unit_price,
        is_foil=is_foil,
        extras=extras,
        order_number=order_number,
        order_date=order_date,
        store_name=store_name,
        source_file=source_file,
        currency=currency,
    )


def parse_nerdz_order(soup: BeautifulSoup, filename: str) -> ParsedOrder:
    """Parse a single Nerdz Cards order page."""
    # --- Order number ---
    order_number = ""
    for h3 in soup.select("h3"):
        h3_text = h3.get_text(strip=True)
        if h3_text.startswith("#"):
            order_number = h3_text
            break

    # --- Order date ---
    order_date: date | None = None
    order_panel = soup.select_one("div.panel-order--number")
    if order_panel:
        for i_tag in order_panel.select("i"):
            date_text = i_tag.get_text(strip=True)
            try:
                dt = datetime.strptime(date_text, "%d/%m/%Y %H:%M")
                order_date = dt.date()
                break
            except ValueError:
                continue

    store_name = "Nerdz Cards"

    # --- Card items ---
    items: list[ParsedPurchaseItem] = []
    for article in soup.select("article.panel-order--content"):
        if "layout-standard" not in article.get("class", []):
            continue
        item = _parse_nerdz_article(article, order_number, order_date, store_name, filename)
        if item is not None:
            items.append(item)

    return ParsedOrder(
        order_number=order_number,
        order_date=order_date,
        store_name=store_name,
        items=items,
        source_file=filename,
    )


# ---------------------------------------------------------------------------
# Liga Magic parser
# ---------------------------------------------------------------------------

_DATE_RE = re.compile(r"(\d{2}/\d{2}/\d{4})\s+(\d{2}:\d{2})")
_ED_RE = re.compile(r"ed=([A-Za-z0-9]+)")


def _parse_liga_card_row(
    row: Tag,
    order_number: str,
    order_date: date | None,
    store_name: str,
    source_file: str,
) -> ParsedPurchaseItem | None:
    """Parse a single card row from an expanded Liga order."""
    # --- Card name ---
    card_name_pt: str | None = None
    card_name_en: str | None = None

    cardtitle_p = row.select_one("p.cardtitle a, p[cardtitle] a")
    if cardtitle_p:
        raw_name = cardtitle_p.get_text(strip=True)
        card_name_pt, card_name_en = _split_bilingual_name(raw_name)
    else:
        return None

    # --- Set code ---
    set_code: str | None = None
    edition_td = row.select_one("td[editioncard] a")
    if edition_td:
        href = edition_td.get("href", "")
        ed_match = _ED_RE.search(href)
        if ed_match:
            set_code = ed_match.group(1).upper()
    # Fallback: from edition icon href or text
    if not set_code:
        edition_link = row.select_one("td[editioncard] a")
        if edition_link:
            link_text = edition_link.get_text(strip=True)
            # Try to extract ed= from card link within text like "ed=DTK"
            ed_match2 = _ED_RE.search(link_text)
            if ed_match2:
                set_code = ed_match2.group(1).upper()

    # --- Set name ---
    set_name: str | None = None
    icon_img = row.select_one("img.icon-edicao")
    if icon_img:
        set_name = icon_img.get("title")
    if not set_name:
        set_label = row.select_one("td.label.hidden-md a")
        if set_label:
            set_name = set_label.get_text(strip=True)

    # --- Language ---
    language: str | None = None
    lang_td = row.select_one("td[languagecard] img")
    if lang_td:
        alt = (lang_td.get("alt") or "").strip()
        if "portugu" in alt.lower():
            language = "PT"
        elif "ingl" in alt.lower():
            language = "EN"
    # Check sibling label
    if language is None:
        for td_el in row.select("td.label"):
            txt = td_el.get_text(strip=True)
            if txt in ("PT", "EN"):
                language = txt
                break

    # --- Quality ---
    quality: str | None = None
    quality_td = row.select_one("td[qualitycard]")
    if quality_td:
        quality = quality_td.get_text(strip=True)
        # May contain an anchor with title
        quality_a = quality_td.select_one("a")
        if quality_a:
            title = quality_a.get("title", "")
            code = _extract_quality_code(title)
            if code:
                quality = code
            else:
                quality = quality_a.get_text(strip=True)

    # --- Quantity ---
    quantity = 1
    qty_div = row.select_one("div.item-estoque")
    if qty_div:
        qty_text = qty_div.get_text(strip=True)
        m = re.match(r"(\d+)", qty_text)
        if m:
            quantity = int(m.group(1))

    # --- Unit price ---
    unit_price = Decimal("0")
    currency = "BRL"
    price_div = row.select_one("div.item-subpreco")
    if price_div:
        unit_price, currency = parse_price_with_currency(price_div.get_text(strip=True))

    # --- Foil / extras (Liga orders don't typically have extras in the HTML) ---
    extras: list[str] = []
    is_foil = False

    return ParsedPurchaseItem(
        card_name_pt=card_name_pt,
        card_name_en=card_name_en,
        set_name=set_name,
        set_code=set_code,
        collector_number=None,  # Liga doesn't show collector number
        language=language,
        quality=quality,
        quantity=quantity,
        unit_price=unit_price,
        is_foil=is_foil,
        extras=extras,
        order_number=order_number,
        order_date=order_date,
        store_name=store_name,
        source_file=source_file,
        currency=currency,
    )


def parse_liga_orders(soup: BeautifulSoup, filename: str) -> list[ParsedOrder]:
    """Parse all expanded orders from a Liga Magic "Meus Pedidos" page."""
    orders: list[ParsedOrder] = []
    warnings: list[str] = []

    for box in soup.select("div.boxshadow.conteudo.box-interna"):
        # --- Order number ---
        order_num_tag = box.select_one("font.titleorder")
        order_number = order_num_tag.get_text(strip=True) if order_num_tag else ""

        # --- Order date ---
        order_date: date | None = None
        date_tag = box.select_one("font.titledate")
        if date_tag:
            date_text = date_tag.get_text(strip=True)
            m = _DATE_RE.search(date_text)
            if m:
                try:
                    dt = datetime.strptime(f"{m.group(1)} {m.group(2)}", "%d/%m/%Y %H:%M")
                    order_date = dt.date()
                except ValueError:
                    pass

        # --- Find sub-orders (each store is a separate div.infovendas) ---
        store_divs = box.select("div.row.infovendas")
        if not store_divs:
            # Might be a direct order (not MP)
            continue

        for store_div in store_divs:
            # --- Store name ---
            store_label = store_div.select_one("div.venda-store label.title")
            store_name = store_label.get_text(strip=True) if store_label else "Liga Magic"
            # Clean store name: remove trailing badge images text
            store_name = store_name.split("\n")[0].strip()

            # --- Store order number ---
            store_order_tag = store_div.select_one("div.venda-store label.aux a")
            store_order_num = (
                store_order_tag.get_text(strip=True) if store_order_tag else order_number
            )

            # Find the card container for this store: next sibling with meucarrinho
            pedido_id_tag = store_div.get("id", "")
            # The id is like "pedido_main_11752528"
            pedido_id = pedido_id_tag.replace("pedido_main_", "")

            # The card data is in div#venda_{pedido_id}
            card_container = box.select_one(f"div#venda_{pedido_id}")
            if card_container is None:
                warnings.append(f"Order {store_order_num} has no expanded card data (Liga format)")
                continue

            # Check if it's a loading spinner (not expanded)
            loading_div = card_container.select_one("div.loading-itens")
            meucarrinho = card_container.select_one("div#meucarrinho")
            if meucarrinho is None and loading_div is not None:
                warnings.append(f"Order {store_order_num} has no expanded card data (Liga format)")
                continue

            if meucarrinho is None:
                continue

            # --- Parse card rows ---
            items: list[ParsedPurchaseItem] = []
            itens_div = meucarrinho.select_one("div.itens")
            if itens_div is None:
                continue

            for card_row in itens_div.select("div.row"):
                # Skip header/footer rows
                if "header" in card_row.get("class", []):
                    continue
                if "footer" in card_row.get("class", []):
                    continue

                item = _parse_liga_card_row(
                    card_row, store_order_num, order_date, store_name, filename
                )
                if item is not None:
                    items.append(item)

            if items:
                orders.append(
                    ParsedOrder(
                        order_number=store_order_num,
                        order_date=order_date,
                        store_name=store_name,
                        items=items,
                        source_file=filename,
                    )
                )

    return orders


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def parse_purchase_html(html_content: str, filename: str) -> list[ParsedOrder]:
    """Auto-detect format and parse.  Returns list of orders.

    Raises :class:`ValueError` if the HTML format is unrecognised.
    """
    soup = BeautifulSoup(html_content, "html.parser")
    title = soup.title.string if soup.title else ""

    if "Nerdz Cards" in (title or "") or "nerdzcards" in html_content[:2000]:
        return [parse_nerdz_order(soup, filename)]
    elif "LigaMagic" in (title or "") or "Meus Pedidos" in (title or ""):
        return parse_liga_orders(soup, filename)
    else:
        raise ValueError(f"Unrecognized HTML format in {filename}")
