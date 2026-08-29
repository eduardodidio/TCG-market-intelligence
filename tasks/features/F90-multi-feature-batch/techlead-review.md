# F90 Multi-Feature Batch -- Tech Lead Review

**Reviewer:** Tech Lead Agent
**Date:** 2026-08-29
**Branch:** homol

---

## Overall Verdict: APPROVED

All six tasks are well-implemented, follow existing codebase patterns, and
integrate correctly. One backend test failure was found but is pre-existing
(not introduced by F90). Frontend tests pass fully (1468 tests, 133 files).

---

## Per-Task Findings

### T01: Schedule Save Fix

**Files reviewed:**
- `src/api/routers/schedules.py`
- `tests/unit/api/test_schedule_endpoints.py`

**Assessment:** Clean and correct.

All endpoints (POST, GET, GET/:id, PATCH, DELETE, POST/:id/trigger) now
return `ApiResponse` envelope via `success_response()`. This is consistent
with how every other router in the project wraps responses.

Tests are thorough: envelope shape assertions for create, list, update; a
round-trip test (create then list); edge cases for empty PATCH bodies,
invalid cron, nonexistent IDs. 15 tests covering the envelope migration.

**No issues found.**

---

### T02: Beta-Test Tab Nav Grouping

**File reviewed:**
- `frontend/src/components/Layout.tsx`

**Assessment:** Well-structured.

The nav items are cleanly split into `PRIMARY_NAV_ITEMS` and
`BETA_NAV_ITEMS` arrays. The collapsible disclosure uses a chevron SVG
with rotation animation, `aria-expanded` for accessibility, and persists
open/close state in localStorage via `BETA_NAV_STORAGE_KEY`. Beta items
are indented (`px-6` vs `px-3`) for visual hierarchy.

Auth/admin filtering works identically for both groups via the shared
`filterNavItems` function.

**No issues found.**

---

### T03: Trending Collection-Only

**Files reviewed:**
- `src/database/repository.py` (get_trending_price_data_for_user)
- `src/services/trending.py`
- `src/api/routers/market.py` (trending endpoints)
- `frontend/src/pages/Trending.tsx`
- `frontend/src/components/TrendingSection.tsx`

**Assessment:** Correct implementation, one minor observation.

The backend changes are solid:
- `get_trending_price_data_for_user` uses a single JOIN query through
  `UserCollectionRow` -- no N+1 queries.
- `TrendingService.get_trending()` accepts `user_id` parameter. Cache keys
  are scoped by `user_{id}` vs `all`, preventing cross-user cache leaks.
- `get_optional_user` dependency is used correctly: trending endpoints are
  accessible without auth (returns all cards), but when `collection_only=True`
  is passed with a valid JWT, results are scoped.

Frontend:
- The `collectionOnly` state defaults to `true` for authenticated users,
  which is a good UX choice.
- `TrendingSection` passes `collection_only` param to the API only when
  truthy, avoiding unnecessary query param noise.

**Non-blocking observation:** The `collectionOnly` checkbox is hidden for
unauthenticated users, which is correct, but the default state is `true`
even before the auth check. If `isAuthenticated` is initially false during
hydration, the first render passes `collectionOnly={false && true} = false`
to TrendingSection, which is correct behavior. No issue.

---

### T04: Schedule Token Cost

**Files reviewed:**
- `src/scheduler/service.py` (token check in _execute_scheduled_scan)
- `frontend/src/components/ScheduleTable.tsx`

**Assessment:** Good implementation with appropriate guardrails.

Token enforcement logic in `_execute_scheduled_scan`:
1. Exempts `admin_daily_liga` scan type (correct -- admin system scan).
2. Uses `repo.count_collection(user_id)` as cost estimate (1 token/card).
3. Checks `credit_svc.check_sufficient()` before deducting.
4. On insufficient credits: pauses schedule with distinct status
   `paused_insufficient_credits`, logs a warning.
5. Deducts tokens before the scan runs (pay-first model, consistent with
   other scan endpoints).

Frontend:
- `ScheduleTable` handles `paused_insufficient_credits` status with a
  dedicated yellow badge and tooltip.
- The StatusBadge `colorMap` includes the new status.

**Non-blocking suggestion:** If a scan fails after tokens are deducted,
tokens are not refunded. This is consistent with the existing manual scan
behavior, but consider a future improvement to refund on scan failure.

---

### T05: Explore Cards Web Search

**Files reviewed:**
- `src/api/routers/card_search.py`
- `src/api/schemas/card_search.py`
- `frontend/src/pages/Cards.tsx`

**Assessment:** Functional, with some observations.

Backend:
- Credit token (1 per search) is deducted before the Liga call. HTTP 402
  on insufficient credits.
- Liga provider is retrieved from `app.state.provider_registry`. Returns
  503 if unavailable (Render deploy where Liga/Playwright is disabled).
- Timeout is 30s with proper `asyncio.wait_for`. 502/504 errors are
  handled with structured logging.
- `_find_local_card` does a case-insensitive match to link web results to
  local DB cards.

Frontend:
- Mode toggle (local/web) is clean. Web search is only shown to
  authenticated users (correct -- requires credits).
- 3-second cooldown after each search prevents token burning.
- "Add to Collection" and "Add to Evaluation" buttons with proper
  disabled/loading/success states.

**Non-blocking observations:**
1. Price display is hardcoded as `R$` in the frontend web results section
   (lines 463-470), not using the user's selected currency. Since Liga
   prices are in BRL this is technically correct but inconsistent with
   the CurrencyIndicator pattern used elsewhere.
2. The search returns at most one result (single card) because Liga's
   `search_card` returns price data for a single card match. The endpoint
   returns `list[WebSearchResult]` which is forward-compatible for when
   multiple results are supported.

---

### T06: Evaluation List / Watchlist

**Files reviewed:**
- `src/database/models.py` (EvaluationEntryRow)
- `src/database/repository.py` (evaluation CRUD methods)
- `src/api/routers/evaluations.py`
- `src/api/schemas/evaluations.py`
- `frontend/src/pages/Evaluations.tsx`
- `frontend/src/App.tsx`

**Assessment:** Well-implemented end-to-end feature.

Security:
- All endpoints require auth (`get_current_user`).
- IDOR protection on delete and promote: verifies `entry.user_id == user.id`
  and returns 404 (not 403) to prevent enumeration.
- MAX_EVALUATION_ENTRIES = 50 prevents abuse.
- `card_name` field has `max_length=500` validation.

Database:
- Model has proper indexes on `user_id` and `card_id`.
- Repository methods use session-scoped queries, no N+1.
- `delete_evaluation_entry` uses hard delete (appropriate for a watchlist).

Promote flow:
- Reuses `batch_add_entries` for collection creation -- good code reuse.
- Properly wraps in SQLAlchemy session with rollback on failure.
- Deletes eval entry only after successful collection add.
- Returns the new `collection_entry_id` for frontend navigation.

Frontend:
- Route is protected (`ProtectedRoute`).
- Table layout with image, name, price, date, and action buttons.
- Optimistic UI: removes entry from list on delete/promote without
  re-fetching.
- Feedback toast (3s auto-dismiss).
- Empty state links to Explore Cards page.

**Non-blocking observations:**
1. No unique constraint on `(user_id, card_name)` in
   `EvaluationEntryRow`. A user can add the same card name multiple times.
   This may be intentional (different printings) but could also lead to
   accidental duplicates from the web search UI. Consider adding a
   frontend-side check or a DB unique constraint on
   `(user_id, card_name, set_code)`.
2. The Evaluations page table header uses `t("common.noImage")` for the
   image column header (line 132), which seems semantically off -- it
   should probably be something like `t("common.image")` or empty.
3. The `_image_url` helper in `evaluations.py` does not use
   `map_to_scryfall_set_code()` unlike the trending service. Since eval
   entries may not have set_code data from Liga web search, this is
   unlikely to cause issues now, but worth noting for future consistency.

---

## Integration Check: T05 to T06

The flow from web search (T05) to evaluation list (T06) works correctly:
- `Cards.tsx` imports `createEvaluation` from `api/evaluations.ts`.
- The create payload maps `result.card_name`, `result.liga_url`,
  `result.normal_price`, and `result.local_card_id` from the web search
  result to the evaluation create body.
- The evaluations API (`/api/v1/evaluations`) is properly registered in
  `app.py` and routed in `App.tsx`.

---

## Test Results

- **Backend:** 622 passed, 1 failed (pre-existing `test_seed_users`
  failure from F88 seed password change -- not related to F90).
- **Frontend:** 1468 passed, 133 test files, all green.

---

## Summary of Non-Blocking Improvements

| # | Task | Observation |
|---|------|-------------|
| 1 | T04 | Consider token refund on scan failure (future) |
| 2 | T05 | Price display hardcoded as R$ instead of using currency context |
| 3 | T06 | No duplicate prevention for same card in eval list |
| 4 | T06 | Image column header uses `common.noImage` key |
| 5 | T06 | `_image_url` helper does not use `map_to_scryfall_set_code` |

None of these are blockers. The feature batch is approved for merge.
