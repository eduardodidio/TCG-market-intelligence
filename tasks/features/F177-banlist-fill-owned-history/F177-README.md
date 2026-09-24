# F177 — Ban list: populate + "Somente minha coleção" filter + history inside the card

**Status:** planned

## Goal
Make the ban list actually work. The Scryfall legality sync is broken: it only reads the
JSON-array bulk URL, doesn't follow redirects, doesn't map set codes, and does one DB round
trip per row, so it fails silently. This feature fixes it with batched, diff-only writes and
a compact storage policy, and ships a `bats/banlist-sync.bat` routine. The list itself gets
three changes: it groups printings by card, it adds a "Somente minha coleção" toggle, and a
card-detail modal now shows the ban/unban history per format. That modal replaces the
standalone "Histórico de banimentos" page: its menu item is removed and `/banlist/history`
redirects to `/banlist`.

Brief (sharded): `_brief/00-overview.md` (diagnosis RC1–RC7, constraints, AC list),
`_brief/01-sync-fix.md`, `_brief/02-backend-api.md`, `_brief/03-frontend.md`,
`_brief/04-routing-docs-ops.md`.

## Architecture impact
- **Collector**: `src/collectors/banlist_sync.py` (rewrite of the bulk path; pure helpers)
- **Database (new modules, no schema change)**: `src/database/legality_writer.py`, `src/database/banlist_queries.py`
- **API**: `src/api/routers/banlist.py` (`GET /banlist` grouped + `owned_only`, new `GET /banlist/status`), `src/api/schemas/banlist.py`
- **Frontend**: `BanList.tsx` (toggle, modal, pagination, empty states), new `BanCardDetailModal.tsx`, `api/banlist.ts`, `types/banlist.ts`, i18n
- **Routing/menu**: `App.tsx` (redirect), `Layout.tsx` (menu item removed), `BanHistory.tsx` deleted
- **Ops**: new `bats/banlist-sync.bat`; the CLI `banlist-sync` is unchanged (no `src/cli/main.py` edit)

## Waves

- **Wave 0**: F177-T01, F177-T02        (PRD + diagrams + branch check; i18n keys)
- **Wave 1**: F177-T03, F177-T04, F177-T05
- **Wave 2**: F177-T06, F177-T07, F177-T08
- **Wave 3**: F177-T09, F177-T10        (batch hotspots: App.tsx/Layout.tsx; bats/ + README.md)

## Files touched per task (for batch overlap detection)

| Task | Wave | Type | Files |
|------|------|------|-------|
| F177-T01 | 0 | docs | NEW `docs/prd/F177-banlist-fill-owned-history.md`, NEW `docs/adr/0018-banlist-compact-legality-storage.md`, NEW `docs/diagrams/F177-architecture.mmd`, NEW `docs/diagrams/F177-journey.mmd` |
| F177-T02 | 0 | frontend | `frontend/src/i18n/locales/en.json`, `frontend/src/i18n/locales/pt-BR.json`, NEW `frontend/tests/i18n/banlist-f177-keys.test.tsx` |
| F177-T03 | 1 | backend | NEW `src/database/legality_writer.py`, NEW `tests/banlist/test_legality_writer.py` |
| F177-T04 | 1 | backend | NEW `src/database/banlist_queries.py`, NEW `tests/banlist/test_banlist_queries.py` |
| F177-T05 | 1 | frontend | NEW `frontend/src/components/BanCardDetailModal.tsx`, NEW `frontend/tests/components/BanCardDetailModal.test.tsx` |
| F177-T06 | 2 | backend | `src/collectors/banlist_sync.py`, NEW `tests/banlist/test_sync_f177.py`, `tests/banlist/test_sync.py` (only assertions encoding old behavior) |
| F177-T07 | 2 | backend | `src/api/routers/banlist.py`, `src/api/schemas/banlist.py`, NEW `tests/banlist/test_api_f177.py`, `tests/banlist/test_api.py` (only if needed) |
| F177-T08 | 2 | frontend | `frontend/src/pages/BanList.tsx`, `frontend/src/api/banlist.ts`, `frontend/src/types/banlist.ts`, `frontend/tests/pages/BanList.test.tsx`, `frontend/tests/api/banlist.test.ts` |
| F177-T09 | 3 | frontend | **HOTSPOT** `frontend/src/App.tsx`, **HOTSPOT** `frontend/src/components/Layout.tsx`, DELETE `frontend/src/pages/BanHistory.tsx`, DELETE `frontend/tests/pages/BanHistory.test.tsx`, `frontend/tests/components/Layout.test.tsx`, NEW `frontend/tests/routes/banlistRedirect.test.tsx` |
| F177-T10 | 3 | docs/infra | **HOTSPOT** NEW `bats/banlist-sync.bat`, **HOTSPOT** `README.md`, `docs/diagrams/F177-*.mmd` (sync only) |

Files explicitly **not** touched: `src/cli/main.py`, `src/database/models.py`,
`src/database/repository.py`, `src/api/app.py`, `render.yaml`.

Other batch features touching the same files should serialize on
`frontend/src/i18n/locales/*.json` (T02), `App.tsx`/`Layout.tsx` (T09), and `README.md`/`bats/` (T10).

## Global acceptance criteria
- [ ] AC1 `python -m src.cli.main banlist-sync` populates `card_legalities` from a JSONL, JSONL.gz, or legacy JSON-array bulk file (follows redirects)
- [ ] AC2 Cards with Liga-style set codes or zero-padded collector numbers match Scryfall entries
- [ ] AC3 Writes are chunked multi-row upserts; a second run with unchanged data writes 0 rows and 0 history
- [ ] AC4 Compact policy: only banned/restricted rows, rows for owned cards, and rows that previously existed. The first run's history holds only `scryfall_baseline` rows for banned/restricted
- [ ] AC5 Sync raises (job fails, the bat exits with code 1) when 0 cards match or 0 lines parse
- [ ] AC6 `GET /api/v1/banlist` returns one entry per card name with `printings`, `owned`, `owned_quantity`; pagination is correct; `owned_only=true` filters (401 without login)
- [ ] AC7 `GET /api/v1/banlist/status` returns `last_synced_at` and counts
- [ ] AC8 BanList has the "Somente minha coleção" toggle (disabled with a hint when logged out; persisted in `?owned=1`)
- [ ] AC9 Clicking a card opens `BanCardDetailModal` with legalities per format and ban/unban history grouped by format
- [ ] AC10 The "Histórico de banimentos" menu item is gone; `/banlist/history` redirects to `/banlist`; `BanHistory.tsx` is deleted
- [ ] AC11 `bats/banlist-sync.bat` exists and the README documents F177
- [ ] AC12 The PRD, ADR 0018, `F177-architecture.mmd`, and `F177-journey.mmd` exist and match the code
- [ ] AC13 `pytest tests/ --cov=src` green; `cd frontend && npm test` green; `ruff check src/` clean; `cd frontend && npm run build` OK

## Diagrams
- `docs/diagrams/F177-architecture.mmd` (owner F177-T01, re-synced by F177-T10)
- `docs/diagrams/F177-journey.mmd` (owner F177-T01, re-synced by F177-T10)

## Operational note (post-merge, user action)
After deploy, run `bats\banlist-sync.bat` once locally (writes to Neon via `.env`) and schedule
it in the Windows Task Scheduler (daily 06:00 suggested). There is no `render.yaml` change.

## ADR number (batch reservation)
This feature's ADR number is **0018**, reserved in `tasks/features/EXECUTION-PLAN-F171-F179.md`. All task files reference 0018; do not renumber.
