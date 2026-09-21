# F165 — Fix trending/movers 500 errors definitively

**Status:** done
**Created:** 2026-09-21
**Priority:** P0 (production bug — user-facing 500s on Dashboard)

## Problem

Dashboard "Em Alta" and "Em Baixa" sections return HTTP 500 on:
- `GET /api/v1/market/trending/gainers?period=30d&currency=PILA&limit=10&collection_only=true`
- `GET /api/v1/market/trending/losers?period=30d&currency=PILA&limit=10&collection_only=true`

## Root Cause Analysis

1. **`src/services/trending.py:63`** — `TrendingService.get_trending()` only catches `OperationalError`, but PostgreSQL/psycopg2 can throw `InternalError`, `InterfaceError`, `DatabaseError` on timeout or connection issues. F164 broadened the catch in `collection.py` but missed `trending.py`.

2. **`src/api/routers/market.py:133-176`** — `get_trending_gainers()` and `get_trending_losers()` have NO try/except around `service.get_trending()`. Any unhandled exception propagates as 500.

3. **`src/database/repository.py:1176-1195`** — `get_trending_price_data_for_user()` builds a massive IN clause with `liga_{cid}`, `liga_{cid}_foil`, `manual_{cid}` for every card in user's collection. For large collections (500+ cards), this creates 1500+ patterns, which can exceed the 8s `statement_timeout` on Neon.

## Tasks

| Task | Description | Wave | Depends |
|------|-------------|------|---------|
| T01  | Broaden exception catch in TrendingService | W1 | — |
| T02  | Add try/except in market router endpoints | W1 | — |
| T03  | Optimize get_trending_price_data_for_user query | W1 | — |
| T04  | Add backend tests for error resilience | W1 | — |

**Waves:** 1 (all tasks are independent, run in parallel)

## Acceptance Criteria

- [ ] `GET /market/trending/gainers` with `collection_only=true` NEVER returns 500 — returns empty data on error
- [ ] `GET /market/trending/losers` with `collection_only=true` NEVER returns 500 — returns empty data on error
- [ ] `GET /market/volatile` NEVER returns 500 — returns empty data on error
- [ ] Large collections (500+ cards) complete within 12s statement_timeout
- [ ] All errors are logged with structured context (error_type, period, user_id)
- [ ] New tests cover: timeout scenarios, non-OperationalError exceptions, empty fallback responses

## Files Changed

- `src/services/trending.py` (T01)
- `src/api/routers/market.py` (T02)
- `src/database/repository.py` (T03)
- `tests/` — new test files (T04)
