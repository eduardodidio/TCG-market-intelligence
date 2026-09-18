# F144 — Dashboard Fixes (Rename Investment + Fix Movers Timeout)

**Status:** planned
**Branch:** homol
**Created:** 2026-09-18

## Problem

1. The DashboardInvestmentSummary title says "Investimento" but should say
   "Investimento Catalogado" to clarify it refers to cataloged investment data.

2. The market movers endpoint (`GET /api/v1/market/movers`) calls
   `repo.get_movers()` which performs catastrophic N+1 queries: it loads ALL
   105k+ cards, then for EACH card queries source_cards, then for EACH
   source_card fires 2 price_observation queries (earliest + latest). This is
   O(cards * source_cards * 2) individual DB round-trips to PostgreSQL, causing
   timeouts on the dashboard.

3. The collection movers endpoint (`GET /api/v1/collection/movers`) calls
   `repo.get_trending_price_data_for_user()` which is already optimized with
   JOINs, but the frontend `CollectionMovers` component has no error state --
   on fetch failure it shows the loading skeleton indefinitely.

## Solution

- **Wave 0** (parallel): i18n rename (trivial) + frontend error handling
- **Wave 1**: Rewrite `get_movers()` with a single SQL query using window
  functions and JOINs, eliminating the N+1 pattern entirely

## Waves

| Wave | Tasks | Parallel? |
|------|-------|-----------|
| 0    | T01, T02 | yes |
| 1    | T03 | solo |

## Files Affected

- `frontend/src/i18n/locales/pt-BR.json` (line 245)
- `frontend/src/i18n/locales/en.json` (line 245)
- `frontend/src/components/CollectionMovers.tsx`
- `frontend/src/components/__tests__/CollectionMovers*.test.tsx`
- `src/database/repository.py` (get_movers, lines 962-1034)
- `src/api/routers/market.py` (callers of get_movers)
- `src/services/market_data.py` (caller of get_movers)
- `tests/` (repository + market router tests)
