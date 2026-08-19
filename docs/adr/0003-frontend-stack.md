# ADR-0003: Front-end Stack: Vite + React + TypeScript + Tailwind + Recharts

**Status:** accepted
**Date:** 2026-08-18
**Deciders:** Eduardo Rutkoski Didio

## Context

TCG Market Intelligence has a fully functional REST API (F06) exposing card
catalog, price history, and market analytics data. The next step is building
a web dashboard so that users can visually explore prices, identify trends,
and monitor market movers without relying on the CLI or raw API calls.

Requirements for the front-end:

- **Chart-heavy** -- price history is the core visualization, requiring
  interactive line charts with multiple series and period selectors.
- **Dark theme** -- trading/finance dashboards conventionally use dark themes
  for reduced eye strain during extended use.
- **Responsive** -- must work on desktop and tablet; mobile is secondary but
  should not be broken.
- **Developer-friendly** -- fast feedback loop (HMR), type safety, and a
  testing story that integrates with the existing CI.
- **SPA is sufficient** -- this is an internal/data tool, not a public-facing
  site. SEO and server-side rendering are not required.

## Decision

Use the following front-end stack, living in `frontend/` within the mono-repo:

| Layer | Choice | Rationale |
|-------|--------|-----------|
| **Build tool** | [Vite](https://vitejs.dev/) | Sub-second HMR, native ESM, zero-config TypeScript support |
| **UI library** | [React 19](https://react.dev/) | Largest ecosystem, hooks-based composition, excellent charting library support |
| **Language** | [TypeScript](https://www.typescriptlang.org/) | Type safety across API types and component props, catches integration bugs at compile time |
| **Styling** | [Tailwind CSS](https://tailwindcss.com/) | Utility-first, built-in dark mode support (`dark:` variants), rapid prototyping |
| **Charts** | [Recharts](https://recharts.org/) | React-native composable charts, lightweight, good defaults for line/area charts |
| **Routing** | [React Router v7](https://reactrouter.com/) | De facto standard for React SPAs, declarative route config |
| **Testing** | [Vitest](https://vitest.dev/) + [React Testing Library](https://testing-library.com/react) | Vite-native test runner (shared config), behavior-driven component tests |

The Vite dev server proxies `/api` and `/health` requests to the FastAPI
backend at `http://localhost:8000`, eliminating CORS issues during
development.

## Consequences

**Easier:**

- Vite's HMR provides near-instant feedback during component development,
  keeping the iteration cycle fast.
- TypeScript interfaces mirror the Pydantic response schemas from F06,
  providing end-to-end type safety from database to UI.
- Tailwind's utility classes and dark mode support make it straightforward
  to build a consistent dark-themed dashboard without writing custom CSS.
- Recharts integrates naturally with React's component model -- charts are
  composed from `<LineChart>`, `<Line>`, `<Tooltip>` components rather than
  imperative canvas APIs.
- Vitest shares Vite's config and transform pipeline, so tests run without
  additional bundler configuration.

**Harder:**

- Adds a Node.js toolchain to the project. Developers need Node 18+ and
  `npm` installed alongside Python.
- The mono-repo now has two dependency ecosystems (Python + Node), which
  increases CI complexity.
- Contributors must be familiar with React, TypeScript, and Tailwind in
  addition to the Python backend stack.
- Recharts is less customizable than low-level libraries like D3.js; highly
  specialized chart types may require switching libraries in the future.

## Alternatives considered

- **Vue.js + Vuetify** -- Vue has a smaller ecosystem for charting libraries
  compared to React. Vuetify provides pre-built components but is opinionated
  about design, making custom dark themes harder to achieve. The team has more
  React experience.

- **Plain HTML + Chart.js** -- lowest complexity, no build step needed.
  However, managing state, routing, and component reuse without a framework
  becomes increasingly painful as the number of pages grows. Chart.js uses
  imperative canvas APIs that are harder to compose declaratively.

- **Next.js** -- React meta-framework with SSR, API routes, and file-based
  routing. Powerful but overkill for an SPA that does not need SEO, SSR, or
  its own API layer. Adds unnecessary complexity (server components, hydration)
  without clear benefit for this use case.

- **SvelteKit** -- modern, fast, smaller bundle size. However, the charting
  ecosystem is less mature than React's, and the smaller community means fewer
  resources for troubleshooting. Not justified given React's maturity advantage.
