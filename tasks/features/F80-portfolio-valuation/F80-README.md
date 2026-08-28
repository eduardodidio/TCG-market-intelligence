# F80 — Daily Portfolio Valuation Tracking

**Status:** planned
**Wave:** 1 (depends on F79 for correct qty-weighted values)

## Summary
Track collection value daily and display appreciation/depreciation percentage. New DB table for snapshots, CLI command for daily cron, API endpoint, frontend % display.

## Tasks
| Task | Description | Wave |
|------|-------------|------|
| F80-T01 | DB model + migration: portfolio_snapshots table | 1 |
| F80-T02 | Snapshot service + CLI command | 1 |
| F80-T03 | API endpoint: GET /collection/valuation | 1 |
| F80-T04 | Frontend: % change display on Dashboard + Collection | 1 |
