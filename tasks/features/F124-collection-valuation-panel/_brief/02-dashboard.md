# 02 — Slim dashboard (Dashboard.tsx)

## Current sections (`frontend/src/pages/Dashboard.tsx`, 317 lines)

| # | Section | testid | Decision |
|---|---------|--------|----------|
| 1 | Welcome banner | — | KEEP (onboarding into collection) |
| 2 | Hero header + FreshnessIndicator | — | KEEP |
| 3 | Collection KPIs (unique, copies, est. value + ValuationBadge 7d, coverage) | `collection-kpis` | KEEP |
| 4 | Collection movers 7d | `dashboard-movers` | KEEP |
| 5 | Collection error / empty states | `collection-error`, `collection-empty` | KEEP |
| 6 | **Market summary strip** (cards tracked, observations, avg price — global market) | `market-summary-strip` | **REMOVE** |
| 7 | **Market empty state** ("No market data yet" + Run scan CTA) | `market-empty` | **REMOVE** |
| 8 | Trending gainers/losers 30d (`collectionOnly={isAuthenticated}`) | `trending-grid` | KEEP (market trends exception) |
| 9 | Trending "View all" link | `trending-view-all` | KEEP |
| NEW | Investment progress block (invested, current value, P&L, P&L %, progress "X of N cards with paid price") | `dashboard-investment` | ADD |

## Gotcha — loading/error gates are tied to market stats

```ts
const stats = useApi<MarketStats>(() => fetchMarketStats({ currency }), [currency], { refetchOnFocus: true });
const loading = stats.loading;
const error = stats.error;
```

The whole page skeleton (`if (loading)`) and full-page `ErrorBanner`
(`if (error)`, retry calls `stats.refetch()`) depend on `/market/stats`.
Removing the strip MUST also remove this fetch, and the page gates must be
re-based on `collectionSummary` (skeleton while `collectionSummary.loading`
and no data yet; the existing `collection-error` EmptyState already covers
errors, so the full-page `if (error)` branch is deleted).

Remove now-unused imports (`fetchMarketStats`, `MarketStats`, and anything
else that becomes unused) — `npm run build` (tsc) fails on unused imports if
`noUnusedLocals` is on.

## Do NOT touch

- `MarketSummaryKpis.tsx` / `MarketPage.tsx` (the dedicated market page
  still uses market stats — only the dashboard is slimmed).
- i18n keys `landing.cardsTracked`, `landing.observations`, `landing.avgPrice`,
  `onboarding.dashboardMarket*`, `onboarding.runScan` — leave them in the JSON
  (other pages may reference them; removing keys is out of scope).
- Backend `/market/stats` endpoint stays.

## Investment progress block (new component)

`frontend/src/components/DashboardInvestmentSummary.tsx`:
- Fetches `fetchPortfolioSummary()` (`frontend/src/api/collection.ts`) and
  receives `totalUnique: number` + `currency: string` as props.
- Renders 4 `KpiCard`s: Total invested, Current value, P&L (green/red),
  P&L %; plus a progress bar: `invested_card_count / totalUnique` with label
  "{{count}} de {{total}} cards com valor pago".
- When `invested_card_count === 0`: render a CTA card (testid
  `dashboard-investment-empty`) "Informe o valor pago dos seus cards para
  acompanhar a valorização" with a `Link` to `/collection`.
- Loading: 4 `SkeletonKpi`. Error: small inline message, never blocks page.
- Only rendered on the dashboard when `summaryData.total_unique > 0` and the
  user is authenticated (portfolio-summary requires auth).
- Reuse existing i18n keys `portfolio.totalInvested`, `portfolio.currentValue`,
  `portfolio.totalPnl`, `portfolio.pnlPct` (used by
  `PortfolioDashboard.tsx:122-138`). New keys under `dashboard.investment*`.
- If `PortfolioSummary` gets the new `unpriced_card_count` field (see
  `01-paid-price.md`), show a muted hint when `> 0`: "{{count}} cards sem preço
  atual (fora do P&L)". Treat the field as optional (`?? 0`).
