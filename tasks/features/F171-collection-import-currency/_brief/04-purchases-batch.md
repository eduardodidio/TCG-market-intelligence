# 04 — Purchase HTML import and batch text entry (T05, T06, T08, T09, T12)

## Purchase parser (T05) — `src/services/purchase_parser.py`
- `ParsedPurchaseItem` gets `currency: str = "BRL"` (add as the **last** field, with a default, so
  existing constructors still work).
- `parse_brl_price(text)` becomes a wrapper: `amount, _ = parse_money(text, hint="BRL")`.
  Return `amount or Decimal("0")`. The legacy BRL cases (`R$ 1.234,56`, `R$ 9,75`, `(unid.)`) keep working.
- New `parse_price_with_currency(text) -> tuple[Decimal, str]`: symbol currency, else "BRL"
  (Liga/Nerdz are BRL stores). Used at the 3 call sites (~L191, ~L198, ~L396) so `item.currency` is set.

## Purchases router (T08) — `src/api/routers/purchases.py`
- In `import_preview`, for each matched/unmatched item: `to_brl(item.unit_price, item.currency,
  item.order_date or date.today(), rate_lookup)`. `unit_price` in the response is **BRL**. Add
  `original_unit_price` (str), `original_currency` (str), `exchange_rate` (str | None). Conversion warnings
  go into the existing `warnings` list.
- Build `rate_lookup` from `CurrencyConverter(repo)` (`src/services/currency.py`).
- `/apply` is unchanged (it receives BRL from the preview).

## Batch parser (T06) — `src/collection/batch_parser.py`
- Optional price token anywhere after the name: `R$12,50`, `R$ 12,50`, `US$3.10`, `$3.10`, `@12,50`
  (bare `@` means the amount has no symbol and currency None).
  Regex must require a symbol or `@`, so card names with numbers are unaffected.
- `ParsedLine` gets `price: Decimal | None = None`, `price_currency: str | None = None`.
- Invalid amount after a symbol → `error = "Invalid price: <token>"`.

## Batch add (T09) — `src/collection/batch_add.py`, `src/api/schemas/collection.py` (batch classes only),
`src/api/routers/collection.py` (`batch_parse` ~L1731 and `batch_add` ~L1757 only)
- `BatchAddEntry` (dataclass and pydantic) gets `acquisition_price: Decimal | None = None`,
  `price_currency: Literal["BRL","USD"] | None = None`.
- `batch_add_entries(...)` gets `rate_lookup: RateLookup | None = None`. Before insert, `to_brl`. Currency None → BRL.
  On failure, store None and append a non-fatal note to the result (`BatchAddResult.warnings: list[str]`).
- `ParsedLineResponse` exposes `price` (str | None) and `price_currency`.

## Frontend purchases page (T12) — `frontend/src/pages/ImportPurchasesPage.tsx`, `frontend/src/api/purchases.ts`
- Add optional `original_unit_price?`, `original_currency?`, `exchange_rate?` to `ParsedMatch`
  and `UnmatchedItem`.
- When `original_currency && original_currency !== "BRL"`, render a small badge next to the price:
  `US$ 12.50 → R$ 67,50` (i18n key `purchases.convertedFrom`, added by T11).
