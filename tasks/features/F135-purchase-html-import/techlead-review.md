# F135 Purchase HTML Import -- Tech Lead Review

**Reviewer:** Tech Lead
**Date:** 2026-09-17
**Branch:** homol
**Tasks reviewed:** T01 (parser), T02 (matcher), T03 (API), T04 (frontend)
**T05 (bulk processing):** Not yet implemented -- excluded from review.

---

## Verdict: APPROVED

All four implemented tasks are well-structured, lint-clean, and pass their
test suites (73 backend tests, 18 frontend tests).  The code follows
project conventions, introduces no new dependencies, and correctly handles
both HTML formats.  The findings below are minor and none block merging.

---

## Summary

The feature adds a three-stage import workflow (upload HTML -> preview
matched cards -> apply acquisition prices) for Nerdz Cards and Liga Magic
purchase history files.  The implementation is split cleanly across four
layers: pure-logic parser, pure-logic matcher, thin API router, and
self-contained React page.  This separation makes each piece independently
testable, which the developer has exploited well.

**Strengths:**

- Clean separation of concerns: parser and matcher are pure functions with
  no I/O dependencies.
- Cascading match strategy with transparent confidence scoring (1.0 / 0.95
  / 0.85 / 0.7) is well-designed and documented.
- Accent normalisation uses stdlib `unicodedata` as required -- no
  `unidecode` dependency introduced.
- File validation covers extension (.html/.htm), size (5 MB), and encoding
  (UTF-8 with latin-1 fallback).
- Frontend handles all three states cleanly, includes drag-and-drop, per-
  card price editing, select-all/deselect-all, confidence badges, dark
  mode support, and unmatched items disclosure.
- DFC (double-faced card) matching works in both directions via
  `_front_face()` indexing.
- Duplicate detection flags when multiple parsed items hit the same
  collection entry.
- Overwrite-existing guard is enforced at both preview (filtering) and
  apply (server-side check) stages.
- Tests are thorough with realistic HTML fixtures and cover edge cases
  (sealed products, promo set codes, unexpanded Liga orders, multi-store
  Liga orders, cross-language matching, accent normalisation, DFC matching,
  already-has-price, wrong user, 404, file-too-large).

---

## Findings by Task

### T01 -- HTML Parser (`src/services/purchase_parser.py`)

| # | Severity | Finding |
|---|----------|---------|
| 1 | Minor | `_CODIGO_RE` uses `(\d+[a-z]?)` for collector number, which handles most cases but would not match multi-letter suffixes like `139ab` or `★`. Edge case -- acceptable for now. |
| 2 | Minor | `parse_liga_orders` builds a `warnings` list locally but never returns it. Unexpanded-order warnings are generated but silently discarded. The caller (API endpoint) cannot surface these to the user. Consider returning warnings alongside orders (e.g., as a tuple or by adding a `warnings` field to a return dataclass). |
| 3 | Info | The `_split_bilingual_name` heuristic classifying names by presence of diacritics can misclassify some PT-only cards that happen to have no accents (e.g., "Serra Angel" in PT is "Anjo de Serra" -- no accents). The matcher's cross-language fallback mitigates this, so it is not a real problem. |

**Tests:** 27 tests covering Nerdz (single card, foil, sealed, EN-only,
promo set code), Liga (expanded, unexpanded, multi-store), bilingual name
splitting, price parsing, auto-detection, and source-file tracking. Good
coverage for a parser module.

### T02 -- Card Matcher (`src/services/purchase_matcher.py`)

| # | Severity | Finding |
|---|----------|---------|
| 4 | Info | `_pick_best` breaks ties by lowest `id`. This is deterministic but may not be the semantically best choice when multiple collection entries exist for the same card (e.g., different printings). Acceptable for MVP -- the user can deselect in the preview table. |
| 5 | Info | No fuzzy/substring matching (e.g., Levenshtein). The cascade is exact-name-only at each tier. This means a typo in the HTML or a slight name discrepancy will result in "unmatched". Given that the names come from the stores' own HTML (not user input), this is a reasonable tradeoff. |

**Tests:** 25 tests covering all five confidence tiers, cross-language
matching, accent normalisation, already-has-price flagging, DFC prefix
matching, apostrophes, duplicate detection, and report totals. Solid
coverage.

### T03 -- API Endpoints (`src/api/routers/purchases.py`)

| # | Severity | Finding |
|---|----------|---------|
| 6 | Medium | **No transactional wrapping on apply.** The apply endpoint calls `repo.update_collection_entry()` in a loop, and each call opens its own Session+commit. If the server crashes mid-loop, some entries will be updated and others will not, leaving the data in a partial state. Consider wrapping the batch in a single transaction (the repo has a `transaction()` context manager per F99). |
| 7 | Minor | The apply endpoint accepts `body: dict` without a Pydantic model. This means there is no request-body validation or OpenAPI schema generation for this endpoint. A Pydantic `BaseModel` with `matches: list[ApplyMatchSchema]` would improve both validation and documentation. |
| 8 | Minor | `sealed_count` is initialized to 0 on line 67 but is never incremented anywhere. The response field `total_sealed_skipped` always returns 0. Sealed products are correctly filtered by the parser (no item is emitted), so they are invisible to the API. Either remove the field or count the difference between raw articles and emitted items. |
| 9 | Info | `_load_full_collection` paginates in 500-entry batches, which is correct for large collections but creates N/500 DB round-trips. For collections under 10K entries this is fine. If perf becomes an issue, a dedicated `list_all_collection()` repo method would help. |

**Tests:** 21 tests covering preview (happy path, unknown format, no files,
non-HTML, overwrite flag, empty collection, sealed, multiple files) and
apply (happy path, skip existing, overwrite, empty matches, wrong user,
not found, multiple entries, file too large). Covers all major branches.

### T04 -- Frontend (`ImportPurchasesPage.tsx` + `purchases.ts`)

| # | Severity | Finding |
|---|----------|---------|
| 10 | Info | The `addFiles` callback clears the error state when valid files are added, but does NOT clear the error when invalid files are rejected alongside valid ones. Line 82 sets the error, line 84 does not clear it if `htmlFiles.length > 0`. This means the error banner can flash briefly and then stay if invalid + valid files are dropped together. Minor UX nit. |
| 11 | Info | The overwrite checkbox in the upload state affects the preview endpoint (`overwrite_existing=true`), but in the apply handler (line 152) the overwrite flag sent per-match is `m.already_has_price`. This means that if the user checks "overwrite existing" and the preview includes matches with existing prices, those matches will correctly have `overwrite: true` in the apply payload. Logic is correct but the indirection is non-obvious -- a comment would help. |
| 12 | Info | i18n keys `nav.importPurchases` are present in both `en.json` and `pt-BR.json`. The page content itself uses hardcoded English strings (headings, button labels, column headers). This is consistent with other pages in the project that have not been fully internationalised. |

**Tests:** 18 tests covering upload state rendering, file selection, non-
HTML rejection, upload button enabling, API call on upload, preview state
rendering, confidence badges, pre-check logic, select/deselect all, price
editing, warnings, unmatched section, already-has-price indicator, empty
matches, apply call, result state, import-more reset, and back-to-upload.
Comprehensive for a page component.

### Integration (app.py, App.tsx, Layout.tsx)

| # | Severity | Finding |
|---|----------|---------|
| 13 | Info | Router registered in `app.py` at line 358/384 under `/api/v1`. Route in `App.tsx` at `/import-purchases`. Nav item in `Layout.tsx` in `PRIMARY_NAV_ITEMS` with icon. All three registrations are correct and consistent. |
| 14 | Info | The `_OPENAPI_TAGS` list in `app.py` does not include a `purchases` tag. The router uses `tags=["purchases"]`, so the tag will appear in Swagger without a description. Non-blocking but inconsistent with other routers. |

---

## Recommendations

1. **(Medium priority)** Wrap the apply loop in a single transaction to
   ensure atomicity. If one update fails, none should be committed. The
   repo's `transaction()` context manager or a bulk-update method would
   work.

2. **(Low priority)** Return Liga parser warnings from
   `parse_liga_orders` so the API can surface them (e.g., "Order #X has
   no expanded card data").  Currently these warnings are generated but
   discarded.

3. **(Low priority)** Replace `body: dict` in the apply endpoint with a
   Pydantic model for proper validation and OpenAPI docs.

4. **(Low priority)** Remove or populate `total_sealed_skipped` in the
   preview response -- it is always 0 currently.

5. **(Low priority)** Add `purchases` to `_OPENAPI_TAGS` in `app.py`.

---

## Test Results

```
Backend:  73 passed, 0 failed  (2.77s)
Frontend: 18 passed, 0 failed  (1.79s)
Ruff:     All checks passed
```

---

## Files Reviewed

### New files
- `src/services/purchase_parser.py` (539 lines)
- `src/services/purchase_matcher.py` (345 lines)
- `src/api/routers/purchases.py` (264 lines)
- `frontend/src/pages/ImportPurchasesPage.tsx` (597 lines)
- `frontend/src/api/purchases.ts` (134 lines)
- `tests/services/test_purchase_parser.py` (659 lines)
- `tests/services/test_purchase_matcher.py` (322 lines)
- `tests/api/test_import_purchases.py` (408 lines)
- `frontend/src/pages/__tests__/ImportPurchasesPage.test.tsx` (469 lines)

### Modified files
- `src/api/app.py` -- purchases router imported and registered
- `frontend/src/App.tsx` -- lazy import + `/import-purchases` route
- `frontend/src/components/Layout.tsx` -- nav item with arrowUpTray icon
- `frontend/src/i18n/locales/en.json` -- `nav.importPurchases` key
- `frontend/src/i18n/locales/pt-BR.json` -- `nav.importPurchases` key
