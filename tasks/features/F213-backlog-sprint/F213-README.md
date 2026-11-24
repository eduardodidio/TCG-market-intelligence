# F213 — Backlog Sprint (8 Features + UX P1)

**Status:** planned
**Created:** 2026-11-24
**Architect:** Claude Opus 4.6

## Overview

Comprehensive sprint covering the entire project backlog. Features are grouped
into 4 Waves with zero inter-dependencies within each Wave, enabling maximum
parallel execution via git worktrees.

## Sub-Features

| ID | Origin | Name | Complexity |
|---|---|---|---|
| F213a | F175 | Trending Market Mode Fix | M |
| F213b | F124 | Collection Valuation Panel | M |
| F213c | F176 | Collection Price History | L |
| F213d | F177 | Banlist Sync + Owned Filter + History | L |
| F213e | F180 | Reality Fracture Catalog Seed | S |
| F213f | F110 | Social & Trade Matching | H |
| F213g | F100 | Admin Console Operations | M |
| F213h | UX P1 | i18n, Accessibility, Dark Mode Fixes | M |

## Wave Plan

### Wave 0 — Quick Wins + Backend Foundations (5 tasks, all parallel)
No inter-dependencies. Pure backend or ops work.

| Task | Sub-Feature | Description | Est |
|---|---|---|---|
| T01 | F213e | Reality Fracture catalog seed script | S |
| T02 | F213a | Trending market query union + cache fix | M |
| T03 | F213d-1 | Banlist sync bug fixes (JSONL parser, batching, diff) | M |
| T04 | F213g-1 | Admin job trigger endpoints (sweep, snapshot, seed) | M |
| T05 | F213c-1 | Price history variant resolution + 1-point/day aggregation | M |

### Wave 1 — Core Features Backend (6 tasks, all parallel)
Depends on Wave 0 foundations being in place.

| Task | Sub-Feature | Description | Est |
|---|---|---|---|
| T06 | F213d-2 | Banlist API: owned_only filter, status endpoint, manual sync | M |
| T07 | F213c-2 | Price history endpoints + daily snapshot source + backfill CLI | M |
| T08 | F213f-1 | Wishlist CRUD hardening + duplicates detection endpoint | M |
| T09 | F213b-1 | Portfolio API: acquisition-only filter, unpriced count, Liga link resolver | M |
| T10 | F213g-2 | Admin audit log endpoint + DB stats dashboard data | M |
| T11 | F213h-1 | i18n: wrap 150+ hardcoded strings (Cards, Admin, Import, DeckBuild) | M |

### Wave 2 — Frontend Features (6 tasks, all parallel)
Backend APIs from Wave 1 are ready.

| Task | Sub-Feature | Description | Est |
|---|---|---|---|
| T12 | F213d-3 | BanList page: owned toggle, BanCardDetailModal, history timeline | M |
| T13 | F213c-3 | Price history chart on CardDetail + variant badge + sources tooltip | M |
| T14 | F213f-2 | WishlistPage + TradeMatchesPage frontend | M |
| T15 | F213b-2 | Collection grid inline acquisition edit + dashboard KPI refactor | M |
| T16 | F213g-3 | Admin dashboard: job triggers UI, audit log viewer, DB stats | M |
| T17 | F213h-2 | Accessibility: aria-labels, keyboard nav, alertdialog roles | M |

### Wave 3 — Polish + Integration (4 tasks, all parallel)
Final integration, dark mode, error handling.

| Task | Sub-Feature | Description | Est |
|---|---|---|---|
| T18 | F213f-3 | Trade matcher service + cross-user matching UI | M |
| T19 | F213h-3 | Dark mode fixes + error retry pattern on remaining pages | S |
| T20 | F213c-4 | Price history backfill script + forward-fill carry + dry-run | M |
| T21 | ALL | README update + diagrams + integration smoke tests | S |

## Totals

- **21 tasks** across **4 waves**
- **Max parallelism per wave:** 6 (Wave 1 and 2)
- **Estimated files changed:** ~80-120
- **New tables:** 0 (wishlists already exists)
- **New endpoints:** ~12
- **New/modified pages:** ~6

## Execution

```bash
# Wave 0 (5 worktrees)
/create-feature F213 --wave 0

# Wave 1 (6 worktrees)
/create-feature F213 --wave 1

# etc.
```

## TEA Gate

Test Architect validates after each Wave:
- Backend: `pytest tests/ --cov=src`
- Frontend: `cd frontend && npm test`
- No Wave proceeds until prior Wave passes TEA gate.
