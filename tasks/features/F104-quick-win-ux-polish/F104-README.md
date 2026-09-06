# F104 — Quick Win UX Polish

**Status:** done
**Priority:** P1
**Estimated tasks:** 8
**Waves:** 2

## Summary

8 independent visual/UX improvements identified from competitive TCG
marketplace research. All are low-effort, high-impact frontend enhancements.
Grouped for maximum parallelization — most tasks can run in a single Wave.

## Problem

The current UI lacks several patterns that are standard in competing TCG
platforms (TCGPlayer, EchoMTG, Moxfield, Archidekt): inline price trends,
hover previews, skeleton loading for images, sticky filters, and
arbitrage indicators. These are quick wins that dramatically improve
perceived quality.

## Solution

1. **Sparklines inline** — mini price trend charts (7d) next to prices in
   card lists (collection, catalog, explore). Reuses existing `DeckSparkline`
   + Recharts. Requires a lightweight backend endpoint for batch mini-history.
2. **Trend indicators** — arrow + percentage change badge next to prices.
3. **Card hover preview** — desktop: hover shows enlarged card image in a
   floating panel; mobile: long-press.
4. **Set completion progress** — progress bar showing X/Y cards owned per set
   in MyCollection page.
5. **Arbitrage badges** — "Best Price" badge + BRL vs USD gap indicator on
   cards that have both Liga and TCG prices.
6. **Skeleton loading for card images** — pulsing placeholder while images
   load (replacing blank space).
7. **Sticky filter bar** — filters stay visible when scrolling card grids.
8. **Scroll position retention** — remember scroll position when navigating
   to card detail and back.

## Architecture

All changes are frontend-only except T01 which adds one lightweight
backend endpoint for batch sparkline data.

```
Backend (T01 only):
  GET /api/cards/price-trends?card_ids=1,2,3&days=7
  → { card_id: [price1, price2, ...], ... }
  Source: price_observations table (existing)

Frontend (T02–T08):
  Components: PriceSparkline, TrendBadge, CardHoverPreview,
              SetCompletionBar, ArbitrageBadge, CardImageSkeleton
  Hooks: useCardHoverPreview, useScrollRestoration
  Pages affected: MyCollection, CatalogPage, Cards, CardDetail,
                  CollectionCardDetail
```

## Data Model Impact

- No schema changes
- No new tables
- One new read-only endpoint

## Risks

- Sparkline batch endpoint could be slow if too many card_ids — mitigated
  by pagination (max 50 per request)
- Hover preview on mobile (long-press) needs careful touch event handling
  to not interfere with scroll

## Waves

### Wave 0 — Backend endpoint (T01, runs alone because T02 depends on it)
- T01: Batch price trends API endpoint

### Wave 1 — All frontend tasks (T02–T08, fully parallel)
- T02: PriceSparkline component + integration in card lists
- T03: TrendBadge component (arrow + % change)
- T04: CardHoverPreview component (desktop hover + mobile long-press)
- T05: Set completion progress bar in MyCollection
- T06: ArbitrageBadge component (best price + BRL/USD gap)
- T07: Skeleton loading for card images in CardTile/CatalogCardTile
- T08: Sticky filter bar + scroll position retention
