# F16 Test Plan -- Explore Cards: Sorting Fields

**Feature:** F16
**Author:** TEA agent
**Date:** 2026-08-21

---

## 1. Scope

This test plan covers the sorting and offset-pagination feature for the My Collection page:

- **Backend repository** (`src/database/repository.py`): `list_collection` with `sort_by`, `sort_dir`, and `offset` parameters (T01)
- **Backend API** (`src/api/routers/collection.py`): `GET /api/v1/collection` with new query params `sort_by`, `sort_dir`, `offset` (T02)
- **Frontend component** (`frontend/src/components/SortSelect.tsx`): reusable sort dropdown (T03)
- **Frontend page** (`frontend/src/pages/MyCollection.tsx`): sort integration, URL param persistence, client-side price sorting, offset-based pagination (T04)
- **Cross-cutting** (T05): regression, coverage thresholds, documentation

Out of scope: server-side price sorting, multi-column sort, user preference persistence.

---

## 2. Test Strategy

| Layer | Framework | Location | Target |
|-------|-----------|----------|--------|
| Backend unit | pytest | `tests/unit/test_repository_sort.py` | Repository sort/offset logic |
| Backend API | pytest + FastAPI TestClient | `tests/api/test_collection_sort.py` | Endpoint param validation, response shape |
| Backend integration | pytest | `tests/integration/` (existing files) | End-to-end sorted query through DB |
| Frontend unit | Vitest + RTL | `frontend/tests/components/SortSelect.test.tsx` | Component rendering, events |
| Frontend integration | Vitest + RTL | `frontend/tests/pages/MyCollection.test.tsx` (extend) | Sort state, URL params, price sort |

Coverage requirements: backend >= 70% (maintain current ~92.75%), all existing tests must pass.

---

## 3. Backend Tests

### 3.1 Repository: `list_collection` sort params (T01)

Test file: `tests/unit/test_repository_sort.py`

All tests use an in-memory SQLite repo fixture with pre-seeded `UserCollectionRow` entries.

| # | Test Name | Setup / Preconditions | Expected Behavior | Task |
|---|-----------|----------------------|-------------------|------|
| B01 | `test_default_sort_is_name_asc` | Insert cards: "Zephyr", "Alpha", "Mid" | Returns ["Alpha", "Mid", "Zephyr"] | T01 |
| B02 | `test_sort_by_name_desc` | Same as B01 | Returns ["Zephyr", "Mid", "Alpha"] with `sort_by="name", sort_dir="desc"` | T01 |
| B03 | `test_sort_by_set_code_asc` | Cards with set_code: "ZNR", "AFR", "DMR" | Returns AFR, DMR, ZNR order | T01 |
| B04 | `test_sort_by_set_code_desc` | Same as B03 | Returns ZNR, DMR, AFR order | T01 |
| B05 | `test_sort_by_collector_number_asc` | Cards with collector_number: "3", "1", "12" | Returns string sort: "1", "12", "3" (known limitation) | T01 |
| B06 | `test_sort_by_added_desc` | Cards with different `created_at` | Returns newest first | T01 |
| B07 | `test_sort_by_added_asc` | Same as B06 | Returns oldest first | T01 |
| B08 | `test_secondary_sort_by_id` | Two cards with same `name_en` | Stable order by `id ASC` as tiebreaker | T01 |
| B09 | `test_offset_returns_correct_slice` | 5 cards sorted by name | `offset=2, limit=2` returns cards 3-4 | T01 |
| B10 | `test_offset_zero_returns_from_start` | 5 cards | `offset=0, limit=3` returns first 3 | T01 |
| B11 | `test_offset_beyond_total_returns_empty` | 3 cards | `offset=100` returns `[]` | T01 |
| B12 | `test_invalid_sort_by_falls_back_to_name` | Cards in DB | `sort_by="invalid"` returns name-asc order | T01 |
| B13 | `test_null_name_sorted_last_asc` | Cards: "Alpha", None, "Beta" | `sort_by="name", sort_dir="asc"` puts None last | T01 |
| B14 | `test_null_name_sorted_first_desc` | Same as B13 | `sort_by="name", sort_dir="desc"` puts None first or last consistently | T01 |
| B15 | `test_after_id_backward_compat` | 5 cards | `after_id=<id_of_card_2>` without offset still works (cursor-based) | T01 |
| B16 | `test_offset_takes_precedence_over_after_id` | 5 cards | Both `offset=1` and `after_id=<some_id>` provided: offset wins | T01 |
| B17 | `test_sort_with_name_search_filter` | Cards matching and not matching search | `sort_by="set", name_search="bolt"` returns only matching cards, sorted by set | T01 |
| B18 | `test_sort_with_set_code_filter` | Cards from multiple sets | `sort_by="name", set_code="DMR"` returns only DMR cards, sorted by name | T01 |
| B19 | `test_limit_plus_one_pattern_for_has_next` | 5 cards | `offset=0, limit=3` returns 4 items (limit+1) to signal has_next | T01 |

### 3.2 Repository: `count_collection` unchanged (T01)

| # | Test Name | Setup / Preconditions | Expected Behavior | Task |
|---|-----------|----------------------|-------------------|------|
| B20 | `test_count_collection_unaffected_by_sort` | 5 cards | `count_collection` returns 5 regardless of sort params | T01 |

### 3.3 API endpoint: query param handling (T02)

Test file: `tests/api/test_collection_sort.py`

Uses FastAPI TestClient with a mocked `Repository` (matching existing pattern in `test_collection_detail.py`).

| # | Test Name | Setup / Preconditions | Expected Behavior | Task |
|---|-----------|----------------------|-------------------|------|
| A01 | `test_sort_by_name_asc_returns_sorted` | Mock repo returns cards in name order | `GET /collection?sort_by=name&sort_dir=asc` returns 200 with sorted data | T02 |
| A02 | `test_sort_by_set_desc` | Mock repo | `GET /collection?sort_by=set&sort_dir=desc` passes params to repo | T02 |
| A03 | `test_sort_by_number` | Mock repo | `GET /collection?sort_by=number` returns 200 | T02 |
| A04 | `test_sort_by_added` | Mock repo | `GET /collection?sort_by=added&sort_dir=desc` returns 200 | T02 |
| A05 | `test_invalid_sort_by_returns_422` | No setup needed | `GET /collection?sort_by=price` returns 422 validation error | T02 |
| A06 | `test_invalid_sort_by_arbitrary_returns_422` | No setup needed | `GET /collection?sort_by=foobar` returns 422 | T02 |
| A07 | `test_invalid_sort_dir_returns_422` | No setup needed | `GET /collection?sort_dir=invalid` returns 422 | T02 |
| A08 | `test_offset_param_positive` | Mock repo returns cards | `GET /collection?offset=10&limit=5` passes offset=10 to repo | T02 |
| A09 | `test_offset_param_zero` | Mock repo | `GET /collection?offset=0` returns 200 | T02 |
| A10 | `test_negative_offset_returns_422` | No setup needed | `GET /collection?offset=-1` returns 422 | T02 |
| A11 | `test_response_meta_includes_offset` | Mock repo | Response JSON `meta` contains `offset` field | T02 |
| A12 | `test_cursor_backward_compat` | Mock repo supports after_id | `GET /collection?cursor=<encoded>` still works | T02 |
| A13 | `test_default_params` | Mock repo | `GET /collection` (no sort params) calls repo with `sort_by="name", sort_dir="asc", offset=0` | T02 |
| A14 | `test_sort_and_offset_combined` | Mock repo | `GET /collection?sort_by=added&sort_dir=desc&offset=20&limit=10` passes all params correctly | T02 |
| A15 | `test_sort_with_search_filter` | Mock repo | `GET /collection?sort_by=set&name=bolt` passes both sort and filter to repo | T02 |

---

## 4. Frontend Tests

### 4.1 SortSelect component (T03)

Test file: `frontend/tests/components/SortSelect.test.tsx`

| # | Test Name | Setup / Preconditions | Expected Behavior | Task |
|---|-----------|----------------------|-------------------|------|
| F01 | `renders all sort options` | Render with `COLLECTION_SORT_OPTIONS` | 8 `<option>` elements with correct labels | T03 |
| F02 | `renders with data-testid` | Render component | Element with `data-testid="sort-select"` exists | T03 |
| F03 | `highlights the current value` | Render with `value="name-asc"` | The select element's value is `"name-asc"` | T03 |
| F04 | `calls onChange with parsed sortBy and sortDir` | Render, fireEvent.change to `"name-desc"` | `onChange` called with `("name", "desc")` | T03 |
| F05 | `calls onChange for set option` | Change to `"set-asc"` | `onChange` called with `("set", "asc")` | T03 |
| F06 | `calls onChange for price option` | Change to `"price-desc"` | `onChange` called with `("price", "desc")` | T03 |
| F07 | `calls onChange for added option` | Change to `"added-desc"` | `onChange` called with `("added", "desc")` | T03 |
| F08 | `renders with custom options subset` | Render with only 3 options | Only 3 `<option>` elements | T03 |

### 4.2 MyCollection page sort integration (T04)

Test file: `frontend/tests/pages/MyCollection.test.tsx` (extend existing file)

Tests use `MemoryRouter`, mocked `fetch`, and existing `makeCollectionCard` / `envelope` helpers.

| # | Test Name | Setup / Preconditions | Expected Behavior | Task |
|---|-----------|----------------------|-------------------|------|
| F09 | `renders sort dropdown on page load` | Standard mock fetch | `data-testid="sort-select"` is present | T04 |
| F10 | `default sort is name-asc` | Standard mock fetch | Sort select value is `"name-asc"` | T04 |
| F11 | `changing sort triggers re-fetch with sort params` | Mock fetch, change sort to "set-asc" | Fetch called with `sort_by=set&sort_dir=asc&offset=0` | T04 |
| F12 | `changing sort resets offset to zero` | Load page, scroll to load more, change sort | Offset reset, new fetch from 0 | T04 |
| F13 | `URL params updated on sort change` | Change sort to "added-desc" | URL contains `?sort=added&dir=desc` | T04 |
| F14 | `page loads with sort from URL params` | `MemoryRouter` with `initialEntries=["/collection?sort=set&dir=asc"]` | Sort select value is `"set-asc"`, API called with `sort_by=set` | T04 |
| F15 | `price sort does not pass sort_by to API` | Change sort to "price-desc" | Fetch called WITHOUT `sort_by=price`; uses default server sort | T04 |
| F16 | `price sort reorders cards client-side` | Cards with prices [5, 10, 1], sort by price desc | Rendered order: 10, 5, 1 | T04 |
| F17 | `price sort handles null prices` | Cards: price=10, price=null, price=5; sort by price asc | Null-price card sorted last: [5, 10, null] | T04 |
| F18 | `offset-based pagination: load more increments offset` | Mock fetch returns cards, trigger load-more | Second fetch includes `offset=<limit>` | T04 |
| F19 | `offset-based pagination: hasMore based on total` | Mock fetch with `meta.total=20`, 10 cards loaded | Load-more button/sentinel visible | T04 |

---

## 5. Integration Tests

### 5.1 API contract tests (T02 + T05)

These tests verify the full request-response contract through FastAPI TestClient with a real (in-memory) SQLite database.

Test file: `tests/integration/test_collection_sort_integration.py`

| # | Test Name | Setup / Preconditions | Expected Behavior | Task |
|---|-----------|----------------------|-------------------|------|
| I01 | `test_api_returns_cards_sorted_by_name_asc` | Seed DB with 3 cards (Zephyr, Alpha, Mid) | Response JSON `data` array is in A-Z order | T02/T05 |
| I02 | `test_api_returns_cards_sorted_by_set` | Seed DB with cards from ZNR, AFR | Response sorted by set_code asc | T02/T05 |
| I03 | `test_api_offset_pagination_returns_correct_page` | Seed 10 cards | `offset=5&limit=3` returns cards 6-8 | T02/T05 |
| I04 | `test_api_sort_plus_filter_combined` | Seed cards, some matching name search | `sort_by=added&name=bolt` returns filtered+sorted | T02/T05 |
| I05 | `test_api_empty_collection_with_sort_returns_empty` | Empty DB | `sort_by=name` returns `{"data": [], ...}` | T02/T05 |
| I06 | `test_api_response_meta_has_offset_and_total` | Seed 5 cards | Response `meta` includes `offset` (number) and `total` (5) | T02/T05 |

---

## 6. Edge Cases & Error Handling

| # | Scenario | Expected Behavior | Layer | Task |
|---|----------|-------------------|-------|------|
| E01 | `sort_by` is an empty string | 422 validation error | API | T02 |
| E02 | `offset` is a float (e.g. `1.5`) | 422 validation error | API | T02 |
| E03 | `offset` is extremely large (e.g. `999999`) | Returns empty list, no crash | Repo/API | T01/T02 |
| E04 | `limit=0` | 422 (existing `ge=1` constraint) | API | T02 |
| E05 | Collection has only 1 card, sorted by any field | Returns that card | Repo | T01 |
| E06 | All cards have same `name_en` | Returns stable order via secondary `id` sort | Repo | T01 |
| E07 | Card with `name_en=None` sorted by name | Null handled gracefully (sorted last for asc) | Repo | T01 |
| E08 | Card with `created_at=None` sorted by added | No crash; null handled | Repo | T01 |
| E09 | Client-side price sort with all prices null | Cards remain in original order (all equal) | Frontend | T04 |
| E10 | Client-side price sort with mixed positive/zero/null | Zero treated as valid price, null sorted to end | Frontend | T04 |
| E11 | URL has invalid sort param (`?sort=invalid`) | Falls back to default `name-asc` | Frontend | T04 |
| E12 | URL has sort but no dir (`?sort=set`) | Uses field's default direction (asc for set) | Frontend | T04 |
| E13 | Changing sort while a fetch is in-flight | Previous fetch result is discarded; only latest sort's results rendered | Frontend | T04 |

---

## 7. Coverage Requirements

| Area | Metric | Threshold | Current Baseline |
|------|--------|-----------|-----------------|
| Backend (pytest-cov) | Line coverage on `src/` | >= 70% | 92.75% |
| Backend test count | Total passing | >= 857 (no regressions) | 857 |
| Frontend test count | Total passing | >= 304 (no regressions) | 304 |
| New backend code | Sort/offset logic in repository + API | 100% of new lines | N/A |
| New frontend code | SortSelect component + sort integration | All branches tested | N/A |

### Verification commands

```bash
# Backend: full suite + coverage
python -m pytest --cov=src --cov-report=term-missing

# Backend: F16-specific tests only
python -m pytest tests/unit/test_repository_sort.py tests/api/test_collection_sort.py -v

# Frontend: full suite
cd frontend && npx vitest run

# Frontend: F16-specific tests only
cd frontend && npx vitest run --reporter=verbose tests/components/SortSelect.test.tsx tests/pages/MyCollection.test.tsx

# Pre-commit hooks (ruff)
pre-commit run --all-files
```

### Regression checklist

- [ ] All 857 existing backend tests pass
- [ ] All 304 existing frontend tests pass
- [ ] Backend coverage >= 70%
- [ ] Pre-commit hooks (ruff) pass with no errors
- [ ] Existing collection endpoints (`GET /collection`, `GET /collection/{id}`, `GET /collection/summary`) still work without sort params
- [ ] Cursor-based pagination still works for backward compatibility
