# F185 — Movers Percentage Integrity Fix

## Problem
The "Maiores Altas" and "Maiores Baixas" percentages are showing incorrect /
inflated values. Root cause analysis identified:

1. `get_movers()` (market-wide) uses `price_start > 0` — allows penny cards
   (R$0.01) as base, causing extreme percentages (e.g., R$0.01->R$5 = 49900%)
2. `get_movers()` has NO cap on `change_pct` — extreme outliers pass through
3. `get_collection_movers_optimized()` already has both fixes (R$0.50 floor +
   1000% cap, added in F166) but `get_movers()` does not
4. The MarketTicker / trending API endpoints also consume `get_movers()` so
   they are affected too
5. No validation on price insertion — extreme outliers stored without checks

## Scope
- Backend: align `get_movers()` filters with `get_collection_movers_optimized()`
- Backend: add data validation for extreme price observations
- Backend: add diagnostic CLI command to identify dirty price data
- Tests for all changes

## Constraints
- Do NOT change `get_collection_movers_optimized()` — it's already correct
- Do NOT delete or modify existing price_observations data without user approval
- CLI diagnostic is read-only (no destructive operations)
