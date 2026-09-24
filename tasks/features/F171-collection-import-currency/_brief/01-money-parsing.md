# 01 — Shared currency types and money parsing (pure)

## `src/currency/types.py` (created in Wave 0, T01)

```python
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Literal

SupportedCurrency = Literal["BRL", "USD"]
CurrencyChoice = Literal["auto", "BRL", "USD"]
# How the currency was decided (most → least authoritative)
CurrencySource = Literal[
    "user", "column", "header", "symbol", "number_format", "origin", "default"
]

@dataclass(frozen=True)
class CurrencyDetection:
    currency: SupportedCurrency
    source: CurrencySource
    confidence: Literal["high", "medium", "low"]
    evidence: list[str] = field(default_factory=list)  # human-readable reasons
    unsupported_symbols: list[str] = field(default_factory=list)  # e.g. ["€"]
```

`src/currency/__init__.py` exists and is empty. Keep it empty (import modules directly).

## `src/currency/money.py` (T02)

```python
def detect_symbol(text: str) -> str | None
    # "BRL" for R$ / BRL ; "USD" for US$ / USD / U$ / bare leading "$" ;
    # "EUR" for € / EUR ; None when no symbol. Case-insensitive, whitespace-tolerant.

def parse_money(text: str | None, hint: SupportedCurrency | None = None
               ) -> tuple[Decimal | None, str | None]:
    # returns (amount, symbol_currency). amount None when unparseable/empty.
```

Number-format rules (after stripping symbol, spaces, NBSP `\xa0`, `(unid.)`-style suffixes):
- Both `.` and `,` are present: the **last** separator is the decimal (`1.234,56` → 1234.56; `1,234.56` → 1234.56).
- Only `,`: when followed by 1–2 digits (`12,5`, `12,50`) the comma is the decimal separator.
  When followed by exactly 3 digits (`1,234`) the value is ambiguous and `hint` decides:
  hint == "USD" → thousands (1234), otherwise decimal (1.234). Document this in the docstring.
- Only `.`: decimal if followed by 1–2 digits (`12.50` → 12.50). `.` followed by exactly 3 digits (`1.234`) →
  thousands if hint == "BRL" (→1234), else decimal (1.234).
- Multiple identical separators (`1.234.567`, `1,234,567`) → thousands.
- Negative numbers or values > 1_000_000 → return `(None, sym)` (invalid for card prices).
- Quantize to `Decimal("0.01")` with `ROUND_HALF_UP`.

```python
def number_format_hint(text: str) -> SupportedCurrency | None
    # "BRL" if pattern ^\d+,\d{2}$ or \d{1,3}(\.\d{3})+,\d{2}
    # "USD" if pattern ^\d+\.\d{2}$ with thousands "," or plain dot-decimal
    # None when no separators / ambiguous (e.g. "12")
```

## Gotchas
- `parse_brl_price` in `src/services/purchase_parser.py` is the legacy parser. T05 makes it a thin
  wrapper over `parse_money(text, hint="BRL")`, keeping the name and return type (Decimal, 0 on failure).
- Never use `float` for money. Use `Decimal(str(x))`.
