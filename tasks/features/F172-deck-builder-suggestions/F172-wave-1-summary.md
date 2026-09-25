# F172 — Wave 1 summary

**Status:** completed
**Tasks:** F172-T02, F172-T03, F172-T04, F172-T05, F172-T06, F172-T07
**Generated:** 2026-09-24T21:00:00Z

## Files touched
- `src/decks/builder.py` (T02: soft legality filter, PT names, dedupe, real prices in `generate_deck`, `is_commander_eligible`)
- `src/api/routers/decks.py`, `src/api/schemas/decks.py` (T02: `search_commanders`/`generate_deck_endpoint` updated, `CommanderCandidate` gains `name_pt`)
- `tests/unit/decks/test_builder.py`, `tests/unit/decks/test_commander_search.py` (new), `tests/unit/api/test_deck_endpoints.py` (T02)
- `src/deck_suggestions/models.py`, `src/deck_suggestions/repository.py` (new — T03: `deck_suggestion_requests` table, checkfirst create, atomic claim, `colors_to_str`/`colors_from_str`)
- `tests/unit/deck_suggestions/test_repository.py` (new, T03)
- `src/deck_suggestions/prompt.py` (new — T04: pure prompt builder + response parser, notes sanitized in `<observacoes_do_usuario>`)
- `tests/unit/deck_suggestions/test_prompt.py` (new, T04)
- `src/deck_suggestions/claude_runner.py` (new — T05: `ClaudeCliRunner`, `ClaudeApiRunner` over `httpx`, `get_runner()`, no `anthropic` SDK)
- `tests/unit/deck_suggestions/test_claude_runner.py` (new, T05)
- `frontend/src/components/decks/CommanderSearch.tsx` (new, T06: extracted search with loading/empty/error states + stale-response guard)
- `frontend/src/components/decks/__tests__/CommanderSearch.test.tsx` (new, T06)
- `frontend/src/pages/DeckBuildWizard.tsx`, `frontend/src/pages/__tests__/DeckBuildWizard.test.tsx` (T06: wizard now uses `CommanderSearch`, Pioneer/Vintage formats added)
- `frontend/src/types/api.ts` (T06: `name_pt` optional field)
- `frontend/src/types/deckSuggestions.ts`, `frontend/src/api/deckSuggestions.ts` (new, T07: typed client for `/api/v1/deck-suggestions`)
- `frontend/src/api/__tests__/deckSuggestions.test.ts` (new, T07)

## Decisions
- _none_ (wave followed brief/task-file spec directly; no deviations recorded in task files)

## Notes for next Wave
- Wave 1 changes are all uncommitted in the worktree (no `F172 Wave 1` commit yet) — Wave 2 tasks should build on the working tree as-is, not assume a commit boundary.
- `CommanderCandidate.name_pt` and `is_commander_eligible` (T02) are now available for T08/T09 backend work; `deckSuggestions.ts` client (T07) is ready for T11–T13 frontend components to consume.
