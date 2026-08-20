# F14 — Collection UX Hotfixes

**Status:** planned
**Created:** 2026-08-20
**Type:** hotfix batch

## Summary

Three UX fixes for the Collection page:

1. **Internal card navigation** — Collection card clicks must open the internal
   detail view (same as Explore Cards) instead of redirecting to Scryfall.
   Add Scryfall + LigaMagic external links inside the detail view.
2. **Price display** — Collection cards are not showing per-card values. Review
   and fix the price display pipeline (backend + frontend).
3. **Infinite scroll** — Replace the "Load More" button with progressive
   infinite scroll on both Collection and Explore Cards pages.

## Wave Plan

| Wave | Tasks | Rationale |
|------|-------|-----------|
| 1 | T01, T02, T03 | All three are independent — different components/concerns |

## Tasks

- **F14-T01** — Collection cards: internal navigation + external links
- **F14-T02** — Fix per-card price display in collection
- **F14-T03** — Infinite scroll (Collection + Explore Cards)

## Files Likely Affected

- `frontend/src/pages/MyCollection.tsx`
- `frontend/src/pages/CardDetail.tsx`
- `frontend/src/pages/Cards.tsx`
- `frontend/src/components/Pagination.tsx`
- `frontend/src/components/CardTile.tsx`
