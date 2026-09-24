# F172 — Brief overview (shared context)

## Problem

In "Montar deck" (`/decks/build`, `frontend/src/pages/DeckBuildWizard.tsx`), searching
for a COMMANDER returns no cards. The Architect traced the root cause (see
`01-commander-search-fix.md`). Besides fixing it, the user wants to pick one of two
modes before starting: **"Montar meu próprio deck"** (the fixed wizard) or
**"Sugestão de deck"**. Suggestion mode saves the REQUEST to a new table and returns
right away with "pedido registrado". A **daily local routine** (`bats/deck-suggestions.bat`
→ `python -m src.cli.main process-deck-suggestions`) then asks Claude to build the
deck from the request plus the user's COLLECTION. It uses owned cards first and lists
the missing ones with BRL prices. The result is stored and shown in the app, and the
user can save it as a deck.

## Scope

1. Commander search fix + review of the whole deck-build module (builder, router, wizard, tests).
2. Mode chooser (manual vs. suggestion), deep-linkable via `/decks/build?mode=manual|suggestion`.
   **No `App.tsx` / `Layout.tsx` change**: the route `/decks/build` already exists.
3. New table `deck_suggestion_requests` + REST API `/api/v1/deck-suggestions`.
4. Claude processor (CLI runner by default, HTTP API runner as opt-in) + CLI command + daily `.bat`.
5. Frontend: request form, request list with status, result view with "Salvar como deck".
6. Docs: PRD, ADR, 2 diagrams, README note.

## Constraints

- **No new dependencies.** The Claude API runner uses `httpx`, which the project already
  depends on (`pyproject.toml`). The `anthropic` SDK is **NOT** added
  (confirmed by the user on 2026-09-24; default provider is `claude -p`).
- Secrets only via env vars (`ANTHROPIC_API_KEY`, never logged, never hardcoded).
- Batch F171–F179 runs in parallel. High-conflict shared files (`frontend/src/App.tsx`,
  `frontend/src/components/Layout.tsx`, `src/cli/main.py`, `src/database/models.py`,
  `src/api/app.py`, `README.md`, `bats/`) are touched **only in Wave 4**
  (F172-T17 / F172-T18). This feature does not touch `App.tsx`, `Layout.tsx` or `models.py` at all.
- The new ORM row lives in a NEW module, `src/deck_suggestions/models.py`, which uses the shared
  `Base`. Its repository creates the table idempotently (`__table__.create(checkfirst=True)`),
  so `src/database/models.py` needs no edit.
- DB portability: SQLite (local) and Neon PostgreSQL (prod). Store the result as JSON **text**
  (`Text` column + `json.dumps`), not as a dialect-specific JSON type.
- User identity: every deck endpoint uses `require_auth_or_api_key` (returns `str`
  user id). `user_collection.user_id` and `decks.user_id` are `String(100)`, so the new
  table uses the same type.
- Gitflow: work happens on `homol` (or the orchestrator's feature worktree branch). Never push to `main`.

## Acceptance criteria (titles; detail lives in component shards)

- AC1 Commander search returns legendary creatures even when `card_legalities` is empty/partial, and matches PT names.
- AC2 The wizard shows loading / empty / error states for commander search. No stale-response race.
- AC3 The user picks the mode (manual vs. suggestion) before the wizard starts.
- AC4 Commander request = commander (via fixed search) + notes. Other formats = colors + archetype (+ notes).
- AC5 The request is persisted as `pending`. The API returns 201 immediately. The list shows status.
- AC6 `process-deck-suggestions` claims pending requests, calls Claude, enriches the result with collection + prices, and stores `done`/`failed`.
- AC7 The result view shows owned vs. missing cards with prices and the missing total. "Salvar como deck" creates a deck.
- AC8 `bats/deck-suggestions.bat` exists and documents the daily Task Scheduler setup.
- AC9 PRD, ADR, `F172-architecture.mmd`, `F172-journey.mmd`, README note.
- AC10 Backend coverage of new modules ≥ 90%. Frontend tests for every new component.
