# F189 Test Plan — Deck UX Overhaul Batch

**Features:** F189 (remove auto-build), F190 (remove beta), F191 (deck CRUD), F192 (Goldfish simulator)
**Tasks:** T01-T06 across 2 waves
**Date:** 2026-10-01
**Author:** TEA Agent

---

## 1. Scope

This test plan covers the four features bundled in the F189 Deck UX Overhaul batch:

| Feature | Description | Tasks |
|---------|------------|-------|
| **F189** | Remove DeckBuildWizard and all related frontend code (pages, components, API functions, types, tests). Backend endpoints remain. | T01 |
| **F190** | Promote deck pages (`/decks`, `/decks/ranking`, `/decks/:id`) out of `BetaRoute` wrappers and into primary sidebar navigation. | T02 |
| **F191** | Add missing deck CRUD: create empty deck endpoint (`POST /decks/create`), update deck endpoint (`PUT /decks/{deck_id}`), `DeckCreateModal` on `DeckList`, inline name/description edit on `DeckView`. | T03, T04 |
| **F192** | Goldfish simulator: pure `simulate_goldfish()` service, `POST /decks/{deck_id}/goldfish` endpoint, `GoldfishPanel` component with Recharts charts on `DeckView`. | T05, T06 |

**Out of scope:**
- Backend endpoints for deck generation (`/decks/generate`, `/decks/commanders`) -- these are intentionally kept.
- `BetaRoute.tsx` component itself -- still used by marketplace, trade-matches, achievements, evaluations, market, trending, banlist, news.
- `DeckEvaluationPanel.tsx` -- still used as tab on `DeckView`.
- `DeckImportModal.tsx` -- still used on `DeckList`.

---

## 2. Test Strategy

### Unit Tests (automated)
- **Backend (pytest):** Test new Pydantic schemas, repository methods, API endpoints (via `TestClient` with mocked dependencies), and the pure `goldfish.py` module. All tests follow the existing pattern in `tests/unit/api/test_deck_endpoints.py` using `_make_app()` helper with `FastAPI` + dependency overrides.
- **Frontend (Vitest + RTL):** Test new components (`DeckCreateModal`, `GoldfishPanel`), modified pages (`DeckList`, `DeckView`), API functions (`createDeck`, `updateDeck`, `fetchGoldfish`), and type correctness.

### Integration Tests (automated)
- **Backend:** Repository-level tests for `update_deck()` method using in-memory SQLite. API endpoint integration tests verifying the full request-response cycle including authorization and error handling.

### Build Verification (automated)
- `npm run build` must succeed after all deletions (T01) and additions (T04, T06).
- `npm test` must pass with zero failures (deleted test files must not leave dangling imports).
- `pytest tests/` must pass with no regressions.

### Manual Verification (human QA)
- Navigation flow, visual appearance, dark mode, mobile responsiveness, and end-to-end user journeys.

---

## 3. Test Matrix

| Task | Feature | Unit Tests | Integration Tests | Frontend Tests | Manual QA |
|------|---------|-----------|------------------|---------------|-----------|
| T01 (Remove DeckBuildWizard) | F189 | -- | -- | Build passes, no dangling imports | Route removal, page integrity |
| T02 (Remove BetaRoute from decks) | F190 | -- | -- | Nav item assertions | Nav placement, auth guard |
| T03 (Backend deck CRUD) | F191 | Schema validation (5), endpoint tests (9) | `repo.update_deck()` (3) | -- | -- |
| T04 (Frontend deck CRUD) | F191 | -- | -- | `DeckCreateModal` (4), `DeckList` (2), `DeckView` inline edit (4), API functions (2) | Create + edit flow |
| T05 (Backend Goldfish) | F192 | Pure functions (16) | Endpoint tests (5) | -- | -- |
| T06 (Frontend Goldfish) | F192 | -- | -- | `GoldfishPanel` (8), `DeckView` tab (2), API function (1) | Chart rendering, dark mode, mobile |

**Estimated new test count:** ~61 automated tests (21 backend, 23 frontend component, 5 integration, 12 build/import verification assertions)

---

## 4. Unit Tests

### T01 — Remove DeckBuildWizard (F189)

No new unit tests are written. This task is purely subtractive. Verification is done via build and import checks.

| ID | Check | Method |
|----|-------|--------|
| T01-U01 | `npm run build` succeeds with no import errors | CI / manual |
| T01-U02 | `npm test` passes (all test files referencing deleted components are also deleted) | CI / manual |
| T01-U03 | No remaining imports of deleted modules: `DeckBuildWizard`, `CommanderSearch`, `DeckBuildModeChooser`, `DeckSuggestionPanel`, `SuggestionRequestForm`, `SuggestionRequestList`, `SuggestionResultView`, `deckSuggestions`, `generateDeck`, `searchCommanders` | `grep -r` across `frontend/src/` |

**Deleted test files (19 files):**
- `frontend/src/pages/__tests__/DeckBuildWizard.test.tsx`
- `frontend/src/pages/__tests__/DeckBuildWizard.synergy.test.tsx`
- `frontend/src/components/decks/__tests__/CommanderSearch.test.tsx`
- `frontend/src/components/decks/__tests__/DeckBuildModeChooser.test.tsx`
- `frontend/src/components/decks/__tests__/DeckSuggestionPanel.test.tsx`
- `frontend/src/components/decks/__tests__/SuggestionRequestForm.test.tsx`
- `frontend/src/components/decks/__tests__/SuggestionRequestList.test.tsx`
- `frontend/src/components/decks/__tests__/SuggestionResultView.test.tsx`
- `frontend/src/api/__tests__/deckSuggestions.test.ts`
- `frontend/src/i18n/__tests__/deckSuggestKeys.test.ts`

---

### T02 — Remove BetaRoute from decks (F190)

No new backend unit tests. Frontend assertions are covered in Section 6.

| ID | Check | Method |
|----|-------|--------|
| T02-U01 | `npm run build` succeeds | CI / manual |
| T02-U02 | `npm test` passes -- any tests asserting `BetaRoute` wrapping on deck pages are updated or removed | CI / manual |

---

### T03 — Backend deck CRUD (F191)

**File:** `tests/unit/api/test_deck_endpoints.py` (extend existing file)

Uses existing `_make_app()` and `_mock_deck()` helpers from the test file.

#### Schema validation tests

| ID | Test Name | Description |
|----|-----------|-------------|
| T03-U01 | `test_deck_create_request_valid` | `DeckCreateRequest(name="My Deck")` succeeds, `description` defaults to `None` |
| T03-U02 | `test_deck_create_request_empty_name_rejected` | `DeckCreateRequest(name="")` raises `ValidationError` (min_length=1) |
| T03-U03 | `test_deck_create_request_long_name_rejected` | `DeckCreateRequest(name="x" * 201)` raises `ValidationError` (max_length=200) |
| T03-U04 | `test_deck_update_request_partial_name` | `DeckUpdateRequest(name="New Name")` succeeds, `description` is `None` |
| T03-U05 | `test_deck_update_request_partial_description` | `DeckUpdateRequest(description="New desc")` succeeds, `name` is `None` |

#### Endpoint tests — create

| ID | Test Name | Description |
|----|-----------|-------------|
| T03-U06 | `test_create_empty_deck` | `POST /decks/create` with `{"name": "Test"}` returns 200 + `deck_id` |
| T03-U07 | `test_create_empty_deck_with_description` | `POST /decks/create` with `{"name": "Test", "description": "Desc"}` returns 200 |
| T03-U08 | `test_create_deck_empty_name_rejected` | `POST /decks/create` with `{"name": ""}` returns 422 |
| T03-U09 | `test_import_deck_still_works` | `POST /decks` with `{"name": "Deck", "format": "text", "content": "4 Lightning Bolt"}` still returns 200 (backward compatibility) |

#### Endpoint tests — update

| ID | Test Name | Description |
|----|-----------|-------------|
| T03-U10 | `test_update_deck_name` | `PUT /decks/1` with `{"name": "New Name"}` returns 200, response contains updated name |
| T03-U11 | `test_update_deck_description` | `PUT /decks/1` with `{"description": "New desc"}` returns 200 |
| T03-U12 | `test_update_deck_partial` | `PUT /decks/1` with only `{"name": "X"}` does NOT clear existing description |
| T03-U13 | `test_update_deck_not_found` | `PUT /decks/999` where `repo.get_deck()` returns `None` returns 404 |
| T03-U14 | `test_update_deck_wrong_user` | `PUT /decks/1` where `deck.user_id != request user_id` returns 404 |

---

### T05 — Backend Goldfish simulator (F192)

**New file:** `tests/unit/decks/test_goldfish.py`

All tests for the pure `src/decks/goldfish.py` module. Uses deterministic `random.Random` seed for reproducibility.

#### Helper function tests

| ID | Test Name | Function Under Test | Description |
|----|-----------|-------------------|-------------|
| T05-U01 | `test_is_land_legendary_land` | `_is_land("Legendary Land -- Desert")` | Returns `True` |
| T05-U02 | `test_is_land_creature` | `_is_land("Creature -- Elf Warrior")` | Returns `False` |
| T05-U03 | `test_is_land_none` | `_is_land(None)` | Returns `False` |
| T05-U04 | `test_is_land_basic_land` | `_is_land("Basic Land -- Forest")` | Returns `True` |
| T05-U05 | `test_parse_cmc_generic_plus_pips` | `_parse_cmc_simple("{3}{U}{U}")` | Returns `5` |
| T05-U06 | `test_parse_cmc_x_cost` | `_parse_cmc_simple("{X}{R}")` | Returns `1` (X=0) |
| T05-U07 | `test_parse_cmc_none` | `_parse_cmc_simple(None)` | Returns `0` |
| T05-U08 | `test_parse_cmc_empty` | `_parse_cmc_simple("")` | Returns `0` |
| T05-U09 | `test_parse_cmc_hybrid` | `_parse_cmc_simple("{W/U}{W/U}")` | Returns `2` |
| T05-U10 | `test_parse_cmc_zero` | `_parse_cmc_simple("{0}")` | Returns `0` |

#### Opening hand evaluation tests

| ID | Test Name | Function Under Test | Description |
|----|-----------|-------------------|-------------|
| T05-U11 | `test_evaluate_hand_zero_lands` | `_evaluate_opening_hand(hand)` | Hand with 0 lands returns `0.0` |
| T05-U12 | `test_evaluate_hand_three_lands` | `_evaluate_opening_hand(hand)` | Hand with 3 lands returns `~1.0` |
| T05-U13 | `test_evaluate_hand_six_lands` | `_evaluate_opening_hand(hand)` | Hand with 6 lands returns `~0.1` |
| T05-U14 | `test_evaluate_hand_two_lands_with_cheap_spell` | `_evaluate_opening_hand(hand)` | Hand with 2 lands + CMC<=2 spell returns `1.0` (0.9 base + 0.1 bonus, capped) |

#### Full simulation tests

| ID | Test Name | Function Under Test | Description |
|----|-----------|-------------------|-------------|
| T05-U15 | `test_goldfish_all_lands` | `simulate_goldfish(all_land_cards)` | `mana_flood_rate == 1.0`, `avg_spells_cast_by_turn` all zeros |
| T05-U16 | `test_goldfish_no_lands` | `simulate_goldfish(no_land_cards)` | `mana_screw_rate == 1.0`, `avg_mana_by_turn` all zeros |
| T05-U17 | `test_goldfish_sample_hands_count` | `simulate_goldfish(normal_deck)` | `len(result.sample_hands) == 3` |
| T05-U18 | `test_goldfish_deterministic_rng` | `simulate_goldfish(deck, rng=Random(42))` | Two calls with same seed produce identical results |
| T05-U19 | `test_goldfish_normal_deck_reasonable_rates` | `simulate_goldfish(normal_deck)` | `screw_rate < 0.5` and `flood_rate < 0.5` for a balanced 60-card deck |
| T05-U20 | `test_goldfish_mana_monotonic` | `simulate_goldfish(normal_deck)` | `avg_mana_by_turn` is monotonically non-decreasing |
| T05-U21 | `test_goldfish_small_deck` | `simulate_goldfish(5_card_deck)` | Handles deck smaller than 7 cards: draws `min(7, deck_size)` for opening hand |
| T05-U22 | `test_goldfish_total_simulations` | `simulate_goldfish(deck, num_simulations=50)` | `result.total_simulations == 50` |
| T05-U23 | `test_goldfish_total_turns` | `simulate_goldfish(deck, turns=5)` | `result.total_turns == 5` and `len(avg_mana_by_turn) == 5` |

---

## 5. Integration Tests

### T03 — Repository integration (F191)

**File:** `tests/unit/api/test_deck_endpoints.py` (or new `tests/integration/test_deck_repository.py`)

| ID | Test Name | Description |
|----|-----------|-------------|
| T03-I01 | `test_repo_update_deck_name` | Call `repo.update_deck(deck_id, name="New")` on a created deck, verify `deck.name == "New"` |
| T03-I02 | `test_repo_update_deck_description_only` | Call `repo.update_deck(deck_id, description="Desc")`, verify name unchanged |
| T03-I03 | `test_repo_update_deck_nonexistent` | Call `repo.update_deck(9999)` returns `None` |

### T05 — Goldfish endpoint integration (F192)

**File:** `tests/unit/api/test_deck_endpoints.py` (extend with `TestGoldfishDeck` class)

Uses existing `_make_app()` pattern with mocked `Repository`.

| ID | Test Name | Description |
|----|-----------|-------------|
| T05-I01 | `test_goldfish_endpoint_200` | `POST /decks/1/goldfish` with valid deck returns 200 + `GoldfishResponse` with all fields |
| T05-I02 | `test_goldfish_nonexistent_deck` | `POST /decks/999/goldfish` where `repo.get_deck()` returns `None` returns 404 |
| T05-I03 | `test_goldfish_wrong_user` | `POST /decks/1/goldfish` where `deck.user_id != auth user` returns 404 |
| T05-I04 | `test_goldfish_empty_deck` | `POST /decks/1/goldfish` where deck has 0 cards returns 400 with error message "Deck has no cards to simulate" |
| T05-I05 | `test_goldfish_query_params` | `POST /decks/1/goldfish?num_simulations=10&turns=5` returns result with `total_simulations=10`, `total_turns=5` |

---

## 6. Frontend Tests

### T01 — Build & import verification (F189)

**No test file needed.** Verification is done via:

| ID | Check | How |
|----|-------|-----|
| T01-F01 | `npm run build` succeeds | CI pipeline |
| T01-F02 | `npm test` passes with 0 failures | CI pipeline |
| T01-F03 | No dangling imports of deleted modules | `grep -rn "DeckBuildWizard\|CommanderSearch\|DeckBuildModeChooser\|DeckSuggestionPanel\|SuggestionRequestForm\|SuggestionRequestList\|SuggestionResultView\|deckSuggestions\|generateDeck\|searchCommanders" frontend/src/ --include="*.ts" --include="*.tsx"` returns 0 results |
| T01-F04 | `DeckGenerateParams`, `GeneratedCard`, `DeckGenerateResult`, `CommanderSearchResult` removed from `frontend/src/types/api.ts` | grep verification |

### T02 — Navigation tests (F190)

**File:** Update existing layout/nav tests or add to `frontend/src/components/__tests__/Layout.test.tsx`

| ID | Test Name | Description |
|----|-----------|-------------|
| T02-F01 | `test_decks_in_primary_nav` | Assert `PRIMARY_NAV_ITEMS` contains entries with `to: "/decks"` and `to: "/decks/ranking"` |
| T02-F02 | `test_decks_not_in_beta_nav` | Assert `BETA_NAV_ITEMS` does NOT contain entries with `to: "/decks"`, `/decks/ranking`, `/decks/build`, `/decks/evaluate` |
| T02-F03 | `test_deck_routes_no_beta_wrapper` | In `App.tsx`, deck routes (`/decks`, `/decks/ranking`, `/decks/:id`) render without `<BetaRoute>` wrapper |

### T04 — DeckCreateModal (F191)

**New file:** `frontend/src/components/__tests__/DeckCreateModal.test.tsx`

| ID | Test Name | Description |
|----|-----------|-------------|
| T04-F01 | `renders form fields and buttons` | Modal contains name input, description textarea, Cancel button, Create button |
| T04-F02 | `disables Create button when name is empty` | Create button has `disabled` attribute when name input is empty |
| T04-F03 | `calls onCreated with deck ID on success` | Mock `createDeck()` to return `{ deck_id: 42 }`, submit form, verify `onCreated(42)` called |
| T04-F04 | `shows error message on API failure` | Mock `createDeck()` to return error, verify error text rendered |

### T04 — DeckList modifications (F191)

**New file:** `frontend/src/pages/__tests__/DeckList.test.tsx` (or extend if exists)

| ID | Test Name | Description |
|----|-----------|-------------|
| T04-F05 | `renders New Deck button` | Assert button with text matching `t("decks.newDeck")` / `data-testid="new-deck-btn"` is present |
| T04-F06 | `clicking New Deck opens DeckCreateModal` | Click "New Deck" button, assert `DeckCreateModal` is rendered |

### T04 — DeckView inline edit (F191)

**New file:** `frontend/src/pages/__tests__/DeckView.test.tsx` (or extend if exists)

| ID | Test Name | Description |
|----|-----------|-------------|
| T04-F07 | `clicking deck name activates edit mode` | Click on deck name element, assert input field appears with current name value |
| T04-F08 | `pressing Enter saves name and exits edit mode` | Type new name, press Enter, verify `updateDeck()` called with `{ name: "new name" }` |
| T04-F09 | `pressing Escape reverts name and exits edit mode` | Type new name, press Escape, verify original name displayed, `updateDeck()` NOT called |
| T04-F10 | `inline description edit works similarly` | Click description area, verify textarea appears, Enter saves, Escape reverts |

### T04 — API function tests (F191)

**New file:** `frontend/src/api/__tests__/decks.test.ts` (extend if exists)

| ID | Test Name | Description |
|----|-----------|-------------|
| T04-F11 | `createDeck sends correct payload` | Mock fetch, call `createDeck("My Deck", "desc")`, verify POST to `/api/v1/decks/create` with `{ name: "My Deck", description: "desc" }` |
| T04-F12 | `updateDeck sends correct payload` | Mock fetch, call `updateDeck(1, { name: "X" })`, verify PUT to `/api/v1/decks/1` with `{ name: "X" }` |

### T06 — GoldfishPanel (F192)

**New file:** `frontend/src/components/__tests__/GoldfishPanel.test.tsx`

Mock `fetchGoldfish()` to return controlled data for all rendering tests.

| ID | Test Name | Description |
|----|-----------|-------------|
| T06-F01 | `renders loading skeleton initially` | On mount, assert loading skeleton/spinner is visible before data resolves |
| T06-F02 | `renders error state with retry button on API failure` | Mock `fetchGoldfish()` to reject, assert `ErrorBanner` or error message rendered with retry button |
| T06-F03 | `renders opening hand quality gauge` | With mock data `{ opening_hand_quality: 0.85 }`, assert "85%" or equivalent rendered |
| T06-F04 | `renders mana by turn chart` | Assert `<ResponsiveContainer>` + `<LineChart>` rendered with correct data-point count matching `avg_mana_by_turn.length` |
| T06-F05 | `renders screw/flood rate badges` | With mock data `{ mana_screw_rate: 0.15, mana_flood_rate: 0.25 }`, assert both percentage values displayed |
| T06-F06 | `renders 3 sample hands` | Assert 3 sample hand sections rendered (best, median, worst) with card names from mock data |
| T06-F07 | `Simulate Again button triggers re-fetch` | Click "Simulate Again", verify `fetchGoldfish()` called a second time |
| T06-F08 | `shows loading state during re-simulation` | Click "Simulate Again", assert loading indicator visible while promise is pending |

### T06 — DeckView tab addition (F192)

**File:** `frontend/src/pages/__tests__/DeckView.test.tsx` (extend)

| ID | Test Name | Description |
|----|-----------|-------------|
| T06-F09 | `renders Goldfish tab button` | Assert third tab button with text matching `t("decks.goldfishTab")` is present |
| T06-F10 | `clicking Goldfish tab shows GoldfishPanel` | Click Goldfish tab, assert `GoldfishPanel` component is rendered |

### T06 — API function test (F192)

**File:** `frontend/src/api/__tests__/decks.test.ts` (extend)

| ID | Test Name | Description |
|----|-----------|-------------|
| T06-F11 | `fetchGoldfish sends correct request` | Mock fetch, call `fetchGoldfish(1, 50, 5)`, verify POST to `/api/v1/decks/1/goldfish` with query params `num_simulations=50&turns=5` |

---

## 7. Manual Verification

### Wave 0 — Cleanup (T01 + T02)

#### T01 — DeckBuildWizard removal

| ID | Step | Expected Result |
|----|------|----------------|
| T01-M01 | Navigate to `/decks/build` | 404 page or redirect (route removed) |
| T01-M02 | Navigate to `/decks` | DeckList page loads correctly with import button |
| T01-M03 | Navigate to `/decks/:id` for existing deck | DeckView renders with Cards + Evaluation tabs |
| T01-M04 | Navigate to `/decks/ranking` | TopDecksPage loads correctly |
| T01-M05 | Open sidebar nav | No "Build Deck" or "Deck Evaluator" entries visible in Beta section |
| T01-M06 | Import a deck via DeckImportModal on `/decks` | Import flow works end-to-end (not broken by removal) |

#### T02 — BetaRoute removal from decks

| ID | Step | Expected Result |
|----|------|----------------|
| T02-M01 | Open sidebar nav (authenticated user) | "My Decks" and "Top Decks" appear in primary nav section (not under Beta) |
| T02-M02 | Verify nav ordering | Deck entries appear after "Alerts", before "Settings": dashboard, myCollection, importPurchases, wishlist, exploreCards, alerts, **myDecks, topDecks**, settings, admin |
| T02-M03 | Click "My Decks" in primary nav | Navigates to `/decks` correctly |
| T02-M04 | Click "Top Decks" in primary nav | Navigates to `/decks/ranking` correctly |
| T02-M05 | Log out, check sidebar | Deck nav items are NOT visible to unauthenticated users (requiresAuth: true) |
| T02-M06 | Check Beta nav section | Other Beta items (market, trending, marketplace, trade-matches, achievements, evaluations, banlist, news) remain under Beta section |
| T02-M07 | Access `/decks` directly while unauthenticated | Redirected to login (ProtectedRoute guard) |

### Wave 1 — New Features (T03 + T04 + T05 + T06)

#### T04 — Deck CRUD frontend

| ID | Step | Expected Result |
|----|------|----------------|
| T04-M01 | On `/decks`, click "New Deck" button | DeckCreateModal opens with name input + description textarea |
| T04-M02 | Leave name empty, try to click Create | Create button is disabled |
| T04-M03 | Enter "Test Deck" as name, click Create | Modal closes, navigates to `/decks/<new_id>` |
| T04-M04 | On new deck page, verify empty deck | Deck shows name "Test Deck", 0 cards |
| T04-M05 | Click on deck name | Input field appears with "Test Deck" pre-filled |
| T04-M06 | Change name to "Renamed Deck", press Enter | Name updates inline, page shows "Renamed Deck" |
| T04-M07 | Reload page | Name persists as "Renamed Deck" |
| T04-M08 | Click on description area (or "Add description" placeholder) | Textarea appears |
| T04-M09 | Type "My deck description", press Enter or click away | Description saves and displays |
| T04-M10 | Start editing name, press Escape | Reverts to previous name without API call |
| T04-M11 | Import a deck via existing DeckImportModal | Import flow still works (backward compatibility with `POST /decks`) |

#### T05 + T06 — Goldfish simulator

| ID | Step | Expected Result |
|----|------|----------------|
| T06-M01 | Navigate to `/decks/:id` for a deck with cards | DeckView loads with 3 tabs: Cards, Evaluation, Goldfish |
| T06-M02 | Click "Goldfish" tab | GoldfishPanel loads, shows loading skeleton, then results |
| T06-M03 | Verify Opening Hand Quality section | Circular gauge or progress bar shows percentage (0-100%) |
| T06-M04 | Verify Mana Curve chart | LineChart with X=turn number, Y=avg mana, tooltip on hover |
| T06-M05 | Verify Spells Cast chart | Bar/line chart with X=turn, Y=avg spells cast per turn |
| T06-M06 | Verify Screw/Flood badges | Two percentage badges visible; red-tinted if > 20% |
| T06-M07 | Verify Sample Hands section | 3 hand groups (Best, Median, Worst) with card names + quality score + land count |
| T06-M08 | Click "Simulate Again" | Loading spinner appears, then new results render (values may differ) |
| T06-M09 | Switch to dark mode | Charts render with dark-mode-compatible colors, no invisible text/lines |
| T06-M10 | Resize to mobile viewport (< 640px) | Charts stack vertically, sample hands wrap properly |
| T06-M11 | Navigate to deck with 0 cards, click Goldfish tab | Error message displayed (backend returns 400) |
| T06-M12 | Switch between Cards/Evaluation/Goldfish tabs | Each tab renders correctly; Goldfish does NOT re-fetch if data already loaded |
| T06-M13 | Verify "Based on N simulations" text | Footer text shows correct simulation count |

### Cross-cutting verification

| ID | Step | Expected Result |
|----|------|----------------|
| CC-M01 | Run `npm run build` | Build succeeds with 0 errors, 0 TypeScript errors |
| CC-M02 | Run `npm test` | All frontend tests pass |
| CC-M03 | Run `pytest tests/ --cov=src` | All backend tests pass, no regressions |
| CC-M04 | Run `ruff check src/` | No lint errors in new/modified Python files |
| CC-M05 | Verify i18n completeness (en.json + pt-BR.json) | All new keys present in both locale files |
| CC-M06 | Check browser console for errors | No uncaught exceptions or React warnings on any deck page |
