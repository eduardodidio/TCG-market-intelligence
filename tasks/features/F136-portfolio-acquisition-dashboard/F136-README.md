# F136 -- Portfolio Dashboard Revision (Acquisition-Only View)

**Status:** planned
**Branch:** homol
**Depends on:** F135 (acquisition prices must be populated first)

## Problem Statement

The main Dashboard page shows general collection statistics (unique cards, total
copies, estimated value, coverage) but lacks investment-focused KPIs. The
existing `DashboardInvestmentSummary` component shows portfolio totals but has no
P&L sparkline and no actionable link for cards missing acquisition prices.

Meanwhile, the collection movers endpoint (`GET /api/v1/collection/movers`)
returns price changes for ALL cards in the collection, including cards without
acquisition prices -- this muddies the investment signal. There is no way to
filter the collection list by acquisition-price status, so users cannot easily
find and fix cards that are missing cost basis data.

The `PortfolioSummary` schema already has an `unpriced_card_count` field but it
is never populated by the backend.

## Goals

1. Add a `has_acquisition_price` filter to the collection list endpoint so users
   can view only investment-tracked cards or only cards missing cost basis.
2. Populate `cards_without_acquisition` (and the existing `unpriced_card_count`)
   in the portfolio summary so the dashboard can show an actionable alert.
3. Add a P&L sparkline (mini portfolio history chart) on the main Dashboard.
4. Add a "X cards without acquisition price" alert on the Dashboard that links
   directly to the collection filtered to show only those cards.
5. Add filter chips on the Collection page for acquisition-price status.
6. Audit all portfolio-related components for acquisition-only consistency.

## Acceptance Criteria

- `GET /api/v1/collection?has_acquisition_price=true` returns only entries with
  `acquisition_price IS NOT NULL`.
- `GET /api/v1/collection?has_acquisition_price=false` returns only entries with
  `acquisition_price IS NULL`.
- `GET /api/v1/collection/portfolio-summary` response includes
  `cards_without_acquisition` count.
- `GET /api/v1/collection/movers?investment_only=true` only considers cards with
  acquisition prices.
- Dashboard shows portfolio KPIs (invested, current, P&L, P&L%) with a mini
  sparkline from portfolio history.
- Dashboard shows an amber alert when cards lack acquisition prices, linking to
  the filtered collection view.
- Collection page has a toggle/chip to filter by acquisition-price status.
- All portfolio components (PortfolioDashboard, CollectionMovers, PnlBadge,
  ExportPnL) use acquisition-only data where appropriate.

## Wave Strategy

### Wave 0 -- Backend Filters (2 tasks, parallel)

| Task | Description |
|------|-------------|
| T01  | Add `has_acquisition_price` filter to collection list endpoint |
| T02  | Add `cards_without_acquisition` to portfolio-summary + `investment_only` param to movers |

### Wave 1 -- Frontend Dashboard & Collection (2 tasks, parallel, depends on Wave 0)

| Task | Description |
|------|-------------|
| T03  | Dashboard revision: portfolio KPIs, P&L sparkline, missing-price alert |
| T04  | Collection filter: acquisition-price filter chips + deep link from dashboard |

### Wave 2 -- Consistency Audit (1 task, depends on Wave 1)

| Task | Description |
|------|-------------|
| T05  | Audit all portfolio components for acquisition-only consistency |

## Key Files

### Backend
- `src/api/routers/collection.py` -- collection list, portfolio-summary, movers endpoints
- `src/api/schemas/collection.py` -- PortfolioSummary, CollectionMoversResponse schemas
- `src/database/repository.py` -- list_collection, count_collection, get_portfolio_invested_total, get_trending_price_data_for_user

### Frontend
- `frontend/src/pages/Dashboard.tsx` -- main dashboard page
- `frontend/src/pages/MyCollection.tsx` -- collection page with filters
- `frontend/src/components/DashboardInvestmentSummary.tsx` -- investment KPI section
- `frontend/src/components/PortfolioDashboard.tsx` -- portfolio dashboard (collection page)
- `frontend/src/components/CollectionMovers.tsx` -- gainers/losers component
- `frontend/src/components/PnlBadge.tsx` -- per-card P&L badge
- `frontend/src/api/collection.ts` -- API client functions

## Constraints

- F135 must ship first so acquisition prices are populated (otherwise all
  filters return empty results).
- The `unpriced_card_count` field already exists in PortfolioSummary schema
  (never populated) -- reuse it rather than adding a duplicate.
- Movers `investment_only` defaults to `false` for backward compatibility.
- Collection filter must work with existing URL search params pattern.
