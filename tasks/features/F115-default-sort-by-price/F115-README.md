# F115 — Default Sort by Price

**Status:** planned
**Created:** 2026-09-09
**Branch:** homol

## Summary

Add backend support for sorting collection/cards by price. Make "price desc"
the true default so cards appear sorted by value on first load. Fix URL
persistence so sort state survives page refresh.

## Wave Plan

| Wave | Tasks | Parallelism | Notes |
|------|-------|-------------|-------|
| 0 | T01 | 1 | Backend: add price sort to repository + API |
| 1 | T02 | 1 | Frontend: wire default + URL sync (depends on T01) |

## Task List

| Task | Summary | Wave | Files |
|------|---------|------|-------|
| T01 | Backend price sort (SQL JOIN + API param) | 0 | repository.py, collection.py, cards.py |
| T02 | Frontend default sort by price + URL persistence | 1 | MyCollection.tsx, Cards.tsx, SortSelect.tsx |

## File Conflict Map

- **repository.py** — T01 only (list_collection query)
- **collection.py** — T01 only (sort_by validation pattern)
- **cards.py** — T01 only (add sort params)
- **MyCollection.tsx** — T02 only (default + URL sync)
- **Cards.tsx** — T02 only (default + URL sync)

## Cross-Feature Parallelism

F115 can run **fully parallel** with F114 (bugfix sweep) — different
sections of shared files (collection.py sort_by vs Liga URL).
F115-T02 touches MyCollection.tsx which F116 does NOT touch.
No conflicts with F117 (clean UI).
