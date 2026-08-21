# QA Report -- F24 Platform Polish & Fixes

**QA Agent** | **Date:** 2026-08-21
**Verdict: PASSED**

---

## Test Execution Results

| Suite | Count | Status |
|-------|-------|--------|
| Backend (pytest) | 1179 passed | PASS |
| Backend coverage | 94.87% (threshold: 70%) | PASS |
| Frontend (Vitest) | 479 passed, 48 test files | PASS |
| Production build (vite build) | Succeeds cleanly | PASS |
| TypeScript strict check (tsc --noEmit) | 16 errors in test files only | WARN |

---

## Acceptance Criteria Checklist

- [x] **Collection card click from My Collection opens detail page correctly** --
  `apiGet` now sends `Authorization: Bearer` header from localStorage (line 37-40
  of `frontend/src/api/client.ts`). The collection detail endpoint checks
  `entry.user_id != user_id` returning 404 for non-owners
  (`src/api/routers/collection.py:170`). Test
  `test_returns_404_when_entry_belongs_to_different_user` confirms IDOR prevention.

- [x] **All Explore Cards show images (Portuguese name fallback to English)** --
  T04 confirmed existing code already handles this correctly; 6 new tests added
  to prove the behavior.

- [x] **Cards without prices show graceful fallback (not blank)** --
  `formatPriceOrFallback()` in `frontend/src/utils/format.ts:94-102` returns
  `null` for `null`, `undefined`, `NaN`, or `0` values. `CardTile` uses it
  to show "No price data" in muted text instead of misleading "R$ 0,00".

- [x] **Dashboard coverage reflects actual linking state with clear explanation** --
  New `priced_count` metric added to `CollectionSummary` schema
  (`src/api/schemas/collection.py:43`). Repository computes it via SQL query
  (`src/database/repository.py:705-733`). Dashboard shows both "linked" and
  "priced" percentages.

- [x] **Dashboard collection value accounts for all priced cards** --
  `get_collection_total_value` sums all priced entries for the authenticated user.

- [x] **Price chart supports zoom in/out, pan, and auto-scales Y-axis** --
  `PriceChart.tsx` imports and uses `Brush` (time range), `ReferenceArea`
  (click-drag zoom), dynamic Y-axis domain, and `resetZoom` button. All
  confirmed present in source.

- [x] **UI fully in English by default, with PT-BR language option** --
  react-i18next initialized with `fallbackLng: "en"` and `LanguageDetector`
  (localStorage key `tcg_language` -> navigator). 205 translation keys in both
  `en.json` and `pt-BR.json`, all keys match perfectly.

- [x] **Language selector on login page and in user settings** --
  `LanguageSelector` component used in `Login.tsx` and `Layout.tsx` (sidebar).
  Confirmed via grep.

- [x] **Visual style matches Lovable reference (dark theme, glass-morphism, tcg-* tokens)** --
  `design-tokens.css` defines CSS custom properties. `tailwind.config.ts` maps
  `tcg-*` color tokens via `var()` references. Tokens are semantically named
  (`tcg-bg`, `tcg-card`, `tcg-gain`, `tcg-loss`, etc.).

- [x] **All existing tests pass** -- 1179 backend + 479 frontend, zero failures.

- [x] **New tests for changed logic (coverage >= 90%)** -- 94.87% backend
  coverage. New test files: `i18n.test.ts`, `LanguageContext.test.tsx`,
  `useLanguage.test.tsx`. Collection detail IDOR test. Auth preference tests.

- [x] **README.md updated with F24 delivery notes** -- F24 section at line 623
  of `README.md` with comprehensive delivery notes covering all 10 tasks.

---

## Security Review

### apiGet Auth Header (T03) -- PASS
- Token is read from `localStorage.getItem("tcg_access_token")` and sent only
  when present, matching the pattern in `apiPost`, `apiDelete`, and `apiPatch`.
- No token leakage risk: the token is only sent to the same-origin API via
  `API_BASE_URL`.

### IDOR Prevention (T03) -- PASS
- `GET /collection/{entry_id}` fetches the entry then checks
  `entry.user_id != user_id`, returning 404 (not 403) to avoid leaking
  existence. This is the correct pattern.
- Backend test `test_returns_404_when_entry_belongs_to_different_user`
  validates this with `user_id="other_user"`.

### Language Preference Validation (T10) -- PASS
- `PreferencesUpdate.preferred_language` uses Pydantic `Field(pattern="^(en|pt-BR)$")`.
- Invalid values like `"fr"` are rejected with 422. Backend test
  `test_set_preferred_language_invalid` confirms this.

---

## Test Gap Analysis

### Gaps Found (non-blocking)

1. **`formatPriceOrFallback` has no unit tests** -- The function in
   `frontend/src/utils/format.ts:94-102` is tested indirectly via component
   tests but has no dedicated unit tests in `format.test.ts`. Recommend adding
   tests for `null`, `undefined`, `0`, `"0"`, `NaN`, and valid price inputs.

2. **`LanguageSelector` component has no dedicated tests** -- The component is
   exercised indirectly through page-level tests (Login, Layout), but has no
   isolated unit tests for compact vs full variants or language change callback.

3. **TypeScript strict errors in test files** -- 16 `tsc --noEmit` errors in
   test files (missing `preferred_language` property in mock objects, missing
   `offset` in mock `ApiMeta`, type mismatches in `MyCollection.test.tsx`).
   These do not block test execution (Vitest runs fine) but indicate stale
   test type definitions that should be updated. Files affected:
   - `tests/components/Layout.test.tsx`
   - `tests/components/MarketMovers.test.tsx`
   - `tests/components/PriceChart.test.tsx`
   - `tests/components/ProtectedRoute.test.tsx`
   - `tests/hooks/useAuth.test.ts`
   - `tests/pages/CollectionCardDetail.test.tsx`
   - `tests/pages/DeckList.test.tsx`
   - `tests/pages/DeckView.test.tsx`
   - `tests/pages/MyCollection.test.tsx`
   - `src/components/ErrorBanner.tsx` (unused variable)
   - `src/i18n/__tests__/i18n.test.ts` (unused import)

### Coverage Assessment
- Backend: 94.87% (well above 90% threshold)
- Frontend: 479 tests across 48 files (comprehensive for an SPA)
- i18n tests: initialization, fallback, resource loading, localStorage
  persistence, interpolation config, language switching round-trip
- Auth preference tests: set EN, set PT-BR, reject invalid, profile includes
  language

---

## Cross-Feature Regression

- [x] **Auth flow** -- `register`, `login`, `refresh`, `logout` endpoints all
  present and unchanged. `preferred_language` is an additive field with default
  `"en"`, backward-compatible.

- [x] **Currency toggle (BRL/USD/PILA)** -- `CurrencyToggle` still present in
  `Layout.tsx`. No changes to currency conversion logic.

- [x] **Deck import** -- `DeckList.tsx`, `DeckView.tsx` included in production
  build output. Deck API endpoints unchanged.

- [x] **Scan functionality** -- `Scans` page present in build output. Scan
  endpoints unchanged.

- [x] **API backward compatibility** -- All schema changes are additive with
  defaults: `priced_count: int = 0`, `preferred_language: str = "en"`,
  `apiPatch` is a new function. No breaking changes.

---

## Documentation Review

- [x] **Architecture diagram** -- `docs/diagrams/F24-architecture.mmd` exists.
  Shows i18n data flow (i18next -> LanguageContext -> components) and backend
  preference persistence (auth router -> UserRow -> repository).

- [x] **User journey diagram** -- `docs/diagrams/F24-journey.mmd` exists.
  Covers language selection flow: unauthenticated (login page selector) and
  authenticated (sidebar selector with server persistence).

- [x] **README.md** -- F24 section at line 623 with comprehensive delivery
  notes covering all deliverables.

- [x] **Tech Lead review** -- `tasks/features/F24-platform-polish/techlead-review.md`
  exists with APPROVED verdict. 4 minor issues noted (Dashboard hardcoded
  strings since fixed, unnecessary getattr, chart hex colors, LanguageSelector
  duplication).

---

## Recommendations

1. **Fix TypeScript strict errors in test files** (priority: medium) -- Add
   `preferred_language` to mock `UserProfile` objects and `offset` to mock
   `ApiMeta` objects in the 9 affected test files. This prevents type drift
   from accumulating across features.

2. **Add `formatPriceOrFallback` unit tests** (priority: low) -- Cover edge
   cases: `null`, `undefined`, `0`, `"0"`, `NaN`, negative numbers, valid
   prices with different currencies.

3. **Add `LanguageSelector` component tests** (priority: low) -- Test compact
   vs full variant rendering, language change callback invocation, and
   current language highlight.

4. **Remove unused `NETWORK_ERROR_MESSAGE` in ErrorBanner.tsx** (priority: low) --
   Declared but never read per TypeScript.

5. **Clean up `getattr` calls in auth dependencies** (priority: low) -- As
   noted in tech lead review, `user.preferred_language` can be accessed
   directly since the domain model defines the field.

---

## Verdict: PASSED

F24 delivers a comprehensive batch of improvements: i18n infrastructure with
full string extraction (205 keys, EN + PT-BR), design token system with dark
theme, critical security fixes (apiGet auth + IDOR prevention), interactive
price chart with zoom, and dashboard coverage breakdown. All 1658 tests pass
(1179 backend + 479 frontend), backend coverage is 94.87%, production build
succeeds, and all 12 acceptance criteria are met. The TypeScript strict errors
in test files and missing unit tests for two utilities are non-blocking items
that can be addressed in a follow-up.
