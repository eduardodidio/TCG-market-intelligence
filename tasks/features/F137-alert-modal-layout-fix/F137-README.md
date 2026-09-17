# F137 -- Alert Modal Layout Fix

**Status:** planned
**Branch:** homol

## Problem Statement

The SetAlertModal overlay escapes to the left side of the viewport. The
overlay uses `fixed inset-0 z-50 flex items-center justify-center` which
should cover the full viewport and center the modal, but in practice the
modal content shifts or clips to the left.

The root cause is likely an interaction between the sidebar layout and
the modal's flex centering. The Layout component uses a `flex h-screen`
root with a sidebar (`fixed` on mobile, `relative` on desktop via
`md:relative`). While `fixed inset-0` should position the overlay
relative to the viewport regardless of parent layout, the flex centering
of the inner modal box can be thrown off when:
- The sidebar width (w-64 expanded, w-16 collapsed) participates in the
  flex container's available space calculation
- Form inputs with `pl-10` (R$ prefix icon) or `w-full` expand beyond
  the modal's `max-w-md` constraint
- No `overflow-hidden` on the overlay allows content to escape visually

## Acceptance Criteria

- SetAlertModal is horizontally centered on all viewports (320px, 768px,
  1280px) regardless of sidebar state (expanded/collapsed/hidden)
- Modal content does not clip or overflow to the left or right
- Form inputs (price input with R$ prefix) stay within modal boundaries
- Existing alerts list renders correctly within modal boundaries
- No visual regression in other modals that share the same overlay pattern
  (CreditConfirmModal, BatchAddModal, CsvImportModal, DeckImportModal,
  TradeInterestModal, DeckView confirm dialog)
- Close on backdrop click and Escape key still work correctly

## Wave Strategy

### Wave 0 -- Single Task (1 task)

| Task | Description |
|------|-------------|
| T01  | Debug and fix SetAlertModal layout overflow |

## Key Files

- `frontend/src/components/SetAlertModal.tsx` -- the modal component
- `frontend/src/components/Layout.tsx` -- sidebar layout (context for the bug)
- `frontend/src/pages/CardDetail.tsx` -- renders SetAlertModal
- `frontend/tests/components/SetAlertModal.test.tsx` -- existing tests

## Related Modals (same overlay pattern)

These modals use the identical `fixed inset-0 z-50 flex items-center
justify-center` pattern. If the fix is structural (e.g., adding
`overflow-hidden`), verify these are not regressed:
- `BatchAddModal.tsx`
- `CreditConfirmModal.tsx`
- `CsvImportModal.tsx`
- `DeckImportModal.tsx`
- `TradeInterestModal.tsx`
- `DeckView.tsx` (inline confirm dialog)

## Constraints

- Fix must not break backdrop-click-to-close behavior (relies on
  `e.target === e.currentTarget` on the overlay div)
- Fix must work with both dark and light themes
- No new dependencies
