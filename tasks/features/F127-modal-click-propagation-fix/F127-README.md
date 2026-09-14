# F127 — Fix Modal Backdrop Click Propagation

**Status:** planned
**Priority:** high (UX bug)
**Estimated tasks:** 1
**Waves:** 1

## Problem

When a user clicks outside the 3D card zoom (backdrop) to close `CardPreviewModal`,
the click propagates to the underlying `Link` component, navigating to the card
detail page instead of simply closing the modal.

## Root Cause

Two compounding issues:

1. **React synthetic event bubbling through portals**: With `createPortal`, React
   events bubble through the React component tree. The backdrop's `onClick={onClose}`
   does not call `e.stopPropagation()`, so the event bubbles from the portal up to
   `Card3DTilt` and potentially reaches the parent `Link`.

2. **Native event leak on synchronous unmount**: When `onClose` sets
   `previewOpen = false`, the portal unmounts synchronously. The browser's
   `mouseup` event (which follows `mousedown`) may fire on the now-exposed `Link`
   element underneath, synthesizing a click on it.

## Solution (T01)

In `CardPreviewModal.tsx`:
- Add `e.stopPropagation()` and `e.preventDefault()` to the backdrop `onClick`
- Add `onMouseDown` with `e.stopPropagation()` to prevent the mousedown/mouseup
  sequence from leaking to elements underneath

## Wave Plan

| Wave | Tasks | Rationale |
|------|-------|-----------|
| 0    | T01   | Single focused fix |

## Files Affected

- `frontend/src/components/CardPreviewModal.tsx` (fix)
- `frontend/src/components/__tests__/CardPreviewModal.test.tsx` (verify)
