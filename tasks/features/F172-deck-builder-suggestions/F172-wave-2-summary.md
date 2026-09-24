# F172 — Wave 2 summary

**Status:** completed (uncommitted — awaiting Wave commit)
**Tasks:** F172-T08, F172-T09, F172-T10, F172-T11, F172-T12, F172-T13
**Generated:** 2026-09-24T19:00:00Z

## Files touched
- `src/api/routers/deck_suggestions.py`, `src/api/schemas/deck_suggestions.py` (T08: CRUD + save-as-deck endpoints)
- `tests/unit/api/test_deck_suggestions_endpoints.py` (T08: coverage 100%)
- `src/deck_suggestions/processor.py` (T09: Claude runner orchestration, owned-card matching, pricing, retry to 3 attempts)
- `tests/unit/deck_suggestions/test_processor.py` (T09)
- `frontend/src/components/decks/DeckBuildModeChooser.tsx` + test (T10 — files present but task header still says `Status: planned`, not updated by developer)
- `frontend/src/components/decks/SuggestionRequestForm.tsx` + test (T11)
- `frontend/src/components/decks/SuggestionRequestList.tsx` + test (T12)
- `frontend/src/components/decks/SuggestionResultView.tsx` + test (T13)

## Decisions
- T08: brief-defined validation errors (format/commander/colors/archetype/`?status=`) return 400; pydantic/FastAPI range errors return 422. Save-as-deck is idempotent per the AC (409 on unreadable/non-`done` result, dedupes commander from `cards`).
- T09: `load_owned_cards` returns an `OwnedCollection` (linked/unlinked/card_ids) instead of a plain list so `resolve_cards` can prefer owned printings; unlinked (unknown-color) collection rows only enter the prompt for 3+ color requests. DFC name matching works both directions (front-only ↔ `Front // Back`).
- T11/T12/T13: locale JSON (`en.json`/`pt-BR.json`) intentionally NOT touched by any Wave 2 task — shared file reserved for Wave 4 (T18) to avoid cross-task stomping. All three use `deckSuggest*.` key namespaces with English `defaultValue` fallbacks so untranslated UI still renders correctly.
- T12: delete confirmation uses `window.confirm` (not `GauchoDialog`), by explicit dev-note choice.

## Notes for next Wave
- T10's task file still shows `Status: planned` despite the component + test existing on disk — Wave 3 (T14, which wires `DeckBuildModeChooser` into the wizard) should verify T10 is actually complete/correct before depending on it.
- Frontend suites have ~17 pre-existing failures unrelated to F172 (Layout, OfflineBanner, TreasureModal, UpdatePrompt, DeckList, DeckView, Login, MyTrades) that also fail in isolation — not introduced by Wave 2; targeted new-file tests pass and `npm run build` is green.
- All Wave 2 work is currently uncommitted in the worktree (only Wave 0 and Wave 1 have commits: `9dc7530`, `4d2c38d`) — commit before starting Wave 3.
- `SuggestionResultView` expects to be remounted via `key={suggestion.id}` by its parent (T14) so its internal `deckName` input resets on selection change.
