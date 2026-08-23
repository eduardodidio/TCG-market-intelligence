# F54 — Trending List Layout + Gaucho Orthography + Ticker Animation

**Status:** shipped
**Created:** 2026-08-23
**Wave count:** 1 (all tasks parallel)

## Summary

Three independent improvements bundled for maximum parallelism:

1. **F54-T01 Trending List Layout** — Replace horizontal-scroll card grids with two side-by-side list grids (gainers / losers), no images, clickable rows → card detail.
2. **F54-T02 Gaucho Orthography Fixes** — Fix all accent/spelling issues in gaucho i18n strings (tchê, aí, tá, né, butiás, próxima, etc.) in both locale files.
3. **F54-T03 Market Ticker Scroll Fix** — Ensure the stock ticker marquee auto-scrolls continuously like a stock exchange display.

## Wave Plan

### Wave 1 (parallel — no dependencies)

| Task | Files | Risk |
|------|-------|------|
| F54-T01 | `Trending.tsx`, `TrendingSection.tsx`, new `TrendingListItem.tsx` | Low |
| F54-T02 | `en.json`, `pt-BR.json` | None |
| F54-T03 | `MarketTicker.tsx`, `index.css`, `useTickerData.ts` | Low |
