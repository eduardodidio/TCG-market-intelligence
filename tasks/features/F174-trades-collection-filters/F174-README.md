# F174 — Trocas com os mesmos filtros e layout de "Minha Coleção"

**Status:** planned
**Branch:** `homol` (or the orchestrator worktree branch cut from `homol`). Never `main`.
**Created:** 2026-09-24
**Batch:** F171–F179 (parallel execution)
**Brief (sharded):** `_brief/00-overview.md`, `_brief/01-backend.md`,
`_brief/02-frontend-kit.md`, `_brief/03-trade-pages.md`, `_brief/04-docs.md`

## Goal

Make the Trades area (Marketplace, My Trades, Trade Matches) look and filter
exactly like "Minha Coleção". Each page gets the same sticky filter bar (search,
set icons, sort, grid-size toggle, chips), the same responsive card grid
(`GRID_SIZE_CONFIG`) and the same tile anatomy. To do this, the collection's
filter bar is extracted into a reusable `CardFilterBar` that MyCollection also
adopts, with zero regression. The trade endpoints get the sort, filter and
set-facet parameters that server-side filtering needs.

## Architecture impact

| Layer | Modules |
|---|---|
| Backend: queries | **NEW** `src/marketplace/trade_queries.py` (`TradeQueries`). `repository.py` is **not** touched |
| Backend: API | `src/api/routers/marketplace.py`, `src/marketplace/service.py`, `src/api/routers/trade_match.py` (routers already registered, so there is no `app.py` change) |
| Frontend: shared kit | **NEW** `components/CardFilterBar.tsx`, `hooks/useCardListFilters.ts`, `utils/cardListFilter.ts`, `utils/tradeSortOptions.ts` |
| Frontend: pages | `pages/Marketplace.tsx` (+ **NEW** `components/MarketplaceCardTile.tsx`), `pages/MyTrades.tsx`, `components/TradeCard.tsx`, `pages/TradeMatchesPage.tsx`, `components/DuplicatesList.tsx`, `pages/MyCollection.tsx` (filter bar only) |
| Frontend: API clients | `api/marketplace.ts`, `api/tradeMatch.ts` |
| i18n | `i18n/locales/en.json`, `pt-BR.json` (one new `tradeFilters` block, appended) |
| Docs | PRD, `F174-architecture.mmd`, `F174-journey.mmd`, `README.md` |

No DB schema change, no migration, no new dependency, no new route or menu item.

## Wave manifest

- **Wave 0**: F174-T01, F174-T02
- **Wave 1**: F174-T03, F174-T04, F174-T05, F174-T06
- **Wave 2**: F174-T07, F174-T08, F174-T09, F174-T10, F174-T11, F174-T12
- **Wave 3**: F174-T13, F174-T14

## Tasks & files touched (for cross-feature overlap detection)

| Task | Wave | Type | Title | Files touched | Depends on |
|---|---|---|---|---|---|
| T01 | 0 | docs/infra | Branch check + PRD | `docs/prd/F174-trades-collection-filters.md` (new) | — |
| T02 | 0 | frontend | i18n `tradeFilters` keys | `frontend/src/i18n/locales/en.json`, `frontend/src/i18n/locales/pt-BR.json` (**shared across batch**: append-only block) | — |
| T03 | 1 | backend | `TradeQueries` module | `src/marketplace/trade_queries.py` (new), `tests/marketplace/test_trade_queries.py` (new) | T01 |
| T04 | 1 | frontend | Pure filter utils + trade sort options | `frontend/src/utils/cardListFilter.ts` (new), `frontend/src/utils/tradeSortOptions.ts` (new), `frontend/src/utils/__tests__/cardListFilter.test.ts` (new) | T01 |
| T05 | 1 | frontend | `CardFilterBar` + `useCardListFilters` | `frontend/src/components/CardFilterBar.tsx` (new), `frontend/src/hooks/useCardListFilters.ts` (new), `frontend/src/components/__tests__/CardFilterBar.test.tsx` (new), `frontend/src/hooks/__tests__/useCardListFilters.test.tsx` (new) | T01 |
| T06 | 1 | frontend | TradeCard → collection-style tile | `frontend/src/components/TradeCard.tsx`, `frontend/src/components/__tests__/TradeCard.test.tsx` (new) | T01 |
| T07 | 2 | backend | Marketplace listings sort + `/listings/sets` | `src/api/routers/marketplace.py`, `src/marketplace/service.py`, `tests/marketplace/test_router.py` | T03 |
| T08 | 2 | backend | Duplicates filters/sort + `/duplicates/sets` | `src/api/routers/trade_match.py`, `tests/api/test_trade_match_router.py` | T03 |
| T09 | 2 | frontend | Marketplace page alignment | `frontend/src/pages/Marketplace.tsx`, `frontend/src/components/MarketplaceCardTile.tsx` (new), `frontend/src/api/marketplace.ts`, `frontend/src/pages/__tests__/Marketplace.test.tsx` (new) | T04, T05 |
| T10 | 2 | frontend | MyTrades page alignment | `frontend/src/pages/MyTrades.tsx`, `frontend/src/pages/__tests__/MyTrades.test.tsx` (new) | T04, T05, T06 |
| T11 | 2 | frontend | TradeMatches page alignment | `frontend/src/pages/TradeMatchesPage.tsx`, `frontend/src/components/DuplicatesList.tsx`, `frontend/src/api/tradeMatch.ts`, `frontend/src/pages/__tests__/TradeMatchesPage.test.tsx`, `frontend/src/components/__tests__/DuplicatesList.test.tsx` | T04, T05 |
| T12 | 2 | frontend | MyCollection adopts `CardFilterBar` (no regression) | `frontend/src/pages/MyCollection.tsx` | T05 |
| T13 | 3 | docs | Architecture + journey diagrams | `docs/diagrams/F174-architecture.mmd` (new), `docs/diagrams/F174-journey.mmd` (new) | T07–T12 |
| T14 | 3 | docs | README note (**shared across batch**) | `README.md` | T07–T12 |

Intra-feature: no two tasks in the same Wave touch the same file.
Cross-batch high-risk files: only `README.md` (T14, last wave) and the i18n JSONs
(T02, append-only). `App.tsx`, `Layout.tsx`, `src/cli/main.py`,
`src/database/models.py`, `src/api/app.py`, `src/database/repository.py` and `bats/`
are **not touched**.

## Key design decisions

1. **New query module instead of editing `repository.py`.** This avoids conflicts with the
   parallel batch. `TradeQueries(repo)` reuses `repo.engine` and
   `repo.get_latest_prices_batch`. Existing repo methods stay (callers and tests
   unchanged). Follow-up (not in scope): make the repo methods delegate.
2. **Server-side vs client-side filtering.** The Marketplace listings and duplicates are
   paginated/unbounded → server-side. My-trades (≤100) and partner matches are
   bounded → client-side via the pure `cardListFilter.ts`.
3. **Backward-compatible endpoints.** The new params are optional, and their defaults give the
   current order (`name asc` for listings, `quantity desc, name` for duplicates).
   Invalid `sort_by`/`sort_dir` → 422 (regex `pattern` + whitelist dict).
4. **Route ordering gotcha.** `GET /marketplace/listings/sets` must be declared
   before `GET /marketplace/listings/{share_code}`.
5. **Grid preference is shared** (single `useGridSize` localStorage key). This is intentional
   and consistent across pages.
6. **MyCollection shares UI, not state.** Only the sticky bar markup moves into
   `CardFilterBar`. MyCollection's state/URL logic is untouched, and its existing tests
   are the regression guard (they must pass unmodified).

## Global acceptance criteria

- [ ] AC1: `CardFilterBar` is used by MyCollection, Marketplace, MyTrades and TradeMatchesPage.
- [ ] AC2: All trade grids use `GRID_SIZE_CONFIG[gridSize]` and the `GridSizeToggle`.
- [ ] AC3: Marketplace: server-side search + set + sort (name/set/number/price), URL-synced (`name`,`set`,`sort`,`dir`), infinite scroll.
- [ ] AC4: MyTrades: search + set + sort + status chips + buyer/seller tabs, rendered as tiles.
- [ ] AC5: TradeMatches: duplicates filtered server-side, matches filtered client-side, slate palette.
- [ ] AC6: `/marketplace/listings` and `/trade/duplicates` accept the new params (422 on invalid) and keep their defaults. `/marketplace/listings/sets` and `/trade/duplicates/sets` return set facets.
- [ ] AC7: No MyCollection regression. All pre-existing frontend tests pass **unmodified**, except the ones this feature explicitly owns (`TradeMatchesPage.test.tsx`, `DuplicatesList.test.tsx`).
- [ ] AC8: `pytest tests/ --cov=src --cov-report=term-missing`, `cd frontend && npm test`, `cd frontend && npm run build` and `ruff check src/` are all green. The new backend module has ≥90% coverage.
- [ ] PRD, two diagrams and the README note are delivered.

## Test impact (existing tests exercising touched code)

- `frontend/src/pages/__tests__/TradeMatchesPage.test.tsx`: owned by T11 (update the mocks for the new fetcher params and add `useGridSize`/router wrappers if needed).
- `frontend/src/components/__tests__/DuplicatesList.test.tsx`: owned by T11 (the new `gridClasses` prop and palette changes).
- `frontend/src/pages/__tests__/MyCollection*.test.tsx`, `CollectionCardTile3D.test.tsx`, `MyCollectionAcquisitionFilter.test.tsx`: guard for T12. **Must not be edited.**
- `frontend/src/components/__tests__/SetIconFilter.test.tsx`: unaffected (the component is not modified).
- `tests/marketplace/test_router.py`, `tests/marketplace/test_service.py`, `tests/api/test_trade_match_router.py`, `tests/api/test_wishlist_repo.py` (`get_user_duplicates`): existing tests must keep passing.

## Diagrams

- `docs/diagrams/F174-architecture.mmd`: owner T13
- `docs/diagrams/F174-journey.mmd`: owner T13
