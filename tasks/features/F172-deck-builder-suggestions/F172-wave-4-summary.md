# F172 — Wave 4 summary

**Status:** completed
**Tasks:** F172-T17, F172-T18
**Generated:** 2026-09-24T23:20:00Z

## Files touched
- `src/api/app.py` (T17: registered `deck_suggestions_router` under `/api/v1` next to `decks_router`)
- `src/cli/main.py` (T17: registered `process-deck-suggestions` command)
- `bats/deck-suggestions.bat` (T17: new CRLF .bat mirroring `process-queue.bat`, staged with `git add -f`)
- `.env.example` (T17: appended `DECK_SUGGEST_*` / `ANTHROPIC_API_KEY` commented block)
- `README.md` (T17: added "Shipped" note for F172, endpoints, command, .bat, env vars, CLI-default decision)
- `tests/unit/api/test_deck_suggestions_wiring.py` (T17: new — asserts 5 `/api/v1/deck-suggestions` routes via `app.openapi()["paths"]`, `process-deck-suggestions` registered in `cli.commands`, and that `/api/v1/decks/{deck_id}` + `/api/v1/decks/ranking` still resolve)
- `frontend/src/i18n/locales/en.json`, `frontend/src/i18n/locales/pt-BR.json` (T18: added sibling objects `deckBuild`, `deckSuggest`, and `deckSuggestions` next to the existing `deckBuilder`, which was left untouched)
- `frontend/src/i18n/__tests__/deckSuggestKeys.test.ts` (T18: new — key parity, used-key coverage, nested keys, no empty values, placeholder parity, `deckBuilder` still present)

## Decisions
- T18 discovered `SuggestionRequestList.tsx` (T12) actually uses the plural namespace `deckSuggestions.list.*` / `deckSuggestions.status.*` instead of the planned `deckSuggest.list.*` / `.status.*`. T18 added keys under both the planned and the actually-used namespace rather than editing T12's component; flagged for TechLead to decide whether to rename.
- T17 confirmed via a clean `git worktree` diff that the 3 `test_error_codes.py` failures and the ~109 pre-existing backend failures are unrelated to Wave 4 (caused by a gitignored `frontend/dist/` toggling the SPA catch-all route, and by already-broken liga/exchange-rate/coverage tests respectively).

## Notes for next Wave
- No Wave 5 planned — this is the last wave. Handoff is to TechLead review: verify the `deckSuggestions.*` vs `deckSuggest.*` namespace split in i18n (T18 note above) and confirm AC6/AC8/AC9/AC10 (T17) and AC2/AC4/AC9 (T18) against the full test run before approving.
- Working tree still has these Wave 4 files as staged/unstaged changes (not yet committed) as of this summary; commit before handoff if the orchestrator expects a `F172 Wave 4` commit like prior waves (`4634c7c`, `b97b834`, `4d2c38d`, `9dc7530`).

DIDIO_DONE: techlead wrote F172-wave-4-summary.md
