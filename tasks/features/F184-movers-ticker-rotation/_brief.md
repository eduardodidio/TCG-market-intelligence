# F184 — Auto-rotating Movers Ticker on Dashboard

## Problem
The Dashboard's "Maiores Altas e Baixas" section (CollectionMovers) is a static
two-column grid. Users must scroll or expand to see movers. The user wants the
top highlights to rotate automatically in an infinite loop — a live ticker bar
at the top of the dashboard, similar to stock tickers.

## Scope
- Frontend-only (no backend changes)
- Reuse the existing `MarketTicker` CSS animation pattern (`animate-ticker`)
- Feed from the existing `fetchCollectionMovers` API (same data source)
- Keep the full expandable `CollectionMovers` below for detail

## Constraints
- Must pause on hover (accessibility + readability)
- Must work on mobile (responsive)
- Must support dark mode
- No new dependencies
