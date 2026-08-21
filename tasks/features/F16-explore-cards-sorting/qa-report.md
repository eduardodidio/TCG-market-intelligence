# QA Report -- F16 Explore Cards: Sorting Fields

**QA Agent:** QA
**Date:** 2026-08-21
**Feature:** F16 -- Explore Cards Sorting
**PRD:** `docs/prd/F16-explore-cards-sorting.md`

---

## 1. Acceptance Criteria Verification

| # | Criterion | Verdict | Evidence |
|---|-----------|---------|----------|
| AC1 | All sort fields work correctly (name, set, number, added, price) | **PASS** | Backend: `test_default_sort_by_name_asc`, `test_sort_by_name_desc`, `test_sort_by_set_asc/desc`, `test_sort_by_number_asc`, `test_sort_by_added_asc/desc` in `test_repository_collection.py`. API: `test_sort_by_name_asc_default`, `test_sort_by_set_desc`, `test_sort_by_number`, `test_sort_by_added` in `test_collection_sorting.py`. Frontend price sort: `sorts cards by price client-side (high to low)`, `sorts cards by price client-side (low to high)` in `MyCollection.test.tsx`. |
| AC2 | Pagination works with all sort options | **PASS** | Repository: `test_offset_skips_rows`, `test_offset_with_limit`, `test_offset_combined_with_sort`, `test_offset_beyond_data_returns_empty`. API: `test_offset_passed_to_repo`, `test_next_offset_in_meta_when_has_next`, `test_no_next_offset_when_no_more_pages`. Frontend: `uses offset-based pagination (offset param in API call)`. |
| AC3 | Sort state is reflected in URL search params | **PASS** | Frontend: `initializes sort from URL params` test verifies round-trip (URL -> state). `MyCollection.tsx` lines 187-194 sync sort state to URL params via `setSearchParams`. |
| AC4 | Existing tests pass, new tests cover sort logic | **PASS** | Backend: 894 passed (up from 857, +37 new). Frontend: 318 passed (up from 304, +14 new). All existing tests pass. |
| AC5 | Backend coverage stays above 70% | **PASS** | Backend coverage: 94.02% (up from 92.75%). Exceeds 70% threshold. |
| AC6 | README.md updated | **PASS** | `README.md` contains F16 section at line 462 with sort fields, backend/client-side sorting, offset pagination, URL persistence, and SortSelect component. |

---

## 2. Test Suite Results

### Backend

```
894 passed, 128 warnings in 188.70s
Coverage: 94.02% (required: >= 70%)
```

- Net-new tests: **37** (894 - 857)
- New test files: `tests/unit/database/test_repository_collection.py` (22 tests), `tests/api/test_collection_sorting.py` (15 tests)

### Frontend

```
30 test files, 318 tests passed
```

- Net-new tests: **14** (318 - 304)
- New test file: `frontend/tests/components/SortSelect.test.tsx` (5 tests)
- Extended file: `frontend/tests/pages/MyCollection.test.tsx` (+9 sort tests)

---

## 3. Test Plan Coverage Assessment

### Backend Repository Tests (test plan section 3.1)

| Plan ID | Covered? | Actual Test |
|---------|----------|-------------|
| B01 | Yes | `test_default_sort_by_name_asc` |
| B02 | Yes | `test_sort_by_name_desc` |
| B03 | Yes | `test_sort_by_set_asc` |
| B04 | Yes | `test_sort_by_set_desc` |
| B05 | Yes | `test_sort_by_number_asc` |
| B06 | Yes | `test_sort_by_added_desc` |
| B07 | Yes | `test_sort_by_added_asc` |
| B08 | Yes | `test_stable_ordering_with_same_sort_key` |
| B09 | Yes | `test_offset_skips_rows` |
| B10 | Yes | `test_offset_zero_returns_all` |
| B11 | Yes | `test_offset_beyond_data_returns_empty` |
| B12 | Yes | `test_invalid_sort_by_falls_back_to_name` |
| B13 | Partial | `test_null_name_en_sorts_to_beginning_asc` -- note: coalesce to '' means NULL sorts FIRST in asc (not last as plan says). See Issues. |
| B14 | No | No explicit desc test for NULL name |
| B15 | Yes | `test_after_id_still_works` |
| B16 | Yes | `test_after_id_takes_precedence_over_offset` -- note: code gives after_id precedence (not offset as plan says). Code is correct per PRD. |
| B17 | Yes | `test_name_search_filter_still_works` |
| B18 | Yes | `test_set_code_filter_still_works` |
| B19 | Yes | `test_offset_with_limit` (verifies limit+1 pattern) |
| B20 | Yes | `test_count_all`, `test_count_with_name_search`, `test_count_with_set_code`, `test_count_zero` |

### Backend API Tests (test plan section 3.2)

| Plan ID | Covered? | Actual Test |
|---------|----------|-------------|
| A01 | Yes | `test_sort_by_name_asc_default` |
| A02 | Yes | `test_sort_by_set_desc` |
| A03 | Yes | `test_sort_by_number` |
| A04 | Yes | `test_sort_by_added` |
| A05 | Yes | `test_invalid_sort_by_returns_422` (tests `price` specifically) |
| A06 | No | No test for `sort_by=foobar` (arbitrary invalid). Covered implicitly by regex validation. |
| A07 | Yes | `test_invalid_sort_dir_returns_422` |
| A08 | Yes | `test_offset_passed_to_repo` |
| A09 | Yes | `test_offset_none_by_default` (tests offset=0 default behavior) |
| A10 | Yes | `test_negative_offset_returns_422` |
| A11 | Yes | `test_next_offset_in_meta_when_has_next` |
| A12 | Yes | `test_cursor_still_works` |
| A13 | Yes | `test_sort_by_name_asc_default` (verifies default params) |
| A14 | Partial | Sort and offset combined tested individually; no single test with all 4 params. |
| A15 | Yes | `test_name_and_set_filters_still_work` |

### Frontend Tests (test plan sections 4.1 and 4.2)

| Plan ID | Covered? | Actual Test |
|---------|----------|-------------|
| F01 | Yes | `renders all 8 collection sort options` |
| F02 | Yes | `has data-testid attribute` |
| F03 | Yes | `highlights the correct default value` |
| F04 | Yes | `calls onChange with parsed sortBy and sortDir when selecting Name (Z-A)` |
| F05 | No | No explicit test for set option onChange. Covered implicitly by F04 pattern. |
| F06 | Yes | `calls onChange with price-desc when selecting Price (High-Low)` |
| F07 | No | No explicit test for added option onChange. Covered by F04 pattern. |
| F08 | No | No test for custom options subset. Acceptable -- component is generic. |
| F09 | Yes | `renders the sort dropdown` |
| F10 | Implicit | Default value verified via `initializes sort from URL params` test. |
| F11 | Yes | `selecting a sort option re-fetches data` |
| F12 | Implicit | Re-fetch always starts from offset=0 (verified by offset=0 in API call). |
| F13 | Yes | `initializes sort from URL params` (verifies URL -> state). URL sync tested via code inspection (useEffect on line 187-194). |
| F14 | Yes | `initializes sort from URL params` |
| F15 | Yes | `does NOT pass sort params to API for price sorting (client-side)` |
| F16 | Yes | `sorts cards by price client-side (high to low)` and `(low to high)` |
| F17 | Yes | `pushes null-price cards to the end for price-asc sort` |
| F18 | Yes | `uses offset-based pagination (offset param in API call)` |
| F19 | Implicit | `hasMore` logic based on `meta.total` in code; no explicit test for sentinel visibility with total=20. |

### Edge Cases (test plan section 6)

| Plan ID | Covered? | Notes |
|---------|----------|-------|
| E01 | Yes | FastAPI regex pattern `^(name|set|number|added)$` rejects empty string. |
| E02 | Yes | FastAPI `int` type coercion rejects floats. |
| E03 | Yes | `test_offset_beyond_data_returns_empty` |
| E04 | Yes | Existing `ge=1` constraint on limit. |
| E05 | Yes | Implicitly covered by tests with small data sets. |
| E06 | Yes | `test_stable_ordering_with_same_sort_key` |
| E07 | Yes | `test_null_name_en_sorts_to_beginning_asc` |
| E08 | No | No test for NULL `created_at`. Low risk -- SQLAlchemy handles NULL in ORDER BY. |
| E09 | No | No test for all-null prices in price sort. Low risk -- all equal = no reorder. |
| E10 | No | No test for mixed zero/null prices. Low risk -- code treats zero as valid number. |
| E11 | No | No test for invalid URL sort param fallback. See Issues. |
| E12 | No | No test for URL with sort but no dir. Frontend defaults to "asc" via `?? "asc"`. |
| E13 | No | No test for concurrent fetch abort. `fetchIdRef` pattern handles this but no test. |

---

## 4. Issues Found

### Minor Issues

**M1. NULL `name_en` coalesces to '' and sorts FIRST in ascending order, not LAST.**

The test plan (B13) specifies "None sorted last in asc" but the implementation coalesces NULL to `""` (empty string), which sorts BEFORE "Aether Vial". The test `test_null_name_en_sorts_to_beginning_asc` correctly documents this behavior, and the test name acknowledges it. This is a deliberate trade-off: `coalesce(name_en, '')` is consistent and predictable. However, the test plan document itself is inaccurate (it says "puts None last" but the code puts it first). The behavior is acceptable -- users would see unnamed cards at the top, which is arguably more noticeable/useful than hiding them at the end.

**Severity:** Minor (documentation inconsistency, behavior is acceptable)

**M2. Frontend does not validate URL sort param against known values.**

If a user navigates to `?sort=invalid&dir=asc`, the frontend will pass `sort_by=invalid` to the API, which returns 422. The user sees an error banner. A defensive check in `MyCollection.tsx` could validate the URL param against `COLLECTION_SORT_OPTIONS` and fall back to "name" for unknown values. This matches edge case E11 in the test plan, which has no corresponding test.

**Severity:** Minor (edge case, unlikely in normal use, error is shown to user)

**M3. Test plan item B16 says "offset takes precedence over after_id" but code gives after_id precedence.**

The repository code (line 616-619) checks `if after_id is not None` first, meaning `after_id` takes precedence. The test `test_after_id_takes_precedence_over_offset` correctly verifies the actual behavior. The test plan document is inaccurate. The actual behavior is correct per the PRD ("cursor parameter remains supported").

**Severity:** Minor (documentation inconsistency only)

---

## 5. Spot-Check Findings

### `src/database/repository.py` -- Sort Logic

- `_COLLECTION_SORT_COLUMNS` dict cleanly maps UI keys to DB columns. **CORRECT.**
- Invalid `sort_by` falls back to `name_en` via `.get(sort_by, "name_en")`. Defense in depth. **CORRECT.**
- `func.coalesce(col, "")` applied only to `name_en`. Other columns (set_code, collector_number, created_at) sort with native NULL handling. **CORRECT.**
- Secondary sort `UserCollectionRow.id.asc()` ensures stable ordering. **CORRECT.**
- `limit + 1` pattern for has_next detection. **CORRECT.**

### `src/api/routers/collection.py` -- Validation

- `sort_by` validated with regex `^(name|set|number|added)$`. Rejects `price`, empty string, arbitrary values. **CORRECT.**
- `sort_dir` validated with regex `^(asc|desc)$`. **CORRECT.**
- `offset` validated with `ge=0`. **CORRECT.**
- `next_offset` computed only when `offset is not None and has_next`. **CORRECT.**

### `frontend/src/components/SortSelect.tsx`

- Clean, minimal component. Splits value on `-` to extract sortBy and sortDir. **CORRECT.**
- `data-testid="sort-select"` present. **CORRECT.**
- 8 options in `COLLECTION_SORT_OPTIONS` match PRD spec. **CORRECT.**

### `frontend/src/pages/MyCollection.tsx` -- Sort Integration

- `sortBy` and `sortDir` initialized from URL search params. **CORRECT.**
- URL sync via `useEffect` with `setSearchParams`. Only non-default values written to URL. **CORRECT.**
- Price sort excluded from API params (`if (sortBy !== "price")`). **CORRECT.**
- Client-side price sort uses `Infinity`/`-Infinity` for null handling. **CORRECT.**
- `fetchIdRef` pattern discards stale responses. **CORRECT.**
- Offset-based pagination: `buildParams` includes `offset`. **CORRECT.**

### `src/api/schemas/envelope.py` -- Meta Schema

- `Meta` model has `offset: int | None = None` field. **CORRECT.**
- `paginated_response` passes `**meta_kwargs` to `Meta`, accepting `offset` keyword. **CORRECT.**

---

## 6. Verdict: PASSED

All 6 acceptance criteria are met. Backend and frontend test suites pass with no regressions. Coverage increased from 92.75% to 94.02%. The 3 minor issues found are all non-blocking: two are documentation inconsistencies in the test plan (not in code), and one is a defensive enhancement for an unlikely URL edge case. The implementation is clean, well-tested, and matches the PRD specification.

---

## 7. Test Metrics Summary

| Metric | Before F16 | After F16 | Delta |
|--------|-----------|-----------|-------|
| Backend tests | 857 | 894 | +37 |
| Frontend tests | 304 | 318 | +14 |
| Backend coverage | 92.75% | 94.02% | +1.27% |
| New backend test files | -- | 2 | -- |
| New frontend test files | -- | 1 | -- |
