# F39 — Ticker estilo Bolsa (Stock-style Ticker)

**Status:** planned
**Created:** 2026-08-21
**Dependencies:** F36 (Trending Cards Engine), F37 (Scheduled Global Scanner)

## Summary

Add a horizontal stock-ticker bar at the top of the application (above the
main content, below the ExchangeRateBanner) that continuously scrolls
through top gainers and losers with card name, current price, and percentage
change. The ticker auto-refreshes data every 5 minutes. Each item is
clickable, navigating to the card's detail page. The ticker is hidden on
small screens (below `md` breakpoint) where horizontal space is
insufficient.

## User Story

As a collector or trader, I want to see a continuously scrolling ticker of
cards that are rising and falling in price at a glance, without navigating
to a separate page, so I can stay aware of market movements passively.

## Current State Analysis

### What Already Exists

1. **F36 (planned)**: `GET /market/trending/gainers` and
   `GET /market/trending/losers` endpoints returning `TrendingCardEntry[]`
   with `card_id`, `name_en`, `name_pt`, `set_code`, `price_end`,
   `change_pct`, `change_abs`, `composite_score`, `currency`.

2. **Layout.tsx**: renders sidebar + main content area. Already hosts
   `<ExchangeRateBanner />` between the mobile header and `<main>`. The
   ticker will be placed directly below the ExchangeRateBanner.

3. **useApi hook**: generic data-fetching hook with AbortController
   cleanup, refetch capability, and stale-response protection.

4. **useCardName hook**: language-aware card name resolution.

5. **useCurrency hook**: provides current currency preference for API
   params.

6. **react-router-dom**: `useNavigate` / `<Link>` for clickable navigation.

7. **i18n**: react-i18next with EN + PT-BR locales.

8. **Tailwind CSS**: dark theme (slate-900 bg, slate-800 surface,
   cyan-400 accent). All styling via utility classes.

### Gaps to Fill

1. **No ticker component**: no horizontal scrolling marquee-style component
   exists anywhere in the frontend.
2. **No CSS animation for continuous scroll**: need a `@keyframes`
   marquee animation that smoothly translates items left, loops seamlessly,
   and pauses on hover.
3. **No auto-refresh mechanism at interval**: existing hooks fetch once
   (or on refetch). Need a polling interval (5 min) that re-fetches
   trending data without full component remount.
4. **No combined gainers+losers API client**: need a function that fetches
   both endpoints and interleaves results.
5. **No accessibility for animated content**: need `prefers-reduced-motion`
   support and proper ARIA attributes.

## Architecture

### Frontend Only

This feature is purely frontend. It consumes the F36 trending API endpoints
(`GET /market/trending/gainers` and `GET /market/trending/losers`). No
backend changes required.

### Component Tree

```
Layout.tsx
  +-- ExchangeRateBanner
  +-- MarketTicker (NEW)           <-- positioned here
  |     +-- TickerItem (NEW)       <-- repeated for each card
  +-- <main> / <Outlet>
```

### MarketTicker Component

A full-width horizontal bar that renders a continuously scrolling list of
`TickerItem` elements. Key behaviors:

1. **Data fetching**: on mount, fetches both `trending/gainers` and
   `trending/losers` (limit=10 each), interleaves them (gainer, loser,
   gainer, loser...), and stores the merged list.

2. **Auto-refresh**: uses `setInterval` (300,000ms = 5 min) to re-fetch
   data. Updates happen seamlessly (replace data without animation reset
   unless item count changes).

3. **Marquee animation**: CSS `@keyframes ticker-scroll` that translates
   the inner container from `0` to `-50%` (since content is duplicated for
   seamless looping). Animation duration scales with item count for
   consistent speed.

4. **Pause on hover**: `:hover` sets `animation-play-state: paused` via
   a Tailwind arbitrary variant or inline style.

5. **Responsive**: `hidden md:flex` -- completely hidden below `md`
   breakpoint (768px).

6. **Reduced motion**: `@media (prefers-reduced-motion: reduce)` stops
   animation entirely, showing a static (non-scrolling) row that can be
   horizontally scrolled manually. Uses Tailwind's
   `motion-reduce:animate-none` utility.

7. **Empty/loading states**: shows nothing (returns null) while loading
   or if no trending data is available. No skeleton -- the bar simply does
   not appear.

8. **Error handling**: on fetch error, the ticker is hidden (graceful
   degradation). The ticker is supplementary UI; errors should not impact
   the rest of the page.

### TickerItem Component

A single item in the ticker strip, rendered as a clickable inline element:

```
[SOL  $42.50  +12.3%]   [DOV  $18.20  -5.7%]
  ^      ^      ^
  name   price  change (green=up, red=down)
```

- **Card name**: short display using `useCardName` (truncated to ~20 chars
  if needed).
- **Set code**: optional small badge (3-letter code, muted).
- **Price**: current price in selected currency, formatted.
- **Change %**: green text + up arrow for positive, red text + down arrow
  for negative.
- **Click**: navigates to `/cards/{card_id}`.
- **Separator**: subtle vertical line or dot between items.

### CSS Animation Strategy

Defined in a small Tailwind plugin or via `@layer utilities` in the main
CSS file:

```css
@keyframes ticker-scroll {
  0% { transform: translateX(0); }
  100% { transform: translateX(-50%); }
}

.animate-ticker {
  animation: ticker-scroll var(--ticker-duration, 30s) linear infinite;
}
```

The inner container renders the items list twice (duplicated) so that when
the first copy scrolls out of view, the second copy seamlessly continues.
`--ticker-duration` is calculated dynamically based on item count to
maintain a readable scroll speed (~80px/s).

### Hook: useTickerData

Custom hook encapsulating:
- Fetching gainers + losers from F36 endpoints
- Merging/interleaving results
- 5-minute polling interval via `setInterval`
- Cleanup on unmount

Returns `{ items: TickerItemData[], loading: boolean }`.

### API Client: fetchTickerData

New function in `frontend/src/api/trending.ts` (same file F36 creates):
```typescript
export async function fetchTickerData(
  currency: string,
  signal?: AbortSignal,
): Promise<TickerItemData[]>
```

Calls both `/market/trending/gainers?period=7d&limit=10&currency=X` and
`/market/trending/losers?period=7d&limit=10&currency=X` in parallel,
interleaves results.

## Acceptance Criteria

1. MarketTicker component renders a horizontally scrolling bar of cards
   with price and change percentage
2. Items are interleaved: gainer, loser, gainer, loser (up to 20 items)
3. Scrolling is smooth, continuous, and loops seamlessly (no gap/jump)
4. Hovering the ticker pauses the animation
5. Data auto-refreshes every 5 minutes without visual disruption
6. Each item is clickable and navigates to `/cards/{card_id}`
7. Gainers show green text with up arrow; losers show red text with down
   arrow
8. Ticker is hidden on screens below `md` breakpoint (768px)
9. `prefers-reduced-motion: reduce` disables animation; items are shown
   statically with optional horizontal scroll
10. Ticker shows nothing (returns null) while loading or on error --
    graceful degradation
11. Card names are language-aware via `useCardName` pattern
12. Price display respects current currency selection
13. i18n keys added for EN and PT-BR (aria labels, alt text)
14. All new components have unit tests
15. No backend changes required

## Constraints

- Depends on F36 trending API endpoints existing
- Frontend-only feature (no backend changes)
- No new npm dependencies -- pure CSS animation (no framer-motion,
  no react-marquee libraries)
- Must not impact performance of the main content area (ticker failures
  are silent)
- Animation must not cause layout shifts in the main content
- Tailwind utility classes only (plus one small @keyframes definition)

## Tasks

| Task | File | Wave | Description |
|------|------|------|-------------|
| T01 | F39-T01.md | 1 | CSS keyframes + Tailwind animation utilities |
| T02 | F39-T02.md | 1 | API client + types + useTickerData hook |
| T03 | F39-T03.md | 2 | TickerItem + MarketTicker components |
| T04 | F39-T04.md | 3 | Layout integration + i18n + responsive/a11y |
| T05 | F39-T05.md | 4 | Tests: components, hook, integration |

## Waves

- **Wave 1** (2 tasks, parallel): T01 (CSS animation definitions) and T02
  (API client + hook). No dependency between them.
- **Wave 2** (1 task): T03 (TickerItem + MarketTicker components). Depends
  on both T01 (animation classes) and T02 (hook providing data).
- **Wave 3** (1 task): T04 (wire into Layout, add i18n, finalize
  responsive + a11y). Depends on T03.
- **Wave 4** (1 task): T05 (comprehensive tests for all new code).

## File Inventory

### New Files
- `frontend/src/components/MarketTicker.tsx` (T03)
- `frontend/src/components/TickerItem.tsx` (T03)
- `frontend/src/hooks/useTickerData.ts` (T02)
- `frontend/tests/components/MarketTicker.test.tsx` (T05)
- `frontend/tests/components/TickerItem.test.tsx` (T05)
- `frontend/tests/hooks/useTickerData.test.ts` (T05)

### Modified Files
- `frontend/src/index.css` -- add `@keyframes ticker-scroll` (T01)
- `frontend/src/api/trending.ts` -- add `fetchTickerData()` (T02)
  (this file is created by F36; F39 adds to it)
- `frontend/src/types/api.ts` -- add `TickerItemData` type (T02)
- `frontend/src/components/Layout.tsx` -- add `<MarketTicker />` below
  ExchangeRateBanner (T04)
- `frontend/src/i18n/locales/en.json` -- add ticker i18n keys (T04)
- `frontend/src/i18n/locales/pt-BR.json` -- add ticker i18n keys (T04)

### No Cross-Wave File Conflicts
- Wave 1: `index.css` (T01), `trending.ts` + `api.ts` types + hook (T02)
  -- no overlap
- Wave 2: `MarketTicker.tsx` + `TickerItem.tsx` (T03) -- new files only
- Wave 3: `Layout.tsx` + i18n JSONs (T04) -- not touched by earlier waves
- Wave 4: test files only (T05)
