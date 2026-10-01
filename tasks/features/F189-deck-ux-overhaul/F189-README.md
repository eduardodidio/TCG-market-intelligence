# F189+F190+F191+F192 — Deck UX Overhaul Batch

**Status:** completed
**Branch:** homol
**Features:** F189 (remove auto-build), F190 (remove beta), F191 (deck CRUD), F192 (Goldfish simulator)

## Summary

Four features to clean up and enhance the deck experience:

1. **F189** — Remove automatic deck building wizard from frontend (keep backend endpoints)
2. **F190** — Promote deck pages out of BetaRoute into primary navigation
3. **F191** — Add missing CRUD: create empty deck + rename/edit deck
4. **F192** — Goldfish simulator: opening hand quality, mana curve simulation, screw/flood analysis

## Wave Breakdown

### Wave 0 — Cleanup (F189 + F190)

These tasks share `App.tsx` and `Layout.tsx` and MUST run sequentially within the wave.

| Task | Feature | Title | Parallel |
|------|---------|-------|----------|
| T01  | F189    | Remove DeckBuildWizard and related frontend code | no (runs first) |
| T02  | F190    | Remove BetaRoute from decks, move to primary nav  | no (runs after T01) |

### Wave 1 — New Features (F191 + F192)

These tasks are fully independent and can run in true parallel.

| Task | Feature | Title | Parallel |
|------|---------|-------|----------|
| T03  | F191    | Backend: create empty deck + update deck endpoints | yes |
| T04  | F191    | Frontend: new deck modal + inline edit on DeckView  | yes (after T03 if strict, but T04 can mock API) |
| T05  | F192    | Backend: Goldfish simulator service + endpoint       | yes |
| T06  | F192    | Frontend: Goldfish tab on DeckView                   | yes (after T05 if strict, but T06 can mock API) |

**Note on T03/T04 and T05/T06 dependencies:** The frontend tasks (T04, T06) depend on their respective backend tasks (T03, T05) for integration testing. However, both frontend tasks can be developed with mocked API responses and integrated in the same wave. The developer should implement T03 before T04 and T05 before T06 if running truly sequentially, but all four can run in parallel if each frontend task stubs the API calls.

## Dependency Graph

```
Wave 0:  T01 (F189) --> T02 (F190)
                              |
                              v
Wave 1:  T03 (F191-BE)    T05 (F192-BE)
           |                  |
           v                  v
         T04 (F191-FE)    T06 (F192-FE)
```

## Files Affected

### Wave 0
- `frontend/src/App.tsx` — remove DeckBuildWizard route, /decks/evaluate redirect, BetaRoute wrappers, lazy import
- `frontend/src/components/Layout.tsx` — remove buildDeck + deckEvaluator from BETA_NAV_ITEMS, move myDecks + topDecks to PRIMARY_NAV_ITEMS
- `frontend/src/pages/DeckBuildWizard.tsx` — DELETE
- `frontend/src/components/decks/CommanderSearch.tsx` — DELETE
- `frontend/src/components/decks/DeckBuildModeChooser.tsx` — DELETE
- `frontend/src/components/decks/DeckSuggestionPanel.tsx` — DELETE
- `frontend/src/components/decks/SuggestionRequestForm.tsx` — DELETE
- `frontend/src/components/decks/SuggestionRequestList.tsx` — DELETE
- `frontend/src/components/decks/SuggestionResultView.tsx` — DELETE
- `frontend/src/api/decks.ts` — remove generateDeck(), searchCommanders() + unused type imports
- `frontend/src/api/deckSuggestions.ts` — DELETE
- `frontend/src/api/__tests__/deckSuggestions.test.ts` — DELETE
- `frontend/src/types/deckSuggestions.ts` — DELETE
- `frontend/src/types/api.ts` — remove DeckGenerateParams, DeckGenerateResult, GeneratedCard, CommanderSearchResult interfaces
- `frontend/src/pages/__tests__/DeckBuildWizard.test.tsx` — DELETE
- `frontend/src/pages/__tests__/DeckBuildWizard.synergy.test.tsx` — DELETE
- `frontend/src/components/decks/__tests__/CommanderSearch.test.tsx` — DELETE
- `frontend/src/components/decks/__tests__/DeckBuildModeChooser.test.tsx` — DELETE
- `frontend/src/components/decks/__tests__/DeckSuggestionPanel.test.tsx` — DELETE
- `frontend/src/components/decks/__tests__/SuggestionRequestForm.test.tsx` — DELETE
- `frontend/src/components/decks/__tests__/SuggestionRequestList.test.tsx` — DELETE
- `frontend/src/components/decks/__tests__/SuggestionResultView.test.tsx` — DELETE
- `frontend/src/i18n/__tests__/deckSuggestKeys.test.ts` — DELETE (tests i18n keys for removed feature)
- `frontend/src/components/BetaRoute.tsx` — kept (still used by other beta pages)

### Wave 1
- `src/api/routers/decks.py` — new POST (empty create) + PUT endpoint + POST goldfish
- `src/api/schemas/decks.py` — new DeckCreateRequest, DeckUpdateRequest, GoldfishResult schemas
- `src/database/repository.py` — new update_deck() method
- `src/decks/goldfish.py` — NEW file (pure simulator service)
- `frontend/src/pages/DeckList.tsx` — "New Deck" button + DeckCreateModal
- `frontend/src/pages/DeckView.tsx` — inline edit for name/description, new Goldfish tab
- `frontend/src/api/decks.ts` — add createDeck(), updateDeck(), fetchGoldfish()
- `frontend/src/types/api.ts` — add GoldfishResult type
- `frontend/src/components/GoldfishPanel.tsx` — NEW file
- `frontend/src/i18n/locales/en.json` — new i18n keys
- `frontend/src/i18n/locales/pt-BR.json` — new i18n keys

## Risk Assessment

- **Low risk:** All Wave 0 changes are deletions + nav reorganization. No backend changes.
- **Medium risk:** F191 backend changes modify the existing POST /decks endpoint (must remain backward-compatible with the import flow).
- **Low risk:** F192 goldfish service is fully isolated (new file, new endpoint, new tab).
