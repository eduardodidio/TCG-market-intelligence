# F122 — Bugfix & Automation Batch

## Description

Batch of 4 independent fixes and infrastructure improvements:

1. **T01 — Collection Scroll CLS Fix**: SkeletonCard height mismatch causes layout shift; async widgets above the grid push it down during load.
2. **T02 — Price Sort Integrity Review**: Verify that price sort params reach the API correctly, pagination preserves order, and currency conversion does not reorder cards client-side.
3. **T03 — Set Completion Fix + Owned/Unowned View**: Sets without catalog data show fake 100%; clicking a set should show all catalog cards with owned highlighted and unowned faded.
4. **T04 — Daily Scan Automation via GitHub Actions**: Cron workflow to run liga-sweep and snapshot-portfolio daily using Neon DATABASE_URL from GitHub Secrets.

## Status: planned

## Waves

All 4 tasks are fully independent (no shared code changes, no output dependencies). Maximum parallelism.

| Wave | Tasks | Rationale |
|------|-------|-----------|
| 0    | T01, T02, T03, T04 | All independent: T01 is frontend-only skeleton/loading, T02 is sort investigation, T03 is set-completion backend+frontend, T04 is new infra file |

## Task List

| Task | Title | Status |
|------|-------|--------|
| F122-T01 | Collection Scroll CLS Fix | planned |
| F122-T02 | Price Sort Integrity Review | planned |
| F122-T03 | Set Completion Fix + Owned/Unowned View | planned |
| F122-T04 | Daily Scan GitHub Actions | planned |
