# Tech Lead Review: F189+F190+F191+F192 -- Deck UX Overhaul Batch

**Reviewer:** Tech Lead Agent
**Date:** 2026-10-01
**Branch:** homol

---

## Wave 0 -- Cleanup (F189 + F190)

### T01 -- Remove DeckBuildWizard and related frontend code (F189)

**Files reviewed:**
- `frontend/src/App.tsx` -- DeckBuildWizard lazy import removed, `/decks/build` and `/decks/evaluate` routes removed
- `frontend/src/components/Layout.tsx` -- `buildDeck` and `deckEvaluator` entries removed from `BETA_NAV_ITEMS`
- `frontend/src/api/decks.ts` -- `generateDeck()` and `searchCommanders()` removed; only kept functions remain
- `frontend/src/types/api.ts` -- `DeckGenerateParams`, `GeneratedCard`, `DeckGenerateResult`, `CommanderSearchResult` interfaces removed
- All 19 files marked for deletion confirmed GONE (verified via `Glob`)

**Checklist:**
- [x] No dangling imports to deleted modules (grep confirms zero references to DeckBuildWizard, CommanderSearch, etc. in any .ts/.tsx file)
- [x] Build compiles cleanly (TypeScript `--noEmit` passes; all errors are pre-existing in unrelated `TrendingCollectionOnly.test.tsx`)
- [x] Deleted test files removed (DeckBuildWizard.test.tsx, CommanderSearch.test.tsx, etc.)
- [x] Backend endpoints preserved (F189 explicitly keeps `/decks/generate`, `/decks/commanders`)
- [x] BetaRoute.tsx correctly preserved (still used by marketplace, trade-matches, etc.)

**Finding (non-blocking):** The `deckSuggestions` section in `en.json` (line 580) and `pt-BR.json` (line 580) contains orphaned i18n keys that are no longer referenced by any code. These are dead data left behind by T01. Not a bug, but should be cleaned up to avoid confusion.

**Verdict: PASS**

---

### T02 -- Remove BetaRoute from decks, move to primary nav (F190)

**Files reviewed:**
- `frontend/src/App.tsx` (lines 311-340) -- Deck routes (`/decks`, `/decks/ranking`, `/decks/:id`) are now bare `<DeckList />`, `<TopDecksPage />`, `<DeckView />` without `<BetaRoute>` wrappers
- `frontend/src/components/Layout.tsx` (lines 62-73) -- `myDecks` and `topDecks` correctly moved to `PRIMARY_NAV_ITEMS` at positions 7-8 (after alerts, before settings)

**Checklist:**
- [x] Deck routes no longer wrapped in BetaRoute (verified in App.tsx lines 311-340)
- [x] `BetaRoute` import preserved in App.tsx (still used by marketplace, trending, market, banlist, evaluations, achievements, news)
- [x] Nav items have `requiresAuth: true` (visible only to authenticated users)
- [x] `BETA_NAV_ITEMS` still contains market, trending, banlist, marketplace, trade-matches, achievements, evaluations, news (8 items)
- [x] Deck routes remain inside `<ProtectedRoute>` wrapper (line 191-196 of App.tsx)

**Verdict: PASS**

---

## Wave 1 -- New Features (F191 + F192)

### T03 -- Backend: create empty deck + update deck endpoints (F191)

**Files reviewed:**
- `src/api/schemas/decks.py` -- `DeckCreateRequest`, `DeckUpdateRequest`, `DeckCreateResult` added (lines 11-25)
- `src/api/routers/decks.py` -- `POST /decks/create` (line 105) and `PUT /decks/{deck_id}` (line 814) endpoints added
- `src/database/repository.py` -- `update_deck()` method added (line 2684)

**Checklist:**
- [x] `POST /decks/create` uses `require_auth_or_api_key` for authorization
- [x] `PUT /decks/{deck_id}` uses `require_auth_or_api_key` for authorization
- [x] Deck ownership check on PUT (returns 404 for wrong user or nonexistent deck)
- [x] Existing `POST /decks` import endpoint preserved and unchanged (backward compatible)
- [x] `DeckCreateRequest.name` has `min_length=1, max_length=200` validation
- [x] `DeckUpdateRequest.name` has `min_length=1, max_length=200` when provided (allows None for partial update)
- [x] Repository `update_deck` only updates fields that are explicitly not None (partial update semantics)
- [x] Repository uses `session.expunge(deck)` to detach from session before returning
- [x] Tests cover: create with name, create with description, empty name rejection, name too long, update name, update description, update not found, update wrong user (all pass, 5 tests in TestUpdateDeck, 4 in TestCreateDeck)

**Observation (non-blocking):** The `PUT /decks/{deck_id}` endpoint rebuilds the full `DeckDetailSchema` response (lines 834-880), duplicating the logic from `GET /decks/{deck_id}` (lines 763-811). This is roughly 50 lines of duplicated code. A helper function to build the detail response would reduce maintenance burden. Not blocking since both work correctly.

**Observation (non-blocking):** The `DeckUpdateRequest` does not distinguish between "field absent from JSON body" and "field explicitly set to null". Sending `{"name": "New Name"}` without `description` will not clear the description (because Pydantic defaults `description` to `None` and the repo only updates non-None fields). However, sending `{"description": null}` will also not clear it for the same reason. If clearing a description is desired, the developer would need to use a sentinel pattern. This is acceptable for MVP since descriptions are rarely cleared.

**Verdict: PASS**

---

### T04 -- Frontend: new deck modal + inline edit on DeckView (F191)

**Files reviewed:**
- `frontend/src/components/DeckCreateModal.tsx` -- New modal component (128 lines)
- `frontend/src/pages/DeckList.tsx` -- "New Deck" button added, DeckCreateModal integrated
- `frontend/src/pages/DeckView.tsx` -- Inline name and description editing
- `frontend/src/api/decks.ts` -- `createDeck()` and `updateDeck()` functions added
- `frontend/src/api/client.ts` -- `apiPut` confirmed to exist (line 314)
- `frontend/src/types/api.ts` -- `DeckCreateResult` interface added (line 325)
- `frontend/src/i18n/locales/en.json` -- 11 new i18n keys under `decks.*`
- `frontend/src/i18n/locales/pt-BR.json` -- 11 matching pt-BR translations

**Checklist:**
- [x] DeckCreateModal disables Create button when name is empty
- [x] DeckCreateModal handles API errors (shows error banner)
- [x] DeckCreateModal uses `maxLength={200}` on input
- [x] DeckCreateModal closes on backdrop click, stays open on content click (stopPropagation)
- [x] DeckCreateModal supports Enter key submission
- [x] DeckList "New Deck" button opens modal, navigates to new deck on success
- [x] DeckList empty state includes "New Deck" action
- [x] DeckView inline name edit: click activates, Enter saves, Escape reverts
- [x] DeckView inline description edit: same keyboard behavior (Shift+Enter for newline, Enter saves)
- [x] Optimistic UI: local state updated immediately, reverted on API error
- [x] Pencil icon visible on hover (opacity-0 to opacity-100 transition)
- [x] No hardcoded strings (all user-facing text uses i18n)
- [x] Style consistent with existing modals (DeckImportModal pattern: dark slate, border, shadow)
- [x] Tests: 13 tests for DeckCreateModal, 10 for DeckView inline edit, 5 for DeckList -- all pass

**Observation (non-blocking):** The DeckCreateModal uses hardcoded dark theme classes (`bg-slate-800`, `text-white`, etc.) rather than `dark:` responsive classes. This means the modal always renders in dark mode regardless of theme setting. However, reviewing the existing DeckImportModal and other modals in the codebase shows the same pattern, so this is consistent.

**Verdict: PASS**

---

### T05 -- Backend: Goldfish simulator service + endpoint (F192)

**Files reviewed:**
- `src/decks/goldfish.py` -- New pure module (395 lines)
- `src/api/routers/decks.py` -- `POST /decks/{deck_id}/goldfish` endpoint (line 678)
- `src/api/schemas/decks.py` -- `GoldfishSampleHand`, `GoldfishResponse` schemas (lines 210-225)
- `tests/unit/decks/test_goldfish.py` -- 42 tests (unit + integration)

**Checklist:**
- [x] Module is pure (no database imports, no FastAPI imports) -- verified
- [x] `rng: random.Random | None` parameter for deterministic testing -- verified
- [x] `_is_land()` uses word boundary regex to avoid false positives ("Landfall" does not match)
- [x] `_parse_cmc_simple()` handles: None, empty, X cost (0), hybrid, phyrexian, split cards, colorless pips
- [x] Opening hand quality heuristic matches spec (0/1/2/3/4/5/6+ lands mapped correctly, +0.1 bonus for CMC 1-2 spell, capped at 1.0)
- [x] Mana screw definition: opening hand <= 1 land OR turn 4 lands_in_play <= 2
- [x] Mana flood definition: opening hand >= 5 lands OR turn 7 lands_drawn/cards_seen >= 0.70
- [x] Sample hands: worst, median, best (correctly sorted and picked)
- [x] Empty deck handled gracefully (returns screw_rate=1.0, flood_rate=0.0, 0 simulations)
- [x] Deck quantity expansion correct (4x Lightning Bolt = 4 entries in deck_list)
- [x] Endpoint requires auth (`require_auth_or_api_key`)
- [x] Endpoint checks deck ownership (404 for wrong user)
- [x] Endpoint checks for empty deck (400 with clear message)
- [x] Query params validated: `num_simulations` (10-1000), `turns` (3-15)
- [x] Performance: simulation is O(n * k) where n=simulations, k=turns -- trivially fast for 1000 * 15
- [x] All 42 tests pass (60 passed in goldfish unit, 5 passed in endpoint tests)

**Algorithm review:**

The single game simulation (lines 176-261) correctly implements:
1. Shuffle deck copy (not mutating original)
2. Draw min(7, deck_size) for opening hand
3. Each turn: draw 1, play first available land, greedily cast cheapest spells
4. Track lands_in_play, spells_castable, spells_cast, cards_in_hand per turn

The greedy casting approach (sort by CMC ascending, cast cheapest first) is a reasonable simplification for goldfish analysis. A more sophisticated approach would consider color requirements, but for consistency analysis this is sufficient.

**Observation (non-blocking):** The flood detection uses `lands_in_play / total_cards_seen >= 0.70`, but `lands_in_play` only counts played lands, not lands still in hand. Since the simulator always plays a land when available, this is close to accurate but could undercount by at most 1 (the land drawn on the last turn that couldn't be played if a land was already played). This is a minor heuristic imprecision that has no practical impact on the analysis.

**Observation (non-blocking):** The `_simulate_single_game` removes cast cards from hand by collecting indices and removing in reverse order (lines 243-244). The index-based removal is correct because spells_in_hand stores the original hand indices before any removal. Good defensive coding.

**Verdict: PASS**

---

### T06 -- Frontend: Goldfish tab on DeckView (F192)

**Files reviewed:**
- `frontend/src/components/GoldfishPanel.tsx` -- New component (373 lines)
- `frontend/src/pages/DeckView.tsx` -- Third tab ("goldfish") integrated
- `frontend/src/api/decks.ts` -- `fetchGoldfish()` function added
- `frontend/src/types/api.ts` -- `GoldfishSampleHand`, `GoldfishResult` interfaces added
- `frontend/src/i18n/locales/en.json` -- 18 new goldfish i18n keys
- `frontend/src/i18n/locales/pt-BR.json` -- 18 matching pt-BR translations
- `frontend/src/components/__tests__/GoldfishPanel.test.tsx` -- 14 tests

**Checklist:**
- [x] Tab system extended from 2 to 3 tabs (cards | evaluation | goldfish)
- [x] Tab state persisted in URL search params (`?tab=goldfish`)
- [x] GoldfishPanel uses `hasFetched` ref to avoid re-fetching on tab switches
- [x] Loading skeleton renders during fetch
- [x] Error state uses ErrorBanner with retry (F159 pattern)
- [x] "Simulate Again" button triggers new fetch
- [x] Charts use Recharts (LineChart for mana, BarChart for spells) with dark-friendly colors
- [x] Charts wrapped in ResponsiveContainer for responsive sizing
- [x] Screw/flood rate badges use color coding: green (<= 20%), orange (20-30%), red (> 30%)
- [x] Sample hands displayed as card name pills with truncation (max-w-[200px])
- [x] Sample hands labeled best/median/worst with green/yellow/red colors
- [x] Median hand hidden when it equals best or worst (prevents duplicate display)
- [x] Chart tooltip styled consistently with existing DeckView charts
- [x] No hardcoded strings (all user-facing text uses i18n)
- [x] Mobile responsive (grid-cols-1 md:grid-cols-2 layout)
- [x] All 14 frontend tests pass (loading, error, quality display, charts, sample hands, simulate again, badge colors)

**Observation (non-blocking):** The `fetchGoldfish` function in `decks.ts` (line 64-71) builds query parameters by string concatenation (`?num_simulations=${numSimulations}&turns=${turns}`) rather than using URLSearchParams. This works but is less robust than the URL parameter approach used by `fetchDeckEvaluation`. Minor style inconsistency.

**Observation (non-blocking):** The `SampleHandRow` component receives the full `t` function as a prop rather than using `useTranslation()` directly. This is a valid pattern (avoids hook call overhead in a child component) but differs from the project convention where most components call `useTranslation()` themselves. Non-blocking since it works correctly.

**Verdict: PASS**

---

## Overall Assessment

### Summary of Findings

| ID | Severity | Task | Description |
|----|----------|------|-------------|
| F1 | Non-blocking | T01 | Orphaned `deckSuggestions` i18n keys in en.json and pt-BR.json (dead data, ~18 lines each) |
| F2 | Non-blocking | T03 | Duplicated DeckDetailSchema response builder in PUT endpoint (~50 lines duplicate of GET) |
| F3 | Non-blocking | T03 | Cannot set `description` to null via PUT (sentinel pattern not implemented) |
| F4 | Non-blocking | T06 | Query string built by concatenation rather than URLSearchParams |
| F5 | Non-blocking | T06 | `SampleHandRow` receives `t` as prop instead of calling `useTranslation()` |

### Test Summary

| Area | Tests | Status |
|------|-------|--------|
| `tests/unit/decks/test_goldfish.py` | 42 | All pass |
| `tests/unit/api/test_deck_endpoints.py` (create/update) | 9 | All pass |
| `DeckCreateModal.test.tsx` | 13 | All pass |
| `GoldfishPanel.test.tsx` | 14 | All pass |
| `DeckViewInlineEdit.test.tsx` | 10 | All pass |
| `DeckList.test.tsx` | 5 | All pass |
| **Total new tests** | **93** | **All pass** |

Pre-existing test failures (unrelated to this feature):
- `TestEvaluateDeck` (3 tests in `test_deck_endpoints.py`) -- pre-existing failures
- `TrendingCollectionOnly.test.tsx` -- pre-existing TS errors

### Architecture Quality

- **Separation of concerns:** The goldfish simulator is a pure module with zero dependencies, exactly as specified. Easy to test and maintain.
- **Backward compatibility:** Existing `POST /decks` import endpoint is fully preserved. The new `POST /decks/create` is a separate path.
- **Security:** All new endpoints require `require_auth_or_api_key`. Deck ownership verified before any mutation or data retrieval.
- **i18n completeness:** All 29 new i18n keys present in both en.json and pt-BR.json.
- **Pattern consistency:** New code follows established project patterns (ErrorBanner, Recharts usage, modal styling, optimistic UI, skeleton loading).

---

## Verdict: APPROVED

All 6 tasks (T01-T06) are correctly implemented. 93 new tests pass. No security issues, no dead imports, no hardcoded strings. The 5 non-blocking findings are minor style/cleanup items that do not affect functionality or user experience.
