# F174 — Component: Docs (PRD, diagrams, README)

## PRD — `docs/prd/F174-trades-collection-filters.md`
Follow `docs/prd/template.md`. Include: problem (the 00-overview "Problem" section), personas
(trader browsing the marketplace, seller managing requests), goals/non-goals,
functional requirements = AC1–AC8, API changes (01-backend), UX notes
(03-trade-pages), risks (batch conflicts → new-module strategy, MyCollection
regression → unmodified tests as the guard, price-sort semantics: sorting uses the Liga
price while the displayed price uses `get_latest_prices_batch`, so they can differ
slightly — accepted, same as MyCollection).

## Diagrams — under `docs/diagrams/` (templates in `docs/diagrams/templates/`)
1. `F174-architecture.mmd` — `flowchart TB`. Subgraphs:
   - **Frontend shared kit:** CardFilterBar (→ SearchBar, SortSelect, SetIconFilter,
     GridSizeToggle), useCardListFilters (URL params), cardListFilter.ts, tradeSortOptions.ts, useGridSize/GRID_SIZE_CONFIG.
   - **Pages:** MyCollection, Marketplace (+MarketplaceCardTile), MyTrades (+TradeCard, FilterChips), TradeMatchesPage (+DuplicatesList).
   - **API clients:** api/marketplace.ts, api/tradeMatch.ts.
   - **Backend:** routers marketplace.py / trade_match.py → MarketplaceService → TradeQueries (new) → SQLAlchemy (user_collection, shared_collections, price_observations).
   - Edges are labelled with endpoints and params (`sort_by`, `sort_dir`, `set_code`, `search`, `/sets`).
2. `F174-journey.mmd` — `flowchart LR` with swimlanes (`subgraph User`,
   `subgraph Frontend`, `subgraph API`): open Trocas → choose page → type
   search / pick set / change sort / change grid size → URL updated →
   (server-side? → API call → results | client-side → local filter) →
   empty results? → "noResults" empty state → clear filters. Error path:
   API error → ErrorBanner → retry. Marketplace: scroll → load more.
   MyTrades: status chip → tab switch → accept/confirm action.

## README.md (dedicated last-wave task — shared file across the batch)
Add a short bullet under the features/changelog section (match the existing
style — read the file first):
- Trades (Marketplace, My Trades, Trade Matches) now use the same filter bar and
  grid as My Collection: search, set icons, sort, grid size, and status chips.
- New endpoints: `GET /api/v1/marketplace/listings/sets` and `GET /api/v1/trade/duplicates/sets`.
- Extended: `GET /api/v1/marketplace/listings?sort_by&sort_dir` and
  `GET /api/v1/trade/duplicates?search&set_code&sort_by&sort_dir`.
Keep the diff minimal (append-only lines) to reduce merge conflicts with F171–F179.
