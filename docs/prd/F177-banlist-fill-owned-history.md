# PRD: F177 -- Ban List: Fill Sync, Owned Filter, Card History

**Status:** planned
**Depends on:** none (uses existing `card_legalities` / `legality_history` schema)
**Priority:** high
**Author:** Architect agent
**Branch:** `wt/F177` (worktree branch; merges into `homol`. Never push to `main`.)

## Problem Statement

The ban list page (`/banlist`, `frontend/src/pages/BanList.tsx`) is empty in
production and locally: `card_legalities` and `legality_history` are never
populated, because `src/collectors/banlist_sync.py::_sync_bulk` fails
silently. Users also have no way to filter the list down to cards they own,
and ban/unban history sits on its own disconnected page
(`/banlist/history`, `BanHistory.tsx`) instead of living next to the card
being inspected.

### Diagnosis (root causes, confirmed by reading code on 2026-09-24)

| # | Root cause | Evidence |
|---|-----------|----------|
| RC1 | Reads only `download_uri` (a JSON **array**: each line is `{...},` with a trailing comma, plus `[`/`]` lines). `json.loads(line)` raises on every line, so `errors++` and 0 cards match. Scryfall also publishes `jsonl_download_uri` (optionally `.jsonl.gz`), which the sync ignores. | `src/catalog/scryfall.py:69-70` already handles `jsonl_download_uri` + gzip; `banlist_sync.py` does not |
| RC2 | `httpx.AsyncClient` is created without `follow_redirects=True`. The bulk download URL can redirect, and `raise_for_status()` then aborts the job. | `banlist_sync.py:80` vs `scryfall.py:136` |
| RC3 | Local `cards.set_code` may be a Liga-style code (`src/utils/set_code_map.py::map_to_scryfall_set_code`). The index key is the raw local code, so Scryfall `set` codes don't match. | `banlist_sync.py:113-114` |
| RC4 | `Repository.upsert_legalities` runs one `INSERT ... ON CONFLICT` per row: 22 formats x ~100k printings ~= 2.4M round trips to Neon, so the job never finishes. It also stores every `legal`/`not_legal` row (~250 MB on Neon free tier). | `src/database/repository.py:2878-2903` |
| RC5 | The first run writes a history row with `old_status=None` for every card x format (millions of noise rows) and sets `effective_date=today` for all of them. | `banlist_sync.py:154-166` |
| RC6 | No routine keeps it updated: no `.bat`, nothing scheduled. `POST /banlist/sync` exists but nobody calls it. | `bats/` only has `process-queue.bat` |
| RC7 | Silent failure: when 0 cards match, the job still "completes", so nobody notices. | -- |

Secondary bug: `GET /banlist` with `status=None` applies `offset` to
**both** the banned and restricted sub-queries (pagination is broken), and
the list shows one tile per **printing**, duplicating cards.

## Goals

1. Fix `banlist-sync` to actually populate `card_legalities` from a real
   Scryfall bulk file (JSONL, JSONL.gz, or legacy JSON array), matching
   local cards via set-code mapping (RC1-RC3).
2. Make writes batched and diff-only so a daily re-run is cheap on Neon's
   free tier, and store only what the app needs (RC4-RC5).
3. Make the sync fail loudly instead of silently completing with 0 matches
   (RC7), and give it a routine (`.bat`) so it actually runs (RC6).
4. Group the ban list by card (not printing), fix pagination, and add an
   "only my collection" filter.
5. Move ban/unban history into a per-card detail modal opened from the ban
   list, instead of a separate disconnected page.

## Non-Goals

- No `render.yaml` / CI-CD change (production cron). A Render cron trigger
  was considered and **rejected without user confirmation** -- see ADR 0018.
- No database schema change and no data migration. `src/database/models.py`
  is untouched; `card_legalities` / `legality_history` keep their current
  columns.
- No edits to `src/cli/main.py` (the `banlist-sync` command already exists
  with the same signature), `src/api/app.py` (router already registered),
  or `Repository.upsert_legalities` / `insert_legality_changes` (other
  code/tests still use them).
- No deck/format validation changes, no new price-related logic.
- No new dependencies (gzip is stdlib; httpx is already a dependency).

## User Stories

### US-1: See a populated ban list
As a user, I want `/banlist` to actually show banned and restricted cards
per format, so the page is useful instead of empty.

### US-2: Filter to my own collection
As a logged-in user, I want to toggle "Somente minha coleção" so I only see
banned/restricted cards I actually own.

### US-3: See per-format legality and history for a card
As a user, I want to click a card in the ban list and see its legality
across all formats plus its ban/unban timeline, without leaving the page.

### US-4: Trust that the data is fresh
As a user, I want to see when the ban list was last synced, and get a clear
empty state if it has never been synced.

## Acceptance Criteria

- **AC1** `banlist-sync` populates `card_legalities` from a JSONL,
  JSONL.gz, or JSON-array bulk file (prefers `jsonl_download_uri`, falls
  back to `download_uri`, same selection rule as `src/catalog/scryfall.py`).
- **AC2** Set-code mapping (`map_to_scryfall_set_code`) lets Liga-style
  local set codes match Scryfall `set` codes; collector-number variants
  (leading zeros) are also matched.
- **AC3** Writes are batched (multi-row `INSERT ... ON CONFLICT`, chunked)
  and diff-only: a daily re-run with no legality changes writes ~0 rows.
- **AC4** A compact storage policy is the sync default: only
  banned/restricted cards, owned cards (any format), and cards with an
  existing row are stored; `scope="full"` stores everything. A baseline
  history policy avoids millions of noise rows on the first run.
- **AC5** The sync raises (fails loudly) when 0 lines parse, or when the
  card index is non-empty but 0 cards match after parsing >1000 lines.
- **AC6** `GET /api/v1/banlist` is grouped by card name (one entry per
  card, not per printing), paginates correctly after grouping, and
  supports `owned_only` (401 without a user).
- **AC7** `GET /api/v1/banlist/status` reports `last_synced_at`,
  legality/banned/restricted/history counts, and format count.
- **AC8** `BanList.tsx` shows a "Somente minha coleção" toggle, enabled
  only for authenticated users, persisted in the URL (`?owned=1`).
- **AC9** Clicking a card opens `BanCardDetailModal` with per-format
  legality and ban/unban history (baseline events labeled distinctly).
- **AC10** The "Histórico de banimentos" menu item is removed;
  `/banlist/history` redirects to `/banlist` (old bookmarks still resolve).
- **AC11** `bats/banlist-sync.bat` exists and the README documents it
  (including the suggested Task Scheduler cadence).
- **AC12** This PRD, `docs/adr/0018-banlist-compact-legality-storage.md`,
  `docs/diagrams/F177-architecture.mmd`, and `docs/diagrams/F177-journey.mmd`
  exist and reflect the design above.

## Data Model

No schema change. Reuses existing tables: `card_legalities`
(`(card_id, format)` unique key) and `legality_history` (append-only,
`source` field already supports arbitrary values such as
`scryfall_baseline` / `scryfall_sync`).

## Rollout Note

There is no scheduled job in this codebase and none is being added
(`render.yaml` is out of scope -- CI/CD changes require explicit user
confirmation per `CLAUDE.md`). Rollout is:

1. Run `bats/banlist-sync.bat` once, locally, against the Neon `.env`
   connection, to populate `card_legalities`/`legality_history` for the
   first time (`scope="compact"` default keeps storage small).
2. Optionally schedule the same `.bat` in Windows Task Scheduler (daily or
   weekly, matching the pattern already used for `process-queue.bat`) so
   the data stays fresh going forward.
3. `POST /api/v1/banlist/sync` remains available as a manual, authenticated
   trigger for ad-hoc re-syncs.

## Success Metrics

- `/banlist` shows non-zero banned/restricted entries per major format
  (commander, standard, modern) after running the sync once.
- A daily re-run of `banlist-sync` writes close to 0 rows when nothing
  changed upstream (diff-only writes working).
- `pytest tests/banlist/ -q` and `ruff check src/` stay green.
- No regression in `tests/banlist/test_sync.py` / `test_api.py` beyond
  assertions that explicitly encoded the old buggy behavior.

## Open Questions

- Whether to eventually add a scheduled Render job for the sync (out of
  scope for F177; needs explicit user confirmation per CLAUDE.md).
