# Tech Lead Review -- F121: V2 Removal + Classic Dashboard Fix

**Reviewer:** Tech Lead Agent
**Date:** 2026-09-11
**Verdict:** APPROVED

---

## 1. V2 Removal Verification

**Status: PASS**

All 8 V2 files confirmed deleted:
- `LayoutV2.tsx`, `DashboardV2.tsx`, `CollectionV2.tsx`, `RoutePrefixContext.tsx`
- All associated test files (LayoutV2.test.tsx, V2Routes.test.tsx, CollectionV2.test.tsx, DashboardV2.test.tsx)

Grep for `LayoutV2|DashboardV2|CollectionV2|RoutePrefixContext|useRoutePrefix|RoutePrefixProvider` across `frontend/src/` returns zero matches. Glob confirms no V2 files exist on disk. `App.tsx` has no `/v2` routes and no `RoutePrefixProvider` wrapper. `Layout.tsx` has no "Try New UI" button.

The removal is complete and clean.

## 2. Critical Backend Fix: `get_latest_prices_batch()` (repository.py:716-872)

**Status: PASS -- well-structured rewrite**

The method was rewritten from per-card N+1 queries to a batch approach with five clear steps:

1. **Batch fetch source_cards** (single `IN` query) -- lines 741-747
2. **Build direct external_id patterns** (manual, liga, liga_foil) -- lines 760-776
3. **Collect all external_ids** into a single set -- line 779
4. **Batch fetch observations** using a subquery join for latest-per-(source, external_id) -- lines 787-818
5. **Python-side candidate selection** iterating already-fetched data -- lines 830-872

Architecture observations:

- **Chunking at 500** (line 789-790): Prevents overly large `IN` clauses. Sensible default for PostgreSQL.
- **Subquery approach** (lines 794-817): Uses `GROUP BY (source, external_id)` with `func.max(observed_at)` then joins back to get the full row. This is a standard "latest per group" pattern and is correct.
- **Price priority preserved**: Sort key at line 864 is `(-observed_at.toordinal(), SOURCE_PRIORITY)` where `SOURCE_PRIORITY` is `manual=0, liga=1, jsonld_snapshot=2, myp=3`. This correctly implements "latest date wins, then source priority" as documented.
- **Foil handling** (lines 853-859): Foil Liga observation replaces normal Liga observation when the card is in `foil_card_ids`. Manual prices still win regardless. Correct.
- **`observed_at.toordinal()`**: Safe because the column is `Date` type in SQLAlchemy, which returns `datetime.date` from both SQLite and PostgreSQL.

No remaining N+1 patterns were found. The loops at lines 1137 and 1695 both build lists in Python and issue a single batch `IN` query.

## 3. PostgreSQL Compatibility Fixes

**Status: PASS**

### `get_market_stats()` (repository.py:1230-1238)

The `_to_date()` helper normalizes three cases:
- `str` (SQLite may return) -> `date.fromisoformat()`
- datetime with `.date()` method (PG may return `datetime`) -> `.date()`
- Already a `date` -> passthrough

This is a reasonable defense-in-depth approach.

### `collection_health()` (collect.py:36-42)

Same three-way normalization for `last_date` from `get_latest_observation_date()`. Handles `str`, `datetime`, and `date` types. The `datetime` import at line 41 is inside the `if` block, which is fine for clarity but could be at the module level. Minor style nit, not blocking.

## 4. Frontend Build

**Status: PASS**

`npm run build` completes successfully in 3.77s, producing 73 precache entries. No TypeScript errors, no missing imports.

## 5. Test Results

**Status: PASS**

- Repository tests (28 tests including batch price methods): all pass
- Collect health API tests: all pass
- Frontend build: clean

## 6. Observations (non-blocking)

1. **Beta nav dark mode styling** (Layout.tsx:258-264): The inactive beta nav items use `text-slate-400 hover:bg-slate-800 hover:text-white` without `dark:` prefixes, while primary nav items use the `dark:` pattern correctly. This is pre-existing (from F113) and not introduced by F121 -- not blocking.

2. **Observation deduplication in obs_index** (lines 822-826): After the batch query, observations are indexed by `(source, external_id)`. If two observations have the same source+external_id and the same max date, only one is kept (the one with the later `observed_at` when iterating). This is fine because the subquery already filtered to `max(observed_at)`, so duplicates at the same date are rare edge cases handled by the Python-side comparison.

3. **CHUNK_SIZE constant** (line 789): Hardcoded to 500. For very large collections this is fine. Could eventually be promoted to a class constant alongside `SOURCE_PRIORITY`, but not necessary now.

---

## Verdict: APPROVED

The V2 removal is thorough and complete. The `get_latest_prices_batch()` rewrite is the most important change and it is well-structured -- it eliminates the N+1 pattern that caused timeouts on PostgreSQL while correctly preserving the price priority logic and foil handling. The PG date normalization is a sensible defensive fix. All tests pass and the frontend builds cleanly.
