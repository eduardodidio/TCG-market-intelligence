# F13 -- Collection Scans: QA Report

**Verdict: PASSED**

**Date:** 2026-08-20
**Backend tests:** 786 passed (0 failed), 92.59% coverage (threshold: 70%)
**Frontend tests:** 228 passed (0 failed), 26 test files

## Acceptance Criteria

- [x] Scan runs are persisted in `scan_runs` table with full metrics
  - `ScanRunRow` in `src/database/models.py` with all columns: id, scan_type, filters_json, status, cards_total, cards_processed, cards_failed, observations_saved, error_summary, started_at, finished_at, created_at
  - Indexes on `status` and `(scan_type, created_at)`
- [x] Scans can filter by collection, set_code, format, rarity, card IDs
  - `ScanFilter` dataclass in `src/domain/models.py` with `scan_type`, `set_codes`, `format_name`, `rarities`, `card_ids`, `limit`
  - `ScanType` enum: collection, set, format, custom
  - `Repository.get_cards_for_scan()` applies filters to query
- [x] `scan` CLI triggers a scan with filter options and prints summary
  - `scan` command with `--type`, `--set`, `--format`, `--rarity`, `--card-ids`, `--limit`, `--dry-run`, `--delay`, `--concurrency`
  - `_print_scan_summary()` outputs structured result
- [x] `scan-history` CLI lists past scan runs with metrics
  - `scan-history` command with `--limit`, `--type`, `--status` filters
  - `_print_scan_history()` renders tabular output
- [x] `POST /api/v1/scans` triggers a background scan
  - Requires API key auth, creates scan run, launches background thread
  - Returns `ScanTriggerResponse` with scan_id and status
  - Correctly passes `run_id` to `run_scan()` (TechLead B1 fix verified)
- [x] `GET /api/v1/scans` lists scan history with pagination
  - Supports `limit`, `offset`, `scan_type`, `status` query params
  - Returns `ScanListResponse` with scans array and total count
- [x] `GET /api/v1/scans/{id}` returns scan detail or 404
  - Returns `ScanRunResponse` with all metrics and error_summary
  - Raises HTTP 404 when scan_id not found
- [x] Frontend Scans page shows history and allows triggering new scans
  - `Scans.tsx` page, `ScanForm.tsx` component, `ScanHistoryTable.tsx` component
  - `useScans.ts` hook for data fetching
  - Scan types match backend enum: "collection", "set", "format", "custom"
- [x] All existing tests pass (715+ backend, 192+ frontend)
  - Backend: 786 passed (71 net new tests)
  - Frontend: 228 passed (36 net new tests)
- [x] New tests added for all layers (coverage >= 90%)
  - Domain: `tests/unit/domain/test_scan_models.py`
  - Database: `tests/unit/database/test_scan_run_model.py`
  - Collector: `tests/collectors/test_scan.py`
  - API schemas: `tests/unit/api/test_scan_schemas.py`
  - API endpoints: `tests/unit/api/test_scan_endpoints.py`
  - CLI: `tests/unit/cli/test_scan_commands.py`
  - Frontend: `ScanForm.test.tsx` (5), `ScanHistoryTable.test.tsx` (4), `Scans.test.tsx` (page tests)
  - Coverage: 92.59% (exceeds 90% threshold)
- [x] README.md updated with F13 delivery notes
  - F13 section in "Shipped" with summary of scan orchestrator, filters, CLI, API, and frontend
  - Commands table updated with `scan` and `scan-history`
  - Endpoints table updated with 3 scan endpoints

## Code Review Findings

### TechLead B1 Fix (run_id parameter) -- VERIFIED
- `run_scan()` in `src/collectors/scan.py` accepts `run_id: int | None = None` (line 30)
- When `run_id` is provided (from API), it skips `create_scan_run()` and reuses the pre-created ID (line 48-49)
- `src/api/routers/scans.py` creates the scan run upfront (line 79) and passes `run_id=scan_id` to `run_scan()` (line 89)
- This prevents duplicate scan_runs rows and ensures the API-returned scan_id matches the actual run

### Frontend Scan Types -- VERIFIED
- `SCAN_TYPES` in `ScanForm.tsx` uses `"set"` and `"format"` (not `"by_set"`, `"by_format"`)
- These match `ScanType` enum values in `src/domain/models.py`: `SET = "set"`, `FORMAT = "format"`

## Documentation Verification

- [x] `docs/prd/F13-collection-scans.md` exists
- [x] `docs/diagrams/F13-architecture.mmd` exists
- [x] `docs/diagrams/F13-journey.mmd` exists
- [x] `README.md` updated with F13 delivery notes
- [x] `tasks/features/F13-collection-scans/F13-README.md` status is `done`

## Notes

- Coverage at 92.59% is healthy and above the 90% target
- The `src/collection/importer.py` shows 0% coverage (44 uncovered lines) -- this pre-dates F13 and is not a regression
- `src/cli/main.py` at 89% coverage is acceptable; uncovered lines are in older commands, not F13 scan commands
- No issues found. Feature is complete and well-tested across all layers.
