# F67 — Daily Liga Collection Scan

**Status:** planned
**Created:** 2026-08-26
**Priority:** P1 (core data freshness)

## Summary

Three related changes to the Liga scan infrastructure:

1. **Per-card credit cost** — Replace flat `BULK_SCAN_COST=5` with 1 credit
   per card for non-admin bulk scans. Add `GET /scans/preview` so the
   frontend can show exact cost before confirmation.
2. **max_age_days filter** — Let users choose how aggressively to skip
   recently-scanned cards when triggering manual "Refresh All". Pass
   through to existing `get_cards_for_liga_scan`.
3. **Admin daily Liga job** — System cron (6 AM) that auto-scans all admin
   collections via Liga with `max_age_days=1`, zero credit cost. Hardcoded
   in scheduler startup (not a user-created schedule).

## Architecture Decisions

- Per-card cost = `CARD_REFRESH_COST` (1 credit), same as single refresh.
  No bulk discount. Deduct entire cost upfront (before scan launch) to
  avoid mid-scan balance issues. Admin bypass unchanged.
- `GET /scans/preview?max_age_days=N` returns `{card_count, credit_cost,
  skipped_count}` so the frontend knows the exact cost before the user
  confirms. Reuses `repo.get_cards_for_liga_scan` with a count query.
- Admin daily scan is a **system job** seeded via
  `repo.seed_default_liga_schedules()` (extend existing method). Scan type
  `admin_daily_liga`. The scheduler handler queries all `is_admin=1` users,
  collects their entries, and runs a single Liga scan across all of them.
- `ScanRequest` schema gains optional `max_age_days: int | None` field,
  threaded through to `run_liga_scan`.
- Frontend: `CreditConfirmModal` shows per-card cost from preview; a
  `MaxAgeDaysSelect` dropdown lets users pick freshness threshold.

## Waves

| Wave | Tasks       | Description                                        |
|------|-------------|----------------------------------------------------|
| 0    | T01, T02    | Backend: preview endpoint + per-card cost; admin job |
| 1    | T03         | Frontend: per-card cost modal + max_age_days UI    |

## Task Index

- **T01** (Wave 0): Scan preview endpoint + per-card credit cost
- **T02** (Wave 0): Admin daily Liga scan job
- **T03** (Wave 1): Frontend per-card cost + max_age_days selector
