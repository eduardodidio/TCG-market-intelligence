# F98 -- Scan Results & Action Feedback

**Status:** planned

## Problem

After bulk refresh, the progress bar disappears after 2 seconds with only
a terse "Complete" message. The scan orchestrator already tracks
`cards_failed`, `observations_saved`, and `error_summary` (a JSON array of
per-card error strings), but none of this detail reaches the user. Delete
actions execute immediately with no undo window. Inline edits save silently
with no visual confirmation.

## Goals

1. Show a persistent scan summary card after bulk refresh completion with
   breakdown: processed, priced, failed (not found / rate limited / other).
2. Expose structured summary fields in the ScanRun API response so the
   frontend does not need to parse `error_summary` JSON.
3. Undo toast for collection card deletion (5-second delayed execution).
4. Subtle save feedback for inline edits (checkmark flash).
5. i18n for all new strings (EN + PT-BR).

## Architecture Decisions

- **No DB migration.** The `error_summary` column already stores a JSON
  array of error strings. The backend will parse this JSON and compute
  derived counts (`not_found_count`, `rate_limited_count`) on read, adding
  them to the API schema as computed fields. This avoids a migration and
  keeps the single source of truth in `error_summary`.
- **Delayed-execution delete** instead of soft-delete. The frontend will
  hold a 5-second timer before calling `DELETE /collection/{id}`. An
  "Undo" toast cancels the timer. This avoids schema changes, migration,
  and cleanup cron for soft-deleted rows.
- **ScanSummaryCard is a new component** that replaces the existing terse
  "Complete" state in `ScanProgressBar`. It receives structured data from
  the `useCollectionRefresh` hook.

## Task List

| Task | Title | Wave | Depends On |
|------|-------|------|------------|
| T01 | Backend: computed summary fields on ScanRun API | 0 | -- |
| T02 | Frontend: ScanSummaryCard component | 1 | T01 |
| T03 | Frontend: useCollectionRefresh summary state | 1 | T01 |
| T04 | Frontend: undo delete toast | 2 | -- |
| T05 | Frontend: inline edit save feedback | 2 | -- |
| T06 | i18n: EN + PT-BR strings | 2 | T02, T03, T04, T05 |

## Waves

### Wave 0 -- Backend (T01)
Extend the ScanRun API response with computed summary fields derived from
the existing `error_summary` JSON column. No DB migration.

### Wave 1 -- Scan Summary UI (T02, T03)
New `ScanSummaryCard` component and updated `useCollectionRefresh` hook to
persist summary data after scan completion instead of clearing it after 2s.

### Wave 2 -- Action Feedback + i18n (T04, T05, T06)
Undo delete toast, inline edit save checkmark, and all new i18n strings.

## Files Likely Touched

**Backend:**
- `src/api/schemas/scans.py` -- add computed fields to `ScanRunResponse`
- `src/api/routers/scans.py` -- populate new fields in `_row_to_response`

**Frontend:**
- `frontend/src/components/ScanSummaryCard.tsx` (new)
- `frontend/src/components/ScanProgressBar.tsx` (delegate done state)
- `frontend/src/hooks/useCollectionRefresh.ts` (persist summary)
- `frontend/src/components/DeleteEntryButton.tsx` (delayed delete)
- `frontend/src/components/UndoToast.tsx` (new)
- `frontend/src/components/InlineEditField.tsx` (save feedback)
- `frontend/src/pages/CollectionCardDetail.tsx` (wire undo delete)
- `frontend/src/i18n/locales/en.json`
- `frontend/src/i18n/locales/pt-BR.json`

## Test Impact

- `tests/api/test_scans.py` -- new assertions for computed fields
- `frontend/tests/components/ScanSummaryCard.test.tsx` (new)
- `frontend/tests/components/DeleteEntryButton.test.tsx` (undo behavior)
- `frontend/tests/components/InlineEditField.test.tsx` (save feedback)
- `frontend/tests/hooks/useCollectionRefresh.test.ts` (summary state)
