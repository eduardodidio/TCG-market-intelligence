# F172 — Wave 3 summary

**Status:** completed
**Tasks:** F172-T14, F172-T15, F172-T16
**Generated:** 2026-09-24T22:20:00Z

## Files touched
- `frontend/src/pages/DeckBuildWizard.tsx` (T14: mode routing — chooser / `ManualDeckWizard` / `DeckSuggestionPanel` via `?mode=`)
- `frontend/src/pages/__tests__/DeckBuildWizard.test.tsx` (T14: updated for mode routing, uses `?mode=manual`)
- `frontend/src/components/decks/DeckSuggestionPanel.tsx` (new, T14: composes form + list + result view)
- `frontend/src/components/decks/__tests__/DeckSuggestionPanel.test.tsx` (new, T14)
- `src/cli/deck_suggestions.py` (new, T15: `process-deck-suggestions` click command; registration deferred to T17)
- `tests/cli/test_deck_suggestions_cli.py` (new, T15: 17 tests, 100% coverage of the module)
- `src/deck_suggestions/claude_runner.py` (T15: added `check()` to `ClaudeCliRunner` and `ClaudeApiRunner`, called from `run()` and from the CLI pre-flight)
- `tests/unit/deck_suggestions/test_claude_runner.py` (T15: `TestRunnerCheck` added)
- `docs/diagrams/F172-architecture.mmd` (new, T16)
- `docs/diagrams/F172-journey.mmd` (new, T16)

## Decisions
- `check()` was added to both Claude runners (CLI/API) so `src/cli/deck_suggestions.py` can fail fast with exit 2 before touching the DB/repository, instead of failing mid-batch.
- Manual wizard was extracted into a local `ManualDeckWizard` component inside `DeckBuildWizard.tsx` rather than a new file, keeping `DeckBuildWizard` itself as the thin mode router (chooser vs. manual vs. suggestion).

## Notes for next Wave
- Wave 4 (T17) must add `bats/deck-suggestions.bat` — T16's architecture diagram already references it as the entry point, and T15 left CLI registration in `src/cli/main.py` for T17.
- New testids from T14 for T18 i18n/QA passes: `deck-suggestion-panel`, `suggestion-panel-placeholder`, `suggestion-detail-loading`, `suggestion-result-area`, `deck-build-manual`; new i18n keys `deckSuggest.panel.selectPrompt` and `deckSuggest.mode.switchBack` currently only have `defaultValue` fallbacks — locale JSON updates are still owned by T18.
- All Wave 3 work is uncommitted on disk (last commit is "F172 Wave 2"); T17/T18 will need this committed or included together.
