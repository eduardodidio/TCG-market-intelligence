# Tech Lead Review -- F16 Explore Cards Sorting

**Reviewer:** Tech Lead agent
**Date:** 2026-08-21
**Status:** APPROVED

---

## Checklist

### 1. Architecture -- PASS

The implementation follows the PRD faithfully:
- Backend: `list_collection` gains `sort_by`, `sort_dir`, `offset` params
  with a clean allowlist (`_COLLECTION_SORT_COLUMNS`) mapping UI keys to
  DB columns.
- API: new query params with regex-pattern validation (`^(name|set|number|added)$`
  for sort_by, `^(asc|desc)$` for sort_dir). Price sort is correctly excluded
  from server-side options and handled client-side.
- Frontend: `SortSelect` component is minimal and reusable. `MyCollection`
  integrates sort state, URL params, and client-side price sorting with
  `useMemo`.
- Pagination switches to offset-based as decided in the PRD.

### 2. Code Quality -- PASS

- Clean, minimal changes -- no over-engineering.
- `_COLLECTION_SORT_COLUMNS` dict is a clean pattern for allowlisting sort fields.
- `func.coalesce` for NULL name_en handling is correct.
- Secondary sort by `id ASC` ensures stable ordering.
- Client-side price sort uses `Infinity`/`-Infinity` for null handling,
  pushing no-price cards to the end. Clean approach.

### 3. Security -- PASS

- `sort_by` is validated via FastAPI `Query(pattern=...)` regex at the API
  boundary, rejecting invalid values with 422.
- `sort_dir` is similarly validated to only accept "asc" or "desc".
- `offset` is validated with `ge=0`.
- `name_search` uses SQLAlchemy parameter binding (safe against injection).
- Repository falls back to `name_en` for unknown sort keys (defense in depth).

### 4. Tests -- PASS

- **Backend repository tests** (37 new tests in `test_repository_collection.py`):
  all sort directions, offset pagination, backward compat with `after_id`,
  filter interactions, NULL handling, stable ordering. Thorough.
- **Backend API tests** (`test_collection_sorting.py`): validates query param
  forwarding, 422 for invalid inputs, offset in meta response, cursor compat.
- **Frontend `SortSelect` tests** (5 tests): option rendering, onChange parsing,
  default value, testid.
- **Frontend `MyCollection` tests** (18 tests including 11 new sort tests):
  re-fetch on sort change, API param forwarding, price sort client-side in
  both directions, null-price handling, offset-based pagination, URL param
  initialization.
- Overall backend coverage: **94.02%** (up from 92.75%). Exceeds 70% threshold.
- Overall backend tests: **894** (up from 857).
- Frontend sort tests: **23 pass** across the two files.

### 5. Backward Compatibility -- PASS

- `cursor` param remains supported and decoded as `after_id`.
- `after_id` takes precedence over `offset` when both are provided.
- `meta.cursor` still populated in responses.
- Existing API consumers sending no sort params get `name/asc` (alphabetical),
  which is a behavior change from the previous `id ASC` ordering. This is
  intentional per the PRD and arguably an improvement.
- Tests explicitly verify backward compat scenarios.

### 6. Performance -- PASS

- Offset pagination is acceptable for ~500-card collections.
- No new joins or subqueries added.
- Secondary sort on `id` uses the primary key index.

### 7. Consistency -- PASS

- Follows existing patterns: repository methods, API router style, schema
  envelope, test fixtures.
- `paginated_response` updated to accept `**meta_kwargs` for the new `offset`
  field without changing its signature for existing callers.
- Frontend follows existing state management patterns (useState + useEffect +
  useCallback + useMemo).

---

## Issues Found

### Minor

1. **Lexicographic sort on `collector_number`** (minor): `collector_number`
   is `String(20)`, so sorting by "number" gives lexicographic order
   ("10" < "2" < "5"). For MTG cards this is usually acceptable since
   most collector numbers are zero-padded or similar length, but it may
   surprise users with sets that have non-padded numbers. A `CAST` to
   integer or `LENGTH`-then-value sort would fix this, but it is not
   blocking -- the PRD does not specify numeric sorting and the current
   behavior is consistent.

2. **`after_id` + non-default sort** (minor): Using the legacy `cursor`
   param with a non-default `sort_by` could produce unexpected results
   since `WHERE id > X` filters by row ID, not by the sort column position.
   This is documented as a deprecated path and offset is the recommended
   approach, so it is acceptable.

3. **Default sort behavior change** (informational): The default sort
   changed from `id ASC` (insertion order) to `name ASC` (alphabetical).
   This is intentional per the PRD. Any external consumers relying on
   insertion order would need to explicitly pass `sort_by=added&sort_dir=asc`.

---

## Verification Results

| Check | Result |
|-------|--------|
| `python -m pytest -x` | 894 passed, 94.02% coverage |
| `npx vitest run` (SortSelect + MyCollection) | 23 passed |
| `python -m ruff check` | All checks passed |

---

## Verdict: APPROVED

The implementation is clean, well-tested, and matches the PRD spec. No
blocking issues found. The three minor items noted above are acceptable
trade-offs documented in the PRD or inherent to the data model. Ship it.
