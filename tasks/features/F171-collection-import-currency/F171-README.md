# F171 — Collection import respecting the source currency

**Status:** planned
**Created:** 2026-09-24
**Batch:** F171–F179 (parallel execution; see file-ownership table)
**PRD:** `docs/prd/F171-collection-import-currency.md` (written by T01)
**Brief (sharded):** `_brief/00-overview.md` … `_brief/05-frontend-csv-modal.md`

## Goal

Bug report: a user exported their collection in BRL, and on import the prices were treated as USD. The
audit (see `_brief/00-overview.md`) found three problems. The CSV importer drops all price columns and knows no
currency. The purchase-HTML parser turns `12.50` into `1250` and `US$ …` into `0`. Batch entry
has no way to give a price. F171 makes every import path currency-aware. It detects the file's currency
(user override > currency column > header hint > R$/US$ symbols > number format > origin > BRL
default), lets the user confirm or override it in the UI and CLI, and converts USD to BRL once, at the import
boundary, using the stored PTAX rates. `acquisition_price` stays **always BRL** (the storage currency),
and a USD value is never stored as BRL. The feature ships BRL and USD fixture exports with tests.

## Architecture impact

- **New pure modules:** `src/currency/types.py`, `src/currency/money.py`,
  `src/currency/import_conversion.py`, `src/collection/csv_columns.py`
- **Backend changed:** `src/collection/importer.py`, `src/collection/batch_parser.py`,
  `src/collection/batch_add.py`, `src/services/purchase_parser.py`, `src/api/routers/purchases.py`,
  `src/api/routers/collection.py` (only the `/batch/parse`, `/batch` and `/import` handlers),
  `src/api/schemas/collection.py`
- **Reviewed, no change:** `src/collection/converter.py` (no monetary fields),
  `src/services/currency.py` (wrapped, not edited)
- **Frontend:** `CsvImportModal.tsx`, `api/collection.ts`, `types/api.ts`, `ImportPurchasesPage.tsx`,
  `api/purchases.ts`, i18n locales
- **CLI:** `import-csv --currency` (`src/cli/main.py`, final wave)
- **No DB schema change**: `models.py`, `app.py`, `App.tsx`, `Layout.tsx` and `bats/` are NOT touched.

## Waves

- **Wave 0**: F171-T01
- **Wave 1**: F171-T02, F171-T03, F171-T11
- **Wave 2**: F171-T04, F171-T05, F171-T06, F171-T12
- **Wave 3**: F171-T07, F171-T08, F171-T09
- **Wave 4**: F171-T10
- **Wave 5**: F171-T13, F171-T14

| Task | Wave | Type | Title | Depends on |
|---|---|---|---|---|
| T01 | 0 | infra/docs | Setup: branch check, shared types, fixtures, PRD, diagrams | — |
| T02 | 1 | backend | `money.py` — pure money/symbol parsing | T01 |
| T03 | 1 | backend | `import_conversion.py` — USD→BRL at import | T01 |
| T11 | 1 | frontend | CsvImportModal currency detection + selector + i18n | T01 |
| T04 | 2 | backend | `csv_columns.py` — header aliases + file currency detection | T02 |
| T05 | 2 | backend | purchase_parser currency-aware (fix 12.50→1250) | T02 |
| T06 | 2 | backend | batch_parser price token | T02 |
| T12 | 2 | frontend | ImportPurchasesPage shows original currency | T11 |
| T07 | 3 | backend | importer.py reads price + currency, dry_run | T03, T04 |
| T08 | 3 | backend | purchases router converts to BRL in preview | T03, T05 |
| T09 | 3 | backend | batch add stores BRL acquisition price | T03, T06 |
| T10 | 4 | backend | `/collection/import` currency + dry_run params | T07, T09 |
| T13 | 5 | backend (CLI) | `import-csv --currency` + dry-run detection | T07 |
| T14 | 5 | docs | ADR + README note + diagram sync | T10, T12, T13 |

## File ownership (for cross-feature overlap detection)

| Task | Files touched (C = create, M = modify) |
|---|---|
| T01 | C `src/currency/types.py`; C `tests/currency/__init__.py`; C `tests/fixtures/collection_import/*.csv` (7 files) + C `tests/fixtures/purchase_usd_sample.html`; C `docs/prd/F171-collection-import-currency.md`; C `docs/diagrams/F171-architecture.mmd`; C `docs/diagrams/F171-journey.mmd` |
| T02 | C `src/currency/money.py`; C `tests/currency/test_money.py` |
| T03 | C `src/currency/import_conversion.py`; C `tests/currency/test_import_conversion.py` |
| T04 | C `src/collection/csv_columns.py`; C `tests/collection/test_csv_columns.py` |
| T05 | M `src/services/purchase_parser.py`; M `tests/services/test_purchase_parser.py` |
| T06 | M `src/collection/batch_parser.py`; M `tests/collection/test_batch_parser.py` |
| T07 | M `src/collection/importer.py`; C `tests/collection/test_importer_currency.py` |
| T08 | M `src/api/routers/purchases.py`; C `tests/api/test_purchases_currency.py` |
| T09 | M `src/collection/batch_add.py`; M `src/api/schemas/collection.py` (batch classes); M `src/api/routers/collection.py` (`batch_parse`, `batch_add` only); C `tests/api/test_collection_batch_currency.py` |
| T10 | M `src/api/routers/collection.py` (`import_collection` only); M `src/api/schemas/collection.py` (`ImportResult` only); C `tests/api/test_collection_import_currency.py` |
| T11 | M `frontend/src/components/CsvImportModal.tsx`; M `frontend/src/api/collection.ts`; M `frontend/src/types/api.ts` (`ImportResult`); M `frontend/src/i18n/locales/pt-BR.json`; M `frontend/src/i18n/locales/en.json`; C `frontend/src/components/__tests__/CsvImportModal.test.tsx` |
| T12 | M `frontend/src/pages/ImportPurchasesPage.tsx`; M `frontend/src/api/purchases.ts`; M `frontend/src/pages/__tests__/ImportPurchasesPage.test.tsx` |
| T13 | M **`src/cli/main.py`** (`import-csv` command only, ~L2703–2790) ⚠ batch high-risk; C `tests/cli/test_import_csv_currency.py` |
| T14 | C `docs/adr/00NN-import-currency-normalization.md` (next free number at commit time); M **`README.md`** ⚠ batch high-risk; M `docs/diagrams/F171-*.mmd` (sync only) |

Intra-feature shared files are ordered by wave: `routers/collection.py` and `schemas/collection.py`
go T09 (W3) → T10 (W4). The i18n locale files have a single owner (T11).

## Global acceptance criteria

- [ ] AC1 BRL exports (R$ symbol / `(R$)` header / `Moeda=BRL` column / Liga origin) import with values unchanged.
- [ ] AC2 USD exports are converted: `acquisition_price == round(usd * PTAX, 2)`.
- [ ] AC3 `currency=BRL|USD` override wins over detection (API, UI, CLI).
- [ ] AC4 Ambiguous files default to BRL with `currency_source="default"`, and the UI shows a warning.
- [ ] AC5 No PTAX rate → USD prices dropped with warnings. The import succeeds and no USD is stored as BRL.
- [ ] AC6 Purchase parser: `12.50` no longer becomes 1250. `US$` prices are converted, not zeroed.
- [ ] AC7 Batch text price tokens are parsed and stored as BRL.
- [ ] AC8 `dry_run` returns detection without writes (API and CLI).
- [ ] AC9 Liga CSV without a price column behaves exactly as before. All existing tests pass
      (`pytest tests/ --cov=src`, `cd frontend && npm test`, `ruff check src/`).
- [ ] AC10 PRD, ADR, `docs/diagrams/F171-architecture.mmd`, `docs/diagrams/F171-journey.mmd`, and a README note exist.

## Diagrams

- `docs/diagrams/F171-architecture.mmd`: owner T01 (created), synced by T14
- `docs/diagrams/F171-journey.mmd`: owner T01 (created), synced by T14

## Open question for the user (non-blocking)

The friend's original export file is not in the repo. The plan covers Liga, ManaBox-style, and generic
exports. If the real file is a different format, add it to `tests/fixtures/collection_import/`, and T04's
alias table can be extended without other changes.

## ADR number (batch reservation)
This feature's ADR number is **0014**, reserved in `tasks/features/EXECUTION-PLAN-F171-F179.md`. It overrides any "next free number" instruction in the task files.
