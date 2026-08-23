# Tech Lead Review -- F51, F52, F53

**Reviewer:** Tech Lead Agent
**Date:** 2026-08-23
**Test Results:** Backend 1756 tests (92.52% coverage, 0 failures) | Frontend 938 tests (92 files, 0 failures)

---

## Verdict: APPROVED

All three features are approved with minor observations noted below. No blocking issues found.

---

## F51 -- Fix Explore Cards (Images, Prices, Refresh)

### Architecture Assessment: PASS

The `CardImage` subcomponent (lines 361-435 of `CardDetail.tsx`) implements a clean 3-tier fallback chain: primary URL (set/number) -> name-based fallback -> SVG placeholder. This matches the established pattern in `CardTile.tsx` and avoids code duplication by being self-contained. The two-state approach (`imgError` + `fallbackError`) correctly handles each transition.

The `collection_entry_id` plumbing is well-architected:
- Backend: `get_card` endpoint uses `get_optional_user` (returns `None` for unauthenticated users, no 401) to conditionally look up the collection entry via `get_collection_entry_id_by_card`.
- Schema: `CardDetail` Pydantic model has `collection_entry_id: int | None = None` -- nullable by default, no breaking change.
- Frontend: `CardDetail` TypeScript interface properly mirrors with `collection_entry_id: number | null`.

### Security Assessment: PASS

- **IDOR check:** The `collection_entry_id` lookup in `cards.py` line 117 correctly scopes the query to `user_id=str(user.id)` -- only the authenticated user's own collection entry is returned. An attacker cannot retrieve another user's entry ID.
- **Refresh endpoint:** The `handleRefresh` callback calls `refreshCardPrice(card.collection_entry_id, ...)` which hits the existing `POST /collection/{entry_id}/refresh` endpoint. That endpoint already has auth + ownership checks (established in F29). No new attack surface.
- **Unauthenticated users:** `get_optional_user` returns `None`, so `collection_entry_id` stays `None` and the refresh button is hidden. Correct.

### Code Quality: PASS

- No dead code. The `refreshMsg` state with auto-clear via `setTimeout` (3 seconds) is consistent with the pattern used in `CollectionCardDetail`.
- `formatPriceOrFallback` correctly handles `null` price by showing localized "No price data" text with muted styling.
- The `CardImage` component is extracted as a separate function at the bottom of the file -- clean separation.

### Test Coverage: PASS (22 tests, 5 new)

New tests cover:
1. Fallback image by name when `set_code` is null
2. Fallback on primary URL error (fireEvent.error simulation)
3. Placeholder when both images fail
4. Refresh button visibility (present when `collection_entry_id` set, hidden when null)
5. Refresh API call with success message rendering

The mock fixture `mockCardDetail()` was updated to include `collection_entry_id: null` as default, with test overrides to `42` for refresh scenarios.

### Observations (non-blocking)

1. **OBS-F51-01:** `CardDetail` line 82 -- the `useEffect` dependency array for page title is `[card]` but does not include `getCardName` or `t`. React hooks rules would flag this. It works in practice because `t` and `getCardName` are stable references, but the eslint-disable comment is missing.

---

## F52 -- Fix Dashboard Trending (Signal Forwarding + Cache Invalidation)

### Architecture Assessment: PASS

**Frontend fix (signal forwarding):** The root cause was that `TrendingSection` called `fetchTrending(direction, params)` without passing the `signal` from `useApi`. The fix at line 35 now passes `(signal) => fetchTrending(direction, params, { signal })`, which threads the AbortController signal through `apiGet` -> `composeAbortSignals` -> `fetch`. This prevents silently aborted requests when the component unmounts/re-renders.

**Backend fix (cache invalidation):** The `make_trending_invalidation_hook` function in `scan_hooks.py` is well-designed:
- Receives `TrendingService` and calls `invalidate_cache()` (which does `self._cache.clear()`)
- Skips when `external_ids` is empty (avoids unnecessary invalidation)
- Registered in `app.py` lifespan alongside the existing market data cache hook
- Error handling: the `ScanHookRegistry.notify()` method catches exceptions per-hook and logs them, preventing one failing hook from blocking others

### Security Assessment: PASS

No new endpoints, no auth changes. The hook registration in `app.py` lifespan uses `try/except` with warning logging -- failure is graceful.

### Code Quality: PASS

- The `app.py` lifespan trending service resolution (lines 48-57) correctly handles both cases: singleton already initialized (`_trending_service is not None`) or fresh creation via `get_trending_service(repo)`. This avoids creating duplicate service instances.
- The `fetchTrending` function signature in `trending.ts` already accepted `options?: { signal?: AbortSignal }` -- the fix was purely at the call site in `TrendingSection`. Minimal, targeted change.

### Test Coverage: PASS (7 new tests total)

Frontend tests (4):
- Validates full API envelope structure
- Correct URL construction with direction/params
- Signal forwarding to fetch
- Error envelope on HTTP error

Backend tests (3 for trending hook):
- `invalidate_cache` called on scan with external IDs
- Skipped when external IDs empty
- Hook works through registry integration

### Observations (non-blocking)

1. **OBS-F52-01:** In `app.py` lines 43-57, the lifespan creates a `MarketDataService` via `_create_market_data_service()` and separately resolves the `TrendingService`. Both create their own `Repository` instances. This means the shutdown cleanup on line 74 only clears the cache of the service created at that point (via a new `_create_market_data_service()` call), not necessarily the same instance. This is harmless since shutdown destroys the process anyway, but the lifecycle management could be cleaner in a future refactor.

---

## F53 -- Pila Easter Eggs (Gaucho Chimarrao + Dialogues)

### Architecture Assessment: PASS

The feature is cleanly decomposed into three layers:
1. **ChimarraoIcon** -- pure presentational button with fixed positioning and pulse animation
2. **GauchoDialog** -- stateful dialog component (message -> options -> reply -> auto-dismiss)
3. **useGauchoEasterEgg** -- hook that encapsulates all business logic (currency check, page routing, session storage, timers)

The hook is consumed in `Layout.tsx` (lines 59, 195-205) which is the correct integration point -- it has access to `location.pathname` and renders the fixed-position elements outside the main content flow.

The dialogue data is driven by `getDialogueForPage()` which maps paths to i18n keys. The `switch` statement handles `/`, `/collection`, `/banlist`, `/decks` and returns `null` for unknown pages. This is extensible.

Session storage (`gaucho_dismissed_{path}`) ensures each page's easter egg only fires once per session. The 2-second delay before showing the icon prevents jarring UI on page load.

### Security Assessment: PASS

No backend changes, no API calls, no user data exposure. Pure frontend cosmetic feature.

### Code Quality: PASS

- `GauchoDialog` auto-dismiss uses `useEffect` cleanup to prevent memory leaks (clearTimeout on unmount).
- The reply flow (`option.reply` present -> show reply text for 2.5s -> dismiss; `option.reply` absent -> immediate dismiss) handles both interaction patterns from the spec.
- `try/catch` around `sessionStorage` access handles private browsing modes gracefully.
- The `type="button"` attribute on all buttons prevents accidental form submissions.

### Test Coverage: PASS (24 new tests)

- ChimarraoIcon: 5 tests (render, click handler, positioning, hover, shadow)
- GauchoDialog: 8 tests (message render, options, reply text, auto-dismiss, close button, no auto-dismiss with options, option-without-reply dismiss)
- useGauchoEasterEgg: 11 tests (all 5 page dialogues, unknown page, icon delay, dismiss persistence, BRL/USD currency guard, sessionStorage)

### Observations (non-blocking)

1. **OBS-F53-01:** The CSS class `animate-fade-in-up` on `GauchoDialog` (line 49) is not defined in `tailwind.config.ts`. Tailwind will silently ignore unknown utility classes, so the dialog will render but without the entrance animation. This should be addressed by adding a custom keyframe/animation in the Tailwind config `extend.animation` and `extend.keyframes` sections.

2. **OBS-F53-02:** The i18n keys in `en.json` and `pt-BR.json` are identical (both contain the Portuguese gaucho slang). This is intentional for the cultural flavor, but English-only users may find the text confusing. Consider whether EN locale should have translated versions or if the gaucho slang IS the feature regardless of language.

3. **OBS-F53-03:** The `useEffect` dependency array on line 102 of `useGauchoEasterEgg.ts` has `dialogData !== null` as a dependency (a boolean expression). This works but is unusual -- the eslint-disable comment is present. A cleaner approach would be to compute a `hasDialogue` variable and include that.

---

## Cross-Feature Checks

| Check | Status |
|-------|--------|
| i18n keys present in both locales | PASS (18 gaucho keys each) |
| No regressions in existing tests | PASS (0 failures across 2694 tests) |
| Coverage above threshold | PASS (92.52% backend, above 70% minimum) |
| No secrets or credentials committed | PASS |
| No dead imports or unused code | PASS |
| Consistent error handling patterns | PASS |
| Type safety (TS + Pydantic schemas aligned) | PASS |

---

## Summary

All three features are well-implemented with appropriate test coverage, proper security controls, and clean architecture. The observations noted above are minor quality improvements that do not block shipping. The most actionable one is **OBS-F53-01** (missing Tailwind animation definition) which should be addressed in a follow-up to ensure the dialog entrance animation works as designed.
