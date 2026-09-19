# F162 — Accessibility Gaps

**Status:** planned
**Branch:** homol
**Created:** 2026-09-18
**Source:** `docs/ux-audit-2026-09-18.md`

## Summary

Several interactive components are missing `focus-visible` rings and
the collapsed sidebar lacks `sr-only` text for screen readers.

## Audit Results

**Good examples (already accessible):** Layout nav links, AlertBell,
ThemeToggle, GridSizeToggle, CreditConfirmModal — all have focus-visible
rings and aria-labels.

**Need fix:**
- SetAlertModal: direction, submit, delete buttons (3 buttons)
- BatchAddModal: cancel, preview buttons (2 buttons)
- TreasureBalance: claim bonus button (1 button)
- Layout.tsx: collapsed sidebar nav items missing sr-only text

## Tasks

| Task | Title                                    | Files |
|------|------------------------------------------|-------|
| T01  | Add focus-visible rings to modal buttons | SetAlertModal.tsx, BatchAddModal.tsx, TreasureBalance.tsx |
| T02  | Add sr-only text for collapsed sidebar   | Layout.tsx |

## Wave Plan

### Wave 0 (parallel — no file conflicts)
- **T01**: Add `focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-cyan-400` to 6 buttons
- **T02**: Add `<span className="sr-only">{label}</span>` when sidebar is collapsed

**Total: 2 tasks in 1 wave**
