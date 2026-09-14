# F126 — Fullscreen 3D Card Preview & Treasure Modal Fix

**Status:** planned
**Priority:** high (UX regression)
**Estimated tasks:** 3
**Waves:** 1 (all parallel)

## Problem

1. **CardPreviewModal** renders inline (no `createPortal`). When rendered inside
   components that apply CSS `transform` (e.g., `Card3DTilt` via react-parallax-tilt,
   sidebar via `transform transition-all`), `position: fixed` becomes relative to
   the nearest transformed ancestor instead of the viewport. Result: the modal
   appears confined to the card tile or page section instead of covering the screen.

2. **CardPreviewModal** uses `max-w-sm` (384px) which is too small for a fullscreen
   zoom experience. The card image should expand to a comfortable viewport size.

3. **TreasureModal** already uses `createPortal` but the user reports similar
   confinement. The Treasure thumbnail in the sidebar may need the same treatment
   to ensure the expanded view is truly viewport-centered and large.

## Root Cause

CSS spec: `position: fixed` is relative to the **containing block** established by
the nearest ancestor with a `transform`, `perspective`, or `filter` property — NOT
the viewport. `Card3DTilt` applies `transform` via react-parallax-tilt, and the
sidebar `<aside>` has `transform transition-all`. Without `createPortal`, the modal
is trapped.

## Solution

- **T01**: Refactor `CardPreviewModal` to use `createPortal(modal, document.body)`
  (same pattern as `TreasureModal` and `CardHoverPreview`). Increase card size
  from `max-w-sm` to `max-w-md` with `max-h-[80vh]` for a proper fullscreen feel.

- **T02**: Audit `TreasureModal` — verify it renders viewport-centered, increase
  z-index consistency, ensure the image fills generously. If the sidebar's CSS
  transform context causes any stacking issues, fix them.

- **T03**: Update existing tests for the new portal behavior (modal renders in
  `document.body`, not inline).

## Wave Plan

| Wave | Tasks | Rationale |
|------|-------|-----------|
| 0    | T01, T02, T03 | All independent, small changes |

## Files Affected

- `frontend/src/components/CardPreviewModal.tsx` (T01)
- `frontend/src/components/TreasureModal.tsx` (T02, audit)
- `frontend/src/components/__tests__/CardPreviewModal.test.tsx` (T03)
- `frontend/src/components/__tests__/TreasureModal.test.tsx` (T03, if exists)
