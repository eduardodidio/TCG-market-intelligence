# F07 Test Plan

**Status:** drafted
**Generator:** TEA
**Generated at:** 2026-08-18
**Source brief:** F07-README.md (Front-end Dashboard — React + Vite + TypeScript)

---

## 1. Header

Feature F07 delivers a React SPA with four pages (Dashboard, Cards, Card Detail, Market Movers) consuming the F06 REST API. The front-end lives in `frontend/` and uses Vite, React 18, TypeScript (strict), Tailwind CSS, Recharts, and React Router v6. Testing is scoped to front-end only — the backend API is not under test here. No E2E framework is in scope.

---

## 2. Fixtures

| Fixture | Path | Domain | Owner |
|---------|------|--------|-------|
| `apiResponses` | `frontend/tests/fixtures/api-responses.ts` | API mock data | F07-T02 |

### Fixture Details

**`apiResponses`** — A single module exporting typed factory functions for every API response shape used across tests. Contains:

- `mockMarketStats()` — returns a valid `ApiResponse<MarketStats>` envelope
- `mockMoversResponse()` — returns a valid `ApiResponse<MoversResponse>` with 5 gainers + 5 losers
- `mockCardSummaries(n?)` — returns `ApiResponse<CardSummary[]>` with `n` cards (default 3), cursor populated if `n >= 24`
- `mockCardDetail()` — returns `ApiResponse<CardDetail>` with source_cards populated
- `mockPriceHistory(n?)` — returns `ApiResponse<PriceObservation[]>` with `n` observations (default 30)
- `mockSetSummaries()` — returns `ApiResponse<SetSummary[]>` with 3 sets
- `mockApiError(code, message)` — returns an envelope with `data: null` and a populated `errors` array
- `mockNetworkError()` — a `TypeError('Failed to fetch')` for simulating network failure

**Justification:** Every page and most component tests need to mock API responses with the same envelope shape. Without this fixture, each test file would duplicate envelope construction, increasing maintenance burden when the API schema changes (rework prevented: schema-change cascades across 6+ test files).

---

## 3. Harnesses por fronteira

### Unit

- **Framework:** Vitest
- **Command:** `cd frontend && npm run test`
- **Default test path:** `frontend/tests/utils/`
- **Scope:** Pure functions (`format.ts` formatters, `constants.ts` values), `useDebounce` hook

### Integration (Component)

- **Framework:** Vitest + React Testing Library + jsdom
- **Command:** `cd frontend && npm run test`
- **Default test path:** `frontend/tests/components/`, `frontend/tests/api/`
- **Scope:** All React components and pages rendered in jsdom with mocked `fetch`. This is the primary test boundary for F07. Tests render components, mock the global `fetch`, verify DOM output, simulate user interactions (clicks, typing), and assert navigation via `MemoryRouter`.

### E2E

**N/A** — No E2E framework (Playwright/Cypress) is in scope for F07. The front-end is dev-only with no deployment target. E2E coverage is deferred to a future feature if/when a deployment story is established.

---

## 4. Perf budgets

| Metrica | Limite | Como medir | Aplicavel a |
|---------|--------|------------|-------------|
| Recharts not in main chunk | 0 bytes in main chunk | `npm run build` + inspect `dist/assets/` — Recharts code should appear only in the CardDetail lazy chunk | F07-T07 |
| Build succeeds | exit 0 | `npm run build` | All tasks |

_No runtime perf budgets (e.g., TTI < Xs) are enforceable without E2E tooling. The lazy-loading check above is the one structural perf constraint that can be validated at build time._

---

## 5. Mocks vs hits real

| Componente | Decisao | Justificativa |
|------------|---------|---------------|
| `fetch` (global) | **mock** | All API calls go through `fetch`. Hitting the real backend would require a running FastAPI server + populated SQLite DB, introducing flakiness, slow startup, and state management in CI. Determinism and speed justify mocking. |
| React Router | **real** | Use `MemoryRouter` from `react-router-dom` wrapping components under test. No mock needed — `MemoryRouter` is the standard RTL integration pattern. Zero cost, full fidelity. |
| Recharts | **real** | Render real Recharts components in jsdom. They produce SVG that can be queried. Mocking would remove the value of the test (verifying chart renders). |
| `import.meta.env` | **mock** | Vitest supports `import.meta.env` natively. Set `VITE_API_BASE_URL` in test setup or per-test override. Trivial, no cost. |

---

## 6. Test scenarios resumo

### F07-T02 — API client, types, routing shell

1. `apiGet` success path: mock `fetch` returning JSON envelope, verify typed response returned
2. `apiGet` error path: mock `fetch` returning 4xx/5xx, verify errors populated in envelope
3. `apiGet` timeout: mock `fetch` with `AbortController` signal, verify timeout behavior
4. `formatBRL(1234.56)` returns `"R$ 1.234,56"`; `formatBRL(null)` returns `"--"`
5. `formatPercent(12.3)` returns `"+12,3%"`; `formatPercent(-5.7)` returns `"-5,7%"`
6. `formatDate("2026-01-15")` returns `"15/01/2026"`
7. `useDebounce` updates value after specified delay (use `vi.useFakeTimers`)
8. `Layout` renders sidebar with 3 nav links; renders `<Outlet />` area

### F07-T03 — Dashboard page

9. `KpiCard` renders title and formatted value
10. `MoversPreview` renders gainers list and losers list with correct links
11. `Dashboard` page: mock stats + movers APIs, verify 4 KPI cards and movers preview render
12. `LoadingSpinner` renders without error
13. `ErrorBanner` renders error message; retry button fires callback

### F07-T04 — Cards list page

14. `SearchBar` renders input, fires onChange callback after debounce
15. `FilterChips` renders chip options, highlights selected chip, fires onSelect
16. `CardTile` renders card name, formatted BRL price, links to `/cards/:id`
17. `Pagination` shows "Load more" when cursor is not null, hides when null
18. `Cards` page: mock cards API, verify grid renders cards; search term update triggers new fetch

### F07-T05 — Card Detail page

19. `PriceChart` renders chart container; period selector buttons are present
20. `CardDetail` page: mock detail + history APIs, verify info panel shows card data (name, set, price, source links)
21. `CardDetail` 404: mock error response, verify "Card not found" message renders
22. Period selector change triggers new history API call (assert `fetch` call count)

### F07-T06 — Market Movers page

23. `MoversTable` renders entries with rank, card name link, formatted prices, formatted change percentage
24. `MoversTable` applies green styling for gainers type, red for losers type
25. `MarketMovers` page: mock movers API, verify both tables render; period selector change triggers refetch
26. `MarketMovers` empty state: mock empty response, verify empty-state message

### F07-T07 — Responsive polish, loading/error UX, accessibility

27. `Skeleton` component renders with `animate-pulse` class
28. `EmptyState` renders message text and optional action button
29. `ErrorBanner` renders `full` and `inline` variants correctly
30. `Layout` responsive: hamburger button toggles sidebar visibility
31. Lazy loading: pages are imported via `React.lazy` (verify dynamic import structure)

### F07-T08 — Documentation

_No front-end tests. Validation is manual (Mermaid syntax, README content). Not annotated._

---

## 7. Anotacoes para tasks

| Task | Fixtures |
|------|----------|
| F07-T02 | `apiResponses` |
| F07-T03 | `apiResponses` |
| F07-T04 | `apiResponses` |
| F07-T05 | `apiResponses` |
| F07-T06 | `apiResponses` |
| F07-T07 | — |

T01 has only smoke tests (build/test exit 0) — no fixture annotation needed.
T08 has no front-end tests — no fixture annotation needed.
T07 tests are component-level but do not depend on API response fixtures (skeleton, empty state, error banner variants, layout toggle are pure UI).
