# PRD: Collection import respecting the source currency

**Feature ID:** F171
**Status:** in-progress
**Owner:** @eduardorutkoskididio
**Date:** 2026-09-24

## Problem

A user exported their collection **in BRL** and, after importing it, the prices
were read as **USD**. An audit of the price-bearing import paths found that
none of them are currency-aware:

- `src/collection/importer.py` (CSV import) only knows Liga Magic headers and
  ignores any price column entirely. Files from other tools (ManaBox,
  Moxfield, generic spreadsheets) lose their prices on import.
- `src/services/purchase_parser.py::parse_brl_price` only strips `R$` and
  assumes `1.234,56` formatting. `US$ 12.50` becomes `Decimal("0")`, and a
  plain `12.50` becomes **1250** — a silent 100x error.
- `src/collection/batch_parser.py` has no price token at all.
- `src/services/currency.py::CurrencyConverter` only converts BRL → USD for
  display. Nothing converts USD → BRL before storage.

**Users:** any collector importing a collection or purchase history from a
non-Liga source (ManaBox exports, generic spreadsheets, USD-denominated
purchases), and existing Liga users who must see zero behavior change.

**Invariant (unchanged, now enforced on import):** `user_collection.acquisition_price`
is always stored in BRL. Conversion happens once, at the import boundary,
using the PTAX rates already stored via `Repository.get_closest_rate`.

## Goal

Every import path (CSV, purchase HTML, batch text entry) correctly detects
the source currency, converts USD amounts to BRL using the PTAX rate at
import/order time, and never silently stores a USD value as if it were BRL.

## Scope

### In scope

- Pure money parsing (`src/currency/money.py`): symbols, thousands/decimal
  separator disambiguation, no `float` usage.
- Currency detection for a CSV file with the following precedence: user
  override > per-row currency column > header hint > symbols in values >
  number-format heuristic > origin (Liga headers ⇒ BRL) > default BRL
  (flagged `default`).
- USD → BRL conversion at import time using existing PTAX rate storage. If no
  rate is available, the price is dropped (`None`) with a warning — a USD
  value is never stored as BRL.
- CSV importer: header aliases for ManaBox/generic exports, optional price
  column mapped to `acquisition_price` (BRL), `dry_run` support.
- `/import` endpoint: `currency=auto|BRL|USD` and `dry_run` query params, with
  detection fields added to the response.
- `CsvImportModal`: shows detected currency after dry run, lets the user
  override (Auto / BRL / USD) before importing.
- Purchase HTML import: currency-aware parsing; USD items are converted to
  BRL at preview time using the order date's rate, original value/currency
  shown in the preview.
- Batch text entry: optional price token (`R$12,50`, `US$3.10`, `$3.10`)
  stored as BRL.
- CLI `import-csv --currency auto|BRL|USD`, dry run prints detected currency.
- Test fixtures for BRL and USD exports (Liga, ManaBox, generic, ambiguous).

### Out of scope

- Storing the original currency/value in the DB (would require a
  `models.py` migration — high-conflict file in the F171–F179 batch).
  Candidate for a follow-up feature.
- EUR or other currencies: detected and reported as `unsupported`, price
  dropped with a warning.
- Changing "import replaces whole collection" behavior.

## User flows

See `docs/diagrams/F171-architecture.mmd` (component/data-flow) and
`docs/diagrams/F171-journey.mmd` (user journey with dry-run detection and
warning branches).

## Success metrics

- AC1–AC10 (below) pass with automated tests.
- Existing Liga CSV import behavior and tests are unchanged (AC9).
- No case exists where a USD amount is written to `acquisition_price`
  without going through PTAX conversion.

## Acceptance criteria

- **AC1** A BRL export (symbol, header, currency column, or Liga origin) is
  imported with BRL values unchanged.
- **AC2** A USD export is converted to BRL with the PTAX rate. The stored
  value equals USD × rate.
- **AC3** A user override (`currency=BRL|USD`) wins over auto-detection.
- **AC4** An ambiguous file defaults to BRL, reports
  `currency_source="default"`, and the UI warns about it.
- **AC5** No rate available: the USD price is dropped with a warning, the
  import still succeeds, and nothing is stored as BRL.
- **AC6** `parse_brl_price("12.50")` bug fixed. `US$` purchase prices are
  converted, not zeroed.
- **AC7** Batch text price token is parsed and stored as BRL.
- **AC8** `dry_run` detects without writing (API + CLI).
- **AC9** Existing Liga CSV import behavior (no price column) is unchanged.
  Existing tests pass.
- **AC10** PRD, `F171-architecture.mmd`, `F171-journey.mmd`, an ADR, and a
  README note exist.

## Open questions

- None outstanding for this scope. Storing the original currency/value is
  deferred to a follow-up (see Out of scope).
