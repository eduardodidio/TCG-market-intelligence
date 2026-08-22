# F40 -- Pagina Global de Mercado (Global Market Page)

**Status:** planned
**Created:** 2026-08-21
**Dependencies:** F35 (Top Decks by Value), F36 (Trending Cards Engine), F37 (Scheduled Scans)

## Summary

Build a unified Market page that composes existing data endpoints and
components from F34 (History Metrics), F35 (Top Decks), and F36 (Trending
Cards) into a single public dashboard. The page is a COMPOSITION layer --
it introduces one thin backend endpoint for aggregated market stats and
assembles previously-built frontend sections into a cohesive view.

This is NOT a feature that builds new analytics engines or data pipelines.
It is a presentation feature that reuses existing infrastructure.

## User Story

As a visitor or collector, I want a single Market page where I can see
the overall market health (total cards tracked, average price, price
movement), the hottest gainers and losers, the most volatile cards, and
the top decks by value -- all in one place with a shared period selector
-- so I can quickly assess the market without navigating multiple pages.

## Current State Analysis

### What Already Exists (after F34, F35, F36 ship)

1. **Market stats** (`GET /market/stats`): total cards, total observations,
   avg price, date range. Already in `market.py` router.

2. **Market movers** (`GET /market/movers`): top gainers/losers by raw %
   change. Already in `market.py` router. Frontend: `MoversTable`,
   `MoversPreview` components.

3. **Trending engine** (F36, planned): `GET /market/trending/gainers` and
   `GET /market/trending/losers` with composite scores, consistency,
   observation density. Frontend: `TrendingCard`, `TrendingSection`
   components.

4. **Deck ranking** (F35, planned): `GET /decks/ranking` with deck values,
   sparklines, value change. Frontend: `TopDecksPage`, `DeckSparkline`
   components.

5. **History metrics** (F34, planned): `GET /collection/{id}/metrics` with
   MA, ATH/ATL, volatility, momentum, performance score. Frontend:
   `MetricsPanel` component.

6. **Dashboard** (`Dashboard.tsx`): already fetches market stats + movers
   preview. Shows KPI cards.

7. **MarketMovers page** (`MarketMovers.tsx`): dedicated movers page with
   period/limit controls. Route: `/market/movers`.

8. **Shared components**: `KpiCard`, `MoversPreview`, `MoversTable`,
   `ErrorBanner`, `EmptyState`, `SkeletonTable`, `SkeletonKpi`,
   `CurrencyIndicator`, period selector pattern (button group).

9. **Navigation**: sidebar `NAV_ITEMS` in `Layout.tsx`, lazy-loaded routes
   in `App.tsx`.

### Gaps to Fill

1. **No aggregated market summary endpoint**: the existing `/market/stats`
   returns raw counts. Need a composite endpoint that adds avg price
   change across all tracked cards, count of gainers vs losers, and
   market "health" indicator (up/down/flat overall).

2. **No unified Market page**: movers, trending, and deck ranking live on
   separate pages. No single view combines them.

3. **No shared period selector**: each section manages its own period
   state. Need a global period context that propagates to all sections.

4. **No "Most Volatile" section**: F36 computes consistency and change
   scores but does not expose a "most volatile" view (high change +
   LOW consistency = volatile). This is a simple re-ranking of trending
   data with different sort criteria.

## Architecture

### Backend Changes

#### 1. Market summary endpoint (`GET /market/summary`)

Add to existing `src/api/routers/market.py`. This is a thin aggregation
layer that calls existing repository methods and the trending service
(from F36).

Query parameters:
- `period`: `7d` | `30d` | `90d` (default `30d`)
- `currency`: `BRL` | `USD` | `PILA` (default `BRL`)

Response schema `MarketSummaryResponse`:

```python
class MarketSummaryResponse(BaseModel):
    total_cards_tracked: int
    total_observations: int
    avg_price: float | None
    avg_price_change_pct: float | None   # mean % change across all cards
    gainers_count: int                    # cards with positive change
    losers_count: int                     # cards with negative change
    unchanged_count: int                  # cards with 0% change
    market_direction: str                 # "up" | "down" | "flat"
    period: str
    currency: str
    computed_at: datetime
```

Implementation:
1. Call existing `repo.get_market_stats()` for totals.
2. Call `repo.get_movers()` (or the trending service if available) to
   count gainers vs losers and compute average change.
3. Determine `market_direction` based on `gainers_count > losers_count`.
4. Cache result for 30 minutes (reuse F44 AggregateCache if available,
   otherwise simple dict cache with TTL).

#### 2. Most Volatile endpoint (`GET /market/volatile`)

Add to `src/api/routers/market.py`. Reuses the trending service from F36
but ranks by HIGH change percentage with LOW consistency (the inverse of
what "trending" rewards). This finds cards with large price swings in
both directions.

Query parameters:
- `period`: `7d` | `30d` | `90d` (default `30d`)
- `limit`: int (default 10, max 50)
- `currency`: `BRL` | `USD` | `PILA`

Response: reuses `TrendingCardEntry` schema from F36 (same fields apply).

Implementation:
1. Call trending service `get_trending()` for both directions.
2. Merge and re-rank by `|change_pct| * (1 - consistency)` -- high
   absolute change AND low consistency = most volatile.
3. Return top N.

If F36 is not yet shipped, this endpoint returns an empty list with a
`501 Not Implemented` or graceful empty response.

#### 3. Pydantic schemas

New file `src/api/schemas/market_summary.py`:
- `MarketSummaryResponse` as described above.

### Frontend Changes

#### 1. MarketPage (`frontend/src/pages/MarketPage.tsx`)

New page at route `/market`. Public (no auth required). Replaces
`/market/movers` as the primary market entry point (movers page remains
accessible but is de-emphasized in nav).

Layout: single-column scrolling page with sections. A sticky period
selector at the top applies to all sections.

Sections (top to bottom):
1. **Market Summary** -- row of KPI cards (reuse `KpiCard` component):
   - Total cards tracked
   - Average price (with currency)
   - Avg price change % (green/red arrow)
   - Gainers vs Losers ratio (e.g., "67% up")
   - Market direction badge ("Bullish" / "Bearish" / "Flat")

2. **Top Gainers** -- horizontal card row (reuse `TrendingSection` from
   F36 with `direction="up"`). Shows top 10 cards trending up with
   images, price change arrows, composite scores.

3. **Top Losers** -- horizontal card row (reuse `TrendingSection` from
   F36 with `direction="down"`). Same layout as gainers.

4. **Most Volatile** -- horizontal card row. Same component pattern as
   trending sections but sourced from `/market/volatile`.

5. **Top Decks by Value** -- compact ranked list (top 5). Reuses the
   `DeckRankingEntry` data shape from F35. Shows deck name, total value,
   value change badge, and mini sparkline (reuse `DeckSparkline` from
   F35). Links to `/decks/ranking` for full view.

Each section has a "View All" link to the corresponding dedicated page.

#### 2. Shared period selector

The period selector (7d / 30d / 90d button group) is already a pattern
used in `MarketMovers.tsx`. Extract it into a reusable component
`PeriodSelector.tsx` and use it on the Market page. All sections receive
the selected period as a prop.

#### 3. API client functions

Add to `frontend/src/api/market.ts`:
- `fetchMarketSummary(params)` -- calls `GET /api/v1/market/summary`
- `fetchVolatile(params)` -- calls `GET /api/v1/market/volatile`

#### 4. Section skeleton loaders

Each section shows a skeleton while loading. Reuse `SkeletonKpi` for
summary, `SkeletonTable` or a new `SkeletonCardRow` for horizontal card
rows.

#### 5. Navigation update

Change the "Market Movers" nav item in `Layout.tsx` to "Market" pointing
to `/market`. The old `/market/movers` route remains functional but is
no longer in the primary nav.

#### 6. i18n keys

Add keys for: page title, section headers, market direction labels
("bullish"/"bearish"/"flat"), KPI labels, "view all" links, empty states.

### No Database Changes

All data comes from existing tables via existing queries. The summary
endpoint is pure aggregation of existing data.

### Graceful Degradation

If dependency features (F35, F36) have not shipped yet:
- Trending sections: show the existing `MoversTable`/`MoversPreview` as
  fallback (data from `/market/movers`).
- Top Decks section: hide entirely if `/decks/ranking` returns 404.
- Most Volatile section: hide if `/market/volatile` returns empty.
- Market Summary: always works (uses existing `/market/stats` data).

## Acceptance Criteria

1. `GET /market/summary?period=30d` returns aggregated market stats
   including avg price change, gainers/losers counts, market direction
2. `GET /market/volatile?period=30d&limit=10` returns cards ranked by
   volatility (high change + low consistency)
3. Market page accessible at `/market` without authentication
4. Market Summary section shows KPI cards with total cards, avg price,
   avg change %, gainers ratio, market direction
5. Top Gainers section shows horizontal scrollable card row (reuses
   TrendingSection from F36 or MoversPreview as fallback)
6. Top Losers section shows horizontal scrollable card row
7. Most Volatile section shows cards with large, inconsistent price swings
8. Top Decks section shows top 5 ranked decks with sparklines
9. Period selector (7d/30d/90d) is shared across all sections
10. "View All" links navigate to dedicated pages (/market/movers,
    /market/trending, /decks/ranking)
11. Currency toggle applies globally to all sections
12. Page degrades gracefully when dependency features are not yet shipped
13. All new backend code has unit tests
14. All new frontend components have tests
15. i18n keys added for EN and PT-BR
16. Navigation updated: "Market" replaces "Market Movers" in sidebar

## Constraints

- Depends on F35, F36 shipping first (for trending and deck components).
  Can ship partially without them via graceful degradation.
- F44 (Shared Data Architecture) is beneficial but NOT required -- the
  summary endpoint can use Repository directly if MarketDataService is
  not yet available.
- No new database tables or columns.
- Public page -- no authentication required.
- Reuse existing components maximally -- do NOT rebuild MoversTable,
  TrendingSection, DeckSparkline, KpiCard.
- PeriodSelector extracted as a shared component, not duplicated.

## Tasks

| Task | File | Wave | Description |
|------|------|------|-------------|
| T01 | F40-T01.md | 0 | Backend: market summary + volatile endpoints |
| T02 | F40-T02.md | 1 | Frontend: PeriodSelector extraction + MarketSummary section |
| T03 | F40-T03.md | 1 | Frontend: MarketPage shell + section composition |
| T04 | F40-T04.md | 2 | Frontend: navigation update + i18n + integration |
| T05 | F40-T05.md | 3 | Tests: backend + frontend comprehensive coverage |

## Waves

- **Wave 0** (1 task): T01 -- backend endpoints. No frontend dependency.
  Unblocks all frontend work.
- **Wave 1** (2 tasks, parallel): T02 (PeriodSelector + MarketSummary KPI
  section), T03 (MarketPage shell wiring sections together + API client).
  T02 produces the shared component; T03 builds the page layout. They
  touch different files and can be developed in parallel.
- **Wave 2** (1 task): T04 -- navigation wiring, i18n, final integration.
  Depends on the page and components from Wave 1.
- **Wave 3** (1 task): T05 -- comprehensive test coverage for all new code.

## File Inventory

### New Files
- `src/api/schemas/market_summary.py` -- Pydantic schemas (T01)
- `frontend/src/components/PeriodSelector.tsx` -- reusable period toggle (T02)
- `frontend/src/components/MarketSummaryKpis.tsx` -- KPI card row (T02)
- `frontend/src/components/TopDecksPreview.tsx` -- compact deck ranking (T03)
- `frontend/src/components/VolatileSection.tsx` -- volatile cards row (T03)
- `frontend/src/pages/MarketPage.tsx` -- main market page (T03)
- `tests/unit/api/test_market_summary.py` -- endpoint tests (T05)
- `frontend/tests/components/PeriodSelector.test.tsx` -- component tests (T05)
- `frontend/tests/components/MarketSummaryKpis.test.tsx` -- component tests (T05)
- `frontend/tests/pages/MarketPage.test.tsx` -- page tests (T05)

### Modified Files
- `src/api/routers/market.py` -- add summary + volatile endpoints (T01)
- `frontend/src/api/market.ts` -- add fetchMarketSummary, fetchVolatile (T03)
- `frontend/src/types/api.ts` -- add MarketSummary, VolatileCard types (T03)
- `frontend/src/pages/MarketMovers.tsx` -- use extracted PeriodSelector (T02)
- `frontend/src/components/Layout.tsx` -- update nav item (T04)
- `frontend/src/App.tsx` -- add /market route (T04)
- `frontend/src/i18n/locales/en.json` -- market page i18n keys (T04)
- `frontend/src/i18n/locales/pt-BR.json` -- market page i18n keys (T04)

### No Cross-Wave File Conflicts
- Wave 0: `market.py` router + new schema file (T01)
- Wave 1: `PeriodSelector.tsx` + `MarketSummaryKpis.tsx` + `MarketMovers.tsx`
  (T02), `MarketPage.tsx` + `TopDecksPreview.tsx` + `VolatileSection.tsx` +
  `market.ts` + `api.ts` types (T03) -- no overlap
- Wave 2: `Layout.tsx` + `App.tsx` + i18n files (T04) -- no overlap with Wave 1
- Wave 3: test files only (T05)

### Reused Components (NOT modified, just imported)
- `KpiCard` -- for market summary stats
- `TrendingSection` / `TrendingCard` (F36) -- for gainers/losers sections
- `MoversPreview` / `MoversTable` -- fallback if F36 not shipped
- `DeckSparkline` (F35) -- for top decks preview
- `ErrorBanner`, `EmptyState`, `SkeletonKpi`, `SkeletonTable` -- shared UI
- `CurrencyIndicator` -- for price display
