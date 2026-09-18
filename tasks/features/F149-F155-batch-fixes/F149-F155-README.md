# F149-F155 — Batch Fixes & UX Improvements

**Status:** done
**Branch:** homol
**Created:** 2026-09-18

## Summary

7 features/fixes targeting guest user visibility, UX polish, performance,
and navigation consolidation.

| ID   | Title                                  | Priority | Type          |
|------|----------------------------------------|----------|---------------|
| F149 | Guest collection visibility fix        | P0       | bug           |
| F150 | Share icon removal + beta tester badge | P1       | UX            |
| F151 | Art card image fix (Arkenstone 44a)    | P1       | bugfix        |
| F152 | Dashboard movers timeout fix           | P1       | bug/perf      |
| F153 | Remove catalog page (merge → explore)  | P1       | UX            |
| F154 | Typeable set filter on Cards page      | P2       | feature       |
| F155 | Full UX sweep for follow-ups           | P3       | audit         |

## Wave Plan

### Wave 0 (parallel — no file conflicts, 4 tasks) — DONE
- **T01** (F149): Fix guest proxy in `require_auth_or_api_key` [backend] ✓
- **T02** (F152): Backend — optimize collection movers query with CTEs [backend] ✓
- **T03** (F151): Fix art card image — prefer DB image_uri, strip letter suffix [backend] ✓
- **T04** (F150): Remove share toggle + add beta tester badge [frontend] ✓

### Wave 1 (parallel — no file conflicts, 2 tasks) — DONE
- **T06** (F153): Remove catalog nav entry + route → redirect /cards [frontend] ✓
- ~~T05 (F152): CANCELLED — frontend timeout already exists (10s default)~~

### Wave 2 (depends on F153 for context) — DONE
- **T07** (F154): Add typeable set/collection filter to Cards page [frontend] ✓

### Wave 3 (depends on all fixes landing) — DONE
- **T08** (F155): Full UX experience sweep — audit report [audit] ✓

**Total: 7 active tasks** (T05 cancelled) across 4 waves
**Max parallelism: Wave 0 runs 4 tasks simultaneously**
