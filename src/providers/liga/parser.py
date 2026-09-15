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

    # Remove R$ prefix, whitespace, and &nbsp;
    cleaned = re.sub(r"R\$(?:\s|&nbsp;|\xa0)*", "", text.strip())
    if not cleaned:
        return None

    # Brazilian format: dots as thousands separator, comma as decimal
    cleaned = cleaned.replace(".", "").replace(",", ".")

    try:
        return Decimal(cleaned)
    except InvalidOperation:
        return None


def _parse_price_mkp(html: str) -> dict | None:
    """Extract prices from the structured ``div.price-mkp`` section.

    LigaMagic renders a summary price bar with three slots::

        <div class="price-mkp">
          <div class="min"><div class="price">R$ 6,84</div></div>
          <div class="medium"><div class="price">R$ 8,50</div></div>
          <div class="max"><div class="price">R$ 12,00</div></div>
        </div>

    Returns ``{"low": Decimal, "mid": Decimal, "high": Decimal}`` or None.
    """
    mkp_match = re.search(
        r'<div\s+class="price-mkp">(.*?)</div>\s*</div>\s*</div>\s*</div>',
        html,
        re.DOTALL,
    )
    if not mkp_match:
        return None

    section = mkp_match.group(1)

    def _extract(cls: str) -> Decimal | None:
        m = re.search(
            rf'<div\s+class="{cls}">\s*<div\s+class="price">\s*(R\$[^<]+)',
            section,
        )
        return _parse_brl(m.group(1)) if m else None

    low = _extract("min")
    mid = _extract("medium")
    high = _extract("max")

    if low is None and mid is None and high is None:
        return None

    return {"low": low, "mid": mid, "high": high}


def parse_card_prices(html: str, card_name: str = "") -> dict:
    """Extract price data from a LigaMagic card page HTML.

    Returns a dict with structure::

        {
            "card_name": str,
            "normal": {"low": Decimal|None, "mid": Decimal|None, "high": Decimal|None},
            "foil": {"low": Decimal|None, "mid": Decimal|None, "high": Decimal|None},
        }

    Extraction strategies (tried in order):
    1. Structured ``div.price-mkp`` section (min/medium/max)
    2. Fallback: collect all R$ values from page body (legacy)
    """
    result: dict = {
        "card_name": card_name,
        "normal": {"low": None, "mid": None, "high": None},
        "foil": {"low": None, "mid": None, "high": None},
    }

    if not html or not html.strip():
        return result

    # --- Strategy 1: Structured price-mkp section ---
    mkp = _parse_price_mkp(html)
    if mkp is not None:
        result["normal"] = mkp

        # Foil: look for a separate foil price-mkp (extras_f section)
        foil_section = _extract_foil_section(html)
        if foil_section:
            foil_mkp = _parse_price_mkp(foil_section)
            if foil_mkp is not None:
                result["foil"] = foil_mkp

        return result

    # --- Strategy 2 (fallback): Find all R$ price values on the page ---
    # Handle R$ with normal space, &nbsp;, no space, or \xa0 (non-breaking space)
    price_matches = re.findall(r"R\$(?:\s|&nbsp;|\xa0)*[\d.,]+", html)
    parsed_prices = []
    for match in price_matches:
        val = _parse_brl(match)
        if val is not None and val > 0:
            parsed_prices.append(val)

    if not parsed_prices:
        return result

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

    # Detect foil prices in fallback mode
    foil_section = _extract_foil_section(html)
    if foil_section:
        foil_matches = re.findall(r"R\$(?:\s|&nbsp;|\xa0)*[\d.,]+", foil_section)
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


def parse_edition_options(html: str) -> list[tuple[str, str]]:
    """Extract edition options from the Liga card page dropdown.

    Returns a list of ``(value, collector_number)`` tuples, e.g.::

        [("480612_1", "1"), ("480263_367", "367"), ...]

    The ``value`` is the full dropdown value used by
    ``editionsCard.changeEdition(value)`` and the ``collector_number``
    is the portion after the underscore.
    """
    results: list[tuple[str, str]] = []
    # Edition dropdown options have format: value="480612_1"
    # The second part of value is the collector number
    for m in re.finditer(
        r'<option[^>]*value="(\d+_[\w]+)"[^>]*>',
        html,
    ):
        val = m.group(1)
        parts = val.split("_", 1)
        if len(parts) == 2:
            results.append((val, parts[1]))
    return results


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
