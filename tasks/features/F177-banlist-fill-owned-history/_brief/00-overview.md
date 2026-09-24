# F177 — Overview (shared context)

## Problem
The ban list page (`/banlist`, `frontend/src/pages/BanList.tsx`) is empty in
production and locally: `card_legalities` / `legality_history` are never
populated by `banlist-sync`. Users also can't filter the list to cards they
own. Ban history sits on its own page (`/banlist/history`, `BanHistory.tsx`)
disconnected from the cards, when it belongs next to the card being inspected.

## Diagnosis (done by the Architect, confirmed by reading code on 2026-09-24)
`src/collectors/banlist_sync.py::_sync_bulk` fails silently:

| # | Root cause | Evidence |
|---|-----------|----------|
| RC1 | Reads only `download_uri` (a JSON **array**: each line is `{...},` with a trailing comma, plus `[` / `]` lines). `json.loads(line)` raises on every line, so `errors++` and 0 cards are matched. Scryfall now also publishes `jsonl_download_uri` (optionally `.jsonl.gz`), and the sync ignores it. | `src/catalog/scryfall.py:69-70` already handles `jsonl_download_uri` + gzip; banlist_sync does not |
| RC2 | `httpx.AsyncClient` is created **without `follow_redirects=True`**. The bulk download URL can redirect, and `raise_for_status()` then aborts the job. | `banlist_sync.py:80` vs `scryfall.py:136` |
| RC3 | Local `cards.set_code` may be a Liga-style code (see `scripts/normalize_set_codes.py`, `src/utils/set_code_map.py::map_to_scryfall_set_code`). The index key is the raw local code, so Scryfall `set` codes don't match. | `banlist_sync.py:113-114` |
| RC4 | `Repository.upsert_legalities` runs **one INSERT…ON CONFLICT per row**. That is 22 formats × ~100k printings ≈ 2.4M round trips to Neon, so it never finishes and times out. It also stores every `legal`/`not_legal` row (~250 MB on Neon free tier). | `src/database/repository.py:2878-2903` |
| RC5 | The first run writes a history row with `old_status=None` for **every** card × format (millions of noise rows) and sets `effective_date=today` for all of them. | `banlist_sync.py:154-166` |
| RC6 | No routine keeps it updated: there is no `.bat` and nothing scheduled. The API `POST /banlist/sync` exists but nobody calls it. | `bats/` only has `process-queue.bat` |
| RC7 | Silent failure: when 0 cards match, the job still "completes", so nobody notices. | — |

Secondary bug: `GET /banlist` with `status=None` applies `offset` to **both**
the banned and the restricted sub-queries (pagination is broken). The list also
shows one tile per **printing**, which duplicates cards.

## Scope
1. Fix the sync (RC1–RC7) with a compact storage policy and batched writes → `01-sync-fix.md`
2. Backend: grouped ban list with `owned_only` filter + sync status endpoint → `02-backend-api.md`
3. Frontend: "Somente minha coleção" toggle + card detail modal with per-format ban history → `03-frontend.md`
4. Remove the "Histórico de banimentos" menu item, redirect `/banlist/history` → `/banlist`, add a `.bat` routine, update the README → `04-routing-docs-ops.md`

## Constraints
- Batch F171–F179 runs in parallel. Hotspot files (`frontend/src/App.tsx`,
  `frontend/src/components/Layout.tsx`, `src/cli/main.py`,
  `src/database/models.py`, `src/api/app.py`, `README.md`, `bats/`) are
  touched ONLY in Wave 3 tasks (F177-T09 / F177-T10).
- **No edits** to `src/cli/main.py` (the `banlist-sync` command already exists and
  keeps its signature), `src/database/models.py` (no schema change), or `src/api/app.py`
  (the banlist router is already registered).
- Prefer NEW modules: `src/database/legality_writer.py`,
  `src/database/banlist_queries.py`, `frontend/src/components/BanCardDetailModal.tsx`.
- No new dependencies (gzip is stdlib, httpx already present).
- Gitflow: work on `homol` (never push to `main`).
- Must work on both SQLite (local) and PostgreSQL/Neon (`src/database/compat.py::dialect_insert`).

## Acceptance criteria (titles; details in the component shards)
- AC1 `banlist-sync` populates `card_legalities` from a JSONL, JSONL.gz, or JSON-array bulk file
- AC2 Set-code mapping lets Liga-style codes match Scryfall
- AC3 Batched, diff-only writes (daily re-run writes ~0 rows)
- AC4 Compact storage policy + baseline history policy
- AC5 Sync fails loudly (raises) when 0 cards match
- AC6 `GET /banlist` is grouped by card name, paginated correctly, supports `owned_only`
- AC7 `GET /banlist/status` reports freshness and counts
- AC8 BanList shows the "Somente minha coleção" toggle (auth only, URL-persisted)
- AC9 Clicking a card opens a modal with legalities + ban/unban history per format
- AC10 The menu no longer shows "Histórico de banimentos"; `/banlist/history` redirects to `/banlist`
- AC11 `bats/banlist-sync.bat` exists; README documents it
- AC12 PRD + `F177-architecture.mmd` + `F177-journey.mmd` exist
