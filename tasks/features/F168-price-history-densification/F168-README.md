# F168 -- Price History Densification

**Status:** planned

## Summary

Cards that appear in "movers" panels show empty or near-empty price history
graphs when clicked (1-2 data points). This feature creates a daily price
snapshot mechanism that records observations for ALL cards with prices in
the database (not just collection cards), adds a backfill CLI to
retroactively seed history from existing price data, and improves the
frontend chart UX for sparse data series.

## Problem

- `price_observations` only gets populated by daily scans (collection-only)
  and provider backfill (never run broadly)
- Cards not in any user collection never accumulate price history
- Even collection cards may have sparse history if recently added
- Users see a card in movers, click it, and find an empty graph

## Goals

1. Daily price snapshot service that reads existing latest prices from
   `source_cards` + `price_observations` and writes a new observation row
   for today (source=`daily_snapshot`) for every card that has a price
2. CLI command `snapshot-prices` + admin API endpoint to trigger it
3. Backfill CLI command `backfill-snapshots` to seed initial history from
   the current latest price (creates 1 observation per card for today)
4. Frontend chart improvements: fill gaps between sparse data points with
   dashed interpolation segments, better empty/sparse state messaging

## Architecture Impact

- **New module:** `src/collectors/price_snapshot.py` -- snapshot service
- **Modified:** `src/cli/main.py` -- new CLI commands
- **Modified:** `src/api/routers/admin.py` -- new admin trigger endpoint
- **Modified:** `frontend/src/components/PriceChart.tsx` -- sparse UX
- **New tests:** backend unit + frontend component tests

## Waves

- **Wave 0**: F168-T01, F168-T02   (backend snapshot service + CLI/API)
- **Wave 1**: F168-T03, F168-T04   (backfill CLI + frontend chart UX)
- **Wave 2**: F168-T05             (integration tests)

## Acceptance Criteria

1. Running `snapshot-prices` CLI creates one `price_observations` row per
   priced card for today's date (source=`daily_snapshot`), idempotent
2. Running it twice on the same day inserts 0 new rows (unique constraint)
3. Admin API endpoint triggers the same logic, returns count
4. `backfill-snapshots` creates an observation for today for all priced
   cards that have no `daily_snapshot` observation yet
5. PriceChart shows improved UX for 1-3 data points (current price line
   with context message)
6. No credit cost for snapshot operations (internal reads only)
7. Works on both SQLite and PostgreSQL (Neon)

## Diagrams

- Update `docs/diagrams/F168-architecture.mmd` -- data flow for snapshot
- Update `docs/diagrams/F168-journey.mmd` -- user journey: movers -> card detail

## Files Likely Modified

- `src/collectors/price_snapshot.py` (new)
- `src/database/repository.py` (new query methods)
- `src/cli/main.py` (new commands)
- `src/api/routers/admin.py` (new endpoint)
- `frontend/src/components/PriceChart.tsx` (sparse UX)
- `frontend/src/i18n/locales/en.json` + `pt-BR.json` (i18n keys)
- `tests/` (new test files)
