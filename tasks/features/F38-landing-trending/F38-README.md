# F38 -- Landing Page: Em Alta / Em Baixa

**Status:** planned
**Created:** 2026-08-21
**Dependencies:** F36 (Trending Cards Engine), F37 (Scheduled Global Scanner)

## Summary

Add "Em Alta" (gainers) and "Em Baixa" (losers) trending sections to the
Dashboard landing page, plus a market summary stats row and a hero header.
All heavy lifting was done in F36 (trending engine, API endpoints,
`TrendingSection` and `TrendingCard` reusable components). This feature
is pure integration -- wire F36 components into Dashboard.tsx, replace the
old `MoversPreview` with richer trending sections, and add a lightweight
summary stats strip.

## User Story

As a user landing on the dashboard, I want to immediately see which cards
are trending up and down based on composite trending scores (not just raw
% change), so I can spot real market trends without navigating to a
separate page.

## Current State Analysis

### Dashboard Today (`frontend/src/pages/Dashboard.tsx`)

1. **Collection KPIs** (4 cards): unique cards, total copies, estimated
   value, coverage percentage.
2. **Market Overview KPIs** (4 cards): total cards, total observations,
   average price, data range.
3. **MoversPreview**: text-only list of top 5 gainers and top 5 losers
   from `GET /market/movers?period=30d&limit=5`. No images, no composite
   scores, no trending indicators.
4. Loading: `SkeletonKpi` + `SkeletonTable` placeholders.
5. Error: `ErrorBanner` with retry.

### What F36 Provides (available after F36 ships)

- `TrendingSection` component: fetches from `/market/trending/{direction}`,
  renders horizontal scrollable row of `TrendingCard` tiles with images,
  price change arrows, composite score bars, skeleton loading, error/empty
  states, and cached-data badge.
- `TrendingCard` component: card tile with image, name, set badge, change
  %, change abs, score bar, clickable link.
- `fetchTrending()` API client.
- `TrendingCardEntry` and `TrendingResponse` TypeScript types.
- i18n keys for trending labels (EN + PT-BR).

### What F44 Provides (available after F44 ships)

- `MarketDataService.get_top_movers()` with `AggregateCache` -- cached
  trending data with 30-min TTL, invalidated on scan completion.
- Pre-computed market summary via `MarketDataService.get_market_summary()`.

## Architecture

### Approach: Pure Frontend Integration

No new backend work. No new components (reuse F36). No new API endpoints.
The entire feature is modifications to `Dashboard.tsx` and a handful of
i18n keys.

### Dashboard Layout (After F38)

```
+--------------------------------------------------+
|  Hero Header: "TCG Market Intelligence"           |
|  Subtitle with freshness indicator                |
+--------------------------------------------------+
|  Collection KPIs (existing, unchanged)            |
|  [Unique Cards] [Copies] [Value] [Coverage]       |
+--------------------------------------------------+
|  Market Summary Stats (compact strip)             |
|  [Cards Tracked] [Observations] [Avg Price]       |
+--------------------------------------------------+
|  "Em Alta" -- TrendingSection(direction=gainers)  |
|  [card] [card] [card] [card] ...  --> scroll      |
|                            "Ver mais" link        |
+--------------------------------------------------+
|  "Em Baixa" -- TrendingSection(direction=losers)  |
|  [card] [card] [card] [card] ...  --> scroll      |
|                            "Ver mais" link        |
+--------------------------------------------------+
```

### Key Decisions

1. **Replace MoversPreview, do not duplicate.** The old `MoversPreview`
   (text-only top-5 gainers/losers from basic movers API) is superseded
   by `TrendingSection` tiles with images, composite scores, and
   anti-false-trending filters. Remove `MoversPreview` from Dashboard.

2. **Graceful degradation.** If the trending API returns empty (no data
   yet, F37 scanner hasn't run), fall back to `EmptyState` with a
   message like "No trending data yet -- run a scan to get started."
   The `TrendingSection` component from F36 already handles this.

3. **Compact market stats.** Collapse the 4-card Market Overview KPI
   grid into a single-row summary strip (3 inline stats) to make room
   for the trending sections without excessive vertical scrolling.

4. **Period defaults.** Use `30d` period for both trending sections on
   the dashboard (no period selector on landing -- the full `/market/trending`
   page has the selector). The "Ver mais" link goes to `/market/trending`.

5. **Limit.** Show up to 10 trending cards per section on the dashboard
   (scrollable). The full Trending page supports 20/50.

### File Changes

**Modified:**
- `frontend/src/pages/Dashboard.tsx` -- main integration work
- `frontend/src/i18n/locales/en.json` -- 4-5 new landing i18n keys
- `frontend/src/i18n/locales/pt-BR.json` -- 4-5 new landing i18n keys

**No new files.** All components come from F36.

**Potentially removed (or unused after this):**
- `MoversPreview` import from Dashboard (component file stays for Market
  Movers page if it uses it; just removed from Dashboard).

## Acceptance Criteria

1. Dashboard shows a hero header with project title and freshness indicator
2. "Em Alta" section displays `TrendingSection` with `direction="gainers"`,
   `period="30d"`, `limit=10`
3. "Em Baixa" section displays `TrendingSection` with `direction="losers"`,
   `period="30d"`, `limit=10`
4. Each section has a "Ver mais" link pointing to `/market/trending`
5. Market Overview KPIs are consolidated into a compact summary strip
6. `MoversPreview` is no longer rendered on Dashboard (replaced by
   trending sections)
7. Skeleton loading state shows placeholder cards while trending data loads
8. Empty state renders when no trending data is available
9. Currency from `useCurrency()` is passed to trending sections
10. All new text uses i18n keys (EN + PT-BR)
11. Layout is responsive (sections stack vertically on mobile, cards scroll
    horizontally)
12. Page loads fast -- trending data comes from F44 cache (30-min TTL)
13. All modified code has tests

## Constraints

- No new backend endpoints
- No new frontend components (reuse F36's `TrendingSection`)
- No duplication of trending logic
- Dashboard must remain functional if trending API returns errors
  (graceful degradation -- show existing KPIs, hide trending sections)
- Must not break existing Dashboard tests

## Tasks

| Task | File | Wave | Description |
|------|------|------|-------------|
| T01 | F38-T01.md | 1 | Dashboard integration: hero, trending sections, compact stats |
| T02 | F38-T02.md | 1 | i18n keys for landing page sections (EN + PT-BR) |
| T03 | F38-T03.md | 2 | Tests: Dashboard integration + snapshot updates |

## Waves

- **Wave 1** (2 tasks, parallel): T01 (Dashboard.tsx changes) and T02
  (i18n keys). T01 references i18n keys by name, T02 adds the values.
  No file overlap -- T01 touches Dashboard.tsx, T02 touches locale JSONs.
- **Wave 2** (1 task): T03 (tests). Depends on T01 and T02 being in place.

## File Inventory

### Modified Files
- `frontend/src/pages/Dashboard.tsx` (T01)
- `frontend/src/i18n/locales/en.json` (T02)
- `frontend/src/i18n/locales/pt-BR.json` (T02)
- `frontend/tests/pages/Dashboard.test.tsx` (T03)

### No New Files

All components, API clients, and types are provided by F36. This feature
is purely integration.

### No Cross-Wave File Conflicts
- Wave 1: Dashboard.tsx (T01), locale JSONs (T02) -- no overlap
- Wave 2: test file only (T03)
