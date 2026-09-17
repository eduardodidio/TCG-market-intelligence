# F132 Tech Lead Review -- Price Request Queue Fix

**Reviewer:** Tech Lead
**Date:** 2026-09-17
**Verdict:** APPROVED

---

## Summary

F132 delivers four tasks that collectively make the price request queue
fully operational. The timeout fix is clean and targeted, the polling hook
is well-architected with proper cleanup, the daily-scan automation is
hardened with error fallbacks, and the admin trigger correctly extracts
shared processing logic into a reusable module. All 50 tests pass (32
frontend + 12 backend + 6 admin UI). Code quality is high with clean
separation of concerns.

---

## T01: Debug and Fix Timeout on Refresh-Price

**Status:** PASS

**Findings:**

- `refreshCardPrice` in `frontend/src/api/cards.ts` correctly passes
  `{ timeoutMs: 30_000 }` as the third argument to `apiPost` (line 60).
  This matches the pattern used by `searchCardsWeb` (line 82, `35_000`).
- `DEFAULT_TIMEOUT_MS` in `client.ts` remains untouched at `10_000` --
  the fix is properly scoped per-call.
- Error handling in `CardTile.tsx` is comprehensive: the `handleRefresh`
  function (lines 74-97) now checks `res.errors` for API-level errors and
  catches thrown exceptions, showing a red X icon and error feedback text
  for both cases. The `refreshError` state auto-clears after 3 seconds
  via `setTimeout`.
- Two frontend tests confirm the timeout override and error states
  (`cards.test.ts` lines 22-41, `CardTile.test.tsx` lines 210-243).

**No issues.**

---

## T02: Verify/Fix process-price-requests in daily-scan.bat

**Status:** PASS

**Findings:**

- `daily-scan.bat` has correct command ordering: `liga-sweep` then
  `process-price-requests --limit 500` then `snapshot-portfolio`.
- Each command has `|| echo [WARN] ... failed` error fallback so
  subsequent steps still run if one fails.
- Timestamp logging with `%time%` added around the price request
  processing step for Task Scheduler debugging.
- Limit increased from 100 to 500 -- at 2s/request, worst case is ~17
  minutes, which is reasonable for a daily batch.

**No issues.**

---

## T03: Frontend Polling for Price Request Status

**Status:** PASS

**Findings:**

- `fetchPriceRequestStatus` added to `frontend/src/api/cards.ts`
  (lines 71-77) with correct endpoint URL and type interface.
- `usePriceRequestPolling` hook (`frontend/src/hooks/usePriceRequestPolling.ts`)
  is well-structured:
  - Uses `useRef` for interval ID and callback refs to avoid stale
    closures (lines 34-37, 39-41).
  - Performs an immediate initial poll on enable (line 91), then sets up
    `setInterval` for subsequent polls.
  - Properly handles all terminal states: `completed`, `failed`, `none`.
  - Timeout after `maxDurationMs` (default 60s) prevents infinite polling.
  - Cleanup on unmount via the effect return (line 98-100) clears the
    interval.
  - Network errors during polling are silently caught, allowing the next
    interval to retry (line 78-79).
- `CardTile.tsx` integration (lines 44-60) replaces the old 5-second
  `setTimeout` with the polling hook. Visual states are complete:
  animated spinner during polling, green checkmark on completion (1.5s),
  red X on failure (3s), yellow clock on polling timeout.
- The `onPriceRefreshed` callback is properly wired up (line 51-53),
  allowing parent components to update their card data without a full
  page refresh.
- 9 hook tests cover: disabled state, enable+poll, completed, failed,
  none, timeout, unmount cleanup, null price, and network error recovery.
- CardTile tests verify spinner icon, error icon, queued feedback, and
  button disabled states.

**Minor observation (non-blocking):** The `poll` callback is memoized
with `useCallback` and depends on `[cardId, maxDurationMs, stopPolling]`.
Since `poll` is in the `useEffect` dependency array (line 101), changing
`cardId` during polling will correctly restart the interval. This is
correct behavior.

**No issues.**

---

## T04: Admin Trigger for Price Request Processing

**Status:** PASS

**Findings:**

- Processing logic cleanly extracted to `src/collectors/price_request_processor.py`
  (134 lines). The `process_pending_price_requests` async function returns
  a `ProcessingResult` dataclass with `total`, `completed`, `failed` counts.
- Both the CLI (`src/cli/main.py` line 1205) and the admin endpoint
  (`src/api/routers/admin.py` line 531) import and call the same function,
  eliminating code duplication.
- The admin endpoint (`POST /api/v1/admin/jobs/process-price-requests`)
  follows the established pattern from `trigger_liga_scan`:
  - `require_admin` dependency for authorization.
  - Short-circuits with `no_pending` if queue is empty.
  - Creates a scan run for tracking.
  - Spawns a daemon background thread.
  - Logs an audit entry.
- Query parameters `limit` (1-1000, default 100) and `delay` (0.5-10.0,
  default 2.0) provide operational flexibility.
- Frontend `triggerProcessPriceRequests` in `admin.ts` passes the limit
  as a query parameter in the URL (`?limit=${limit}`), which matches the
  backend's `Query()` parameter pattern.
- `AdminPriceRequestsSection.tsx` has a well-implemented "Process Queue"
  button with: pending count display, disabled state when queue is empty,
  spinner during processing, feedback message, auto-refresh of stats
  after 5 seconds.
- The tooltip `admin.priceRequests.localOnly` communicates the constraint
  that processing requires a residential IP.
- 7 backend tests (5 admin endpoint + 7 processor) and 6 frontend tests
  cover the main paths.

**Observations (non-blocking):**

1. The background thread exception handling: if
   `process_pending_price_requests` raises an unhandled exception inside
   the thread, it will silently die because it is a daemon thread. The
   function itself has comprehensive try/except handling inside, so this
   is unlikely in practice. The scan run status is not updated to
   "completed" or "failed" at the end -- but this mirrors the existing
   `trigger_liga_scan` pattern, so it is consistent.

2. There is a pre-existing duplicate test file at
   `frontend/src/components/__tests__/AdminPriceRequestsSection.test.tsx`
   (9 tests from F130) that does not mock `triggerProcessPriceRequests`.
   It still passes because none of those tests click the button, but the
   mock factory returns `undefined` for the unmocked export. This is not
   a regression from F132 -- it is a pre-existing condition. The new test
   file at `frontend/src/components/admin/__tests__/` properly mocks all
   three imports.

---

## Architecture Assessment

The separation of concerns is clean:

```
src/collectors/price_request_processor.py  -- shared async business logic
src/cli/main.py                            -- CLI entry point (calls processor)
src/api/routers/admin.py                   -- API entry point (calls processor in thread)
frontend/src/hooks/usePriceRequestPolling.ts -- encapsulated polling logic
frontend/src/components/CardTile.tsx       -- UI integration via hook
frontend/src/components/admin/...          -- admin UI integration
```

The polling hook is a good React pattern -- it keeps CardTile free of
polling mechanics and is independently testable. The extracted processor
module follows the project's existing pattern of moving reusable logic out
of CLI commands.

---

## Test Coverage Summary

| Area | Tests | Status |
|------|-------|--------|
| `cards.test.ts` (API timeout) | 3 | PASS |
| `usePriceRequestPolling.test.ts` | 9 | PASS |
| `CardTile.test.tsx` | 20 | PASS |
| `AdminPriceRequestsSection.test.tsx` (new) | 6 | PASS |
| `test_price_request_processor.py` | 7 | PASS |
| `test_admin_process_price_requests.py` | 5 | PASS |
| **Total** | **50** | **ALL PASS** |

---

## Recommendations (non-blocking, future improvement)

1. **Stale duplicate test file:** Consider removing or updating the older
   `frontend/src/components/__tests__/AdminPriceRequestsSection.test.tsx`
   (from F130) since it does not mock the new `triggerProcessPriceRequests`
   import. It works by accident today but could break if Vitest tightens
   mock validation.

2. **Scan run completion tracking:** The admin trigger creates a scan run
   but never updates its status to completed/failed. Consider adding a
   try/finally in the background thread to update scan run status, which
   would allow the admin job status page to show accurate results.

3. **Polling backoff:** The current 5-second fixed interval is fine for
   the typical use case. If the queue grows significantly, consider
   exponential backoff to reduce unnecessary API calls.

---

**Verdict: APPROVED** -- All four tasks are correctly implemented, well-tested,
and follow established project patterns. Ship it.
