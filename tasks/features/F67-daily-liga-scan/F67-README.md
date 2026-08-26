# F67 — Daily Liga Collection Scan (Admin Auto-Scan)

**Status:** planned
**Created:** 2026-08-26
**Priority:** P1 (core data freshness)
**Wave Group:** 2 (depends on F65 — admin credit exemption)

## Summary

Create a scheduled daily job that automatically scans all admin users'
collections via the Liga provider to keep price data fresh. This scan is
free for admins (no credit deduction). Uses existing APScheduler (F37) and
Liga scan infrastructure (F60). Users with credits can also trigger manual
full-collection scans that cost 1 credit per card.

## Acceptance Criteria

1. New scheduled scan type: "admin_daily_liga"
2. Job runs daily (configurable cron) via APScheduler
3. Scans admin users' collections via Liga provider
4. Uses `max_age_days` filter to skip recently-scanned cards
5. No credit cost for admin daily scans
6. Manual "Refresh All" for non-admin users costs 1 credit per card
7. Progress trackable via existing SSE/scan infrastructure
8. Job auto-pauses on repeated failures (existing F37 behavior)

## Architecture Decisions

- Reuse existing `run_liga_scan` + `ScanScheduler` — no new scheduler needed
- Admin exemption: check `is_admin` before credit deduction in scan orchestrator
- `max_age_days=1` default: skip cards scanned in last 24h to avoid redundant work
- Scan runs as background task — not blocking API

## Waves

| Wave | Tasks | Description |
|------|-------|-------------|
| 0    | T01   | Admin daily scan job + credit exemption in scan flow |
| 1    | T02   | Bulk refresh credit integration (per-card cost for non-admins) |

## Tasks

- **T01** (Wave 0): Scheduled admin_daily_liga job + admin credit exemption
- **T02** (Wave 1): Per-card credit cost for non-admin bulk "Refresh All"
