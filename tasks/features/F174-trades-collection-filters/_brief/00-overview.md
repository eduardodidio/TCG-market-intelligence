# F174 — Overview: Trocas com os mesmos filtros e layout de "Minha Coleção"

## Problem
The Trades area — `Marketplace.tsx` (`/marketplace`), `MyTrades.tsx`
(`/marketplace/my-trades`), `TradeMatchesPage.tsx` (duplicates / they-have /
they-want) and `TradeCard.tsx` — uses a different UI from "Minha Coleção"
(`MyCollection.tsx`). It has only a search bar (Marketplace), or no filters at
all (MyTrades, TradeMatches). Grids are hard-coded (`grid-cols-2 … lg:grid-cols-5`),
MyTrades is a vertical list of horizontal rows, and TradeMatches uses light/dark
`gray-*` classes while the rest of the app is `slate-*` dark-only. The backend
endpoints for trades are missing sort parameters, set facets, and
(for duplicates) search/set filters.

## Scope
1. **Shared filter kit (frontend):** extract the collection filter bar into a
   reusable `CardFilterBar` component. It composes the existing `SearchBar`,
   `SortSelect`, `SetIconFilter` and `GridSizeToggle` and uses the same sticky
   markup as MyCollection. Add a URL-synced `useCardListFilters` hook and pure
   client-side filter/sort helpers.
2. **Backend:** add sort (`sort_by`/`sort_dir`) to `GET /marketplace/listings`,
   add search/set/sort to `GET /trade/duplicates`, and add set-facet endpoints
   `GET /marketplace/listings/sets` and `GET /trade/duplicates/sets`. All of
   these are **additive and backward-compatible** (the defaults keep today's order).
3. **Trade pages:** Marketplace, MyTrades and TradeMatches adopt
   `CardFilterBar`, `GRID_SIZE_CONFIG[gridSize]` grids, the same tile anatomy
   (aspect-[5/7] image, badges, slate palette) and `SkeletonCard` loading.
   MyTrades also gets status `FilterChips`.
4. **MyCollection adopts `CardFilterBar`** for its search + sort + set row, with
   **no behaviour/testid regression**, so the component is truly shared.
5. Docs: PRD, `F174-architecture.mmd`, `F174-journey.mmd`, README note.

## Out of scope
- Changing the trade workflow (interest → accept → confirm), fees or credits.
- Moving MyCollection state into `useCardListFilters` (only the UI bar is shared).
- Refactoring `src/database/repository.py` (new queries go in a NEW module;
  see `01-backend.md`).
- A real slide-in "drawer": the project's "mobile filter drawer" (F163) is
  the mobile actions dropdown plus `sm:hidden` rows. The trade pages follow
  the same responsive pattern.

## Constraints
- Batch F171–F179 runs in parallel. **Do not edit** `frontend/src/App.tsx`,
  `frontend/src/components/Layout.tsx`, `src/cli/main.py`,
  `src/database/models.py`, `src/api/app.py` or `src/database/repository.py`.
  No new routes or menu items are needed, and routers are already registered.
- `README.md` is edited only by the dedicated last-wave task F174-T14.
- i18n JSON (`en.json`, `pt-BR.json`) is shared across the batch. Only F174-T02
  touches it, and it adds ONE new top-level `"tradeFilters"` block at the end of
  the file. Do not edit existing blocks.
- No new dependencies (frontend or backend).
- Branch: work on `homol` (or the orchestrator's worktree branch cut from
  `homol`). Never commit to `main`. Stage files one by one (no `git add -A`).
- Tests: backend `pytest tests/ --cov=src --cov-report=term-missing`, frontend
  `cd frontend && npm test`, build `cd frontend && npm run build`, lint
  `ruff check src/`.

## Acceptance criteria (titles — details in component shards)
- AC1 — `CardFilterBar` exists and is used by MyCollection, Marketplace, MyTrades and TradeMatches.
- AC2 — All trade grids use `GRID_SIZE_CONFIG[gridSize]` and the shared `GridSizeToggle` (the preference is shared via `useGridSize`).
- AC3 — Marketplace supports search + set filter + sort (name/set/number/price), server-side, URL-synced, with infinite scroll.
- AC4 — MyTrades supports search + set + sort + status chips + buyer/seller tabs, and shows trades as tiles.
- AC5 — TradeMatches supports search + set + sort on duplicates (server-side) and search + set on partner matches (client-side).
- AC6 — New/extended endpoints validate input (422 on invalid `sort_by`/`sort_dir`) and keep their old defaults.
- AC7 — Zero regression on MyCollection: all existing `MyCollection*.test.tsx` pass unmodified, and the `sticky-filter-bar` / `sort-select` / `set-icon-filter` testids are kept.
- AC8 — PRD, two diagrams and the README note are delivered. Backend and frontend test suites, the build and ruff are green.
