# F185 — Movers Percentage Integrity Fix

**Status:** done

## Goal

Fix incorrect/inflated percentage values in market movers (maiores altas e
baixas) by aligning `get_movers()` sanity filters with the already-correct
`get_collection_movers_optimized()`, and adding price observation validation
to prevent future dirty data.

## Architecture Impact

- **Backend** — `src/database/repository.py` (`get_movers` method)
- **Backend** — `src/api/routers/market.py` (volatile endpoint also uses raw movers)
- **Backend** — `src/database/repository.py` (`insert_price_observations` validation)
- **Backend** — `src/cli/main.py` (new diagnostic CLI subcommand)

## Wave Manifest

- **Wave 0**: F185-T01 (fix `get_movers()` filters), F185-T02 (fix market volatile endpoint)
- **Wave 1**: F185-T03 (price observation validation), F185-T04 (diagnostic CLI + diagrams)

## Acceptance Criteria

1. `get_movers()` applies R$0.50 minimum price floor (same as collection movers)
2. `get_movers()` caps `change_pct` at +/-1000% (same as collection movers)
3. Market volatile endpoint applies same sanity filters
4. Price observation insertion rejects prices <= 0
5. CLI `diagnose-prices` command lists outlier observations (read-only)
6. All existing tests continue to pass
7. New tests cover the filter changes

## Diagrams

- `docs/diagrams/F185-architecture.mmd` — data flow showing filter points
- `docs/diagrams/F185-journey.mmd` — price observation lifecycle
