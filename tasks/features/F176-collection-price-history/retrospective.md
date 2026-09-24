# Retrospective — F176

## What worked

- The four-shard brief (`00-overview`, `01-diagnosis`, `02-key-resolution`,
  `03-snapshot-backfill`, `04-api-ui`) let each Wave read only the shards it
  needed, and the Wave-0 diagnosis (T01) proved the root-cause hypothesis
  (key-contract mismatch, not a data bug) with real fixture numbers before
  any code changed — the Governance amendment #1 checkpoint caught nothing to
  re-plan, but it was cheap insurance that paid for itself in confidence.
- A single pure resolver module (`price_history_keys.py`, no DB/collector
  imports) plus one shared service (`collection_price_history.build_history`)
  used by all three endpoints (`collection.py` x2, `cards.py`) kept AC5/AC9
  (single priority order, cross-endpoint agreement) trivially true by
  construction instead of needing three independent re-implementations kept
  in sync by hand.
- Marking forward-filled rows with a distinct source (`daily_snapshot_backfill`)
  rather than reusing `daily_snapshot` gave a clean, testable way to
  distinguish real vs. synthetic points (AC7/AC8) without a schema change.
- Explicitly designating `bats/daily-snapshot.bat` as a fallback and the
  post-sweep hook as primary (Governance amendment #6) avoided a
  "two sources of truth for scheduling" ambiguity that earlier attempts
  (F33/F34/F112/F168) apparently didn't resolve.

## What to avoid

- A gap flagged in a Wave summary's "Notes for next Wave"
  (`daily_snapshot_backfill` missing from `SOURCE_PRIORITY`, first flagged in
  the Wave 2 summary, repeated in the Wave 3 summary) sat unfixed for two
  more Waves and had to be caught by TechLead as an IMPORTANT finding. No
  Wave whose task list didn't literally own `price_history_keys.py` picked
  it up, even though every Wave after was told about it.
- Bookkeeping (`Status: planned` headers left stale on `F176-T04.md`,
  `F176-T08.md`, `F176-T11.md` after they shipped) drifted for the same
  reason: it's nobody's specific task to "go back and fix the header," so it
  doesn't happen without an explicit sweep step.
- Several TechLead attempts stalled (5 checkpoints with no `review-*.md`)
  before someone worked out that `pytest tests/ --cov=src` duplicates flags
  already baked into this repo's `pyproject.toml` `addopts` and errors out
  immediately — a silent, repeated failure mode that cost real wall-clock
  time across the batch.

## Patterns to repeat

- Read-only diagnosis script + `diagnosis.md` before writing any fix code,
  for any bug where the root cause is contested or unclear (H1–H6 hypothesis
  table format worked well).
- One pure domain module owning a cross-cutting invariant (key resolution +
  merge priority here) consumed by every call site, instead of duplicating
  the rule per endpoint.
- Marking synthetic/derived data with its own `source` value instead of
  reusing an existing one, whenever "real vs. synthetic" needs to be
  queryable or deletable later.

## Propagated to learnings

- `memory/agent-learnings/developer.md` — cross-Wave gap follow-through;
  don't leave a flagged gap in a file your Wave doesn't own for the *next*
  Wave to maybe notice.
- `memory/agent-learnings/architect.md` — same gap, from the planning side:
  insert an explicit fast-follow task when a Wave summary flags an
  unresolved gap in a module no later Wave's task list touches.
- `memory/agent-learnings/techlead.md` and `memory/agent-learnings/qa.md` —
  this repo's `pytest` `addopts` already includes `--cov`; re-passing
  `--cov=src --cov-report=term-missing` from `CLAUDE.md`'s documented Test
  command errors out before running anything — run `pytest tests/<paths>`
  bare instead when verifying test status here.
