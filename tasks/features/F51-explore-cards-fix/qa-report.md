# QA Report -- F51, F52, F53

**QA Agent** | Date: 2026-08-23
**Verdict: PASS**

---

## Test Suite Results

| Suite | Tests | Files | Coverage | Status |
|-------|-------|-------|----------|--------|
| Backend (pytest) | 1756 passed | -- | 92.52% | PASS |
| Frontend (vitest) | 938 passed | 92 | -- | PASS |

No regressions detected. All pre-existing tests continue to pass.

---

## F51 -- Fix Explore Cards (Images, Prices, Refresh)

### Acceptance Criteria Verification

| Criteria | Status | Evidence |
|----------|--------|----------|
| F51-T01: CardDetail 3-tier image fallback (set/number -> name -> placeholder) | PASS | `CardImage` subcomponent (CardDetail.tsx lines 361-435) implements `imgError` + `fallbackError` states. Primary URL uses `scryfallImageUrl(setCode, collectorNumber)`, fallback uses `scryfallImageByName(nameEn)`, final state renders SVG placeholder with `data-testid="card-image-placeholder"`. |
| F51-T02: Price display shows "No price data" when null | PASS | `formatPriceOrFallback()` returns `null` for absent/zero prices. CardDetail (lines 228-238) renders `t("common.noPriceData")` in muted `text-slate-500` when null. CurrencyIndicator shown alongside valid prices. i18n keys present in both locales (`en.json` and `pt-BR.json`). |
| F51-T03: Refresh button on CardDetail for collection-linked cards | PASS | Button rendered conditionally on `card.collection_entry_id != null` (line 202). Backend `get_card` endpoint uses `get_optional_user` to look up `collection_entry_id` scoped to `user_id` (IDOR-safe). Calls existing `POST /collection/{entry_id}/refresh`. Success updates displayed price via `setCard()`. |

### Test Coverage

- `CardDetail.test.tsx`: 37 test cases including 5 new (fallback-by-name, fallback-on-error, placeholder, refresh-button visibility, refresh-API-call)
- Security: `collection_entry_id` lookup scoped to authenticated user's own collection (verified in `cards.py` line 117-118)

---

## F52 -- Fix Dashboard Trending (Signal Forwarding + Cache Invalidation)

### Acceptance Criteria Verification

| Criteria | Status | Evidence |
|----------|--------|----------|
| F52-T01: Signal forwarding in TrendingSection | PASS | `TrendingSection.tsx` line 35 now passes `(signal) => fetchTrending(direction, params, { signal })` to `useApi`. Previously called `fetchTrending(direction, params)` without threading the AbortController signal, causing silently aborted requests on re-renders. |
| F52-T02: Trending cache invalidation on scan completion | PASS | `make_trending_invalidation_hook()` in `scan_hooks.py` calls `trending_service.invalidate_cache()` when `external_ids` is non-empty. Registered in `app.py` lifespan alongside existing market data cache hook. 3 backend tests verify: invalidation called, skipped on empty IDs, works through registry. |

### Test Coverage

- Frontend: 4 new tests in `trending.test.ts` (envelope structure, URL construction, signal forwarding, error envelope)
- Backend: 3 new tests in `test_scan_hooks.py` (trending invalidation called, skipped when empty, registry integration)

---

## F53 -- Pila Easter Eggs (Gaucho Chimarrao + Dialogues)

### Acceptance Criteria Verification

| Criteria | Status | Evidence |
|----------|--------|----------|
| F53-T01: ChimarraoIcon component | PASS | Fixed bottom-right positioning (`fixed bottom-6 right-6 z-50`), pulse animation (`animate-pulse`), green shadow, hover scale transition. Renders chimarrao emoji. 5 tests in `ChimarraoIcon.test.tsx`. |
| F53-T02: GauchoDialog component | PASS | Glass-morphism styling (`bg-slate-800/95 backdrop-blur`), green border, close button, option buttons, reply text with 2.5s auto-dismiss, auto-dismiss (4s) when no options. 8 tests in `GauchoDialog.test.tsx`. |
| F53-T03: Layout integration + hook + i18n | PASS | `useGauchoEasterEgg` hook in `Layout.tsx` (line 59). Currency guard (`isPila`), page-based dialogue routing (5 pages), 2s icon delay, sessionStorage dismiss tracking. 18 i18n keys present in both `en.json` and `pt-BR.json` (intentionally identical gaucho slang). 11 tests in `useGauchoEasterEgg.test.tsx`. |

### Test Coverage

- 24 new tests total across 3 test files (ChimarraoIcon: 5, GauchoDialog: 8, useGauchoEasterEgg: 11)

---

## Bug Fix Applied: OBS-F53-01

**Problem:** The CSS class `animate-fade-in-up` used in `GauchoDialog.tsx` (line 49) was not defined in `tailwind.config.ts`. Tailwind silently ignores unknown utility classes, so the dialog rendered but without its entrance animation.

**Fix:** Added custom keyframes and animation definition to `frontend/tailwind.config.ts`:

```typescript
keyframes: {
  'fade-in-up': {
    '0%': { opacity: '0', transform: 'translateY(8px)' },
    '100%': { opacity: '1', transform: 'translateY(0)' },
  },
},
animation: {
  'fade-in-up': 'fade-in-up 0.3s ease-out',
},
```

**Verification:** Frontend test suite re-run after fix: 92 files, 938 tests, all passing.

---

## TechLead Observations Disposition

| Observation | Disposition |
|-------------|-------------|
| OBS-F53-01: Missing `animate-fade-in-up` CSS animation | **FIXED** by QA (see above) |
| OBS-F53-02: i18n keys identical in EN and PT-BR | **Accepted** -- intentional design (gaucho slang IS the feature) |
| OBS-F52-01: Separate Repository instances in app.py lifespan | **Accepted** -- harmless, process-scoped lifecycle |
| OBS-F51-01: useEffect dependency array missing `t`/`getCardName` | **Accepted** -- stable references, cosmetic lint issue |
| OBS-F53-03: Boolean expression in useEffect deps | **Accepted** -- eslint-disable present, works correctly |

---

## Cross-Feature Checks

| Check | Status |
|-------|--------|
| No regressions in 2694 total tests (backend + frontend) | PASS |
| Backend coverage above 70% threshold (92.52%) | PASS |
| i18n keys present in both locales | PASS |
| No secrets or credentials in changed files | PASS |
| Type safety: TS interfaces match Pydantic schemas | PASS |
| Security: no new unprotected endpoints | PASS |

---

## Final Verdict

**PASS** -- All three features meet their acceptance criteria, test suites are green with no regressions, and the one actionable bug (OBS-F53-01) has been fixed. Ready to ship.
