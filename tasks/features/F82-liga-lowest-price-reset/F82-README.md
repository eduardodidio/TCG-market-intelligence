# F82 Liga Lowest Price Strategy + Database Reset

**Status:** done

## Description

Two independent fixes shipping together:

1. **Liga Lowest Price Priority** -- The Liga price pipeline currently stores `mid` (median) as the primary price. All four code paths that extract Liga prices use `mid or low or high` fallback priority. This must be changed to `low or mid or high` so the system always stores the lowest available Liga marketplace price.

2. **CLI reset-prices Command** -- Existing price data was collected with the wrong strategy. A new CLI command `reset-prices` will delete price observations (all sources or filtered by source) with auto-backup, so the user can wipe stale data and re-scan with the corrected strategy. The existing `db-clear-prices` command cannot clear Liga prices because `cleanup.py` has `PROTECTED_SOURCES = {"liga", "manual"}`. The new command bypasses this protection with an explicit `--confirm` safety gate.

## Affected Code Paths (T01)

There are **four** locations with the wrong `mid or low or high` priority:

| File | Line | Function / Context |
|------|------|--------------------|
| `src/collectors/scan.py` | 54 | `_fetch_price_liga()` -- `normal.get("mid") or normal.get("low") or normal.get("high")` |
| `src/collectors/liga_sweep.py` | 44 | `_fetch_liga_price()` -- same pattern |
| `src/api/routers/collection.py` | 1059 | `refresh_card_price_liga` endpoint -- same pattern |
| `src/providers/liga/provider.py` | 369 | `get_current_price()` -- `avg_price = prices["normal"]["mid"]` |

## Wave Breakdown

### Wave 0 (parallel -- no dependencies)

| Task | Description |
|------|-------------|
| T01 | Liga Lowest Price Priority -- fix all 4 code paths + update tests |
| T02 | CLI reset-prices Command -- new repo method + CLI command + tests |

## Acceptance Criteria

1. Liga price extraction always uses the lowest available price (`low or mid or high` fallback)
2. `provider.get_current_price()` returns `low` as `avg_price` (primary price field)
3. CLI command `reset-prices` deletes price observations with auto-backup
4. `reset-prices --source liga` works (not blocked by PROTECTED_SOURCES)
5. All existing tests pass with updated price strategy
6. New tests cover the lowest-price priority logic and the reset command
