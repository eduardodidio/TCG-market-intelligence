# PRD: F172 -- Montar Deck: commander search fix + "Sugestão de deck"

**Feature ID:** F172
**Status:** approved
**Owner:** @eduardodidio
**Date:** 2026-09-24
**ADR:** [0015 — Deck suggestion queue processed by Claude](../adr/0015-deck-suggestion-queue-claude.md)
**Tasks:** `tasks/features/F172-deck-builder-suggestions/`

## Problem

In "Montar deck" (`/decks/build`, `frontend/src/pages/DeckBuildWizard.tsx`),
searching for a **commander** returns no cards, so Commander-format users
cannot build a deck at all. The root cause is in
`get_commander_candidates()` (`src/decks/builder.py`), which depends on
`card_legalities` rows that are often empty or partial, and only matches
English names.

Beyond the fix, users want help building a deck: "take what I already own and
suggest a deck around this commander / these colors, and tell me what I still
need to buy and how much it costs". The app runs on Render, which has no
access to Claude, and generating a deck with an LLM takes minutes — so this
cannot be answered inside the HTTP request.

**Users:** logged-in collectors (and API-key clients) who have a collection
imported in TEDHC Market and want to build Commander or 60-card decks.

## Goals

1. Commander search in the wizard works again (legendary creatures, PT names,
   independent of `card_legalities` coverage).
2. The user chooses the mode before the wizard starts: **"Montar meu próprio
   deck"** (manual, the fixed wizard) or **"Sugestão de deck"** (Claude).
3. A suggestion request is saved instantly ("pedido registrado") and processed
   later by a **daily local routine** that calls Claude.
4. The suggestion prioritizes cards the user owns and lists missing cards
   with BRL prices and the total missing cost.
5. The user can save a finished suggestion as a regular deck.

## Non-goals (this iteration)

- Real-time / synchronous generation inside the API request.
- Processing on Render (no Claude CLI or key on the server).
- Adding the `anthropic` Python SDK or any other new dependency.
- In-process scheduling (APScheduler etc.) — the routine is an external
  Task Scheduler job (F09 learning).
- Editing a suggestion before saving (edit the saved deck instead).
- Format-legality validation beyond what the prompt asks for (warnings only).
- Changing the LigaMagic web search (`/cards/search-web`), `App.tsx`,
  `Layout.tsx` or `src/database/models.py`.

## User stories

### US-1: Fixed manual wizard (mode "Montar meu próprio deck")
As a user, I want the commander search to return legendary creatures when I
type part of an English or Portuguese name, so that I can finish the manual
wizard.

- Results appear even when `card_legalities` is empty or partial (AC1).
- The search shows loading, empty and error states; a slow old response never
  overwrites a newer one (AC2).

### US-2: Choose the mode
As a user, I want to pick "Montar meu próprio deck" or "Sugestão de deck"
before starting, and deep-link to either via `/decks/build?mode=manual` or
`/decks/build?mode=suggestion` (AC3).

### US-3: Request a suggestion
As a user, I want to describe the deck I want and submit it without waiting.

- **Commander:** choose the commander (same fixed search) + optional notes.
  Colors are derived from the commander's color identity (AC4).
- **Other formats** (standard, pioneer, modern, legacy, vintage, pauper,
  casual): colors (WUBRG or colorless) + archetype (aggro, control,
  midrange, combo, tempo, ramp) + optional notes (AC4).
- The request is saved as `pending` and the API returns 201 immediately with
  "pedido registrado" (AC5).
- At most 5 open (pending + processing) requests per user.

### US-4: Follow my requests
As a user, I want to see my requests and their status (pending, processing,
done, failed), and cancel one that is still pending (AC5).

### US-5: See the result
As a user, I want to see the suggested deck with the strategy, the cards I
own vs. the cards I am missing, the unit price and cost of each missing card,
and the total missing cost in BRL (AC7).

### US-6: Save as deck
As a user, I want to click "Salvar como deck" and get a normal deck in "Meus
decks" with the commander and all suggested cards (AC7). Saving twice returns
the same deck.

### US-7: Daily routine (operator)
As the operator, I want a `.bat` I can schedule once a day that processes all
pending requests with my local Claude login, so that no key lives on Render
(AC6, AC8).

## Functional requirements

| AC | Requirement |
|---|---|
| AC1 | Commander search returns legendary creatures even when `card_legalities` is empty/partial, and matches PT names. |
| AC2 | The wizard shows loading / empty / error states for commander search. No stale-response race. |
| AC3 | The user picks the mode (manual vs. suggestion) before the wizard starts. |
| AC4 | Commander request = commander (via fixed search) + notes. Other formats = colors + archetype (+ notes). |
| AC5 | The request is persisted as `pending`. The API returns 201 immediately. The list shows status. |
| AC6 | `process-deck-suggestions` claims pending requests, calls Claude, enriches the result with collection + prices, and stores `done`/`failed`. |
| AC7 | The result view shows owned vs. missing cards with prices and the missing total. "Salvar como deck" creates a deck. |
| AC8 | `bats/deck-suggestions.bat` exists and documents the daily Task Scheduler setup. |
| AC9 | PRD, ADR, `F172-architecture.mmd`, `F172-journey.mmd`, README note. |
| AC10 | Backend coverage of new modules ≥ 90%. Frontend tests for every new component. |

## Data model

New table `deck_suggestion_requests`, defined in its own module
`src/deck_suggestions/models.py` (shared `Base`, created idempotently with
`__table__.create(checkfirst=True)` — `src/database/models.py` is not edited).

| Column | Type | Notes |
|---|---|---|
| `id` | int PK | autoincrement |
| `user_id` | String(100) | same type as `decks.user_id` / `user_collection.user_id` |
| `format_name` | String(30) | commander, standard, pioneer, modern, legacy, vintage, pauper, casual |
| `commander_card_id` | int FK `cards.id` | `ON DELETE SET NULL` |
| `commander_name` | String(500) | denormalized, survives card deletion |
| `colors` | String(10) | WUBRG order, `"C"` = colorless |
| `archetype` | String(30) | required for non-commander formats |
| `notes` | Text | ≤ 1000 chars |
| `status` | String(20) | `pending` → `processing` → `done` / `failed` |
| `result_json` | Text | `json.dumps(SuggestionResult)` — portable across SQLite and PostgreSQL |
| `error_message` | Text | ≤ 1000 chars |
| `attempts` | int | incremented on each claim; max 3 for transient errors |
| `saved_deck_id` | int FK `decks.id` | `ON DELETE SET NULL` |
| `created_at`, `started_at`, `processed_at`, `updated_at` | DateTime | |

Indexes: `user_id`, `status`, `created_at`.

The stored result (`SuggestionResult`) contains `deck_name`, `strategy`
(pt-BR), `format_name`, `commander`, `cards[]` (name, quantity, category,
reason, resolved `card_id`/printing/image, `is_owned`, `owned_quantity`,
`missing_quantity`, `unit_price`, `missing_cost`), `summary`
(`total_cards`, `owned_cards`, `missing_cards`, `missing_cost_brl`,
`unresolved_count`), `unresolved[]`, `warnings[]`, `provider`, `model`,
`generated_at`.

## API

Router `src/api/routers/deck_suggestions.py`, mounted under `/api/v1`.
Auth: `require_auth_or_api_key` (same as the decks router). Responses use the
`ApiResponse` envelope.

| Method | Path | Body / query | Response | Errors |
|---|---|---|---|---|
| POST | `/api/v1/deck-suggestions` | `format_name`, `commander_card_id?`, `colors[]`, `archetype?`, `notes?` | 201 suggestion | 400 validation, 429 when ≥ 5 open requests |
| GET | `/api/v1/deck-suggestions` | `?status=&limit=20` (1..50) | list with `summary`, without `result` | 400 bad status |
| GET | `/api/v1/deck-suggestions/{id}` | — | suggestion with full `result` | 404 (also for another user's request) |
| POST | `/api/v1/deck-suggestions/{id}/save` | `{deck_name?}` (1..300) | `{deck_id}` (idempotent) | 404, 409 when status ≠ done |
| DELETE | `/api/v1/deck-suggestions/{id}` | — | 204 | 404, 409 when not pending |

The existing commander search `GET /api/v1/decks/commanders?q=` is fixed in
place (no contract change).

## Daily routine (ops)

1. The operator schedules `bats/deck-suggestions.bat` in Windows Task
   Scheduler (suggested: daily at 03:00) on the machine where Claude Code is
   logged in.
2. The `.bat` runs
   `python -m src.cli.main process-deck-suggestions --limit 10`, which writes
   directly to the same Neon database that Render reads.
3. For each claimed request: load the user's collection → filter by color
   identity (cap 300 cards) → build a pt-BR prompt → call Claude → parse the
   JSON deck → resolve names against the catalog → enrich with ownership and
   latest BRL prices → mark `done`. Parse errors or permanent errors mark it
   `failed`; transient errors release it for retry (up to 3 attempts). One bad
   request never aborts the batch. Rows stuck in `processing` for more than
   2 h are reclaimed.
4. Command options: `--db`, `--limit` (default 5), `--provider cli|api`,
   `--dry-run` (count only, no claim).

Environment variables (from `.env`, never written in the `.bat`):

| Variable | Default | Purpose |
|---|---|---|
| `DECK_SUGGEST_PROVIDER` | `cli` | `cli` = `claude -p` (local login); `api` = HTTP Messages API |
| `DECK_SUGGEST_CLAUDE_BIN` | `claude` | path to the Claude CLI |
| `DECK_SUGGEST_MODEL` | `claude-sonnet-5` | model (CLI passes `--model` only when set) |
| `DECK_SUGGEST_TIMEOUT` | `300` | seconds per request |
| `ANTHROPIC_API_KEY` | — | only for `provider=api`; never logged |

## Risks

| Risk | Mitigation |
|---|---|
| **Prompt injection via notes** — the user's free text tries to change the model's instructions. | Notes are truncated to 1000 chars and wrapped in `<observacoes_do_usuario>…</observacoes_do_usuario>`, and the prompt states explicitly that this block is data, not instructions. The CLI runs with tools disabled (`--disallowedTools …`, `--max-turns 1`) in an empty temp directory, so an injected instruction cannot touch files or the network. Output is strictly parsed and validated JSON; nothing from the model is executed. |
| **Claude cost** | Default provider is the user's local Claude CLI login (no API key billing on Render). Max 5 open requests per user, `--limit` per run, one daily run, collection capped at 300 cards in the prompt, `max_tokens` 8000 on the API path. |
| **Hallucinated or misspelled card names** | Names are resolved case-insensitively against `CardRow.name_en` (then `name_pt`, then DFC front face). Unresolved names are kept with `card_id=None`, listed in `unresolved[]` and counted in `summary.unresolved_count`, and shown to the user. They never break the result. |
| **Wrong deck size / illegal quantities** | Quantities are clamped (singleton for commander, max 4 otherwise, basics free) and duplicates merged; a size mismatch becomes a warning, not a failure. |
| **Stale price data** | Prices come from the latest stored observation (`median_price`); cards without a price show "sem preço" and are excluded from the total. |
| **Concurrent runners double-processing** | Claim uses a conditional `UPDATE … WHERE status = :old` (rowcount = 1). |
| **Parallel batch conflicts (F171–F179)** | Own module for the ORM row, shared files touched only in Wave 4. |

## Success metrics

- Commander search returns results for common commanders (e.g. "Atraxa",
  "Edgar") in EN and PT on the production catalog.
- ≥ 90% of processed requests end as `done` (not `failed`).
- ≤ 5% of suggested cards end up unresolved on average.
- Median suggested deck uses ≥ 40% owned cards for users with ≥ 500 cards.
- Backend coverage of `src/deck_suggestions/*` and the new router ≥ 90%;
  every new frontend component has tests.

## Open questions

- Should failed requests be retryable by the user from the UI? (Out of scope
  now: the user can create a new request.)
- Should the user be notified (alert/e-mail) when a suggestion finishes?
  Candidate follow-up using the alerts module.
