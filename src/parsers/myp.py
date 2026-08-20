"""Parsers for MYP Cards HTML pages and inline data."""

from __future__ import annotations

import json
import re
from datetime import date, datetime
from decimal import Decimal, InvalidOperation

from bs4 import BeautifulSoup

from src.domain.models import (
    CardIdentity,
    HistoricalPrice,
    JsonLdPrice,
    MypSearchResult,
    PriceSnapshot,
    SourceCard,
)


def parse_set_links(html: str) -> list[str]:
    """Extract set slugs from an editions page.

    Returns list of slugs like 'dominaria-remastered'.
    """
    soup = BeautifulSoup(html, "html.parser")
    slugs = set()
    for a in soup.find_all("a", href=True):
        href = a["href"]
        # Match /magic/{slug} but exclude produto, preco, deck, edicoes
        m = re.match(r"^/magic/([a-z0-9][a-z0-9-]+)$", href)
        if m:
            slug = m.group(1)
            if slug not in ("edicoes", "produto", "preco"):
                slugs.add(slug)
    return sorted(slugs)


def parse_search_results(json_text: str) -> list[MypSearchResult]:
    """Parse MYP search API JSON response into a list of MypSearchResult.

    The MYP search endpoint (``/produto/search``) returns a JSON array of
    objects with keys like ``idproduto``, ``nomeenproduto``,
    ``slugnomeenproduto``, ``codigoproduto``, etc.

    Returns an empty list on empty arrays, malformed JSON, or unexpected
    response shapes (no exceptions raised).
    """
    try:
        data = json.loads(json_text)
    except (json.JSONDecodeError, TypeError):
        return []

    if not isinstance(data, list):
        return []

    results: list[MypSearchResult] = []
    for item in data:
        if not isinstance(item, dict):
            continue

        raw_id = item.get("idproduto") or item.get("id")
        name = item.get("nomeenproduto") or item.get("nomeptproduto") or item.get("nome")
        slug = item.get("slugnomeenproduto") or item.get("slugnomeptproduto") or item.get("slug")

        # id and slug are mandatory; skip items missing them
        if raw_id is None or not slug:
            continue

        external_id = str(raw_id)
        name = name or slug  # fallback to slug if name is missing

        url = f"https://mypcards.com/magic/produto/{external_id}/{slug}"

        sku = item.get("codigoproduto") or item.get("sku") or None
        set_code, collector_number = parse_sku(sku) if sku else (None, None)

        image_url = item.get("imagem") or item.get("image") or None

        results.append(
            MypSearchResult(
                external_id=external_id,
                name=name,
                slug=slug,
                url=url,
                sku=sku,
                set_code=set_code,
                collector_number=collector_number,
                image_url=image_url,
            )
        )

    return results


def parse_card_links(html: str) -> list[tuple[str, str]]:
    """Extract (card_id, slug) tuples from a set or search page.

    Returns list of (id, slug) like ('179334', 'tutor-esclarecido').
    """
    cards = set()
    for m in re.finditer(r'href="/magic/produto/(\d+)/([^"]+)"', html):
        cards.add((m.group(1), m.group(2)))
    return sorted(cards)


def parse_json_ld_product(html: str) -> dict | None:
    """Extract the Product JSON-LD block from a card page."""
    for m in re.finditer(r'<script type="application/ld\+json">(.*?)</script>', html, re.DOTALL):
        try:
            data = json.loads(m.group(1))
            if data.get("@type") == "Product":
                return data
        except (json.JSONDecodeError, AttributeError):
            continue
    return None


def parse_sku(sku: str) -> tuple[str | None, str | None]:
    """Parse MYP SKU like 'magic_ltr_748' into (set_code, collector_number).

    Returns (set_code_lower, collector_number) or (None, None).
    Set codes are normalized to lowercase for consistent matching
    across the system (collection CSV, Scryfall URLs, DB).
    """
    parts = sku.split("_")
    if len(parts) >= 3:
        set_code = parts[1].lower()
        collector_number = parts[2]
        return set_code, collector_number
    return None, None


def parse_card_page(html: str, card_id: str, card_slug: str) -> SourceCard | None:
    """Parse a card product page into a SourceCard with identity."""
    product = parse_json_ld_product(html)
    if not product:
        return None

    sku = product.get("sku", "")
    set_code, collector_number = parse_sku(sku) if sku else (None, None)

    # MYP is a PT-BR site — JSON-LD 'name' is always the Portuguese name.
    # The breadcrumb last item sometimes carries a different (EN) name.
    json_ld_name = product.get("name", "")
    name_pt = json_ld_name
    name_en = json_ld_name  # fallback until EN name is resolved

    # Check breadcrumb for a different (possibly EN) name
    breadcrumb = None
    for m_iter in re.finditer(
        r'<script type="application/ld\+json">(.*?)</script>', html, re.DOTALL
    ):
        try:
            data = json.loads(m_iter.group(1))
            if data.get("@type") == "BreadcrumbList":
                breadcrumb = data
                break
        except (json.JSONDecodeError, AttributeError):
            continue

    if breadcrumb:
        items = breadcrumb.get("itemListElement", [])
        if len(items) >= 4:
            card_name_bc = items[-1].get("name", "")
            if card_name_bc and card_name_bc != json_ld_name:
                # Breadcrumb differs from JSON-LD — use it as EN name
                name_en = card_name_bc

    identity = CardIdentity(
        game="magic",
        name_en=name_en,
        name_pt=name_pt,
        set_code=set_code,
        collector_number=collector_number,
    )

    return SourceCard(
        source="myp",
        external_id=card_id,
        url=f"https://mypcards.com/magic/produto/{card_id}/{card_slug}",
        sku=sku,
        identity=identity,
    )


def parse_price_snapshot(html: str, card_id: str) -> PriceSnapshot | None:
    """Extract current price snapshot from a card page."""
    product = parse_json_ld_product(html)
    if not product:
        return None

    price_str = product.get("offers", {}).get("price")
    min_price = _to_decimal(price_str) if price_str else None
    tcg_price = _extract_tcg_price(html)

    return PriceSnapshot(
        source="myp",
        external_id=card_id,
        observed_at=datetime.now(),
        min_price=min_price,
        avg_price=min_price,  # MYP shows avg_price in stat; fallback to min
        tcg_price=tcg_price,
        currency="BRL",
    )


def parse_jsonld_price(html: str) -> JsonLdPrice | None:
    """Extract current price from JSON-LD offers on a product page.

    Returns None if no Product JSON-LD block is found.
    Returns JsonLdPrice with price=None if price is zero or missing.
    """
    if not html:
        return None

    product = parse_json_ld_product(html)
    if not product:
        return None

    offers = product.get("offers", {})
    price_raw = offers.get("price")
    currency = offers.get("priceCurrency", "BRL")

    # Parse availability URL to short form
    availability_url = offers.get("availability", "")
    if isinstance(availability_url, str) and "/" in availability_url:
        availability = availability_url.rsplit("/", 1)[-1]
    else:
        availability = str(availability_url) if availability_url else "Unknown"

    # Parse price -- treat zero as None (no meaningful price data)
    price = _to_decimal(price_raw)
    if price is not None and price == Decimal("0"):
        price = None

    return JsonLdPrice(
        price=price,
        currency=currency,
        availability=availability,
    )


def parse_price_history(html: str, card_id: str) -> list[HistoricalPrice]:
    """Extract historical prices from a price history page.

    Parses window.precoChartConfig JSON from inline script.
    """
    m = re.search(r"window\.precoChartConfig\s*=\s*(\{.*?\});", html)
    if not m:
        return []

    try:
        config = json.loads(m.group(1))
    except json.JSONDecodeError:
        return []

    labels = config.get("labels", [])
    series_list = config.get("series", [])

    # Build lookup by series key
    series_by_key: dict[str, list] = {}
    meta_by_key: dict[str, list] = {}
    for s in series_list:
        series_by_key[s["key"]] = s.get("dados", [])
        if "meta" in s:
            meta_by_key[s["key"]] = s["meta"]

    mediana = series_by_key.get("mediana", [])
    tcg = series_by_key.get("tcg", [])
    ultimo = series_by_key.get("ultimo", [])
    volume = series_by_key.get("volume", [])
    ultimo_meta = meta_by_key.get("ultimo", [])

    results = []
    for i, label in enumerate(labels):
        observed = _parse_date(label)
        if not observed:
            continue

        results.append(
            HistoricalPrice(
                source="myp",
                external_id=card_id,
                observed_at=observed,
                median_price=_to_decimal(mediana[i]) if i < len(mediana) else None,
                tcg_price=_to_decimal(tcg[i]) if i < len(tcg) else None,
                last_sold_price=_to_decimal(ultimo[i]) if i < len(ultimo) else None,
                quantity_available=int(volume[i]) if i < len(volume) else None,
                last_sold_meta=ultimo_meta[i] if i < len(ultimo_meta) else None,
                currency="BRL",
            )
        )

    return results


def parse_pagination_max(html: str) -> int:
    """Find the maximum page number from pagination links."""
    pages = [int(p) for p in re.findall(r"page=(\d+)", html)]
    return max(pages) if pages else 1


# --- Helpers ---


def _to_decimal(value) -> Decimal | None:
    if value is None:
        return None
    try:
        if isinstance(value, (int, float)):
            return Decimal(str(value))
        s = str(value).replace(",", ".").strip()
        return Decimal(s) if s else None
    except (InvalidOperation, ValueError):
        return None


def _parse_date(label: str) -> date | None:
    """Parse DD/MM/YYYY date string."""
    try:
        return datetime.strptime(label.strip(), "%d/%m/%Y").date()
    except ValueError:
        return None


def _extract_stat_price(html: str, css_class: str) -> Decimal | None:
    """Extract a price from the statistics section by CSS class."""
    m = re.search(rf'class="{css_class}"[^>]*>.*?R\$\s*([\d.,]+)', html, re.DOTALL)
    if m:
        return _to_decimal(m.group(1))
    return None


def _extract_tcg_price(html: str) -> Decimal | None:
    """Extract TCG Player price from the stats section."""
    m = re.search(r"estat-tcg\s[^>]*>.*?R\$\s*([\d.,]+)", html, re.DOTALL)
    if m:
        return _to_decimal(m.group(1))
    return None
