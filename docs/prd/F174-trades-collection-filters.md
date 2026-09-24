# PRD F174 — Trades: Collection Filters & Layout

**Feature ID:** F174
**Status:** draft
**Owner:** @eduardodidio
**Date:** 2026-09-24

## Problem

The Trades area — `Marketplace.tsx` (`/marketplace`), `MyTrades.tsx`
(`/marketplace/my-trades`), `TradeMatchesPage.tsx` (duplicates / they-have /
they-want) and `TradeCard.tsx` — uses a different UI from "Minha Coleção"
(`MyCollection.tsx`). It has only a search bar (Marketplace), or no filters
at all (MyTrades, TradeMatches). Grids are hard-coded
(`grid-cols-2 … lg:grid-cols-5`), MyTrades is a vertical list of horizontal
rows, and TradeMatches uses light/dark `gray-*` classes while the rest of
the app is `slate-*` dark-only. The backend endpoints for trades are
missing sort parameters, set facets, and (for duplicates) search/set
filters.

## Personas

- **Trader browsing the marketplace** — wants to search, filter by set and
  sort listings the same way they already browse their own collection.
- **Seller managing requests** — wants to filter/sort their outgoing and
  incoming trades (MyTrades) and duplicate matches (TradeMatches) instead of
  scrolling a flat list.

## Goals

- Unify the Trades pages (Marketplace, MyTrades, TradeMatches) with
  MyCollection's filter bar, grid layout and tile anatomy via one shared
  `CardFilterBar` component.
- Extend the marketplace and duplicates endpoints with sort/search/set-facet
  support, additive and backward-compatible.
- Zero regression on MyCollection while it also adopts the shared component.

## Non-goals

- Changing the trade workflow (interest → accept → confirm), fees or
  credits.
- Moving MyCollection's state management into `useCardListFilters` (only
  the UI bar is shared, not the state hook).
- A real slide-in "drawer" UI — the existing mobile actions dropdown +
  `sm:hidden` rows pattern (F163) is followed instead.

## Scope

### In scope

1. **Shared filter kit (frontend):** `CardFilterBar` composing `SearchBar`,
   `SortSelect`, `SetIconFilter` and `GridSizeToggle`, with the same sticky
   markup as MyCollection. A URL-synced `useCardListFilters` hook and pure
   client-side filter/sort helpers.
2. **Backend:** sort params on `GET /marketplace/listings`, search/set/sort
   on `GET /trade/duplicates`, and new set-facet endpoints
   `GET /marketplace/listings/sets` and `GET /trade/duplicates/sets`. All
   additive; existing defaults preserve today's ordering.
3. **Trade pages:** Marketplace, MyTrades and TradeMatches adopt
   `CardFilterBar`, `GRID_SIZE_CONFIG[gridSize]` grids, the shared tile
   anatomy (aspect-[5/7] image, badges, slate palette) and `SkeletonCard`
   loading. MyTrades also gets status `FilterChips`.
4. **MyCollection adopts `CardFilterBar`** for its search + sort + set row,
   with no behavior/testid regression.
5. Docs: this PRD, `F174-architecture.mmd`, `F174-journey.mmd`, README note.

### Out of scope

- Trade workflow, fees, credits changes.
- Refactoring `src/database/repository.py` (new queries go in a new module,
  `src/marketplace/trade_queries.py`).
- A real slide-in drawer component.

## Functional requirements

- **AC1** — `CardFilterBar` exists and is used by MyCollection, Marketplace,
  MyTrades and TradeMatches.
- **AC2** — All trade grids use `GRID_SIZE_CONFIG[gridSize]` and the shared
  `GridSizeToggle` (preference shared via `useGridSize`).
- **AC3** — Marketplace supports search + set filter + sort
  (name/set/number/price), server-side, URL-synced, with infinite scroll.
- **AC4** — MyTrades supports search + set + sort + status chips +
  buyer/seller tabs, shown as tiles.
- **AC5** — TradeMatches supports search + set + sort on duplicates
  (server-side) and search + set on partner matches (client-side).
- **AC6** — New/extended endpoints validate input (422 on invalid
  `sort_by`/`sort_dir`) and keep their old defaults.
- **AC7** — Zero regression on MyCollection: all existing
  `MyCollection*.test.tsx` pass unmodified, and the `sticky-filter-bar` /
  `sort-select` / `set-icon-filter` testids are kept.
- **AC8** — PRD, two diagrams and the README note are delivered. Backend
  and frontend test suites, the build and ruff are green.
- **AC9** — Work happens on `homol` (or an orchestrator worktree branch cut
  from it); this PRD is written and reviewed before Wave 1 implementation
  starts.

## API changes

| Endpoint | Change | New params | Defaults |
|---|---|---|---|
| `GET /api/v1/marketplace/listings` | Extended | `sort_by: name\|set\|number\|price`, `sort_dir: asc\|desc` | `sort_by=name`, `sort_dir=asc` (matches current order) |
| `GET /api/v1/marketplace/listings/sets` | New | `exclude_user_id` (implicit via optional auth) | — |
| `GET /api/v1/trade/duplicates` | Extended | `search` (max 100 chars), `set_code` (max 10 chars), `sort_by: quantity\|name\|set\|number\|price`, `sort_dir: asc\|desc` | `sort_by=quantity`, `sort_dir=desc` (matches current order) |
| `GET /api/v1/trade/duplicates/sets` | New | — (auth required) | — |

All sort/filter values are resolved through a server-side whitelist dict in
`TradeQueries` (`src/marketplace/trade_queries.py`); invalid `sort_by`/
`sort_dir` are rejected by FastAPI regex `Query` patterns (422) before
reaching the query layer. No user input is interpolated into SQL.

## UX notes

- Filter bar layout, sticky positioning and tile anatomy (aspect-[5/7]
  image, badges, slate-only palette) mirror MyCollection exactly, per
  `_brief/03-trade-pages.md`.
- MyTrades adds status `FilterChips` above the shared filter bar for
  buyer/seller tab context.
- Empty states ("noResults") and `ErrorBanner` + retry follow the existing
  MyCollection pattern.
- Mobile: no dedicated drawer; reuse the F163 mobile actions dropdown +
  `sm:hidden` rows pattern already used elsewhere.

## Risks & mitigations

- **Batch conflicts** (F171–F179 run in parallel touching shared files) →
  mitigated by putting new backend queries in a new module
  (`src/marketplace/trade_queries.py`) instead of editing
  `src/database/repository.py`, and by not touching `App.tsx`,
  `Layout.tsx`, `main.py`, `models.py`, `app.py` or `repository.py`.
- **MyCollection regression** when it adopts `CardFilterBar` → mitigated by
  requiring all existing `MyCollection*.test.tsx` to pass unmodified and by
  keeping the `sticky-filter-bar` / `sort-select` / `set-icon-filter`
  testids stable (AC7).
- **Price-sort semantics** — sorting uses the Liga `mid` price via a
  correlated subquery, while the displayed price comes from
  `get_latest_prices_batch`; these can differ slightly. Accepted, since
  MyCollection has the same behavior today.

## Do not touch (shared files, per batch constraints)

- `frontend/src/App.tsx`
- `frontend/src/components/Layout.tsx`
- `src/cli/main.py`
- `src/database/models.py`
- `src/api/app.py`
- `src/database/repository.py`
- `README.md` (owned exclusively by task F174-T14)
- i18n files `en.json` / `pt-BR.json` (only F174-T02 touches them, appending
  one new `"tradeFilters"` block)

## Out of scope

- Trade workflow (interest → accept → confirm), fees or credit changes.
- Moving MyCollection state into `useCardListFilters`.
- Refactoring `src/database/repository.py`.
- A real slide-in filter drawer.
- New dependencies (frontend or backend) — none are introduced by this
  feature.
