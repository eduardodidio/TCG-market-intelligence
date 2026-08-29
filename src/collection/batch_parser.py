"""Pure-function text parser for batch card entry.

Format: [Qty[x]] CardName [[set_code]] [Quality] [Language] [Extras...]

Examples::

    2 Lightning Bolt
    Lightning Bolt
    2x Lightning Bolt [m15]
    2 Lightning Bolt [m15] NM EN Foil
    3x Swords to Plowshares [ice] SP BR
    # this is a comment (skipped)
"""

from __future__ import annotations

import re
from dataclasses import dataclass

QUALITY_CODES = frozenset({"M", "NM", "SP", "MP", "HP", "D"})
LANGUAGE_CODES = frozenset({"BR", "EN", "DE", "ES", "FR", "IT", "JP", "KO", "RU", "TW"})
EXTRAS_KEYWORDS = [
    "Extended Art",
    "Pre Release",
    "Etched",
    "Promo",
    "Foil",
]

# Pre-compiled patterns
_QTY_RE = re.compile(r"^(\d+)x?\s+")
_SET_RE = re.compile(r"\[([\w]+)\]")
# Quality/language must be standalone words (word boundaries) and uppercase
_QUALITY_RE = re.compile(r"\b(" + "|".join(QUALITY_CODES) + r")\b")
_LANGUAGE_RE = re.compile(r"\b(" + "|".join(LANGUAGE_CODES) + r")\b")
# Extras: case-insensitive, multi-word entries first
_EXTRAS_RE = re.compile(
    r"\b(" + "|".join(re.escape(kw) for kw in EXTRAS_KEYWORDS) + r")\b",
    re.IGNORECASE,
)


@dataclass
class ParsedLine:
    """Result of parsing a single text line."""

    line_number: int
    raw_text: str
    quantity: int = 1
    name: str = ""
    set_code: str | None = None
    quality: str | None = None
    language: str | None = None
    extras: str | None = None
    error: str | None = None


def parse_batch_text(text: str) -> list[ParsedLine]:
    """Parse multi-line text into structured card entries.

    Skips empty lines and lines starting with ``#``.
    Returns a :class:`ParsedLine` per non-skipped line, with ``error``
    set when the line could not be understood.
    """
    results: list[ParsedLine] = []

    for line_number, raw in enumerate(text.splitlines(), start=1):
        stripped = raw.strip()

        # Skip empty lines and comments
        if not stripped or stripped.startswith("#"):
            continue

        parsed = _parse_single_line(line_number, stripped)
        results.append(parsed)

    return results


def _parse_single_line(line_number: int, text: str) -> ParsedLine:
    """Parse a single non-empty, non-comment line."""
    remaining = text

    # 1. Extract quantity (optional leading digits with optional 'x')
    quantity = 1
    m = _QTY_RE.match(remaining)
    if m:
        quantity = int(m.group(1))
        remaining = remaining[m.end() :]

    # 2. Extract set code [xxx]
    set_code = None
    m = _SET_RE.search(remaining)
    if m:
        set_code = m.group(1).lower()
        remaining = remaining[: m.start()] + remaining[m.end() :]

    # 3. Extract extras (before quality/language to avoid conflicts)
    extras_found: list[str] = []
    for m in _EXTRAS_RE.finditer(remaining):
        extras_found.append(m.group(1))
    if extras_found:
        remaining = _EXTRAS_RE.sub("", remaining)

    # 4. Extract quality code
    quality = None
    m = _QUALITY_RE.search(remaining)
    if m:
        quality = m.group(1)
        remaining = remaining[: m.start()] + remaining[m.end() :]

    # 5. Extract language code
    language = None
    m = _LANGUAGE_RE.search(remaining)
    if m:
        language = m.group(1)
        remaining = remaining[: m.start()] + remaining[m.end() :]

    # 6. Remaining = card name
    name = " ".join(remaining.split()).strip()

    extras_str = ", ".join(extras_found) if extras_found else None

    if not name:
        return ParsedLine(
            line_number=line_number,
            raw_text=text,
            quantity=quantity,
            set_code=set_code,
            quality=quality,
            language=language,
            extras=extras_str,
            error="No card name found",
        )

    return ParsedLine(
        line_number=line_number,
        raw_text=text,
        quantity=quantity,
        name=name,
        set_code=set_code,
        quality=quality,
        language=language,
        extras=extras_str,
    )
