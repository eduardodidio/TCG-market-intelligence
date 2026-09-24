# F174 — Component: Trade pages alignment

All pages use `CardFilterBar` + `useCardListFilters` + `useGridSize` from
`02-frontend-kit.md`, and a grid of `grid ${GRID_SIZE_CONFIG[gridSize].gridClasses}`.
Loading uses `SkeletonCard` inside the same grid (8 items), empty uses `EmptyState`, and errors use
`ErrorBanner`. Keep the page-level `Breadcrumb` and titles. Palette: `slate-*`
dark (no `bg-white`/`gray-*`/`dark:` pairs). Keep **all existing data-testids**
that tests or other code reference.

## Marketplace (`frontend/src/pages/Marketplace.tsx`, route `/marketplace`)
- Move `MarketplaceCardTile` to **new** `frontend/src/components/MarketplaceCardTile.tsx`
  and add a `compact?: boolean` prop. When compact is set, hide the CopyCodeButton and the fee line and
  use a smaller padding (mirrors `CollectionCardTile compact`). Keep testids
  `marketplace-card-{entry_id}`, `interest-btn-{entry_id}`.
- Filters are server-side: `fetchListings({ limit: "40", offset, search, set_code, sort_by, sort_dir })`.
  Default sort is `name-asc`. Set options come from new `fetchListingSets()` →
  `GET /api/v1/marketplace/listings/sets` → `{ sets: {set_code,set_name,count}[] }`
  mapped to `{ label: set_name || set_code.toUpperCase(), value: set_code }`.
- Infinite scroll: page size 40. `hasMore = page.length === 40`. Use `useInfiniteScroll`
  with a sentinel `<div ref={sentinelRef} data-testid="marketplace-sentinel" />`.
  Guard against stale responses with a `fetchIdRef` counter (the pattern in MyCollection).
- Changing any filter resets offset to 0 and replaces the list.
- Keep the "Minhas trocas" link, the interest modal and the success toast.
- The old `setSearchParams({ search })` URL key `search` is replaced by `name`.
  For backward compatibility, if `?search=` is present on first load, seed the search from it.
- `api/marketplace.ts`: add `fetchListingSets(): Promise<{ sets: ListingSet[] }>`
  and export `interface ListingSet { set_code: string; set_name: string | null; count: number }`.

## MyTrades (`frontend/src/pages/MyTrades.tsx`, route `/marketplace/my-trades`)
- Data: unchanged `fetchMyTrades()` (≤100 rows). All filtering is **client-side**
  with `filterCardList`/`sortCardList`. Accessors: name=`card_name`,
  setCode=`set_code`, number=`collector_number`, date=`created_at`, status=`status`.
- Keep the buyer/seller tabs (`trade-tabs`, `tab-buyer`, `tab-seller`, with counts computed
  **after** search/set/status filtering). Tab state goes to the URL param `tab` (the hook
  preserves it).
- Status chips via `FilterChips` inside `CardFilterBar` children. Options:
  pending/accepted/completed/rejected/cancelled, labels `tradeFilters.status.<s>`. The
  status filter is held in local state.
- Set options come from `buildSetOptions(trades)`.
- Layout: grid of the new tile-style `TradeCard` (see below) with `compact` from `GRID_SIZE_CONFIG`.
- Fix the existing bug: the empty state message for the seller tab uses `marketplace.noListings`
  for both tabs. Use `tradeFilters.noTradesBuyer` / `tradeFilters.noTradesSeller`,
  and `tradeFilters.noResults` when filters exclude everything.
- Remove the dead `if (result.both_confirmed) … else …` duplicate branch
  (both call `loadTrades()`).

## TradeCard (`frontend/src/components/TradeCard.tsx`)
Convert it from a horizontal row to a **collection-style tile**: `Card3DTilt` wrapper,
`aspect-[5/7]` image (`CardImage` with `scryfallImageUrl(set, number)` +
`scryfallImageByName(card_name)` fallback), a status badge at the top-left (keep
`trade-status-{id}` and `STATUS_STYLES`), a role label, a fee line, and action buttons
full-width below. Add a `compact?: boolean` prop (hides the counterparty code and fee line).
Keep testids `trade-card-{id}`, `accept-btn-{id}`, `reject-btn-{id}`,
`confirm-btn-{id}`, `trade-completed-{id}`, `trade-pending-{id}`. Props stay the same
except for the new optional `compact`. Status text is shown via `t("tradeFilters.status.<s>")`
instead of the raw status string.

## TradeMatchesPage (`frontend/src/pages/TradeMatchesPage.tsx`)
- One `CardFilterBar` is shown above the tab content. Sort options depend on the tab:
  duplicates → `DUPLICATES_SORT_OPTIONS` (default `quantity-desc`), and
  theyHave/theyWant → `MATCH_SORT_OPTIONS` (default `name-asc`).
  Hint: call `useCardListFilters` once and, when switching tabs, reset the sort to that tab's default.
- **Duplicates** are filtered server-side: `fetchDuplicates({ limit: "200", search, set_code, sort_by, sort_dir })`,
  with set options from new `fetchDuplicateSets()` → `GET /api/v1/trade/duplicates/sets`
  (an `ApiResponse<ListingSet[]>` envelope via `apiGet`). The `useApi` fetcher deps must include the filters.
- **theyHave/theyWant** are filtered client-side over `match.matched_cards` (accessors:
  name=`name_en`, setCode=`set_code`). Partners with 0 remaining cards are hidden,
  and set options are built from all matched cards across partners. The partner
  expandable card stays. Its inner grid uses `GRID_SIZE_CONFIG[gridSize].gridClasses`.
- `DuplicatesList.tsx`: add an optional `gridClasses?: string` prop. When provided, it
  replaces the hard-coded grid classes. When it is omitted, the existing `compact`
  behaviour is kept (today TradeMatchesPage is its only caller, but keep the
  default for safety).
- Palette: convert `gray-*`/`bg-white`/`dark:` classes on this page (and in
  `DuplicatesList` tiles) to the `slate-*` dark palette. Tab bar: keep testids
  `tab-duplicates`, `tab-theyHave`, `tab-theyWant`, `matches-list`,
  `partner-card`, `matched-card`, `duplicate-card`.
- `api/tradeMatch.ts`: add `fetchDuplicateSets()`. `fetchDuplicates(params)` already
  accepts params.

## MyCollection adoption (`frontend/src/pages/MyCollection.tsx`)
Replace **only** the sticky container + search/sort row + SetIconFilter with
`<CardFilterBar …>` and pass the acquisition chips, mobile actions row and
desktop actions row as `children` unchanged. Do **not** pass `gridSize` (the page
keeps its two responsive GridSizeToggle placements inside children). State,
URL sync and fetching logic stay untouched. All `MyCollection*.test.tsx`,
`CollectionCardTile3D.test.tsx` etc. must pass **without modification**.

## i18n keys (added by F174-T02 in a new top-level `tradeFilters` block)
```json
"tradeFilters": {
  "sortQuantityDesc": "Quantity (High-Low)",
  "sortNewest": "Newest first",
  "sortOldest": "Oldest first",
  "sortStatus": "Status",
  "statusLabel": "Status",
  "status": { "pending": "Pending", "accepted": "Accepted", "rejected": "Rejected", "completed": "Completed", "cancelled": "Cancelled" },
  "noResults": "No cards match the current filters.",
  "noTradesBuyer": "You haven't expressed interest in any card yet.",
  "noTradesSeller": "No one has requested your cards yet.",
  "searchPlaceholder": "Search trades by card name..."
}
```
pt-BR: "Quantidade (maior-menor)", "Mais recentes", "Mais antigas", "Status",
"Status", {Pendente, Aceita, Recusada, Concluída, Cancelada},
"Nenhuma carta corresponde aos filtros.", "Você ainda não demonstrou interesse em nenhuma carta.",
"Ninguém solicitou suas cartas ainda.", "Buscar trocas pelo nome da carta...".
