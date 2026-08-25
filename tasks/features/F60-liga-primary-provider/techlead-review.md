# F60 Tech Lead Review (Re-review)

**Verdict:** APPROVED
**Reviewed:** 2026-08-25
**Test results:** 2063 passed, 91.80% coverage, 0 failures

## Summary

F60 delivers a well-structured migration from MYP to LigaMagic as the primary price provider. The first review identified one critical and two major issues. All three have been correctly fixed. The architecture -- generic scan orchestrator, provider-routed scheduling, admin monitoring dashboard, protected price cleanup -- is sound and ready to merge.

## Resolved Findings

### C1 CRITICAL (was: external_id mismatch) -- FIXED

All writers and readers now use the `liga_{card_id}` convention consistently:

- `src/api/routers/collection.py:953` -- single-card refresh writes `f"liga_{entry.card_id}"`
- `src/database/repository.py:482` -- `get_latest_prices_batch` reads `f"liga_{card_id}"`
- `src/database/repository.py:1309` -- `get_cards_for_liga_scan` freshness filter builds `concat("liga_", cast(card_id, String))`
- `src/database/repository.py:2310` -- `get_liga_coverage_stats` uses the same `concat` pattern
- `src/database/repository.py:2388` -- `get_liga_missing_cards` uses the same `concat` pattern
- Tests updated: `test_collection_refresh_liga.py:53,133` use `"liga_42"` matching the numeric card_id pattern

### M1 MAJOR (was: O(N) queries in coverage/missing) -- FIXED

Both `get_liga_coverage_stats` (line 2296-2324) and `get_liga_missing_cards` (line 2375-2405) now use a subquery + LEFT JOIN approach:

1. A subquery aggregates `MAX(observed_at)` per `external_id` from `price_observations WHERE source='liga'`.
2. The main query LEFT JOINs `user_collection` against this subquery using `concat("liga_", cast(card_id, String))`.
3. Counts (priced/stale/missing) are computed in a single pass over the joined result set.

This reduces the query count from O(N) to O(1), which is the correct approach for this workload.

### M2 MAJOR (was: API Liga scan crashes with provider=None) -- FIXED

In `src/api/routers/scans.py:149-158`, the background thread now correctly routes Liga scans through `run_liga_scan` (which manages the `LigaMagicProvider` lifecycle internally), while MYP scans go through the original `run_scan`. The branching is clean:

```python
if provider_name == "liga":
    asyncio.run(run_liga_scan(db_url=db_url, scan_filter=scan_filter, ...))
else:
    asyncio.run(run_scan(db_url=db_url, ..., provider_name=provider_name))
```

## Remaining Minor Items (non-blocking)

These were noted in the first review and remain as optional improvements. None block merge.

**m1: Duplicated `_fetch_liga_price` logic.** `scan.py` and `liga_sweep.py` share nearly identical price extraction from `search_card`. Could be extracted to a shared utility. Low priority.

**m2: `except (LigaError, Exception)` redundancy.** Logically equivalent to `except Exception`. Not wrong, but could be cleaner with separate blocks or simplified.

**m3: `list_scans` endpoint has no auth.** `GET /scans` is unauthenticated, inconsistent with other endpoints. Low risk since scan metadata is not sensitive.

**m4: Admin page table headers not i18n'd.** Hardcoded English strings in `AdminLigaStatus.tsx`. Should be addressed in a future i18n pass.

**m5: `func.concat` portability on SQLite.** SQLAlchemy's `func.concat` may not translate to `||` on all SQLite builds. Using the `+` operator or `||` directly would be more portable. Tests pass on the project's SQLite version, so this is not urgent.

## Positive Observations

1. **Clean provider abstraction.** The scan orchestrator's `provider_name` parameter with Liga-specific constraints (concurrency=1, minimum delay) integrates naturally with the existing scan infrastructure.

2. **Protected sources.** `PROTECTED_SOURCES = {"liga", "manual"}` in `cleanup.py` prevents accidental deletion of Liga price data. Good safety design.

3. **Comprehensive test coverage.** 302 new backend tests (1761 to 2063) with 91.80% coverage. Test structure covers filters, priority ordering, error handling, and edge cases thoroughly.

4. **Schedule seeding.** Idempotent `seed_default_liga_schedules` with daily partial (50 cards, 3 AM) and weekly full (Sunday 1 AM) is a sensible default for ~350 cards at 5.5s/card.

5. **Liga sweep CLI.** Batch-with-pause design (`batch_size=20, batch_pause=60s`) with `KeyboardInterrupt` handling and resume via `max_age_days` is well-suited for initial population.

6. **Error handling in refresh endpoint.** Returns 200 with warning errors instead of 500 on `LigaError`, preserving partial success UX (consistent with F46 pattern).

7. **Frontend auth consistency.** All new endpoints use `require_auth_or_api_key`, admin page behind `ProtectedRoute`, nav link has `requiresAuth: true`.
