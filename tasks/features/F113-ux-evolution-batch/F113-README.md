# F113 — UX Evolution Batch

**Status:** done
**Created:** 2026-09-08
**Branch:** homol

## Summary

Batch of 10 fixes/features covering auth, navigation, catalog bugfix, card
list UX, set completion, explore cards, web search resilience, portfolio
data flow, README cleanup, and project cleanup.

## Wave Plan

| Wave | Tasks | Parallelism | Notes |
|------|-------|-------------|-------|
| 0 | T01, T02, T03, T04, T05 | 5 parallel | Zero file overlap — trivial/backend only |
| 1 | T06, T07, T08 | 3 parallel | Different file groups |
| 2 | T09 | 1 | Consolidates Cards.tsx changes (R5+R9) |

## Task List

| Task | Request | Summary | Wave |
|------|---------|---------|------|
| T01 | R3 | README "Future" section cleanup | 0 |
| T02 | R7 | Catalog page URL fix + show all DB cards | 0 |
| T03 | R8+R2 | Auth redirect + nav restructure (Layout+App) | 0 |
| T04 | R10 | Web search PT/EN name fallback | 0 |
| T05 | R4 | Project cleanup (sujeiras) | 0 |
| T06 | R6 | Set completion UX: collapse, icons, navigate | 1 |
| T07 | R1 | Portfolio/Liga dashboard data flow fix | 1 |
| T08 | R3+ | CLAUDE.md placeholders + docs sync | 1 |
| T09 | R5+R9 | Cards page: scroll reset, set icons, price refresh | 2 |

## File Conflict Map

- **Layout.tsx** — T03 only (R2 auth guard in App.tsx, R8 nav items in Layout.tsx, same dev)
- **Cards.tsx** — T09 only (R5 scroll + R9 icons/refresh consolidated)
- **MyCollection.tsx** — T06 only (set completion section)
- **catalog hooks** — T02 only
- **card_search.py** — T04 only
