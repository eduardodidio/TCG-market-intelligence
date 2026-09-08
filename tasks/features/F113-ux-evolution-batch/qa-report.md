# F113 QA Report

**QA Agent** | **Date:** 2026-09-08 | **Branch:** homol

---

## 1. Test Suite Results

### Backend (pytest)

- **F113-specific tests:** 81 passed, 0 failed
  - `test_card_search.py` (T04 alternate name fallback): 12 passed
  - `test_cards_refresh_price.py` (T09 refresh endpoint): 8 passed
  - `test_f113_portfolio_liga.py` (T07 foil/priced/movers): 14 passed
  - `test_catalog_router.py` (T02 rarity/sort): 30 passed
  - `test_f90_gap_tests.py` (pre-existing, now passing after bugfix): 17 passed
- **Full API unit tests:** 277 passed, 5 failed (pre-existing: `test_scan_sse.py`)
- **Full unit suite:** ~580 passed, ~51 failed (all pre-existing in `test_repository_marketplace.py`, `test_liga_coverage.py`, `test_repository_decks.py`, `test_repository_collection.py`, `test_currency.py` -- unrelated to F113)

### Frontend (Vitest)

- **188 test files, 1828 tests -- all passing**
- New file added by QA: `CardTile.test.tsx` (8 tests)

---

## 2. Per-Task Validation

### T01 - README "Future" cleanup: PASS

Trivial docs change. Verified in commit 539e4dd.

### T02 - Catalog page URL fix + rarity filter + price sort: PASS

- All 3 catalog hooks (`useCatalogCards`, `useCatalogSets`, `useCatalogStats`) use `/api/v1/catalog/` prefix. No references to old `/api/catalog/` remain in frontend.
- Backend `catalog.py` line 132: rarity filter splits on comma (`rarity.split(",")`) and uses parameterized `IN` query (no SQL injection risk).
- Price sort with null-to-end logic confirmed in catalog router tests.

### T03 - Auth redirect + nav restructure: PASS

- Single `ProtectedRoute` wraps the Layout route (App.tsx lines 188-191). All child routes inherit auth protection.
- `/marketplace/share/:code` is correctly extracted as a separate public route block (App.tsx lines 170-184) with its own Layout, no auth required.
- `/login` and `/change-password` are standalone public routes outside Layout.
- Achievements at `/achievements` is in `BETA_NAV_ITEMS` (Layout.tsx line 48), not in `PRIMARY_NAV_ITEMS`. Marketplace at `/marketplace` is also in `BETA_NAV_ITEMS` (line 46).

### T04 - Web search PT/EN name fallback: PASS

- `_find_alternate_name` function exists at `card_search.py:36`. Does case-insensitive lookup against local Scryfall catalog.
- Called as fallback from `_search_via_liga` (line 153) when Liga returns no prices.
- Called as fallback from `_search_via_myp` (line 213) when MYP returns empty results.
- 12 dedicated tests covering EN-to-PT, PT-to-EN, no-match, case-insensitive, both-names-match, and retry logic for both providers.

### T05 - Project cleanup: PASS

Removed 6 unused agent prompt files (674 lines). No source code affected.

### T06 - Set completion UX: PASS

- `SetCompletionSection` in `SetCompletionBar.tsx` has localStorage-persisted collapse/expand state.
- Scryfall SVG set icons with `onError` fallback handling.
- Click-to-navigate: `onClick={() => navigate(\`/collection?set=\${setCode}\`)}` with keyboard accessibility (`role="button"`, `tabIndex={0}`, Enter/Space handlers).
- 21 tests in `SetCompletionBar.test.tsx` covering collapse, expand, localStorage persistence, icon rendering, navigation on click.

### T07 - Portfolio/Liga data flow fix: PASS

- **Bug A (foil backfill):** `_load_card_external_ids` at line 349 of `portfolio_backfill.py` handles `liga_{card_id}_foil` pattern. Foil patterns inserted at priority position (line 81: `search_pairs.insert(-1, ...)`).
- **Bug B (priced count):** `get_collection_summary` in `repository.py` expanded to check direct Liga/manual patterns via `IN` query. 4 tests confirm liga-only, liga-foil, source_card, and manual-price cards are all counted.
- **Bug C (empty state):** `PortfolioDashboard.tsx` line 190: shows `portfolio.noHistory` message when `history.length <= 1`.
- **Bug D (movers):** `get_trending_price_data_for_user` queries direct patterns in addition to source_cards join. 3 tests confirm liga-only, liga-foil, and source_card prices appear in trending data.
- 14 backend + frontend tests covering all 4 bugs.

### T08 - CLAUDE.md placeholders: PASS

Mission, architecture, and commands sections updated from placeholder text. Verified content is accurate.

### T09 - Cards page scroll reset, set icons, price refresh: PASS

- **Scroll reset:** `window.scrollTo({ top: 0, behavior: "smooth" })` at Cards.tsx line 117 on filter/sort change.
- **Set icons:** `FilterChips.tsx` supports optional `icon` property (line 4: `icon?: string`). Renders `<img>` with `onError` fallback (line 43-50).
- **Per-card refresh:** `POST /api/v1/cards/{card_id}/refresh-price` endpoint exists at `cards.py:254`. 8 backend tests covering success, 404, 503, 402, 429, DB storage, and credit deduction.
- **CardTile refresh:** Overlay button appears on hover with `opacity-0 group-hover:opacity-100` transition. Calls `refreshCardPrice(card.id)`, updates display price, triggers `onPriceRefreshed` callback.
- **Refresh All:** CreditConfirmModal with sequential progress, abort ref, credit refetch. Integrated in Cards.tsx.

---

## 3. Bugs Found and Fixed

### Bug: `_find_alternate_name` crashes on mocked DB session (T04 regression)

- **File:** `src/api/routers/card_search.py:60`
- **Symptom:** `ValueError: not enough values to unpack (expected 2, got 0)` when `Session.execute().first()` returns a non-None object that cannot be unpacked (e.g., MagicMock in tests, or unexpected DB row format).
- **Root cause:** The `_find_alternate_name` function introduced in T04 lacked defensive error handling for the tuple unpacking `name_en, name_pt = row`.
- **Fix:** Added `try/except` around both the Session execution and the tuple unpacking, returning `None` on any error. This is appropriate because `_find_alternate_name` is a best-effort fallback lookup.
- **Impact:** Fixed 1 pre-existing test (`test_f90_gap_tests.py::TestSearchWebMalformedData::test_missing_normal_key_returns_empty`) that was broken by the T04 changes.

---

## 4. Test Gaps Filled

### CardTile refresh interaction tests (8 tests)

- **File:** `frontend/src/components/__tests__/CardTile.test.tsx`
- **Gap identified by:** Tech Lead review (issue #2)
- **Tests added:**
  1. Renders card name and price
  2. Renders refresh button for authenticated user
  3. Hides refresh button for unauthenticated user
  4. Calls `refreshCardPrice` and updates display price on success
  5. Disables button while refreshing (loading state)
  6. Handles refresh failure gracefully (price unchanged)
  7. Shows set code badge
  8. Links to card detail page

---

## 5. Pre-Existing Test Failures (Not F113-Related)

The following test failures exist on `homol` independent of F113:

| File | Failures | Nature |
|------|----------|--------|
| `test_repository_marketplace.py` | 37 | Trade interest/agreement CRUD tests (FK constraint issues) |
| `test_liga_coverage.py` | 9 | Liga coverage tests |
| `test_repository_decks.py` | 2 | Deck repository tests |
| `test_repository_collection.py` | 2 | Collection repository tests |
| `test_currency.py` | 1 | Currency conversion edge case |
| `test_scan_sse.py` | 5 | SSE streaming tests |

These are all pre-existing and unrelated to F113 changes.

---

## 6. Tech Lead Issues Assessment

| Issue | Severity | Status |
|-------|----------|--------|
| Redundant except clause (T04) | Cosmetic | Acknowledged, non-blocking |
| No frontend tests for T09 refresh (T09) | Minor | **FIXED** -- 8 tests added |
| Credit deducted even with no price (T09) | Design | Intentional (pay-for-attempt pattern) |
| `_find_alternate_name` bypasses Repository (T04) | Minor | Acknowledged, pragmatic shortcut |
| `_find_alternate_name` crash on unexpected row (T04) | Medium | **FIXED** -- defensive try/except added |

---

## 7. Verdict: PASS

All 9 tasks deliver correct functionality. The single regression found (`_find_alternate_name` crash) has been fixed with defensive error handling. Test gap for CardTile refresh interactions has been filled with 8 new frontend tests. No security issues, no data integrity bugs, no F113-introduced regressions.

**Final counts:**
- Backend F113 tests: 81 passed
- Frontend: 188 files, 1828 tests, all passing
- Bugs found: 1 (fixed)
- Test gaps filled: 1 file, 8 tests
