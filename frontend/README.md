# TCG Market Intelligence -- Front-end Dashboard

React SPA for visualizing TCG price data, market trends, and card analytics.
Consumes the F06 REST API.

## Prerequisites

- **Node.js 18+** and **npm**
- **F06 REST API** running at `http://localhost:8000`

Start the API server before running the front-end:

```bash
# From the project root
python -m src.cli.main serve
```

## Setup

```bash
cd frontend
npm install
npm run dev
```

The dev server starts at `http://localhost:5173`. API requests are
automatically proxied to the backend at `http://localhost:8000`.

## Available Scripts

| Script | Command | Description |
|--------|---------|-------------|
| `dev` | `npm run dev` | Start Vite dev server with HMR |
| `build` | `npm run build` | Type-check and build for production |
| `preview` | `npm run preview` | Preview production build locally |
| `test` | `npm run test` | Run tests with Vitest |
| `test:coverage` | `npm run test:coverage` | Run tests with coverage report |
| `lint` | `npm run lint` | Type-check with TypeScript compiler |

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `VITE_API_BASE_URL` | (empty -- uses Vite proxy) | Override API base URL for production builds |

In development, the Vite proxy handles API routing (`/api` and `/health`
are forwarded to `http://localhost:8000`). For production builds, set
`VITE_API_BASE_URL` to the backend URL.

## Project Structure

```
frontend/
  index.html              HTML entry point
  vite.config.ts          Vite config (proxy, aliases, test setup)
  tailwind.config.ts      Tailwind CSS config (dark mode)
  tsconfig.json           TypeScript config (strict mode)
  postcss.config.js       PostCSS plugins (Tailwind, autoprefixer)
  package.json            Dependencies and scripts
  src/
    main.tsx              React entry point
    App.tsx               Router configuration
    index.css             Tailwind directives and global styles
    api/
      client.ts           Fetch wrapper with envelope unwrapping
      cards.ts            Card API functions (list, detail, history)
      market.ts           Market API functions (stats, movers)
      sets.ts             Sets API function
    components/
      Layout.tsx          App shell (nav bar, main content area)
      KpiCard.tsx         Statistic card for dashboard KPIs
      MoversPreview.tsx   Top 5 movers preview for dashboard
      MoversTable.tsx     Full movers table (gainers/losers)
      SearchBar.tsx       Debounced search input
      FilterChips.tsx     Set filter chip buttons
      CardTile.tsx        Card display in browse grid
      Pagination.tsx      Cursor-based pagination controls
      PriceChart.tsx      Recharts line chart for price history
      LoadingSpinner.tsx  Spinner for loading states
      Skeleton.tsx        Skeleton placeholder for loading states
      ErrorBanner.tsx     Error message display
    hooks/
      useApi.ts           Generic data fetching hook with loading/error
      useDebounce.ts      Debounce hook for search input
    pages/
      Dashboard.tsx       Home page (KPIs + movers preview)
      Cards.tsx           Card browse page (search, filter, paginate)
      CardDetail.tsx      Individual card with price chart
      MarketMovers.tsx    Gainers and losers tables
    types/
      api.ts              TypeScript interfaces for API responses
    utils/
      constants.ts        Shared constants (periods, limits)
      format.ts           Number and date formatting helpers
  tests/
    setup.ts              Vitest setup (jsdom, RTL matchers)
    fixtures/
      api-responses.ts    Mock API response data
    api/
      client.test.ts      API client tests
    components/
      *.test.tsx          Component tests (12 files)
    hooks/
      useDebounce.test.ts Debounce hook tests
    pages/
      CardDetail.test.tsx Card detail page tests
      Cards.test.tsx      Cards page tests
    utils/
      format.test.ts      Formatting utility tests
```

## Tech Stack

| Layer | Technology | Version |
|-------|------------|---------|
| Build | Vite | 6.3 |
| UI | React | 19.1 |
| Language | TypeScript | 5.8 |
| Styling | Tailwind CSS | 3.4 |
| Charts | Recharts | 2.15 |
| Routing | React Router | 7.6 |
| Testing | Vitest + RTL | 3.2 / 16.3 |

## Architecture

See [F07 Architecture Diagram](../docs/diagrams/F07-architecture.mmd) for the
full component hierarchy and data flow.

The SPA follows a layered pattern:

1. **Pages** -- route-level components that compose shared components
2. **Components** -- reusable UI elements (charts, tables, inputs)
3. **Hooks** -- data fetching and state management (`useApi`, `useDebounce`)
4. **API Client** -- typed fetch wrappers that call the backend endpoints
5. **Types** -- shared TypeScript interfaces matching Pydantic schemas
