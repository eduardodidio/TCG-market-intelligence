# F73 — Scan Hygiene (Reset + Stale Detection)

**Status:** planned
**Wave structure:** Wave 0 (parallel with F72, F76)
**Dependencies:** None

## Summary

Reset all existing scan_runs records (historical noise) and add startup logic to auto-mark stale "running" scans as "error" when the app starts.

## Tasks

| Task | Description | Wave |
|------|-------------|------|
| F73-T01 | One-time scan reset migration + stale scan detection on startup | 0 |
| F73-T02 | Backend tests | 0 |

## Acceptance Criteria

- All existing scan_runs records are deleted (clean slate)
- On app startup, any scan with status="running" from a previous day is marked status="error"
- Stale scans get error_summary explaining they were auto-marked
- New scans work normally after reset
- Tests cover stale detection logic
