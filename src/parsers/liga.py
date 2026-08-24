"""Parser for LigaMagic card page HTML.

Extracts card names and marketplace prices from rendered LigaMagic pages.
Designed to work with HTML captured by Playwright (post-JS rendering).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal, InvalidOperation

from src.domain.models import PriceSnapshot


@dataclass
class LigaPriceData:
    """Extracted price data from a LigaMagic card page."""

    card_name_pt: str | None = None
    card_name_en: str | None = None
    normal_low: float | None = None
    normal_mid: float | None = None
    normal_high: float | None = None
    foil_low: float | None = None
    foil_mid: float | None = None
    foil_high: float | None = None


def parse_price_value(text: str) -> float | None:
    """Parse a Brazilian price string like 'R$ 12,50' to float 12.50.

    Handles formats:
    - "R$ 12,50"      -> 12.50
    - "R$12.50"       -> 12.50
    - "R$ 1.234,56"   -> 1234.56
    - "12,50"          -> 12.50
    - "1.234,56"       -> 1234.56

    Returns None if the text cannot be parsed.
    """
    if not text or not isinstance(text, str):
        return None

    # Strip R$ prefix and whitespace
    cleaned = re.sub(r"R\$\s*", "", text.strip())
    if not cleaned:
        return None

    # Remove any remaining non-numeric chars except . and ,
    cleaned = re.sub(r"[^\d.,]", "", cleaned)
    if not cleaned:
        return None

    # Determine decimal format:
    # If we have both . and , the last one is the decimal separator.
    # Brazilian format: 1.234,56 (dot=thousands, comma=decimal)
    # US format: 1,234.56 (comma=thousands, dot=decimal)
    dot_pos = cleaned.rfind(".")
    comma_pos = cleaned.rfind(",")

    if comma_pos > dot_pos:
        # Brazilian format: 1.234,56 -> remove dots, replace comma with dot
        cleaned = cleaned.replace(".", "").replace(",", ".")
    elif dot_pos > comma_pos and comma_pos != -1:
        # US format: 1,234.56 -> remove commas
        cleaned = cleaned.replace(",", "")
    elif comma_pos != -1 and dot_pos == -1:
        # Only comma: 12,50 -> Brazilian decimal
        cleaned = cleaned.replace(",", ".")
    # else: only dot or no separator -> already in correct format

    try:
        value = float(cleaned)
        return value if value >= 0 else None
    except (ValueError, OverflowError):
        return None


def parse_card_page(html: str) -> LigaPriceData:
    """Extract price data from a LigaMagic card page.

    Strategies:
    1. Page title: "Card PT / Card EN - Liga Magic" -> PT and EN names
    2. CSS class [class*="price"] sections contain Normal and Foil prices
    3. Regex R$\\s*[\\d.,]+ captures all prices on the page
    4. Price tiers: each variant (Normal/Foil) shows low/mid/high

    Args:
        html: Full HTML content of a LigaMagic card page (post-JS render).

    Returns:
        LigaPriceData with extracted names and prices. Fields are None when
        data could not be extracted.
    """
    result = LigaPriceData()

    if not html:
        return result

    # --- Extract card names from page title ---
    title_match = re.search(r"<title>(.*?)</title>", html, re.IGNORECASE | re.DOTALL)
    if title_match:
        title = title_match.group(1).strip()
        result.card_name_pt, result.card_name_en = _parse_title_names(title)

    # --- Extract prices ---
    # Strategy: Find price sections by class containing "price"
    # LigaMagic shows "Preco Medio de Venda no Marketplace" with Normal/Foil
    # Each section has 3 values: low, mid, high
    normal_prices, foil_prices = _extract_sectioned_prices(html)

    if normal_prices:
        if len(normal_prices) >= 1:
            result.normal_low = normal_prices[0]
        if len(normal_prices) >= 2:
            result.normal_mid = normal_prices[1]
        if len(normal_prices) >= 3:
            result.normal_high = normal_prices[2]

    if foil_prices:
        if len(foil_prices) >= 1:
            result.foil_low = foil_prices[0]
        if len(foil_prices) >= 2:
            result.foil_mid = foil_prices[1]
        if len(foil_prices) >= 3:
            result.foil_high = foil_prices[2]

    # Fallback: if no sectioned prices found, try regex on entire page
    if result.normal_low is None and result.normal_mid is None:
        all_prices = _extract_all_prices_regex(html)
        if all_prices:
            # Assign first 3 as normal prices (best-effort)
            if len(all_prices) >= 1:
                result.normal_low = all_prices[0]
            if len(all_prices) >= 2:
                result.normal_mid = all_prices[1]
            if len(all_prices) >= 3:
                result.normal_high = all_prices[2]

    return result


def liga_price_to_snapshot(
    price_data: LigaPriceData,
    card_id: str,
    observed_at: datetime | None = None,
) -> PriceSnapshot:
    """Convert LigaPriceData to domain PriceSnapshot.

    Uses normal_mid as the primary price (most representative marketplace
    price). Falls back to normal_low if mid is unavailable.

    Args:
        price_data: Parsed price data from a LigaMagic page.
        card_id: External card identifier (e.g. source_card external_id).
        observed_at: Observation timestamp. Defaults to now.

    Returns:
        PriceSnapshot with source="liga" and currency="BRL".
    """
    if observed_at is None:
        observed_at = datetime.now()

    # Primary price: normal_mid (most representative), fallback to normal_low
    primary_price = price_data.normal_mid or price_data.normal_low
    min_price = price_data.normal_low

    return PriceSnapshot(
        source="liga",
        external_id=card_id,
        observed_at=observed_at,
        min_price=_to_decimal(min_price),
        avg_price=_to_decimal(primary_price),
        tcg_price=None,  # LigaMagic does not provide TCG Player prices
        last_sold_price=None,
        quantity_available=None,
        currency="BRL",
    )


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _parse_title_names(title: str) -> tuple[str | None, str | None]:
    """Parse card names from a page title.

    Expected format: "Card PT / Card EN - Liga Magic"
    Also handles: "Card Name - Liga Magic" (single name, no slash)

    Returns (name_pt, name_en).
    """
    # Remove " - Liga Magic" suffix (case-insensitive)
    cleaned = re.sub(r"\s*-\s*Liga\s*Magic\s*$", "", title, flags=re.IGNORECASE).strip()
    if not cleaned:
        return None, None

    # Split on " / " to get PT and EN names
    if " / " in cleaned:
        parts = cleaned.split(" / ", 1)
        name_pt = parts[0].strip() or None
        name_en = parts[1].strip() or None
        return name_pt, name_en

    # Single name (no slash separator)
    return cleaned, cleaned


def _extract_sectioned_prices(html: str) -> tuple[list[float], list[float]]:
    """Extract Normal and Foil prices from class-based sections.

    LigaMagic price sections use CSS classes containing "price".
    The page has a Normal section and optionally a Foil section,
    each with low/mid/high price values.

    Returns (normal_prices, foil_prices) as lists of floats.
    """
    normal_prices: list[float] = []
    foil_prices: list[float] = []

    # Look for price sections. LigaMagic renders price blocks with
    # class names containing "price" or "preco". The text content
    # includes R$ values that we extract with regex.
    #
    # Pattern: find blocks that mention Normal or Foil and extract R$ values
    # within each block.

    # Try to split by Normal/Foil sections
    # Case-insensitive search for section markers
    normal_section = _find_section(html, r"(?:Normal|NORMAL|normal)")
    foil_section = _find_section(html, r"(?:Foil|FOIL|foil)")

    if normal_section:
        normal_prices = _extract_prices_from_text(normal_section)
    if foil_section:
        foil_prices = _extract_prices_from_text(foil_section)

    # If no sections found, try extracting from class="...price..." elements
    if not normal_prices and not foil_prices:
        price_blocks = re.findall(
            r'class="[^"]*(?:price|Price|preco|Preco)[^"]*"[^>]*>(.*?)</(?:div|span|td|p)',
            html,
            re.DOTALL | re.IGNORECASE,
        )
        all_section_prices: list[float] = []
        for block in price_blocks:
            prices = _extract_prices_from_text(block)
            all_section_prices.extend(prices)

        if all_section_prices:
            # First 3 are normal, next 3 are foil (convention)
            normal_prices = all_section_prices[:3]
            foil_prices = all_section_prices[3:6]

    return normal_prices, foil_prices


def _find_section(html: str, marker_pattern: str) -> str | None:
    """Find a section of HTML starting from a marker pattern.

    Returns up to 2000 chars of HTML after the marker, which should
    contain the price values for that section.
    """
    m = re.search(marker_pattern, html)
    if not m:
        return None
    start = m.start()
    return html[start : start + 2000]


def _extract_prices_from_text(text: str) -> list[float]:
    """Extract all R$ price values from a text snippet."""
    matches = re.findall(r"R\$\s*[\d.,]+", text)
    prices: list[float] = []
    for match in matches:
        value = parse_price_value(match)
        if value is not None and value > 0:
            prices.append(value)
    return prices


def _extract_all_prices_regex(html: str) -> list[float]:
    """Extract all R$ prices from the entire page using regex.

    Returns a deduplicated list of prices in order of appearance.
    """
    matches = re.findall(r"R\$\s*[\d.,]+", html)
    prices: list[float] = []
    seen: set[float] = set()
    for match in matches:
        value = parse_price_value(match)
        if value is not None and value > 0 and value not in seen:
            prices.append(value)
            seen.add(value)
    return prices


def _to_decimal(value: float | None) -> Decimal | None:
    """Convert a float to Decimal, returning None for None input."""
    if value is None:
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None
