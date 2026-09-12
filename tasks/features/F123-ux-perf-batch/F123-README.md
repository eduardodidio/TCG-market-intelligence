# F123 --- UX Polish & Performance Batch

**Status:** planned
**Created:** 2026-09-11
**Branch:** homol

## Summary

Batch of 5 improvements: collapsible sidebar, Liga link fix, card preview
modal (3D tilt on click), sort persistence validation, and infinite scroll
performance. Tasks are structured for maximum parallelism across two waves.

## Important: Pre-existing State

- **Card3DTilt** already exists and is integrated (CardTile, CatalogPage,
  DeckCardTile, CardHoverPreview). `react-parallax-tilt` already installed.
  Foil shimmer CSS already exists. NO need to reinstall or recreate.
- **CardPreviewModal** does NOT exist --- this is what needs to be created.
- **`loading="lazy"`** already present on CardImage.tsx (line 40).
- **"Try New UI"** already removed in F121. NON-ISSUE.
- **Default sort** already `price desc` in MyCollection.tsx. Needs validation only.

## Wave Plan

| Wave | Tasks | Parallelism | Notes |
|------|-------|-------------|-------|
| 0 | T01, T02, T03 | 3 parallel | Sidebar, Liga links, CardPreviewModal (new component) |
| 1 | T04, T05, T06 | 3 parallel | Modal integration in tiles, sort validation, scroll perf |

## Task List

| Task | Summary | Wave | Est. |
|------|---------|------|------|
| T01 | Collapsible sidebar with icons and localStorage persistence | 0 | M |
| T02 | Fix Liga Magic card links (backend canonical name lookup) | 0 | S |
| T03 | CardPreviewModal component (click card image -> modal with 3D tilt) | 0 | S |
| T04 | Integrate CardPreviewModal in CardTile, CatalogCardTile, DeckCardTile | 1 | S |
| T05 | Collection sort persistence validation (price desc default) | 1 | S |
| T06 | Infinite scroll performance (prefetch + page size) | 1 | S |

## File Conflict Map

| File | Tasks | Conflict? |
|------|-------|-----------|
| Layout.tsx | T01 | No |
| collection.py (backend) | T02 | No |
| card_search.py (backend) | T02 | No |
| CardDetail.tsx | T02 | No |
| CardPreviewModal.tsx (new) | T03 creates, T04 uses | Sequential (Wave 0 then 1) |
| CardTile.tsx | T04 | No |
| CatalogCardTile.tsx | T04 | No |
| DeckCardTile.tsx | T04 | No |
| MyCollection.tsx | T05, T06 | Both Wave 1, different sections. Low risk. |
| Cards.tsx | T06 | No |
| useInfiniteScroll.ts | T06 | No |
| constants.ts | T06 | No |

## Cross-Feature Parallelism

- F123 has no dependencies on pending features.
- T01 (sidebar) is fully isolated --- touches only Layout.tsx.
- T02 (Liga links) is fully isolated --- backend routers + CardDetail.tsx.
- T03/T04 (preview modal) uses existing Card3DTilt. No new deps needed.
- T05 and T06 both touch MyCollection.tsx in different areas.

## New Dependencies

None. `react-parallax-tilt` already installed.

## Diagrams

- Architecture and journey diagrams to be created during implementation.
