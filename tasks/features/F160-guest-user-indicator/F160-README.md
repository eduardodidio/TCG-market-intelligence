# F160 — Guest User Visual Indicator

**Status:** planned
**Branch:** homol
**Created:** 2026-09-18
**Source:** `docs/ux-journey-audit-2026-09-18.md` — P3 deferred

## Summary

Guest users see the admin's collection (F149 fix) but have no visual
indication that they're viewing someone else's data.

## Tasks

| Task | Title                                    | Files |
|------|------------------------------------------|-------|
| T01  | Show guest indicator in sidebar          | Layout.tsx, i18n |

## Wave Plan

### Wave 0
- **T01**: Below display name in sidebar, when `user.role === "guest"`,
  show a subtle subtitle "Viewing [admin]'s collection"

**Total: 1 task in 1 wave**
