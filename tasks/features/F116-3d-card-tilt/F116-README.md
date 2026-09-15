# F116 — 3D Card Tilt Effect

**Status:** planned
**Created:** 2026-09-09
**Branch:** homol

## Summary

Add a 3D tilt/hover effect (inspired by deckcheck.co) to all card
visualizations. Cards respond to mouse movement with perspective rotation,
slight scale, and optional holographic shimmer for foils. Use
`react-parallax-tilt` for the base effect, with a custom wrapper component
for project-wide consistency.

## Wave Plan

| Wave | Tasks | Parallelism | Notes |
|------|-------|-------------|-------|
| 0 | T01 | 1 | Install dep + create Card3DTilt wrapper |
| 1 | T02, T03 | 2 parallel | Integrate in all card views + foil shimmer |

## Task List

| Task | Summary | Wave | Files |
|------|---------|------|-------|
| T01 | Card3DTilt wrapper component + react-parallax-tilt | 0 | package.json, Card3DTilt.tsx (new) |
| T02 | Integrate 3D tilt in CardTile, CatalogCardTile, DeckCardTile | 1 | CardTile.tsx, CatalogCardTile.tsx, DeckCardTile.tsx |
| T03 | Holographic foil shimmer effect for foil cards | 1 | Card3DTilt.tsx, foil-shimmer.css (new) |

## File Conflict Map

- **CardTile.tsx** — T02 only (wrap image in Card3DTilt)
- **CatalogCardTile.tsx** — T02 only
- **DeckCardTile.tsx** — T02 only
- **Card3DTilt.tsx** — T01 creates, T03 extends (sequential)
- **package.json** — T01 only (npm install)

## Cross-Feature Parallelism

F116 should start **after F114-T01** merges (both touch CardTile.tsx).
Can run parallel with F115 (sort) — different files.
Can run parallel with F117 (clean UI) if F117 uses Card3DTilt.
