# F189-T01 — Remove DeckBuildWizard and related frontend code

**Feature:** F189
**Wave:** 0
**Status:** planned
**Parallel:** no (runs first in Wave 0; T02 depends on this completing)

## User Story

As a user, I want the deck wizard to be removed because it generated low-quality decks, so the UI only shows the useful deck features (import, view, evaluate, rank).

## Dev Notes

### Files to DELETE (components + pages)
- `frontend/src/pages/DeckBuildWizard.tsx` (745 lines)
- `frontend/src/components/decks/CommanderSearch.tsx`
- `frontend/src/components/decks/DeckBuildModeChooser.tsx`
- `frontend/src/components/decks/DeckSuggestionPanel.tsx`
- `frontend/src/components/decks/SuggestionRequestForm.tsx`
- `frontend/src/components/decks/SuggestionRequestList.tsx`
- `frontend/src/components/decks/SuggestionResultView.tsx`

### Files to DELETE (API + types)
- `frontend/src/api/deckSuggestions.ts`
- `frontend/src/types/deckSuggestions.ts`

### Files to DELETE (tests)
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

### Files to MODIFY

**`frontend/src/App.tsx`**
- Remove lazy import for DeckBuildWizard (lines 43-46)
- Remove the `/decks/build` route block (lines 340-351)
- Remove the `/decks/evaluate` redirect route (lines 352-355)
- Keep all other deck routes (/decks, /decks/ranking, /decks/:id)

**`frontend/src/components/Layout.tsx`**
- Remove from BETA_NAV_ITEMS (lines 73-86):
  - `{ to: "/decks/build", labelKey: "nav.buildDeck", ... }` (line 79)
  - `{ to: "/decks/evaluate", labelKey: "nav.deckEvaluator", ... }` (line 80)
- Keep the myDecks and topDecks entries (they move to PRIMARY in T02)

**`frontend/src/api/decks.ts`**
- Remove `generateDeck()` function (lines 48-54)
- Remove `searchCommanders()` function (lines 56-64)
- Remove unused type imports from line 1: `CommanderSearchResult`, `DeckGenerateParams`, `DeckGenerateResult`
- Keep: `fetchDecks`, `fetchDeck`, `importDeck`, `deleteDeck`, `fetchDeckEvaluation`

**`frontend/src/types/api.ts`**
- Remove `DeckGenerateParams` interface (lines 685-695)
- Remove `GeneratedCard` interface (lines 697-710)
- Remove `DeckGenerateResult` interface (lines 712-726)
- Remove `CommanderSearchResult` interface (lines 728-739)
- Keep all other types

### Key constraints
- Backend endpoints (`/decks/generate`, `/decks/commanders`, deck-suggestions) are NOT removed. Only frontend consumers are deleted.
- BetaRoute.tsx is NOT deleted (still used by other beta pages like marketplace, trade-matches, etc.)
- DeckEvaluationPanel.tsx is NOT deleted (still used as tab on DeckView)
- DeckImportModal.tsx is NOT deleted (still used on DeckList)

### Edge cases
- Verify no other files import from deleted modules. Grep for all deleted component/function names before finalizing.
- The `/decks/evaluate` redirect to `/decks?evaluate=true` can be safely removed since the evaluate tab is accessed from DeckView directly.

## Testing

- [ ] `npm run build` succeeds with no import errors after deletions
- [ ] `npm test` passes (all tests referencing deleted components are also deleted)
- [ ] Grep confirms no remaining imports of: DeckBuildWizard, CommanderSearch, DeckBuildModeChooser, DeckSuggestionPanel, SuggestionRequestForm, SuggestionRequestList, SuggestionResultView, deckSuggestions, generateDeck, searchCommanders
- [ ] Manual: navigating to /decks/build shows 404 or redirects (route removed)
- [ ] Manual: /decks page still loads correctly
- [ ] Manual: /decks/:id page still shows Cards + Evaluation tabs
- [ ] Manual: /decks/ranking page still works
