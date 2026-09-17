# F135 Purchase HTML Import -- QA Report

**QA Agent:** Claude Opus 4.6
**Date:** 2026-09-17
**Branch:** homol
**Tasks validated:** T01 (parser), T02 (matcher), T03 (API), T04 (frontend)
**T05 (bulk processing):** Not yet implemented -- excluded from validation.

---

## Verdict: PASS

All four implemented tasks pass their test suites, lint cleanly, and build
successfully. TechLead Finding #6 (medium severity -- missing transaction
wrapping on apply) has been fixed. Five new backend tests were added to
cover the fix and fill test gaps.

---

## Test Results

### Backend

```
Parser:   27 passed  (test_purchase_parser.py)
Matcher:  25 passed  (test_purchase_matcher.py)
API:      26 passed  (test_import_purchases.py)  -- 21 original + 5 new
Total:    78 passed, 0 failed
```

### Frontend

```
ImportPurchasesPage: 18 passed, 0 failed  (1.72s)
```

### Build & Lint

```
Frontend build:    OK (3.92s, 74 PWA entries)
Ruff (3 files):    All checks passed
```

### Regression

```
Collection patch tests:  19 passed (backward-compatible session param)
Portfolio tests:         4 pre-existing failures (unrelated to F135)
```

---

## TechLead Finding #6 -- Fixed

**Problem:** The apply endpoint (`POST /api/v1/purchases/apply`) called
`repo.update_collection_entry()` in a loop, each call opening its own
`Session` + `commit()`. A crash mid-loop would leave data in a partial
state (some entries updated, others not).

**Fix (two parts):**

1. **`src/database/repository.py`** -- Added optional `session` keyword
   parameter to `update_collection_entry()`, following the same pattern
   used by `upsert_source_card()`. When a session is provided, the method
   uses it and calls `flush()` instead of `commit()` (caller manages the
   transaction). When no session is provided, behavior is unchanged
   (creates own session, commits). The parameter is keyword-only (`*`),
   so all existing callers are 100% backward compatible.

2. **`src/api/routers/purchases.py`** -- Restructured the apply endpoint
   into a two-phase approach:
   - **Phase 1 (validation):** Read all entries, validate ownership,
     check prices/dates, prepare updates. Any 404/403 raises immediately.
   - **Phase 2 (atomic write):** Apply all validated updates inside a
     single `repo.transaction()` context manager, passing the transaction
     session to each `update_collection_entry()` call. If any update
     fails, the entire batch rolls back.

**Verification:** New test `test_apply_uses_transaction` confirms that
`repo.transaction()` is used and the session is passed to every
`update_collection_entry()` call.

---

## Other TechLead Findings (not addressed -- low priority)

| # | Severity | Finding | Status |
|---|----------|---------|--------|
| 1 | Minor | `_CODIGO_RE` edge case with multi-letter suffixes | Accepted -- edge case |
| 2 | Minor | `parse_liga_orders` warnings discarded | Acknowledged -- low priority |
| 3 | Info | Bilingual name heuristic false positives | Mitigated by matcher cascade |
| 4 | Info | `_pick_best` tiebreaker by lowest id | Acceptable for MVP |
| 5 | Info | No fuzzy matching | Reasonable for store-generated HTML |
| 7 | Minor | Apply endpoint uses `dict` instead of Pydantic model | Acknowledged -- low priority |
| 8 | Minor | `total_sealed_skipped` always 0 | Acknowledged -- cosmetic |
| 9 | Info | Pagination in `_load_full_collection` | Fine for < 10K entries |
| 10 | Info | Error banner flash on mixed valid+invalid drop | Minor UX nit |
| 11 | Info | Overwrite flag indirection non-obvious | Logic correct, comment would help |
| 12 | Info | Page content uses hardcoded English strings | Consistent with project |
| 13 | Info | Router registrations correct | Verified |
| 14 | Info | Missing `purchases` tag in `_OPENAPI_TAGS` | Cosmetic |

---

## Test Gaps Filled (5 new tests)

| Test | Purpose |
|------|---------|
| `test_apply_invalid_price_is_skipped` | Invalid price format ("not-a-number") is skipped, not a 500 |
| `test_apply_invalid_date_is_ignored` | Bad date string results in `acquired_at=None`, not an error |
| `test_apply_uses_transaction` | Verifies `repo.transaction()` is called and session is passed to each `update_collection_entry` call |
| `test_apply_no_entry_id_silently_skipped` | Match without `collection_entry_id` key is silently ignored |
| `test_apply_mixed_valid_and_invalid` | Mix of invalid price + valid + already-has-price in one batch -- validates correct counts |

Also cleaned up 3 pre-existing lint violations in the test file (unused
imports: `io`, `date`, `patch`).

---

## Files Modified by QA

- `src/database/repository.py` -- added `session` kwarg to `update_collection_entry()`
- `src/api/routers/purchases.py` -- wrapped apply loop in `repo.transaction()`
- `tests/api/test_import_purchases.py` -- added 5 tests, fixed unused imports

## Files Reviewed (read-only)

- `src/services/purchase_parser.py` (539 lines)
- `src/services/purchase_matcher.py` (345 lines)
- `frontend/src/pages/ImportPurchasesPage.tsx` (597 lines)
- `frontend/src/api/purchases.ts` (134 lines)
- `tests/services/test_purchase_parser.py`
- `tests/services/test_purchase_matcher.py`
- `frontend/src/pages/__tests__/ImportPurchasesPage.test.tsx`
