# ADR 0014 — Normalize import currency to BRL at the import boundary

**Status:** Accepted · **Date:** 2026-09-24 · **Feature:** F171

## Context

A user exported their collection in BRL and, after importing it, the prices
were read as USD. The price-bearing import paths (`src/collection/importer.py`
CSV import, `src/services/purchase_parser.py` purchase-HTML import,
`src/collection/batch_parser.py` batch text entry) had no notion of currency:
Liga-only headers were assumed, foreign-format numbers were mis-parsed
(`parse_brl_price("12.50")` returned `1250` instead of `12.50`), and
`CurrencyConverter` only converted BRL → USD for display, never the reverse.
`user_collection.acquisition_price` is the storage invariant and must always
be BRL — it is read directly by portfolio value, set-completion cost, and
every read-time BRL/USD toggle. A wrong currency at import silently corrupts
that value with no downstream signal.

## Decision

- **BRL is the storage currency.** `acquisition_price` is always BRL; a
  foreign amount is never written as-is.
- **Conversion happens once, at the import boundary**, not at read time.
  `src/currency/import_conversion.py::to_brl` converts a parsed
  `(amount, currency)` pair to BRL using a PTAX rate obtained through
  `CurrencyConverter.get_display_rate` (via the `RateLookup` adapter
  `rate_lookup_from_converter`), for the relevant date (row date for CSV,
  order date for purchase HTML, import date for batch entry).
- **No rate means drop the price, not guess.** If no PTAX rate is available
  for the date, or the detected currency is neither BRL nor USD, the
  conversion returns `brl=None` with a `warning` (`"no_rate"` /
  `"unsupported_currency"`) and the caller stores no price rather than
  storing a foreign amount as BRL or a fabricated estimate. The import still
  succeeds; the warning is surfaced to the user (API `price_warnings`, CLI
  `Warnings:` lines, purchase preview `currency_conversion_failed` reason).
- **Detection follows a fixed precedence chain**
  (`src/collection/csv_columns.py::detect_file_currency` for CSV,
  `src/currency/money.py::detect_symbol` for a single value): user override
  (`currency=BRL|USD`) > per-row currency column > header hint
  (`Preço (R$)` / `Price (USD)`) > symbol in values (`R$`, `US$`, `$`) >
  number-format heuristic (`1.234,56` vs `1,234.56`) > origin (Liga headers
  ⇒ BRL) > default BRL, flagged `currency_source="default"` with low
  confidence so the UI can warn the user before they confirm.

## Alternatives considered

1. **Store the original currency and amount in a DB column**
   (`user_collection.acquisition_currency` / `acquisition_price_original`).
   Rejected for this feature: it requires a `models.py` migration, and
   `src/database/models.py` is a batch-wide high-conflict file shared by
   several features (F171–F179) landing in the same window. Left as a
   possible follow-up once the batch merges.
2. **Convert at read time for mixed-currency collections** (store whatever
   currency the source used, convert on every read). Rejected: it would
   require every existing read path (portfolio value, set completion,
   history charts) to carry a per-row currency and rate-as-of-purchase,
   multiplying the surface area for the same bug this ADR fixes, for a
   collection that is overwhelmingly single-currency (BRL, since Liga
   Magic and MYP Cards are Brazilian).

## Consequences

- A USD export converts correctly to BRL at import; a BRL export (by
  symbol, header, currency column, or Liga origin) is unchanged.
- An unpriced or unrated row degrades to "no price" instead of a silently
  wrong number — visible via `price_warnings` / CLI `Warnings:` /
  purchase-preview `currency_conversion_failed`, never invisible.
- `dry_run` (API and CLI) lets a user see the detected currency and
  confidence before committing an import.
- EUR and other currencies are detected and reported as `unsupported`; the
  price is dropped. No behavior regression for currencies this feature
  does not support.
- The original foreign amount is not retained anywhere once converted
  (see alternative 1) — a future feature that needs it must add that
  column separately.
