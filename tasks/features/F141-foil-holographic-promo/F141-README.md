# F141 -- Foil Holographic + Promo Badge on Card Inspection

**Status:** planned
**Created:** 2026-09-18
**Owner:** Eduardo Rutkoski Didio

## Objective

Enhance foil card visuals with a realistic holographic/iridescent shimmer
overlay that reacts to mouse position, and add a "PROMO" badge overlay for
promo cards. Both effects apply on CardPreviewModal (full-screen inspector)
and Card3DTilt (grid thumbnails).

## Summary

The current `foil-shimmer.css` animates a rainbow gradient on a fixed
cycle. This feature upgrades it to a mouse-reactive holographic effect
using CSS custom properties (`--mouse-x`, `--mouse-y`) set via JS, giving
a realistic angle-reactive iridescence. A new PromoBadge component
provides a silver/platinum stamp overlay for promo cards (detected
client-side from `set_code` prefix or `extras` field -- no backend changes
needed).

## Tasks

| Task | Description | Wave | Status |
|------|-------------|------|--------|
| F141-T01 | Upgrade foil-shimmer.css with mouse-reactive holographic effect | 0 | planned |
| F141-T02 | Wire mouse tracking into Card3DTilt and CardPreviewModal | 0 | planned |
| F141-T03 | Add isPromo prop to CardPreviewModal + PromoBadge component | 1 | planned |
| F141-T04 | Thread isPromo through callers (CardTile, detail pages) | 1 | planned |
| F141-T05 | Tests for foil overlay, promo badge, and reduced-motion | 2 | planned |

## Waves

- **Wave 0:** F141-T01, F141-T02 (foil holographic -- CSS + JS wiring, independent)
- **Wave 1:** F141-T03, F141-T04 (promo badge -- component + callers, independent of each other)
- **Wave 2:** F141-T05 (tests for all new behavior)

## Scope

**IN:**
- `frontend/src/styles/foil-shimmer.css` -- upgraded holographic effect
- `frontend/src/components/Card3DTilt.tsx` -- mouse event handlers for CSS vars
- `frontend/src/components/CardPreviewModal.tsx` -- mouse tracking + isPromo prop + PromoBadge overlay
- `frontend/src/components/PromoBadge.tsx` -- new component (silver stamp)
- `frontend/src/utils/promo.ts` -- `isPromoCard(setCode, extras)` helper
- Callers: CardTile, CardDetail, CollectionCardDetail, CatalogPage, SharedCollectionPage, etc.
- Tests for all of the above

**OUT:**
- Backend changes (no new DB columns, no new API fields)
- Card grid thumbnail changes beyond what Card3DTilt already provides
- New dependencies (pure CSS + vanilla JS mouse events)

## Architecture Decisions

### AD-1: Mouse-reactive holographic via CSS custom properties

The `foil-shimmer::after` pseudo-element gradient angle and position will
be driven by `--mouse-x` and `--mouse-y` custom properties (0-1 range)
set on the container element via `onMouseMove`. This avoids JS animation
frames and lets CSS handle the rendering. When the mouse leaves, the
effect falls back to the existing keyframe animation.

**Why not a canvas/WebGL solution?** Overkill for this use case. CSS
custom properties + `background-position` achieve a convincing iridescent
look with zero dependencies and near-zero performance cost.

### AD-2: Promo detection is client-side only

Since the scope excludes backend changes, promo status is derived from
existing fields:
- `set_code` starting with `p` (e.g., `pone`, `pltr`) -- Liga convention
- `extras` field containing "promo" (case-insensitive)

A small utility function `isPromoCard(setCode, extras)` centralizes this
logic. If the backend later adds a `promo` boolean, callers can switch
to it without touching the component.

### AD-3: PromoBadge is a positioned overlay, not inline

The promo badge renders as an absolute-positioned element on top of the
card image (bottom-center, like the real holofoil stamp on MTG cards),
not as an inline badge like FoilBadge. This matches user expectation of
a "stamp" on the card art.

### AD-4: prefers-reduced-motion disables animation only

With `prefers-reduced-motion: reduce`, the holographic overlay stays
visible (static gradient at center position) but does not animate or
react to mouse movement. The promo badge is unaffected (it has no
animation).
