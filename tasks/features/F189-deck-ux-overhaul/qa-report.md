# QA Report: F189+F190+F191+F192 -- Deck UX Overhaul Batch

**QA Agent** | **Date:** 2026-10-01 | **Branch:** homol

---

## 1. Build Verification

| Check | Status |
|-------|--------|
| `npm run build` | PASS -- built in 4.32s, 77 PWA precache entries, zero errors |
| Backend tests (`tests/unit/decks/ + test_deck_endpoints.py -k "not evaluate"`) | PASS -- 353 passed, 34 deselected (evaluate excluded as directed) |
| Frontend tests (`npx vitest run`) | PASS -- 2588 passed, 2 failed (pre-existing LegalitySection.test.tsx) |

---

## 2. Test Run Results

### Backend (353 passed)
All deck-related backend tests pass, including:
- `test_goldfish.py` -- 42 tests (unit + integration for goldfish simulator)
- `test_deck_endpoints.py` -- 9 tests for create/update endpoints (4 create, 5 update)
- Pre-existing `TestEvaluateDeck` (3 tests) excluded via `-k "not evaluate"`

### Frontend (2588 passed, 2 pre-existing failures)
- `DeckCreateModal.test.tsx` -- 13/13 passed
- `GoldfishPanel.test.tsx` -- 14/14 passed
- `Layout.test.tsx` -- 35/35 passed (after QA fix, see below)
- `LegalitySection.test.tsx` -- 2 failures (pre-existing, last modified in F87, unrelated to this feature)

### QA Fix Applied: Layout.test.tsx

The developer did not update `Layout.test.tsx` after moving deck nav items from `BETA_NAV_ITEMS` to `PRIMARY_NAV_ITEMS` (F190). Four tests were failing due to hardcoded nav item counts and incorrect beta-collapse assertions.

**Changes made by QA:**
- Line 138: Updated comment and count from 7 to 9 (added My Decks + Top Decks to primary)
- Line 159: Updated comment and count from 19 to 17 (9 primary + 8 beta)
- Lines 185-187: Changed `not.toContain("My Decks")` to `toContain("My Decks")` and `toContain("Top Decks")` since they are now primary nav items visible even when beta is collapsed
- Line 416-417: Updated admin total from 20 to 18 (10 primary + 8 beta)

File: `frontend/tests/components/Layout.test.tsx`

---

## 3. Feature Verification

### F189 -- Removed auto-build

| Check | Status |
|-------|--------|
| `DeckBuildWizard.tsx` does NOT exist | PASS -- confirmed via Glob |
| `/decks/build` route removed from App.tsx | PASS -- no match for `decks/build` or `decks/evaluate` |
| `/decks/evaluate` redirect removed from App.tsx | PASS |
| Layout.tsx has no `buildDeck` or `deckEvaluator` nav items | PASS -- grep returns no matches |
| Backend endpoints preserved (`/decks/generate`, `/decks/commanders`) | PASS -- per tech lead review |
| `DeckGenerateParams`, `DeckGenerateResult`, `GeneratedCard`, `CommanderSearchResult` removed from api.ts | PASS |

### F190 -- Decks out of beta

| Check | Status |
|-------|--------|
| No `BetaRoute` wrapper around deck routes in App.tsx | PASS -- lines 311-339 show bare `<DeckList />`, `<TopDecksPage />`, `<DeckView />` |
| `myDecks` and `topDecks` in PRIMARY_NAV_ITEMS in Layout.tsx | PASS -- positions 7-8 (after alerts, before settings) |
| `BETA_NAV_ITEMS` no longer contains deck items | PASS -- only 8 items remain (Market, Trending, Ban List, Marketplace, Trade Matches, Achievements, Evaluations, News) |
| Deck routes remain inside `<ProtectedRoute>` | PASS |

### F191 -- Deck CRUD

| Check | Status |
|-------|--------|
| `POST /decks/create` endpoint exists in decks.py | PASS -- line 105 |
| `PUT /decks/{deck_id}` endpoint exists in decks.py | PASS -- line 814 |
| `DeckCreateModal.tsx` exists | PASS -- `frontend/src/components/DeckCreateModal.tsx` |
| `DeckCreateModal.test.tsx` exists with tests | PASS -- 13 tests, all passing |
| DeckView.tsx has inline edit capability | PASS -- `editName`, `setEditName`, `editDescription` state variables confirmed |
| `createDeck()` in api/decks.ts | PASS -- line 34 |
| `updateDeck()` in api/decks.ts | PASS -- line 44 |
| `DeckCreateResult` interface in api.ts | PASS -- line 325 |

### F192 -- Goldfish

| Check | Status |
|-------|--------|
| `src/decks/goldfish.py` exists | PASS -- confirmed via Glob |
| goldfish.py is pure (no DB/API imports) | PASS -- only imports: `__future__`, `random`, `re`, `dataclasses` |
| `POST /decks/{deck_id}/goldfish` endpoint exists | PASS -- line 678 in decks.py |
| `GoldfishPanel.tsx` exists | PASS -- `frontend/src/components/GoldfishPanel.tsx` |
| `GoldfishPanel.test.tsx` exists with tests | PASS -- 14 tests, all passing |
| DeckView.tsx has 3 tabs (cards, evaluation, goldfish) | PASS -- `useState<"cards" \| "evaluation" \| "goldfish">` at line 34 |
| `GoldfishResult` and `GoldfishSampleHand` types in api.ts | PASS -- lines 691, 697 |
| `fetchGoldfish()` in api/decks.ts | PASS -- line 64 |

---

## 4. Dead Code Scan Results

| Pattern | Files Found | Status |
|---------|-------------|--------|
| `DeckBuildWizard` in .ts/.tsx | 0 | CLEAN |
| `CommanderSearch` in .ts/.tsx | 0 | CLEAN |
| `DeckBuildModeChooser` in .ts/.tsx | 0 | CLEAN |
| `DeckSuggestionPanel` in .ts/.tsx | 0 | CLEAN |
| `SuggestionRequestForm` in .ts/.tsx | 0 | CLEAN |
| `SuggestionRequestList` in .ts/.tsx | 0 | CLEAN |
| `SuggestionResultView` in .ts/.tsx | 0 | CLEAN |
| `deckSuggestions` imports in .ts/.tsx | 0 | CLEAN |
| `generateDeck` in frontend .ts/.tsx | 0 | CLEAN |
| `searchCommanders` in frontend .ts/.tsx | 0 | CLEAN |

**Non-blocking:** Orphaned `deckSuggestions` i18n keys remain in `en.json` line 580 and `pt-BR.json` line 580. These are dead data (no code references them) but cause no harm. Cleanup recommended in a future housekeeping pass.

---

## 5. Test Gaps Identified

| Priority | Gap | Description |
|----------|-----|-------------|
| **P1 (fixed)** | Layout.test.tsx nav counts | Tests had hardcoded counts that were not updated after F190. **Fixed by QA in this report.** |
| P2 | DeckView tab URL persistence | No test verifies that `?tab=goldfish` in the URL correctly initializes the active tab on mount |
| P2 | DeckView inline edit error rollback | No test verifies that the optimistic UI correctly reverts the name/description when the API call fails |
| P3 | Goldfish empty deck UI | No frontend test for the empty-deck error state (backend returns 400, but GoldfishPanel error handling is only tested for generic fetch failure) |
| P3 | DeckList "New Deck" button in empty state | The DeckList empty state includes a "New Deck" action per tech lead, but no specific test targets the empty-state CTA |
| P3 | Unauthenticated deck nav assertion comment | Line 217 still reads "Auth-required beta items should be hidden" but decks are now primary items. Cosmetic. |

---

## 6. Issues Found

| ID | Severity | Feature | Description | Resolution |
|----|----------|---------|-------------|------------|
| Q1 | **Blocking** | F190 | Layout.test.tsx had 4 failing tests due to nav item count changes | **Fixed by QA** -- updated counts and assertions in Layout.test.tsx |
| Q2 | Non-blocking | F189 | Orphaned `deckSuggestions` i18n keys in en.json and pt-BR.json | Cleanup in future pass |
| Q3 | Non-blocking | F191 | PUT endpoint response duplicates GET response builder (~50 lines) | Refactor in future pass |
| Q4 | Non-blocking | F192 | `fetchGoldfish` uses string concatenation for query params | Minor style inconsistency |

---

## 7. Overall Verdict: PASS

All four features (F189, F190, F191, F192) are correctly implemented. The single blocking issue (Layout test failures from F190) was identified and fixed during QA. After the fix:

- **Build:** Clean (4.32s)
- **Backend tests:** 353 passed (deck-related)
- **Frontend tests:** 2588 passed, 2 pre-existing failures (unrelated LegalitySection)
- **Dead code:** Zero references to deleted modules
- **New test coverage:** 93 tests across 6 test files (13 DeckCreateModal + 14 GoldfishPanel + 10 DeckViewInlineEdit + 5 DeckList + 42 goldfish unit + 9 endpoint)
- **Feature requirements:** All checklist items verified PASS
