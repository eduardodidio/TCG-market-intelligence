# PRD: F07 - Front-end Dashboard

**Status:** Delivered
**Date:** 2026-08-18
**Author:** Eduardo Rutkoski Didio

## Problem

TCG Market Intelligence collects pricing data and exposes it through a REST
API (F06), but there is no visual interface for exploring the data. Users must
use the CLI or send raw HTTP requests to view card prices, trends, and market
movers. A web dashboard is needed to make the data accessible and actionable
for non-technical users and for quick visual analysis.

## User Personas

- **Data Analyst / Collector** -- tracks card prices over time, looks for
  buying opportunities (price dips), monitors portfolio value trends. Needs
  quick access to price charts, historical comparisons, and market movers.

## Goals

1. Provide a market overview dashboard with key performance indicators (total
   cards, total sets, total observations, average price)
2. Enable card browsing with search, set filtering, and cursor-based pagination
3. Display interactive price history charts with configurable time periods
4. Show market movers (top gainers and losers) with period selection
5. Deliver a responsive, dark-themed UI suitable for extended data analysis

## Pages

### 1. Dashboard (Home)

- KPI cards showing aggregate market statistics (total cards, sets,
  observations, average price)
- Market movers preview (top 5 gainers and losers, 7-day period)
- Quick navigation to Cards and Market Movers pages

### 2. Cards (Browse)

- Search bar with debounced input (300ms)
- Set filter chips for narrowing results
- Card grid/list with name, set, and current price
- Cursor-based pagination (next/previous)
- Click-through to Card Detail page

### 3. Card Detail

- Card identity information (name, set, collector number)
- Interactive price history chart (Recharts line chart)
- Period selector: 30d, 90d, 180d, 1y, 3y
- Price series: median, TCG, last sold
- Source card information (external ID, SKU, URL)

### 4. Market Movers

- Period selector: 7d, 30d, 90d
- Gainers table (top cards by price increase %)
- Losers table (top cards by price decrease %)
- Card name links to Card Detail page

## Functional Requirements

| ID | Requirement |
|----|-------------|
| FR-01 | Dashboard displays 4 KPI cards from `/api/v1/market/stats` |
| FR-02 | Dashboard shows top 5 gainers and losers from `/api/v1/market/movers` |
| FR-03 | Cards page fetches from `/api/v1/cards` with `name`, `set` query params |
| FR-04 | Cards page supports cursor-based pagination (`cursor`, `limit` params) |
| FR-05 | Card Detail fetches card info from `/api/v1/cards/{id}` |
| FR-06 | Card Detail fetches price history from `/api/v1/cards/{id}/history` |
| FR-07 | Card Detail period selector updates chart with new period param |
| FR-08 | Market Movers fetches from `/api/v1/market/movers` with period param |
| FR-09 | Search input is debounced (300ms) to avoid excessive API calls |
| FR-10 | Set filter chips are populated from `/api/v1/sets` |
| FR-11 | All pages display loading skeletons while data is being fetched |
| FR-12 | All pages display error banners when API calls fail |

## Non-Functional Requirements

| ID | Requirement |
|----|-------------|
| NFR-01 | Dark theme by default (Tailwind `dark` mode) |
| NFR-02 | Responsive layout: desktop (1024px+), tablet (768px+), mobile (320px+) |
| NFR-03 | Initial page load under 3 seconds on localhost |
| NFR-04 | Accessible: semantic HTML, ARIA labels on interactive elements |
| NFR-05 | Component test coverage with Vitest + React Testing Library |
| NFR-06 | TypeScript strict mode -- no `any` types in production code |

## API Dependency

The front-end requires the F06 REST API server to be running at
`http://localhost:8000`. The Vite dev server proxies `/api` and `/health`
requests to the backend, so no CORS configuration is needed during
development.

## Out of Scope (this phase)

- Authentication and authorization
- User accounts and portfolio tracking
- AI-powered recommendations or alerts
- Card image hosting or display
- Deployment configuration (Docker, cloud hosting)
- Server-side rendering (SSR)
- Internationalization (i18n)
- Real-time updates (WebSocket/SSE)
- Mobile native app

## Technical Stack

See [ADR-0003](../adr/0003-frontend-stack.md) for the full decision record.

| Layer | Technology |
|-------|------------|
| Build | Vite 6 |
| UI | React 19, TypeScript 5.8 |
| Styling | Tailwind CSS 3.4 |
| Charts | Recharts 2.15 |
| Routing | React Router v7 |
| Testing | Vitest 3.2, React Testing Library 16.3 |

## Acceptance Criteria

1. **AC1:** Dashboard page renders 4 KPI cards and market movers preview
2. **AC2:** Cards page supports search, set filtering, and pagination
3. **AC3:** Card Detail page displays interactive price chart with period
   selector
4. **AC4:** Market Movers page shows gainers and losers tables with period
   selector
5. **AC5:** All pages show loading states and error handling
6. **AC6:** Dark theme applied consistently across all pages
7. **AC7:** Responsive layout works on desktop and tablet viewports
8. **AC8:** Component tests pass with Vitest
9. **AC9:** Documentation complete (ADR, PRD, diagrams, README)
