# F171 — Wave 2 summary

**Status:** completed
**Tasks:** F171-T04, F171-T05, F171-T06, F171-T12
**Generated:** 2026-09-24T12:55:00Z

## Files touched
- `src/collection/csv_columns.py` (T04: new module — header aliases + file currency detection, untracked/uncommitted)
- `tests/collection/test_csv_columns.py` (T04: 300 lines of tests, untracked/uncommitted)
- `src/services/purchase_parser.py` (T05: currency-aware money parsing, fixes `12.50`→`1250` bug and `US$` zeroing)
- `tests/services/test_purchase_parser.py` (T05: new currency scenarios)
- `src/collection/batch_parser.py` (T06: `ParsedLine.price`/`price_currency`, `_PRICE_RE` token extraction before name parsing)
- `tests/collection/test_batch_parser.py` (T06: price-token test cases)
- `frontend/src/pages/ImportPurchasesPage.tsx` (T12: converted-currency badge for USD preview rows)
- `frontend/src/api/purchases.ts` (T12: `original_unit_price`/`original_currency`/`exchange_rate` optional fields)
- `frontend/src/pages/__tests__/ImportPurchasesPage.test.tsx` (T12: badge tests)
- `tasks/features/F171-collection-import-currency/F171-T04.md`, `F171-T05.md` (status bumped to `done`)

## Decisions
- T06 followed the plan's "last match wins" rule for `_PRICE_RE` and strips the matched token before name extraction, same ordering as `[set]`.
- T12 read `original_unit_price`/`original_currency`/`exchange_rate` defensively (all optional) since the real backend contract lands in T08 (Wave 3).

## Notes for next Wave
- **T06 and T12 task files still say `Status: planned`** even though the diffs (`batch_parser.py` +41 lines, `test_batch_parser.py` +88, `ImportPurchasesPage.tsx` +35, its test +111) are present and complete — verified by running the tests. Wave 3 owners (T07/T09 for batch_parser, T08 wiring the real API for T12) should confirm with the Wave 2 developers and update the status field before TechLead reviews.
- All Wave 2 changes are **uncommitted** in the working tree (no `F171 Wave 2` commit exists yet); T04's two new files (`src/collection/csv_columns.py`, `tests/collection/test_csv_columns.py`) are still untracked. Whoever commits Wave 2 must stage files one by one (never `git add -A`, per CLAUDE.md).
- `pytest tests/collection/test_batch_parser.py tests/collection/test_csv_columns.py tests/services/test_purchase_parser.py` → 122 passed.
- `npx vitest run src/pages/__tests__/ImportPurchasesPage.test.tsx` → 21 passed, 1 failed (`shows result state after apply`). Confirmed via `git stash` that this failure **pre-exists on the base commit** (before any Wave 2 change) — it is not a T12 regression, but it's still failing and should be fixed before/alongside Wave 3 frontend work.
