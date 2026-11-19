# F210 — Remove Liga Magic Provider

## Goal
Remove all Liga Magic infrastructure from the project. MYP Cards becomes the
sole price provider. Manual price entry (acquisition_price, price ingest
endpoint) MUST be preserved.

## Scope
- 51 backend files (847 Liga occurrences)
- 41 frontend files (281 Liga occurrences)
- 117 test files with Liga references
- Full module deletions + reference cleanup

## Wave 0 — Bulk deletions (all parallel, no deps)

| Task | Description | Files |
|------|-------------|-------|
| T01 | Delete `src/providers/liga/` directory | 8 files |
| T02 | Delete Liga collectors: `liga_scan.py`, `liga_sweep.py`, `liga_url_recorder.py` | 3 files |
| T03 | Delete `src/parsers/liga.py` | 1 file |
| T04 | Delete Liga test fixtures (`tests/fixtures/liga_*`, `card_page_*`, `set_page_*`, `editions_page_*`, `price_history_*`) | ~12 files |
| T05 | Delete Liga-only test files (30+ files under `tests/providers/liga/`, `tests/collectors/test_liga_*`, `tests/cli/test_liga_*`, etc.) | ~30 files |

## Wave 1 — Backend reference cleanup (parallel by module)

| Task | Description | Key files |
|------|-------------|-----------|
| T06 | CLI: remove liga-sweep, liga-scan, liga-verify, liga-relink, liga-debug commands; update remaining commands that reference liga | `src/cli/main.py` |
| T07 | API routers: remove Liga refs from admin, catalog, cards, collection, scans, card_search, alerts, evaluations, price_ingest, purchases | `src/api/routers/*.py`, `src/api/app.py`, `src/api/deps.py` |
| T08 | API schemas: remove Liga fields from cards, collection, scans, card_search, evaluations schemas | `src/api/schemas/*.py` |
| T09 | Collectors & services: clean scan.py, admin_scan.py, price_request_processor.py, myp_sweep.py, portfolio_backfill.py | `src/collectors/*.py` |
| T10 | Database layer: clean repository, models, trending_queries, cleanup.py | `src/database/*.py`, `src/domain/models.py` |
| T11 | Config, registry, scheduler, services: remove Liga from provider registry, scheduler, purchase_parser, config, catalog seeder, collection modules | `src/config.py`, `src/providers/registry.py`, `src/scheduler/`, `src/services/`, `src/catalog/`, `src/collection/`, `src/marketplace/`, `src/utils/` |

## Wave 2 — Frontend cleanup (parallel by area)

| Task | Description | Key files |
|------|-------------|-----------|
| T12 | Delete Liga components: AdminLigaSection, ImportLigaLink; clean AdminPanel, CatalogPage | `frontend/src/components/admin/AdminLigaSection.tsx`, pages |
| T13 | Clean pages: CardDetail, CollectionCardDetail, Cards, MyCollection, DeckView | `frontend/src/pages/*.tsx` |
| T14 | Clean API layer, hooks, types, utils | `frontend/src/api/`, `frontend/src/hooks/`, `frontend/src/types/`, `frontend/src/utils/` |
| T15 | Clean i18n: remove Liga keys from en.json and pt-BR.json | `frontend/src/i18n/locales/` |
| T16 | Clean components: ArbitrageBadge, PriceHistoryMeta, PriceSourceBadge, PriceChart | `frontend/src/components/` |

## Wave 3 — Test cleanup (parallel)

| Task | Description | Key files |
|------|-------------|-----------|
| T17 | Update backend tests that reference Liga as secondary concern (mocks, assertions, fixtures) | ~80 test files |
| T18 | Update/remove frontend test files with Liga references | ~15 test files |

## Wave 4 — Verification (sequential)

| Task | Description |
|------|-------------|
| T19 | Run `ruff check src/` + `pytest tests/` — fix any import/reference errors |
| T20 | Run `cd frontend && npm run build && npm test` — fix any TS/test errors |

## Preserved (NOT deleted)
- `POST /api/v1/price-ingest` — manual price entry endpoint (remove Liga-specific logic, keep generic)
- `acquisition_price` on `user_collection` — manual price on import
- `AcquisitionPriceInput` component — manual price entry in UI
- MYP provider (`src/providers/myp/`) — untouched
- Price history tables, portfolio, alerts — data stays, Liga source references become historical
