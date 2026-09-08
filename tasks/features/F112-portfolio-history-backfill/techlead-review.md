# Tech Lead Review -- F112 Portfolio History Backfill & Dashboard Activation

**Reviewer:** Tech Lead Agent
**Date:** 2026-09-08
**Verdict:** APPROVED

---

## Summary

F112 delivers a solid, well-structured feature that solves a real UX problem: the PortfolioDashboard (F105) was fully built but showed empty because no historical data existed. The feature adds three backend capabilities (acquisition price backfill, synthetic snapshot generation, auto-snapshot hook) and one frontend component (CollectionMovers), all integrated cleanly into the existing architecture. Test coverage is thorough (52 backend tests, 14 frontend tests, all passing).

---

## Architecture

**Rating: Good**

- `src/collectors/portfolio_backfill.py` sits correctly in the collectors layer alongside `portfolio_snapshot.py` and follows the same patterns.
- The scan hook integration in `scan_hooks.py` follows the established factory pattern (`make_*_hook`), consistent with `make_cache_invalidation_hook`, `make_trending_invalidation_hook`, and `make_alert_checker_hook`.
- No circular imports detected. The import chain is clean: `scan_hooks.py` imports from `collectors.portfolio_snapshot`, not from `portfolio_backfill`, keeping the dependency graph acyclic.
- The CLI command follows existing patterns (`--db`, `--user-id`, `--dry-run`).
- The `/collection/movers` endpoint is correctly placed under the collection router with auth, following the existing pattern for collection-scoped data.
- The `CollectionMovers` component is properly separated and imported into `PortfolioDashboard`, maintaining component granularity.

---

## Code Quality

**Rating: Good**

### Strengths

- Clear separation of concerns: backfill logic, snapshot hook, API endpoint, and frontend component are all independent modules.
- The `_pick_price` helper establishes a consistent price priority (median > tcg > last_sold) reusable across contexts.
- The `_build_price_index` + `_find_best_price` pattern with `bisect_right` is a textbook approach for time-series lookups -- efficient and readable.
- The backfill function correctly uses `Session(repo.engine)` to manage its own transaction scope, consistent with the repository pattern used elsewhere.
- The movers endpoint computation (lines 378-426 of `collection.py`) is clean: compute changes, split into gainers/losers, batch-fetch card info, build response. No N+1 queries.
- Good use of `data-testid` attributes in the frontend for reliable testing.

### Minor Issues

1. **Type annotation mismatch on `get_trending_price_data_for_user`** (repository.py line 997): The method signature declares `user_id: int` but the movers endpoint passes a `str` (from `require_auth_or_api_key`). This works at runtime because SQLAlchemy coerces the type, but the annotation is incorrect. This is a pre-existing issue, not introduced by F112.

2. **`__import__` usage in CLI** (main.py line 2068): The `__import__("sqlalchemy").select(UserRow)` pattern is unusual. A normal `from sqlalchemy import select` at the top of the function block would be cleaner. This is a style nit.

3. **Hardcoded "R$" in CLI output** (main.py line 2172): `f"value=R$ {value:.2f}"` assumes BRL. Minor since this is a CLI admin tool and the project is BRL-focused.

---

## Performance

**Rating: Good**

- **Single-query preload**: `_build_price_index` loads all price observations for all relevant external_ids in one query, then builds an in-memory index. This avoids N queries per card per day.
- **Binary search**: `_find_best_price` uses `bisect_right` for O(log n) lookups per card per day, rather than linear scans.
- **Batch card info fetch**: The movers endpoint calls `get_card_info_with_image_batch` once for all visible movers, not per-card.
- **Session scoping**: The backfill snapshot function opens a single session for all preloading (snapshot dates, collection entries, source cards, price index), then closes it before the day-by-day loop. This avoids holding a long-lived session during writes.

One consideration: for users with very large collections (1000+ cards) and 30 days of history, the price index could be large in memory. Given the project scope (personal collection tool), this is acceptable.

---

## Safety & Data Integrity

**Rating: Good**

- **Idempotency**: `backfill_acquisition_prices` only touches entries where `acquisition_price IS NULL`, so re-running is safe. Tests verify this explicitly (test_idempotent, test_does_not_overwrite_existing_price).
- **Snapshot skip logic**: `backfill_portfolio_snapshots` loads existing snapshot dates and skips them, preserving real snapshots produced by `take_snapshot`. The `upsert_portfolio_snapshot` call is itself idempotent.
- **Error isolation in hook**: The `make_portfolio_snapshot_hook` catches exceptions per-user, so a failure for one user does not block others. Test `test_error_in_one_user_does_not_block_others` verifies this.
- **No destructive operations**: The feature only inserts/updates; it never deletes data.
- **Dry-run support**: The CLI command supports `--dry-run` to preview changes without writing.

---

## Tests

**Rating: Good**

- **52 backend tests, 14 frontend tests** -- all passing.
- **T01 (test_portfolio_backfill.py)**: 12 tests covering `_pick_price` priority, `_find_nearest_observation` (same date, before, after, no source cards, no observations), and `backfill_acquisition_prices` integration (update, skip without card_id, skip without observations, nearest date selection, user_id filter, idempotency, price fallback, all-null observation, mixed entries).
- **T02 (test_portfolio_backfill_snapshots.py)**: 7 tests covering forward-fill, exact date, no price before target, multiple external IDs, empty index, existing snapshots skipped, entries created after target excluded, empty collection, summary counts, forward-fill across days, unlinked cards.
- **T03 (test_scan_hooks_portfolio.py)**: 5 tests covering the hook factory: snapshots all users, skips empty external_ids, skips no users, error isolation, registry integration.
- **T04 backend (test_collection_movers.py)**: 10 tests covering empty data, single data points, gainers sorted desc, losers sorted asc, mixed, custom params, validation (days max 90, limit max 20), limit capping, zero start price exclusion.
- **T04 frontend (CollectionMovers.test.tsx)**: 8 tests covering loading skeleton, empty state, null data, gainers/losers rendering, color classes, set code display, custom props, image rendering.
- **T05 (test_cli_backfill.py)**: 6 tests covering default options, --days, --skip-prices, summary table output, dry-run, dry-run with --skip-prices.

Edge cases are well-covered. The mocking strategy in snapshot tests is necessarily complex but well-structured via `_make_session_context`.

---

## Security

**Rating: Good**

- The `/collection/movers` endpoint uses `require_auth_or_api_key` for authentication, consistent with all other collection endpoints.
- Input validation via FastAPI `Query(ge=1, le=90)` and `Query(ge=1, le=20)` prevents abuse. Tests verify 422 on out-of-range values.
- The CLI command is admin-only by nature (requires DB access).

---

## Findings

### Critical

None.

### Major

None.

### Minor

| # | Finding | File | Recommendation |
|---|---------|------|----------------|
| M1 | `get_trending_price_data_for_user` declares `user_id: int` but receives `str` at runtime | `repository.py:997` | Fix type annotation to `str`. Pre-existing issue but surfaced by this feature. |
| M2 | `scan_hooks.py` imports `take_snapshot` and `Repository` at module level (lines 19-22), breaking the previous pattern of lazy imports inside hook closures | `scan_hooks.py:19-22` | Move imports inside `make_portfolio_snapshot_hook` or inside `_hook` to keep the module lightweight and avoid import-time side effects. Other hooks use `TYPE_CHECKING` + lazy imports. |
| M3 | The hook creates a new `Repository(db_url)` instance on every scan completion | `scan_hooks.py:111` | Consider reusing a single Repository instance (created once in the factory), same as the other hooks do with their service references. |
| M4 | `__import__("sqlalchemy").select(UserRow)` in CLI is non-idiomatic | `cli/main.py:2068` | Use a normal import statement. |

---

## Recommendations

1. **M2 is the most actionable item**: move the top-level imports of `take_snapshot`, `Session`, `Repository`, and `UserCollectionRow` inside the `make_portfolio_snapshot_hook` function or its inner `_hook`. This avoids loading `portfolio_snapshot` and `repository` modules at import time in `scan_hooks.py`, which was previously a lightweight module. Not a blocker since all imports resolve correctly, but it degrades module isolation.

2. Consider adding a log line in the backfill when the price index is empty (no price observations found for any card), so operators can diagnose "backfill ran but nothing happened" scenarios more easily.

3. The `CollectionMovers` component uses `useEffect` with `fetchCollectionMovers` directly. If the PortfolioDashboard is toggled rapidly, stale responses could update state. A minor robustness improvement would be to use an abort controller or a `stale` flag pattern. Not critical for POC scope.

---

## Conclusion

F112 is a well-executed feature that solves the empty-dashboard problem with a clean, efficient, and safe implementation. The backfill pipeline is idempotent, the snapshot hook integrates cleanly into the existing scan hook registry, and the movers panel adds genuine value to the portfolio dashboard. All tests pass. The minor findings are non-blocking style and import hygiene items.

**Verdict: APPROVED**
