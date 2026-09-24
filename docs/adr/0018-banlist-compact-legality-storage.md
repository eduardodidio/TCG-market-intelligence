# ADR 0018 — Ban list: compact legality storage + baseline history policy

**Status:** Accepted · **Date:** 2026-09-24 · **Feature:** F177

## Context

`src/collectors/banlist_sync.py::_sync_bulk` never populates
`card_legalities` / `legality_history` in production or locally. Reading
the code confirms seven compounding root causes (RC1-RC7, full detail in
`docs/prd/F177-banlist-fill-owned-history.md`):

- It reads only the legacy `download_uri` (a JSON array), never the JSONL
  / JSONL.gz `jsonl_download_uri` that `src/catalog/scryfall.py` already
  knows how to stream. Every line fails `json.loads`, so 0 cards match.
- `httpx.AsyncClient` has no `follow_redirects=True`, so a redirected bulk
  URL aborts the job.
- The card index key is the raw local `set_code`, which can be a
  Liga-style code, so Scryfall's `set` values never match it.
- `Repository.upsert_legalities` does one `INSERT ... ON CONFLICT` per
  row. At 22 formats x ~100k printings, that is ~2.4M round trips to
  Neon's free-tier Postgres — the job times out long before finishing, and
  storing every `legal`/`not_legal` row would cost ~250 MB on a plan that
  does not have room for it.
- The first run writes an `old_status=None` history row for every card x
  format (millions of noise rows), all dated `effective_date=today`.
- Nothing schedules the sync (no `.bat`, nothing calls `POST
  /banlist/sync`), and when it does run and matches 0 cards, it still
  reports success — nobody notices the failure.

## Decision

### 1. Compact legality storage (default `scope="compact"`)

`run_banlist_sync(..., scope="compact" | "full")` stores a `(card_id,
format)` legality row only when at least one holds:

- `status in {"banned", "restricted"}` — the data the ban list needs,
- `card_id` is in `owned_card_ids` (any `user_collection.card_id`, across
  all users — the per-card legality panel needs every format for cards
  people actually own),
- a row for `(card_id, format)` already exists (so a transition such as
  banned -> legal still gets recorded and updated).

`scope="full"` stores every row (all formats, all printings) and is
available for operators who want the complete Scryfall legality snapshot,
but is not the default and not what the CLI/`.bat` invoke.

### 2. Diff-only, chunked writes

Legality upserts and history inserts go through new pure functions in
`src/database/legality_writer.py` (`bulk_upsert_legalities`,
`bulk_insert_legality_changes`), which issue one multi-row `INSERT ...
ON CONFLICT` per chunk (`CHUNK_SIZE = 500`) via
`src/database/compat.py::dialect_insert`, instead of one statement per row.
A write is skipped entirely when the existing status already equals the
new status, so a daily re-run with no upstream changes writes close to
zero rows. `Repository.upsert_legalities` / `insert_legality_changes` are
left untouched — other code and tests still use them; the sync switches to
the new functions instead of changing the shared ones.

### 3. Baseline history policy (`source="scryfall_baseline"`)

To avoid the "millions of noise rows on first run" problem (RC5), history
rows are written under this policy:

- An existing row whose status differs from the new one gets a change row
  (`old_status=<existing>`, `source="scryfall_sync"`, `effective_date=today`).
- No existing row, and the new status is banned/restricted:
  - on the **first sync ever** for that card (no prior legality row at
    all) → a history row with `old_status=None`,
    `source="scryfall_baseline"`, `effective_date=None`. This marks
    "already banned when tracking started" rather than fabricating a ban
    date.
  - on any **later** sync → `old_status=None`, `source="scryfall_sync"`,
    `effective_date=today` (a genuinely new ban/restriction).
- No existing row, and the new status is legal/not_legal → no history row
  at all (nothing changed from the app's point of view).

This keeps the first run's history table proportional to the number of
currently banned/restricted (or owned) cards, not to `cards x formats`.

### 4. Fail loudly (RC7)

After streaming the bulk file, `run_banlist_sync` raises `RuntimeError`
when:

- 0 lines were parsed at all (`"banlist_sync parsed 0 lines from bulk
  file"`), or
- the card index is non-empty, more than 1000 lines were parsed, and 0
  cards matched (`"banlist_sync matched 0 cards — check set-code mapping
  / bulk format"`).

A sync that silently "succeeds" with zero effect is treated as a bug, not
a valid outcome.

### 5. No routine change beyond a manual `.bat`

`bats/banlist-sync.bat` is added (mirrors `bats/process-queue.bat`) so an
operator — or Windows Task Scheduler, at the user's discretion — can run
`python -m src.cli.main banlist-sync` on a cadence. `src/cli/main.py` and
`src/api/app.py` are not touched; the CLI command and the `POST
/banlist/sync` route already exist and keep their current signatures.

## Alternatives Considered

- **Full storage of every `(card_id, format, status)` row.** Rejected: at
  ~2.4M rows this is not viable on Neon's free tier (storage and the sheer
  number of upserts), and the app never reads `legal`/`not_legal` rows for
  cards nobody owns.
- **A Render cron job to run the sync automatically in production.**
  Considered, but rejected for this feature without explicit user
  confirmation — `render.yaml` / CI-CD changes require it per `CLAUDE.md`.
  The rollout instead documents running the `.bat` locally (writes to Neon
  via `.env`) and calling `POST /banlist/sync` manually. A scheduled
  production job is left as an open question for a future feature.

## Consequences

- The `LegalityPanel` (per-card legality display) shows accurate data for
  every owned card and every banned/restricted card in every format. For a
  card that is neither owned nor ever banned/restricted, and the sync ran
  with the default `scope="compact"`, the panel has no stored row for most
  formats and must show an explicit "unavailable" / "not synced for this
  format" state rather than implying the card is legal everywhere. Running
  the sync with `scope="full"` removes this gap at the cost of the storage
  and write volume described above.
- History rows tagged `source="scryfall_baseline"` must be rendered
  distinctly in the UI (e.g. "Already banned when tracking started")
  instead of a fabricated ban date — `BanCardDetailModal` implements this.
- Because writes are diff-only, storage growth is bounded by actual
  legality changes over time, not by the size of Scryfall's full bulk
  file.
- `Repository.upsert_legalities` / `insert_legality_changes` remain in
  place for any other caller; `legality_writer.py` is strictly additive.
- No schema migration is required; this ADR only changes what the sync
  chooses to write and when it writes to the existing tables.
