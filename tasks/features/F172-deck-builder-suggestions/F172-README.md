# F172 — Montar Deck: revisão completa + modo "Sugestão de deck"

**Status:** planned
**Batch:** F171–F179 (parallel). Shared high-conflict files are isolated in Wave 4 (T17, T18).
**Tasks:** 18 across 5 Waves
**Brief (sharded):** `_brief/00-overview.md` … `_brief/05-integration-docs.md`

## Feature goal

Fix the commander search in "Montar deck", which returns nothing today. The main cause is a hard
`card_legalities` filter plus EN-only name matching (see `_brief/01-commander-search-fix.md`). Review the whole
deck-build module (the budget/price wiring is broken and legality blocks generation). Add a second mode, **"Sugestão de deck"**.
The user registers a request (commander + notes, or colors + archetype + notes for 60-card formats). It is persisted in a new
`deck_suggestion_requests` table, and the app answers immediately. A **daily local routine** (`bats/deck-suggestions.bat` →
`process-deck-suggestions`) asks Claude (Claude CLI by default, Anthropic HTTP API opt-in, credentials only from env)
to build the deck while prioritizing the user's collection. It prices the missing cards with our Liga/MYP data
and stores the result, which the user can review and save as a deck.

## Architecture impact

| Layer | Modules |
|---|---|
| Domain / builder | `src/decks/builder.py` (commander search, legality soft-filter, prices, `is_commander_eligible`) |
| Persistence | NEW `src/deck_suggestions/models.py`, `src/deck_suggestions/repository.py` (own table, `checkfirst` create — `models.py` untouched) |
| AI integration | NEW `src/deck_suggestions/prompt.py` (pure), `claude_runner.py` (CLI subprocess / httpx API), `processor.py` |
| API | `src/api/routers/decks.py` + `src/api/schemas/decks.py` (fix); NEW `src/api/routers/deck_suggestions.py`, `src/api/schemas/deck_suggestions.py` |
| CLI / ops | NEW `src/cli/deck_suggestions.py`; `src/cli/main.py` (2-line registration); NEW `bats/deck-suggestions.bat` |
| Frontend | `DeckBuildWizard.tsx` (mode switch via `?mode=`); NEW `components/decks/*`, `api/deckSuggestions.ts`, `types/deckSuggestions.ts` |
| Docs | PRD, ADR, `F172-architecture.mmd`, `F172-journey.mmd`, README |

## Wave manifest

- **Wave 0**: F172-T01
- **Wave 1**: F172-T02, F172-T03, F172-T04, F172-T05, F172-T06, F172-T07
- **Wave 2**: F172-T08, F172-T09, F172-T10, F172-T11, F172-T12, F172-T13
- **Wave 3**: F172-T14, F172-T15, F172-T16
- **Wave 4**: F172-T17, F172-T18

## Tasks and files touched (overlap detection)

| Task | Wave | Type | Depends on | Files touched |
|---|---|---|---|---|
| F172-T01 | 0 | docs/infra | — | `docs/prd/F172-deck-builder-suggestions.md` (new), `docs/adr/00NN-deck-suggestion-queue-claude.md` (new), `src/deck_suggestions/__init__.py` (new), `frontend/src/components/decks/.gitkeep` (new), `tests/unit/deck_suggestions/__init__.py` (new) |
| F172-T02 | 1 | backend | T01 | `src/decks/builder.py`, `src/api/routers/decks.py`, `src/api/schemas/decks.py`, `tests/unit/decks/test_builder.py`, `tests/unit/decks/test_commander_search.py` (new), `tests/unit/api/test_deck_endpoints.py` |
| F172-T03 | 1 | backend | T01 | `src/deck_suggestions/models.py` (new), `src/deck_suggestions/repository.py` (new), `tests/unit/deck_suggestions/test_repository.py` (new) |
| F172-T04 | 1 | backend | T01 | `src/deck_suggestions/prompt.py` (new), `tests/unit/deck_suggestions/test_prompt.py` (new) |
| F172-T05 | 1 | backend | T01 | `src/deck_suggestions/claude_runner.py` (new), `tests/unit/deck_suggestions/test_claude_runner.py` (new) |
| F172-T06 | 1 | frontend | T01 | `frontend/src/components/decks/CommanderSearch.tsx` (new), `frontend/src/components/decks/__tests__/CommanderSearch.test.tsx` (new), `frontend/src/pages/DeckBuildWizard.tsx`, `frontend/src/pages/__tests__/DeckBuildWizard.test.tsx`, `frontend/src/types/api.ts` (1 optional field) |
| F172-T07 | 1 | frontend | T01 | `frontend/src/types/deckSuggestions.ts` (new), `frontend/src/api/deckSuggestions.ts` (new), `frontend/src/api/__tests__/deckSuggestions.test.ts` (new) |
| F172-T08 | 2 | backend | T02, T03 | `src/api/routers/deck_suggestions.py` (new), `src/api/schemas/deck_suggestions.py` (new), `tests/unit/api/test_deck_suggestions_endpoints.py` (new) |
| F172-T09 | 2 | backend | T03, T04, T05 | `src/deck_suggestions/processor.py` (new), `tests/unit/deck_suggestions/test_processor.py` (new) |
| F172-T10 | 2 | frontend | T01 | `frontend/src/components/decks/DeckBuildModeChooser.tsx` (new) + test |
| F172-T11 | 2 | frontend | T06, T07 | `frontend/src/components/decks/SuggestionRequestForm.tsx` (new) + test |
| F172-T12 | 2 | frontend | T07 | `frontend/src/components/decks/SuggestionRequestList.tsx` (new) + test |
| F172-T13 | 2 | frontend | T07 | `frontend/src/components/decks/SuggestionResultView.tsx` (new) + test |
| F172-T14 | 3 | frontend | T06, T10–T13 | `frontend/src/components/decks/DeckSuggestionPanel.tsx` (new) + test, `frontend/src/pages/DeckBuildWizard.tsx`, `frontend/src/pages/__tests__/DeckBuildWizard.test.tsx` |
| F172-T15 | 3 | backend | T09 | `src/cli/deck_suggestions.py` (new), `tests/cli/test_deck_suggestions_cli.py` (new); optionally `src/deck_suggestions/claude_runner.py` + its test (adds `check()`; T05 finished in Wave 1) |
| F172-T16 | 3 | docs | T08, T09 | `docs/diagrams/F172-architecture.mmd` (new), `docs/diagrams/F172-journey.mmd` (new) |
| F172-T17 | 4 | infra | T08, T15 | **shared:** `src/api/app.py`, `src/cli/main.py`, `bats/deck-suggestions.bat` (new), `.env.example`, `README.md`; `tests/unit/api/test_deck_suggestions_wiring.py` (new) |
| F172-T18 | 4 | frontend | T06, T10–T14 | **shared:** `frontend/src/i18n/locales/en.json`, `frontend/src/i18n/locales/pt-BR.json`; `frontend/src/i18n/__tests__/deckSuggestKeys.test.ts` (new) |

Intra-feature sequencing: `DeckBuildWizard.tsx` is edited by T06 (Wave 1) and then by T14 (Wave 3), never in the same wave.
**Not touched:** `frontend/src/App.tsx`, `frontend/src/components/Layout.tsx`, `src/database/models.py`
(the route `/decks/build` already exists, and the mode goes in `?mode=`).

## Global acceptance criteria

- [ ] Commander search finds legendary creatures by EN or PT name, even with an empty `card_legalities` table. Explicitly banned commanders are excluded.
- [ ] The wizard commander search shows loading / empty / error states. It has no stale-response race.
- [ ] Generated decks (manual mode) contain non-land cards when legality data is missing, and the budget limit is enforced with real prices.
- [ ] `/decks/build` asks "Montar meu próprio deck" vs "Sugestão de deck". `?mode=` deep links work.
- [ ] Suggestion requests are persisted (`deck_suggestion_requests`) with status `pending`. `POST` returns 201 at once. The list shows the status.
- [ ] `python -m src.cli.main process-deck-suggestions` processes pending requests via Claude (CLI default, `--provider api` opt-in), prioritizing owned cards. Missing cards carry BRL prices. Failures are stored as `failed` with a message, and transient ones are retried up to 3 attempts.
- [ ] The result view shows owned vs. missing cards and the cost to complete. "Salvar como deck" creates a deck (idempotent).
- [ ] `bats/deck-suggestions.bat` exists. No secret is hardcoded anywhere.
- [ ] `pytest tests/ --cov=src` green, new modules ≥ 90% covered. `cd frontend && npm test` and `npm run build` green. `ruff check src/` clean.
- [ ] PRD, ADR, `docs/diagrams/F172-architecture.mmd`, `docs/diagrams/F172-journey.mmd`, README updated.

## Decisions (confirmed by user on 2026-09-24: `claude -p` default, no `anthropic` SDK)

1. **Anthropic SDK (`anthropic` package): NOT added.** `ClaudeApiRunner` calls the Messages API over the existing
   `httpx` dependency. Adding the SDK would be a new dependency and needs explicit user approval. Only
   `src/deck_suggestions/claude_runner.py` would change.
2. **Default provider = Claude CLI (`claude -p`)**, run locally by the daily .bat and using the user's logged-in Claude Code.
   Switch with `DECK_SUGGEST_PROVIDER=api` + `ANTHROPIC_API_KEY` in `.env`.
3. **Default model** for the API runner: `claude-sonnet-5` (override with `DECK_SUGGEST_MODEL`).
4. **Open-request limit** per user: 5 (pending + processing).
5. **Credits:** requests are free in this version (no `CreditService` deduction). Revisit if costs grow.

## Diagrams

- `docs/diagrams/F172-architecture.mmd` — owner F172-T16
- `docs/diagrams/F172-journey.mmd` — owner F172-T16

## Test impact (existing tests that must be updated)

- `frontend/src/pages/__tests__/DeckBuildWizard.test.tsx` — T06 (search extracted into a component) and T14 (the mode chooser now renders first → tests must use `?mode=manual`).
- `tests/unit/decks/test_builder.py` — T02 (legality soft filter, prices).
- `tests/unit/api/test_deck_endpoints.py` — T02 (`CommanderCandidate.name_pt`, eligibility helper).

## Gitflow

Work on `homol` (or the orchestrator's per-feature worktree branch that merges into `homol`). Never push to `main`.

## ADR number (batch reservation)
This feature's ADR number is **0015**, reserved in `tasks/features/EXECUTION-PLAN-F171-F179.md`. It overrides any "next free number" instruction in the task files.
