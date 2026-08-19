# F07 Tech Lead Review

**Reviewer:** TechLead agent
**Date:** 2026-08-18
**Feature:** F07 -- Front-end Dashboard

---

## 1. Architecture

**Rating: Strong**

The component hierarchy follows a clean, conventional React SPA pattern:

- `App.tsx` -- top-level routing with `React.lazy()` for all four pages
- `Layout.tsx` -- sidebar shell wrapping `<Outlet />` for nested routes
- `pages/` -- route-level components that compose shared components
- `components/` -- reusable UI primitives (KpiCard, MoversTable, PriceChart, etc.)
- `hooks/` -- `useApi` (generic data fetching) and `useDebounce`
- `api/` -- thin typed wrappers over a single `apiGet` fetch function
- `types/api.ts` -- mirrors backend Pydantic schemas
- `utils/` -- pure formatting functions and constants

The API client pattern (`client.ts`) is well designed:

- Single `apiGet<T>()` function returns the standard `ApiResponse<T>` envelope
- Proper timeout via `AbortController` with configurable duration
- Signal composition for external abort + timeout
- HTTP errors, backend error envelopes, network errors, and timeouts all handled
- Empty/undefined params are filtered

State management is appropriately minimal -- no Redux or Zustand. Each page
manages its own state via `useState` + `useApi` or direct `useState` with
manual fetch calls. This is the right call for four pages with independent data
requirements.

The `useApi` hook correctly:
- Tracks stale responses via `fetchCountRef` (race condition protection)
- Provides `refetch` for retry flows
- Cleans up via `AbortController` on unmount/re-render

**One observation (MINOR):** The `Cards.tsx` page manages its own fetch
lifecycle manually (useState + useEffect + fetchIdRef) instead of using the
`useApi` hook, because it needs cursor-based pagination (append mode). This is
a reasonable pragmatic choice -- the `useApi` hook assumes replace-mode data.
If more pages need pagination in the future, extracting a `useApiPaginated`
hook would reduce duplication, but it is not needed now.

---

## 2. Code Quality

**Rating: Strong**

- TypeScript strict mode enabled (`strict: true`, `noUnusedLocals`,
  `noUnusedParameters`, `noFallthroughCasesInSwitch`,
  `forceConsistentCasingInFileNames`)
- `tsc --noEmit` passes with zero errors
- Zero uses of `any` in production code (verified via grep)
- Consistent naming: PascalCase components, camelCase functions/hooks,
  SCREAMING_SNAKE for constants
- All components are named exports (not default exports), which is consistent
  with the `React.lazy()` `.then(m => ({ default: m.X }))` pattern in App.tsx
- `formatBRL`, `formatPercent`, `formatDate` are pure functions with null
  handling
- The `ErrorBanner` component properly detects network errors and shows a
  user-friendly message instead of raw error text
- `data-testid` attributes used consistently for test selectors
- Focus-visible ring classes applied to all interactive elements (links,
  buttons) -- good keyboard accessibility
- ARIA labels on hamburger button, period selector groups, and error alerts
- External links use `rel="noopener noreferrer"` and `target="_blank"`

**Minor notes:**

- **(MINOR)** The `@/` path alias is configured in both `tsconfig.json` and
  `vite.config.ts` but never used -- all imports use relative paths. This is
  harmless but slightly misleading. Either remove the alias or adopt it
  consistently. Not blocking.

- **(MINOR)** `PERIOD_OPTIONS` in `constants.ts` duplicates the PERIODS array
  in `PriceChart.tsx` and `MarketMovers.tsx`. Each component defines its own
  local array. This is acceptable since the pages have different period sets
  (PriceChart has 5 options, MarketMovers has 3), but the naming overlap with
  the unused `PERIOD_OPTIONS` constant could confuse future developers.

---

## 3. Tests

**Rating: Strong**

163 tests passing across 20 test files. Coverage areas:

| Area | Files | Tests | Notes |
|------|-------|-------|-------|
| API client | client.test.ts | 7 | Success, params, errors, timeout |
| Utils | format.test.ts | (verified) | BRL, percent, date formatting |
| Hooks | useDebounce.test.ts | (verified) | Timer-based behavior |
| Components | 12 files | ~80+ | KpiCard, CardTile, Layout, ErrorBanner, etc. |
| Pages | Dashboard, Cards, CardDetail, MarketMovers | ~50+ | Full integration with mocked fetch |

Testing patterns are correct:

- `fetch` is mocked at the global level (not at the module level), matching
  how the API client uses it
- `MemoryRouter` wraps all components that use routing (Links, useParams)
- Recharts `ResponsiveContainer` is mocked to avoid jsdom SVG measurement
  issues (correct approach -- jsdom has no layout engine)
- Fixture factory functions (`mockMarketStats()`, `mockCardSummaries(n)`, etc.)
  are typed and centralized in `tests/fixtures/api-responses.ts`
- Stale response handling is implicitly tested via the race condition tests
- Error paths tested: HTTP errors, network errors, timeouts, 404 vs generic
  error differentiation

**One observation (MINOR):** Several PriceChart tests emit `act()` warnings
in stderr. These are React 19 warnings about state updates outside `act()`.
The tests still pass and the assertions are correct, but wrapping the
`fireEvent.click` calls in `act()` and awaiting would clean up the console
output. Not blocking -- this is a cosmetic issue in test output.

---

## 4. Diagrams

**Rating: Adequate**

- `docs/diagrams/F07-architecture.mmd` -- Component hierarchy diagram showing
  Browser -> Vite -> App -> Layout -> Pages, with component dependencies and
  API client layer. Includes the Vite proxy to FastAPI backend. Clear and
  accurate representation of the actual code structure.

- `docs/diagrams/F07-journey.mmd` -- User flow diagram covering Dashboard,
  Card Browsing (search -> debounce -> filter -> paginate -> detail), Card
  Detail (chart period selector loop), and Market Movers (period selector,
  click-through to detail). Covers all four pages and major interactions.

Both diagrams are syntactically valid Mermaid and accurately reflect the
implemented architecture and user flows.

---

## 5. Documentation

**Rating: Complete**

| Document | Status | Notes |
|----------|--------|-------|
| ADR-0003 | Present | `docs/adr/0003-frontend-stack.md` -- covers Vite+React+TS+Tailwind+Recharts with alternatives |
| PRD | Present | `docs/prd/F07-frontend-dashboard.md` -- 12 FRs, 6 NFRs, acceptance criteria |
| F07-README | Present | Task manifest with waves, structure, dependencies |
| F07-test-plan | Present | TEA-generated, 31 scenarios, fixture definitions |
| README.md | Updated | F07 section added with feature description and run instructions |
| Diagrams | Present | 2 Mermaid files (architecture + journey) |

**One observation (MINOR):** The PRD mentions "React Router v7" while the
F07-README says "React Router v6". The actual installed version is
`react-router-dom ^7.6.0` (package.json). The PRD is correct; the README
has a minor version label mismatch. Not blocking.

---

## 6. Cross-task Consistency

All 8 tasks across 4 waves are internally consistent:

- T01-T02 (Wave 0) established the scaffolding that T03-T08 build upon
- Types in `types/api.ts` match all component prop interfaces
- API client functions in `api/*.ts` return the same `ApiResponse<T>` envelope
- Skeleton components match the layout of their loaded counterparts
- Test fixtures align with actual type definitions
- No backend regressions (385 backend tests still passing)

---

## 7. Performance

- Code splitting verified: Recharts (the heaviest dependency) lands exclusively
  in the `CardDetail` chunk (400KB), not in the main bundle (238KB)
- Build completes in ~3 seconds with zero warnings
- Lazy loading via `React.lazy()` ensures only the visited page's code is loaded

---

## Summary of Findings

| Severity | Item | Action |
|----------|------|--------|
| MINOR | `act()` warnings in PriceChart tests | Wrap state-changing interactions in `act()` |
| MINOR | Unused `@/` path alias configured | Remove alias or adopt it consistently |
| MINOR | `PERIOD_OPTIONS` constant in `constants.ts` unused | Remove or use it in PriceChart/MarketMovers |
| MINOR | F07-README says "React Router v6" but actual version is v7 | Correct label |

No BLOCKING or IMPORTANT issues found.

---

## Verdict: APPROVED

The F07 front-end dashboard is well-architected, cleanly implemented, and
thoroughly tested. The component hierarchy is conventional and easy to navigate.
The API client pattern with typed envelopes, abort signal composition, and
error normalization is production-quality. Testing coverage is comprehensive
with correct mocking strategies. Documentation is complete with ADR, PRD,
diagrams, and README updates. The four MINOR issues noted above are cosmetic
and do not warrant blocking the merge.

---

## Retrospective Seeds

- **Pattern:** Unused configuration (path aliases defined but never adopted)
  creates confusion about project conventions.
- **Role(s) affected:** developer, architect
- **Lesson:** When scaffolding a project (Wave 0), either use configured
  features or remove them. Unused config signals intent without follow-through.

- **Pattern:** React 19 `act()` warnings in component tests that perform
  state-changing interactions.
- **Role(s) affected:** developer
- **Lesson:** When testing components that update state on user interaction,
  wrap `fireEvent` calls in `await act(async () => { ... })` to suppress
  console warnings and match React 19 testing expectations. Add this to the
  test setup instructions for future features.
