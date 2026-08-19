# F07 — Front-end Dashboard

**Status:** done
**Created:** 2026-08-18

## Summary

Build a React + TypeScript front-end (Vite) that consumes the existing REST API (F06) to provide a web dashboard for TCG price intelligence. The UI is inspired by PokeBolsa with a dark theme, responsive layout, and four core pages: Dashboard (market KPIs and movers preview), Cards (searchable grid with filters and pagination), Card Detail (price history chart with period selectors), and Market Movers (gainers/losers tables). The front-end lives in a `frontend/` directory in the mono-repo. No authentication, no portfolio features, no AI — just clean data visualization.

## Tech Stack

- **Vite** — build tooling with fast HMR
- **React 18+** — functional components and hooks
- **TypeScript** — strict mode for type safety
- **React Router v7** — client-side routing
- **Recharts** — lightweight charting for price history
- **Tailwind CSS** — utility-first styling with dark theme
- **Vitest + React Testing Library** — unit and component tests
- **fetch API** — thin wrapper, no axios

## Waves

| Wave | Tasks | Description |
|------|-------|-------------|
| 0 | T01, T02 | Scaffolding: Vite project, deps, Tailwind, routing shell, API client, TypeScript types |
| 1 | T03, T04 | Core pages: Dashboard (KPIs + movers preview), Cards list (search, filters, pagination) |
| 2 | T05, T06 | Detail pages: Card Detail with price history chart, Market Movers full page |
| 3 | T07, T08 | Polish: responsive layout + loading/error states, documentation + diagrams + README |

## Project Structure

```
frontend/
├── index.html
├── package.json
├── tsconfig.json
├── vite.config.ts
├── tailwind.config.ts
├── postcss.config.js
├── src/
│   ├── main.tsx
│   ├── App.tsx
│   ├── api/              # API client functions
│   │   ├── client.ts     # Base fetch wrapper
│   │   ├── cards.ts      # Card endpoints
│   │   ├── market.ts     # Market endpoints
│   │   └── sets.ts       # Sets endpoint
│   ├── components/       # Reusable UI components
│   │   ├── Layout.tsx    # Sidebar + main content shell
│   │   ├── Navbar.tsx
│   │   ├── KpiCard.tsx
│   │   ├── CardTile.tsx
│   │   ├── PriceChart.tsx
│   │   ├── MoversTable.tsx
│   │   ├── SearchBar.tsx
│   │   ├── FilterChips.tsx
│   │   ├── Pagination.tsx
│   │   ├── LoadingSpinner.tsx
│   │   └── ErrorBanner.tsx
│   ├── pages/            # Route-level pages
│   │   ├── Dashboard.tsx
│   │   ├── Cards.tsx
│   │   ├── CardDetail.tsx
│   │   └── MarketMovers.tsx
│   ├── hooks/            # Custom React hooks
│   │   ├── useApi.ts
│   │   └── useDebounce.ts
│   ├── types/            # TypeScript interfaces (mirror API schemas)
│   │   └── api.ts
│   └── utils/            # Formatters, helpers
│       ├── format.ts     # Currency, percentage, date formatting
│       └── constants.ts  # API base URL, period options, etc.
├── public/
│   └── favicon.svg
└── tests/
    ├── setup.ts
    ├── api/
    │   └── client.test.ts
    ├── components/
    │   ├── KpiCard.test.tsx
    │   ├── CardTile.test.tsx
    │   └── MoversTable.test.tsx
    └── utils/
        └── format.test.ts
```

## Dependencies

Runtime:
- `react` ^18
- `react-dom` ^18
- `react-router-dom` ^6
- `recharts` ^2

Dev:
- `vite` ^5
- `@vitejs/plugin-react` ^4
- `typescript` ^5
- `tailwindcss` ^3
- `postcss`, `autoprefixer`
- `vitest`, `@testing-library/react`, `@testing-library/jest-dom`, `jsdom`
- `@types/react`, `@types/react-dom`

## Open Questions

1. **API base URL configuration**: The front-end needs to know where the API lives. For local dev, Vite proxy or `VITE_API_BASE_URL` env var. For production, this is TBD since there is no deployment story yet.
2. **Card images**: The API does not serve card images. Card tiles will use a generic placeholder. Scryfall image integration is a future feature.
3. **Deployment**: No deployment target defined. The front-end is dev-only for now (served via `npm run dev` with Vite proxy to the FastAPI backend).
