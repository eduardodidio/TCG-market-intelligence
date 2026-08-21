"""Pila currency formatter — extenso formatting for RS regional currency.

Pila is a 1:1 currency with BRL used colloquially in Rio Grande do Sul.
Format: "230 pilas e 21 centavos"
"""

from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal


def format_pila(value: Decimal | float | None) -> str:
    """Format a value in Pila currency (extenso style).

    Rules:
    - None -> "--"
    - Integer part uses pt-BR thousands separator (.)
    - "pila" (singular) / "pilas" (plural, including 0)
    - "centavo" (singular) / "centavos" (plural)
    - Omit centavos when 0
    - Negative values are prefixed with "-"

    Examples:
        format_pila(None)     -> "--"
        format_pila(0)        -> "0 pilas"
        format_pila(1.0)      -> "1 pila"
        format_pila(1.01)     -> "1 pila e 1 centavo"
        format_pila(230.21)   -> "230 pilas e 21 centavos"
        format_pila(1000.0)   -> "1.000 pilas"
    """
    if value is None:
        return "--"

    dec = Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    negative = dec < 0
    dec = abs(dec)

    integer_part = int(dec)
    centavos = int((dec - integer_part) * 100)

    # Format integer with pt-BR thousands separator
    formatted_int = _format_thousands(integer_part)
    pila_word = "pila" if integer_part == 1 else "pilas"

    prefix = "-" if negative else ""
    result = f"{prefix}{formatted_int} {pila_word}"

    if centavos > 0:
        centavo_word = "centavo" if centavos == 1 else "centavos"
        result += f" e {centavos} {centavo_word}"

    return result


def _format_thousands(n: int) -> str:
    """Format an integer with '.' as thousands separator (pt-BR style)."""
    s = str(n)
    if len(s) <= 3:
        return s

    parts: list[str] = []
    while s:
        parts.append(s[-3:])
        s = s[:-3]
    parts.reverse()
    return ".".join(parts)
