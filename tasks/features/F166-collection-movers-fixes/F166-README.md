# F166 — Collection Movers Panel Fixes

**Status:** planned
**Created:** 2026-09-21
**Type:** bugfix + enhancement

## Summary

Fix the Collection Movers panel on Dashboard:
1. Percentages are absurdly high due to cards with very low `price_start` (e.g. R$0.01 -> R$5.00 = 49900%)
2. Dashboard shows only top 3 — user wants top 5 as default
3. No expand button — user wants progressive expand to top 10 and top 100

## Wave Plan

| Wave | Tasks | Description |
|------|-------|-------------|
| 0 | T01, T02 | Backend sanity filter + raise limit to 100 (parallel) |
| 1 | T03 | Frontend: top 5 default + expandable top 10/100 buttons |

## Files Changed

### Backend (Wave 0)
- `src/database/repository.py` — add sanity filters to `get_collection_movers_optimized()`
- `src/api/routers/collection.py` — raise max limit from 20 to 100
- `tests/unit/test_collection_movers.py` — new tests for outlier filtering

### Frontend (Wave 1 — depends on backend limit raise)
- `frontend/src/components/CollectionMovers.tsx` — top 5 default, expand buttons
- `frontend/src/pages/Dashboard.tsx` — change limit={3} to limit={5}
- `frontend/tests/components/CollectionMovers.test.tsx` — test expand behavior

## Tasks

- [F166-T01](F166-T01.md) — Backend: sanity filters for outlier percentages
- [F166-T02](F166-T02.md) — Backend: raise max limit to 100
- [F166-T03](F166-T03.md) — Frontend: top 5 default + expandable view (top 10 / top 100)
