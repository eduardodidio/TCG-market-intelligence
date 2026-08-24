"""Pure HTML parsing functions for LigaMagic card pages.

All functions accept raw HTML strings and return structured data.
No browser or network dependency — suitable for unit testing with
fixture HTML.
"""

from __future__ import annotations

import re
from decimal import Decimal, InvalidOperation


def _parse_brl(text: str) -> Decimal | None:
    """Parse a Brazilian Real price string like 'R$ 1.234,56' into Decimal.

    Handles common formats:
    - "R$ 1.234,56"
    - "R$1234,56"
    - "R$ 12,50"
    - "1.234,56"  (no R$ prefix)
    """
    if not text:
        return None

    # Remove R$ prefix and whitespace
    cleaned = re.sub(r"R\$\s*", "", text.strip())
    if not cleaned:
        return None

    # Brazilian format: dots as thousands separator, comma as decimal
    cleaned = cleaned.replace(".", "").replace(",", ".")

    try:
        return Decimal(cleaned)
    except InvalidOperation:
        return None


def parse_card_prices(html: str, card_name: str = "") -> dict:
    """Extract price data from a LigaMagic card page HTML.

    Returns a dict with structure::

        {
            "card_name": str,
            "normal": {"low": Decimal|None, "mid": Decimal|None, "high": Decimal|None},
            "foil": {"low": Decimal|None, "mid": Decimal|None, "high": Decimal|None},
        }

    Extraction strategies (tried in order):
    1. Regex for R$ price patterns near known labels
    2. Fallback: collect all R$ values from page body
    """
    result: dict = {
        "card_name": card_name,
        "normal": {"low": None, "mid": None, "high": None},
        "foil": {"low": None, "mid": None, "high": None},
    }

    if not html or not html.strip():
        return result

    # --- Strategy 1: Find all R$ price values on the page ---
    price_matches = re.findall(r"R\$\s*[\d.,]+", html)
    parsed_prices = []
    for match in price_matches:
        val = _parse_brl(match)
        if val is not None and val > 0:
            parsed_prices.append(val)

    if not parsed_prices:
        return result

    # --- Strategy 2: Map prices to low/mid/high ---
    # LigaMagic typically shows prices in order: low, mid, high
    # for normal cards, then the same for foil.
    # With obfuscated CSS, we rely on positional extraction.

    # Deduplicate while preserving order
    seen: set[Decimal] = set()
    unique_prices: list[Decimal] = []
    for p in parsed_prices:
        if p not in seen:
            seen.add(p)
            unique_prices.append(p)

    # Sort ascending for low/mid/high assignment
    sorted_prices = sorted(unique_prices)

    if len(sorted_prices) >= 3:
        result["normal"]["low"] = sorted_prices[0]
        result["normal"]["mid"] = sorted_prices[len(sorted_prices) // 2]
        result["normal"]["high"] = sorted_prices[-1]
    elif len(sorted_prices) == 2:
        result["normal"]["low"] = sorted_prices[0]
        result["normal"]["high"] = sorted_prices[1]
    elif len(sorted_prices) == 1:
        result["normal"]["mid"] = sorted_prices[0]

    # --- Strategy 3: Detect foil prices ---
    # Look for "foil" keyword near R$ values
    foil_section = _extract_foil_section(html)
    if foil_section:
        foil_matches = re.findall(r"R\$\s*[\d.,]+", foil_section)
        foil_prices = []
        for match in foil_matches:
            val = _parse_brl(match)
            if val is not None and val > 0:
                foil_prices.append(val)

        foil_sorted = sorted(set(foil_prices))
        if len(foil_sorted) >= 3:
            result["foil"]["low"] = foil_sorted[0]
            result["foil"]["mid"] = foil_sorted[len(foil_sorted) // 2]
            result["foil"]["high"] = foil_sorted[-1]
        elif len(foil_sorted) == 2:
            result["foil"]["low"] = foil_sorted[0]
            result["foil"]["high"] = foil_sorted[1]
        elif len(foil_sorted) == 1:
            result["foil"]["mid"] = foil_sorted[0]

    return result


def _extract_foil_section(html: str) -> str | None:
    """Try to extract the foil-related portion of the HTML.

    Looks for content after a 'foil' marker (case-insensitive).
    Returns the substring from the foil marker to the end, or None.
    """
    # Case-insensitive search for foil section markers
    patterns = [
        r"(?i)foil\s*</",  # "Foil</td>" or "Foil</div>"
        r'(?i)class="[^"]*foil',  # class containing "foil"
        r"(?i)>foil<",  # ">Foil<"
        r"(?i)foil\s*:",  # "Foil:" label
    ]

    earliest_pos = len(html)
    for pattern in patterns:
        match = re.search(pattern, html)
        if match and match.start() < earliest_pos:
            earliest_pos = match.start()

    if earliest_pos < len(html):
        return html[earliest_pos:]

    return None


def parse_card_name_from_page(html: str) -> str | None:
    """Extract the card name from a LigaMagic card page.

    Tries multiple strategies:
    1. <title> tag content
    2. Known card-name selectors
    """
    # Strategy 1: title tag (usually "Card Name - LigaMagic")
    title_match = re.search(r"<title[^>]*>([^<]+)</title>", html, re.IGNORECASE)
    if title_match:
        title = title_match.group(1).strip()
        # Strip site suffix
        for suffix in [" - LigaMagic", " | LigaMagic", " - Liga Magic"]:
            if title.endswith(suffix):
                title = title[: -len(suffix)].strip()
                break
        if title:
            return title

    return None
