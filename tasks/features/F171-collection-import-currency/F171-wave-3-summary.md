# F171 — Wave 3 summary

**Status:** completed
**Tasks:** F171-T07, F171-T08, F171-T09
**Generated:** 2026-09-24T13:05:00Z

## Files touched
- `src/collection/importer.py` (T07: `import_collection_csv` now uses `resolve_columns`/`detect_file_currency`, converts per-row prices via `to_brl`, adds `currency`/`rate_lookup`/`dry_run`/`today` kwargs)
- `tests/collection/test_importer_currency.py` (T07: new, 8 fixtures + override/edge/error/boundary scenarios)
- `src/api/routers/purchases.py` (T08: `import_preview` converts USD `unit_price` to BRL via `_convert_item` + `rate_lookup_from_converter`, adds `original_unit_price`/`original_currency`/`exchange_rate`)
- `tests/api/test_purchases_currency.py` (T08: new)
- `src/collection/batch_add.py` (T09: `BatchAddEntry.acquisition_price`/`price_currency`, `BatchAddResult.warnings`, conversion before row insert; also fixed a pre-existing `session.begin_nested()` savepoint leak that caused a `RecursionError` on 500-entry batches)
- `src/api/schemas/collection.py` (T09: batch pydantic classes only — `BatchAddEntry`, `ParsedLineResponse`, `BatchAddResultResponse`)
- `src/api/routers/collection.py` (T09: `batch_parse`/`batch_add` handlers only, wires `rate_lookup_from_converter`)
- `tests/api/test_collection_batch_currency.py` (T09: new)
- `tasks/features/F171-collection-import-currency/F171-T07.md`, `F171-T09.md` (status bumped to `done`)

`src/collection/converter.py` was reviewed (per T07 dev notes) and confirmed to carry no monetary fields — **not changed**.

## Decisions
- Row currency precedence (T07): explicit user `currency` choice wins for every row → else the row's own currency column → else a symbol detected in the price cell → else the file-level detection fallback. An unsupported currency (e.g. bare `EUR`) is passed through to `to_brl`, which drops the price and adds an `unsupported_currency` warning instead of silently defaulting to BRL.
- T09 fixed a latent bug in `batch_add_entries`: the per-entry `session.begin_nested()` savepoint was never committed on the success path, so large batches accumulated nested transactions and blew the recursion limit on `session.commit()`. Fixed in the same file this task already owned (one-line `savepoint.commit()`), not a separate cleanup task.

## Notes for next Wave
- **T08's task file still says `Status: planned`** even though `src/api/routers/purchases.py` (+53/-lines) and `tests/api/test_purchases_currency.py` are present, complete, and passing — this wave did not update that file's header; T10/T14 owners (or TechLead) should confirm with the T08 developer and bump the status before further review.
- All Wave 3 changes are **uncommitted** in the working tree (no `F171 Wave 3` commit exists yet, on top of the existing `64d8815 F171 Wave 2` commit). Whoever commits Wave 3 must stage files one by one (never `git add -A`, per CLAUDE.md) — note `src/api/routers/collection.py` and `src/api/schemas/collection.py` are shared with T10 (Wave 4), which touches different handlers/classes in the same files.
- Targeted suite `pytest tests/collection/test_importer_currency.py tests/api/test_purchases_currency.py tests/api/test_collection_batch_currency.py` → 38 passed.
- Full `pytest tests/collection/ tests/api/ tests/services/test_purchase_parser.py` → 1061 passed, 5 failed. Verified via `git stash` that all 5 failures (`test_cards_router.py::TestGetHistory::test_specific_period`, 2x `test_collection_acquisition_fields.py`, 2x `test_collection_liga_links.py`) **pre-exist on the Wave 2 base commit** — not Wave 3 regressions, but still unresolved going into Wave 4.
- `ruff check` on all 5 files touched by T07/T08/T09 → clean.
- Wave 2's carried-forward frontend failure (`ImportPurchasesPage.test.tsx::shows result state after apply`) was not re-checked this wave (no frontend files touched); still open for whoever picks up frontend work.
