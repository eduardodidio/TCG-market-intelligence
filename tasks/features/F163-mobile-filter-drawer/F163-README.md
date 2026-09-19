# F163 — Mobile Filter Drawer

**Status:** planned
**Branch:** homol
**Created:** 2026-09-18
**Source:** `docs/ux-audit-2026-09-18.md`

## Summary

MyCollection filter bar has 12 inline controls taking 180-250px on mobile
(40-50% of screen). Cards.tsx is 84-92px (acceptable). CatalogPage
already has collapsible filters. Focus on MyCollection.

## Approach

Rather than building a full drawer component (no UI library available),
collapse the action buttons (select mode, import, add, bulk canonize,
refresh) into a "More Actions" dropdown menu on mobile. Keep search +
sort + set filter visible (essential for navigation).

## Tasks

| Task | Title                                    | Files |
|------|------------------------------------------|-------|
| T01  | MyCollection action buttons → mobile dropdown | MyCollection.tsx, i18n |

## Wave Plan

### Wave 0
- **T01**: Wrap action buttons in a div hidden on mobile, add a dropdown
  menu button (`sm:hidden`) that reveals them. Desktop unchanged.

**Total: 1 task in 1 wave**
