# F186 — Fix MoversTicker Infinite Scroll Animation

## Status: planned

## Problem

The `MoversTicker` component on the Dashboard renders items correctly but
the CSS scroll animation is visually static — items do not move. The
`animate-ticker` class applies `translateX(-50%)` via the `ticker-scroll`
keyframe, and the component duplicates its items array (`[...items, ...items]`)
to create a seamless loop. However, the inner `div` uses `inline-flex`
without explicit `width: max-content`, so the browser computes the flex
container's width as fitting within the parent `overflow-hidden` div. A
`translateX(-50%)` on a container whose computed width equals the parent
width produces no visible movement.

## Root Cause

In `MoversTicker.tsx` line 86, the inner animated `div` has class
`inline-flex whitespace-nowrap` but no width constraint. The parent div
has `overflow-hidden`, which clips the inner content but also constrains
the inner div's computed width to the parent's width. Since `translateX(-50%)`
translates by 50% of the element's own width, and the element's width
equals the viewport-width parent, the translate shifts the content by
exactly half the visible area — but because the items only span that same
visible area (due to the constrained width), no new content scrolls in.

The fix: add `w-max` (Tailwind for `width: max-content`) to the inner div.
This forces the browser to compute the div's width as the full intrinsic
width of all children (2x the items), making `translateX(-50%)` shift by
exactly one set of items — the classic marquee/ticker pattern.

## Scope

Frontend-only. Two files changed, one test file updated. No backend changes.
No new dependencies.

## Affected Files

| File | Change |
|------|--------|
| `frontend/src/components/MoversTicker.tsx` | Add `w-max` class to inner div |
| `frontend/src/index.css` | No change needed (keyframes are correct) |
| `frontend/src/components/__tests__/MoversTicker.test.tsx` | Add test verifying `w-max` class on inner div |

## Waves

### Wave 0 (1 task, parallel-safe)

| Task | Title | Type |
|------|-------|------|
| T01 | Fix ticker layout + add w-max + update tests | fix |

## Acceptance Criteria

1. The MoversTicker scrolls continuously from right to left with a seamless loop
2. Hover pauses the animation (existing CSS, must not regress)
3. `prefers-reduced-motion` disables animation and shows scrollbar (existing, must not regress)
4. Click on an item navigates to `/cards/{id}` (existing, must not regress)
5. `npm run build` passes with zero TypeScript errors
6. All existing MoversTicker tests continue to pass
7. New test verifies `w-max` class is present on the animated inner div

## Out of Scope

- Animation speed tuning (current formula `items.length * 60 / 60` is intentional)
- Visual redesign of ticker items
- Backend movers data changes
