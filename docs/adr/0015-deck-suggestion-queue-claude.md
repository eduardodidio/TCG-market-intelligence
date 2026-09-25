# ADR 0015 — Deck suggestion queue processed daily by Claude

**Status:** Accepted · **Date:** 2026-09-24 · **Feature:** F172

## Context

F172 adds a "Sugestão de deck" mode to `/decks/build`: the user describes a
deck (a commander, or colors + archetype, plus free-text notes) and Claude
builds it from the user's collection, listing the missing cards with BRL
prices.

Constraints that shape the design:

- Generating a 60–100 card deck with an LLM takes from tens of seconds to
  several minutes — far too long for an HTTP request.
- Production runs on Render, which has no Claude access (no CLI login, and we
  do not want an API key stored there). The operator already runs local jobs
  (`push-all.bat`, `bats/process-queue.bat`) that write directly to the shared
  Neon database that Render reads.
- Project guardrail: no new dependencies without confirmation. `httpx` is
  already a dependency; the `anthropic` SDK is not.
- F172 runs in the parallel batch F171–F179. `src/database/models.py` is a
  high-conflict shared file.
- F09 learning: external scheduling (Task Scheduler/cron + script) is
  preferred over an in-process scheduler.

## Decision

1. **Asynchronous request queue.** `POST /api/v1/deck-suggestions` validates
   the request and stores it in the new table `deck_suggestion_requests` with
   status `pending`, then returns 201 right away ("pedido registrado"). Status
   moves `pending → processing → done | failed`. The result is stored as JSON
   **text** (`Text` + `json.dumps`), which works on both SQLite and PostgreSQL.
2. **Daily local processing.** The CLI command
   `python -m src.cli.main process-deck-suggestions` claims pending rows
   (conditional `UPDATE … WHERE status = :old` so concurrent runners never
   double-claim; rows stuck in `processing` for more than 2 h are reclaimed),
   calls Claude, enriches the answer with ownership and prices, and stores
   `done` or `failed`. Transient errors are retried up to 3 attempts. The
   command is scheduled externally with `bats/deck-suggestions.bat`
   (Windows Task Scheduler, daily).
3. **No SDK: Claude CLI by default, httpx as opt-in.**
   - Default provider `cli`: `claude -p --output-format json --max-turns 1`,
     tools disabled, prompt via stdin, run in an empty temp directory. It
     uses the operator's local Claude login, so no key is needed anywhere.
   - Opt-in provider `api` (`DECK_SUGGEST_PROVIDER=api`): a small `httpx`
     client for the Messages API using `ANTHROPIC_API_KEY` from `.env`
     (never logged, never hardcoded).
   - Both are behind a `ClaudeRunner` protocol (`get_runner()`), so tests use a
     fake runner and never call Claude.
4. **The table is defined in its own module.** `DeckSuggestionRequestRow`
   lives in `src/deck_suggestions/models.py` on the shared `Base`, and the
   repository creates it idempotently with
   `__table__.create(engine, checkfirst=True)` (memoized per engine).
   `src/database/models.py` is not edited.
5. **Untrusted input and output.** User notes are truncated to 1000 chars and
   wrapped in a delimited block that the prompt declares as data, not
   instructions. The model's output is parsed as strict JSON and validated
   (quantities clamped, duplicates merged). Card names that do not resolve to
   the catalog are kept as `unresolved` instead of failing the request.

## Alternatives considered

1. **Synchronous generation inside the request.** Rejected: latency of
   minutes blocks a worker and times out the SPA, and Render has no Claude
   access (it would need an API key on the server and per-request billing).
2. **Official `anthropic` Python SDK.** Rejected (user decision,
   2026-09-24): it adds a new dependency for a single POST call that `httpx`
   already covers, and the default path is the `claude -p` CLI anyway.
3. **In-process scheduler (APScheduler / FastAPI background loop).**
   Rejected, following the F09 learning: it needs a new dependency, makes the
   API process stateful, and would run on Render, which has no Claude access.
   An OS-native scheduled `.bat` is simpler and debuggable.
4. **Add the row to `src/database/models.py` (with a migration).** Rejected
   for this batch: `models.py` is shared by F171–F179 running in parallel;
   an own-module table with `checkfirst` avoids merge conflicts. It can be
   moved into `models.py` later without a schema change.
5. **Native JSON column type.** Rejected: dialect-specific behavior between
   SQLite and PostgreSQL; the result is only read as a whole, so `Text` is
   enough.

## Consequences

- Users get an answer the next day, not instantly; the UI makes this explicit
  (status list, "pedido registrado").
- Suggestions are only processed while the operator's machine runs the daily
  job and the Claude CLI is logged in. If the job does not run, requests stay
  `pending` (visible in the UI) and are processed on the next run.
- No new dependency and no secret on Render. Choosing `provider=api` requires
  `ANTHROPIC_API_KEY` in the local `.env` and incurs API billing.
- Cost is bounded by the 5-open-requests-per-user limit, `--limit` per run,
  and the 300-card cap on the collection sent in the prompt.
- The table is created on first use, not by the usual schema setup. Anything
  that reads the table must go through the repository (which calls
  `ensure_table`).
- LLM hallucinations degrade gracefully (unresolved list and warnings) instead
  of failing the request.
