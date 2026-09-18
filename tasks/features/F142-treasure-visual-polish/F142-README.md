# F142 — Treasure Card Visual Polish (Shine + Elegant Movement)

**Status:** planned
**Branch:** homol
**Complexity:** small (CSS-only visual refinements)

## Summary

The treasure token thumbnail in the sidebar lost its golden glow/shine after
previous refactors. The user wants the golden aura restored on the sidebar
thumbnail and the modal open/close animation made smoother and more elegant.
All existing mechanics (sparkle particles, origin-rect fly-back, click-to-open,
escape-to-close, Card3DTilt with foil) remain unchanged.

## Problem

1. **TreasureBalance sidebar thumbnail** has only a static `border-amber-500/50`
   and `shadow-lg` — no animated golden glow.
2. **TreasureModal open/close** uses `cubic-bezier(0.34, 1.56, 0.64, 1)` which
   overshoots (bouncy), not elegant. No hover/float effect while the modal is
   open.
3. The modal image has a static golden `box-shadow` when open but no continuous
   shimmer effect — the foil-shimmer from Card3DTilt is rainbow, not gold.

## Waves

### Wave 1 (2 tasks, independent)

| Task | File | Description |
|------|------|-------------|
| T1 | `task-01-sidebar-glow.md` | Add pulsing golden glow animation to sidebar thumbnail |
| T2 | `task-02-modal-animation.md` | Refine modal open/close easing + add golden shimmer overlay |

## Scope

**IN:**
- TreasureBalance.tsx — animated golden glow on the `<img>` thumbnail
- TreasureModal.tsx — smoother easing curve, gentle float while open, golden shimmer CSS
- foil-shimmer.css or new CSS file for golden glow keyframes

**OUT:**
- Credit system logic (unchanged)
- TreasureTokenCard redesign (unchanged)
- Sparkle particles (unchanged)
- Card3DTilt foil behavior (unchanged)
- New features or endpoints

## Files Affected

- `frontend/src/components/TreasureBalance.tsx`
- `frontend/src/components/TreasureModal.tsx`
- `frontend/src/styles/foil-shimmer.css` (or new `treasure-glow.css`)
- Tests for TreasureBalance and TreasureModal (snapshot/class assertions)
