"""Pure money and currency-symbol parsing (F171).

Parses free-text monetary values such as ``"R$ 1.234,56"`` or
``"US$ 1,234.56"`` into a ``(Decimal, currency)`` pair without ever
guessing wrong between the Brazilian (``1.234,56``) and US
(``1,234.56``) number formats.

Examples::

    >>> detect_symbol("R$ 9,75")
    'BRL'
    >>> detect_symbol("US$ 3.10")
    'USD'
    >>> detect_symbol("no symbol here")

    >>> parse_money("R$ 1.234,56")
    (Decimal('1234.56'), 'BRL')
    >>> parse_money("US$ 1,234.56")
    (Decimal('1234.56'), 'USD')
    >>> parse_money("12,50")
    (Decimal('12.50'), None)
    >>> parse_money("1.234", hint="BRL")
    (Decimal('1234.00'), None)
    >>> parse_money("1.234", hint="USD")
    (Decimal('1.23'), None)
    >>> parse_money("abc")
    (None, None)

    >>> number_format_hint("12,50")
    'BRL'
    >>> number_format_hint("12.50")
    'USD'
    >>> number_format_hint("12")

Number-format disambiguation rules (applied after stripping the currency
symbol, whitespace, NBSP, and suffixes like ``"(unid.)"`` or ``"/un"``):

- Both ``.`` and ``,`` present: the **last** separator is the decimal
  separator (``1.234,56`` -> ``1234.56``; ``1,234.56`` -> ``1234.56``).
- Only ``,`` present: followed by 1-2 digits it is the decimal separator
  (``12,5`` -> ``12.5``). Followed by exactly 3 digits it is ambiguous:
  ``hint == "USD"`` treats it as a thousands separator (``1234``),
  otherwise as decimal (``1.234``).
- Only ``.`` present: followed by 1-2 digits it is the decimal separator
  (``12.50`` -> ``12.50``). Followed by exactly 3 digits it is ambiguous:
  ``hint == "BRL"`` treats it as a thousands separator (``1234``),
  otherwise as decimal (``1.234``).
- Multiple occurrences of the same separator (``1.234.567``,
  ``1,234,567``) are always a thousands separator.
- Negative numbers or amounts greater than 1,000,000 are rejected as
  invalid card prices and return ``(None, symbol)``.
- The result is quantized to ``Decimal("0.01")`` with ``ROUND_HALF_UP``.
"""

from __future__ import annotations

import re
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

from src.currency.types import SupportedCurrency

_MAX_AMOUNT = Decimal("1000000")
_CENTS = Decimal("0.01")

# Currency symbol/code detection, longest/most-specific tokens first.
_BRL_SYMBOL_RE = re.compile(r"(?i)\bR\$|\bBRL\b")
_USD_SYMBOL_RE = re.compile(r"(?i)\bUS\$|\bUSD\b|\bU\$|\$")
_EUR_SYMBOL_RE = re.compile(r"(?i)\bEUR\b|€")

# Cleanup of noise around the numeric token.
_NBSP_RE = re.compile("\xa0")
_SUFFIX_RE = re.compile(r"\([^)]*\)|/\s*un\.?\s*$", re.IGNORECASE)
_NEGATIVE_RE = re.compile(r"-")
_VALID_NUMBER_RE = re.compile(r"^\d[\d.,]*$")

_BRL_FORMAT_RE = re.compile(r"^\d+,\d{2}$|^\d{1,3}(\.\d{3})+,\d{2}$")
_USD_FORMAT_RE = re.compile(r"^\d+\.\d{2}$|^\d{1,3}(,\d{3})+\.\d{2}$")


def detect_symbol(text: str) -> str | None:
    """Detect a currency symbol/code in ``text``.

    Returns ``"BRL"``, ``"USD"``, ``"EUR"``, or ``None`` when no known
    symbol is present. Case-insensitive and whitespace-tolerant.
    """
    if not text:
        return None
    if _BRL_SYMBOL_RE.search(text):
        return "BRL"
    if _EUR_SYMBOL_RE.search(text):
        return "EUR"
    if _USD_SYMBOL_RE.search(text):
        return "USD"
    return None


def _strip_noise(text: str) -> str:
    cleaned = _NBSP_RE.sub(" ", text)
    cleaned = _SUFFIX_RE.sub("", cleaned)
    return cleaned.strip()


def _extract_number_token(cleaned: str) -> str | None:
    """Strip known currency symbols/codes and surrounding whitespace,
    returning the bare numeric token (still containing separators and
    an optional leading minus sign), or ``None`` if nothing usable is left.
    """
    token = cleaned
    token = re.sub(r"(?i)\bR\$|\bUS\$|\bBRL\b|\bUSD\b|\bU\$|\bEUR\b|\$|€", "", token)
    token = token.strip()
    return token or None


def _normalize_number(token: str, hint: SupportedCurrency | None) -> Decimal | None:
    has_dot = "." in token
    has_comma = "," in token

    if has_dot and has_comma:
        last_dot = token.rfind(".")
        last_comma = token.rfind(",")
        if last_comma > last_dot:
            normalized = token.replace(".", "").replace(",", ".")
        else:
            normalized = token.replace(",", "")
    elif has_comma:
        if token.count(",") > 1:
            normalized = token.replace(",", "")
        else:
            after = token.split(",")[-1]
            if len(after) == 3:
                normalized = token.replace(",", "") if hint == "USD" else token.replace(",", ".")
            else:
                normalized = token.replace(",", ".")
    elif has_dot:
        if token.count(".") > 1:
            normalized = token.replace(".", "")
        else:
            after = token.split(".")[-1]
            if len(after) == 3:
                normalized = token.replace(".", "") if hint == "BRL" else token
            else:
                normalized = token
    else:
        normalized = token

    try:
        return Decimal(normalized)
    except InvalidOperation:
        return None


def parse_money(
    text: str | None, hint: SupportedCurrency | None = None
) -> tuple[Decimal | None, str | None]:
    """Parse a free-text money value into ``(amount, symbol_currency)``.

    ``amount`` is ``None`` when the text is empty, unparseable, negative,
    or exceeds the maximum allowed card price. ``symbol_currency`` is the
    currency detected from a symbol/code in the text (``"BRL"``, ``"USD"``,
    ``"EUR"``), or ``None`` when no symbol was present -- independent of
    whether parsing succeeded.
    """
    if not text:
        return None, None

    symbol = detect_symbol(text)
    cleaned = _strip_noise(text)

    if _NEGATIVE_RE.search(cleaned):
        return None, symbol

    token = _extract_number_token(cleaned)
    if not token:
        return None, symbol

    if not _VALID_NUMBER_RE.match(token):
        return None, symbol

    amount = _normalize_number(token, hint)
    if amount is None:
        return None, symbol

    if amount < 0 or amount > _MAX_AMOUNT:
        return None, symbol

    quantized = amount.quantize(_CENTS, rounding=ROUND_HALF_UP)
    return quantized, symbol


def number_format_hint(text: str) -> SupportedCurrency | None:
    """Guess a currency from the number format alone (no symbol).

    ``"BRL"`` for ``12,50`` or ``1.234,56`` style numbers, ``"USD"`` for
    ``12.50`` or ``1,234.56`` style numbers, ``None`` when the format
    gives no signal (e.g. a bare integer like ``"12"``).
    """
    if not text:
        return None
    cleaned = _strip_noise(text).strip()
    if _BRL_FORMAT_RE.match(cleaned):
        return "BRL"
    if _USD_FORMAT_RE.match(cleaned):
        return "USD"
    return None
