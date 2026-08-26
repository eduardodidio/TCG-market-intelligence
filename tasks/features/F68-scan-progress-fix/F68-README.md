# F68 — Scan Progress Bar Fix

**Status:** shipped
**Created:** 2026-08-26
**Priority:** P1 (user-facing bug)
**Wave Group:** 0 (independent — parallel with F63, F64, F70)

## Summary

When users click "Refresh All" on the collection page, the progress bar does
not update in real-time. The `/scans` page also doesn't reflect live progress.
Backend logs show normal scan progression — the issue is on the frontend side
(SSE/polling not updating UI state).

## Root Cause

Two backend bugs in the scan orchestrator:

1. **No intermediate DB updates**: `cards_processed` was only written to the
   database at scan completion. When the SSE stream dropped and the frontend
   fell back to polling `GET /scans/{id}`, it always saw 0 progress.

2. **Failed cards excluded from progress**: Error handlers incremented
   `cards_failed` but not `cards_processed`, so progress could never reach
   100% when cards failed.

The SSE path and all frontend hooks (`useScanStream`, `useCollectionRefresh`,
`ScanProgressBar`) were correctly implemented — no frontend changes needed.

## Fix

- Added `_persist_progress()` to `src/collectors/scan.py` that writes current
  counters to the database after every card (success or failure)
- All error handlers now increment both `cards_processed` and `cards_failed`
- Updated 9 test assertions across 2 test files

## Acceptance Criteria

1. "Refresh All" shows live progress bar updating card-by-card
2. Last scanned card name displays during refresh
3. Progress persists across page navigation (resume from localStorage)
4. Completion state shows briefly then clears
5. Error states display and auto-clear

## Waves

| Wave | Tasks | Description |
|------|-------|-------------|
| 0    | T01   | Diagnose and fix SSE/polling progress updates |

## Tasks

- **T01** (Wave 0): Debug and fix scan progress bar real-time updates — **done**
