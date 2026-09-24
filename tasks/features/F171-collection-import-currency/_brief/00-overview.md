# F171 — Collection import respecting the source currency — Overview

## Problem

A user exported their collection **in BRL** and, after importing it, the prices
were read as **USD**. An audit of the current code (2026-09-24) found that the
price-bearing import paths do not know about currency at all:

- `src/collection/importer.py` (CSV import, used by `POST /api/v1/collection/import`,
  `CsvImportModal`, and CLI `import-csv`) only knows the **Liga Magic headers**
  (`Edicao (Sigla)`, `Card #`, ...) and **ignores any price column**. Files from
  other tools (ManaBox/Moxfield/generic spreadsheets with `Price`, `Purchase price`,
  `Preço`, `Valor`, a `Currency`/`Moeda` column, or `R$` / `US$` / `$` symbols)
  have their prices dropped. The user then re-enters prices or reads them
  through the currency toggle, which assumes the stored value is BRL.
- `src/services/purchase_parser.py::parse_brl_price` removes only `R$` and assumes
  the `1.234,56` format. `US$ 12.50` becomes `Decimal("0")`, and `12.50` becomes
  **1250** (the `.` is treated as a thousands separator). This is a silent 100x error.
- `src/collection/batch_parser.py` has no price token, so users cannot give a
  price or currency during batch entry.
- `src/services/currency.py::CurrencyConverter` only converts **BRL → USD**, for
  display. Nothing converts **USD → BRL** before storage.
- `src/collection/converter.py` (`row_to_collection_entry`) was reviewed and has
  no monetary fields. **No change is needed.** This task records the review.

**Invariant (unchanged, now enforced on import):** BRL is the storage currency.
`user_collection.acquisition_price` is **always BRL**. Conversion happens once,
at the import boundary, through the PTAX rates already stored (`Repository.get_closest_rate`).

## Scope

1. Pure money parsing: `R$ 1.234,56`, `US$ 1,234.56`, `$12.50`, `12,50`, `1234.5`
   → `(Decimal, detected_currency | None)`.
2. Currency detection for a CSV file, in precedence order:
   user override > per-row currency column > header hint (`Preço (R$)`,
   `Price (USD)`) > symbols in values > number-format heuristic > origin
   (Liga headers ⇒ BRL) > default BRL (flagged as `default`).
3. USD → BRL conversion at import time. If no rate is available, the
   **price is dropped (None) and a warning is added. A USD value is never stored as BRL.**
4. CSV importer maps a price column to `acquisition_price` (BRL). It also accepts
   header aliases for ManaBox/generic exports and supports `dry_run` (detect only, no writes).
5. `/import` endpoint: `currency=auto|BRL|USD` and `dry_run` query params. The response
   adds detection fields.
6. `CsvImportModal`: shows the detected currency after the dry run and a currency selector
   (Auto / BRL / USD), then imports.
7. Purchase HTML import: currency-aware parsing. USD items are converted to BRL
   at preview time using the order date rate. The preview shows the original currency and value.
8. Batch text entry: optional price token (`R$12,50`, `US$3.10`, `$3.10`) stored
   as BRL acquisition price.
9. CLI `import-csv --currency auto|BRL|USD`, and the dry run prints the detected currency.
10. Tests with BRL and USD fixture exports. Also a PRD, 2 diagrams, an ADR, and a README note.

## Out of scope

- Storing the original currency/value in the DB (would need `models.py` + migration,
  a high-conflict file in the F171–F179 batch). Can be done in a follow-up.
- EUR or other currencies. These are detected and reported as `unsupported`: the price is dropped
  and a warning is added.
- Changing the "import replaces whole collection" behavior.

## Constraints

- Batch F171–F179 runs in parallel. High-conflict files: `frontend/src/App.tsx`,
  `frontend/src/components/Layout.tsx`, `src/cli/main.py`, `src/database/models.py`,
  `src/api/app.py`, `README.md`, `bats/`. F171 touches **only** `src/cli/main.py`
  and `README.md` from that list, in the last wave (T13, T14). It does **not** touch
  `models.py`, `app.py`, `App.tsx` or `Layout.tsx`.
- No new dependencies (stdlib `decimal`, `re`, `csv` only).
- Work on the feature branch or worktree given by the orchestrator. Never commit to `main`.
- Liga sweep semantics (`mid` price, `external_id`) are untouched.

## Acceptance criteria (titles; detail in component shards)

- AC1 A BRL export (symbol, header, currency column, or Liga origin) is imported with BRL values unchanged.
- AC2 A USD export is converted to BRL with the PTAX rate. The stored value equals USD × rate.
- AC3 A user override (`currency=BRL|USD`) wins over auto-detection.
- AC4 An ambiguous file defaults to BRL, reports `currency_source="default"`, and the UI warns about it.
- AC5 No rate available: the USD price is dropped with a warning, the import still succeeds, and nothing is stored as BRL.
- AC6 `parse_brl_price("12.50")` bug fixed. `US$` purchase prices are converted, not zeroed.
- AC7 Batch text price token is parsed and stored as BRL.
- AC8 `dry_run` detects without writing (API + CLI).
- AC9 Existing Liga CSV import behavior (no price column) is unchanged. Existing tests pass.
- AC10 PRD, `F171-architecture.mmd`, `F171-journey.mmd`, ADR, and a README note exist.
