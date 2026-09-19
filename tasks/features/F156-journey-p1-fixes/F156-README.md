# F156 — Journey P1 Fixes (Flow-Breaking UX)

**Status:** planned
**Branch:** homol
**Created:** 2026-09-18
**Source:** `docs/ux-journey-audit-2026-09-18.md` — 4 P1 issues

## Summary

4 flow-breaking UX issues identified in the journey audit. Each breaks
a user flow by creating a dead-end or missing connection.

| ID    | Title                                    | Priority | Type    |
|-------|------------------------------------------|----------|---------|
| F156a | Web search "Added" → link to collection  | P1       | UX      |
| F156b | Alert notifications clickable → card     | P1       | UX+API  |
| F156c | Admin scan confirmation + progress       | P1       | UX      |
| F156d | Mobile back button on detail pages       | P1       | UX      |

## Wave Plan

### Wave 0 (parallel — no file conflicts, 4 tasks)
- **T01** (F156a): Add "View in Collection" toast after web search add [frontend]
- **T02** (F156b): Make alert notifications link to card detail [frontend+backend]
- **T03** (F156c): Add confirmation modal + loading state to admin ops [frontend]
- **T04** (F156d): Add mobile back button to Breadcrumb component [frontend]

**All 4 tasks touch different files — fully parallel.**

**Total: 4 tasks in 1 wave**
