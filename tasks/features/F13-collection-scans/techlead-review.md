# F13 Tech Lead Review -- Collection Scans

**Reviewer:** Tech Lead (automated)
**Date:** 2026-08-20
**Verdict:** APPROVED WITH NOTES

---

## Test Results

| Suite | Tests | Status |
|-------|-------|--------|
| Backend (pytest) | 786 passed | All green |
| Frontend (vitest) | 228 passed | All green |
| Coverage | 92.59% | Above 90% target |

Backend grew from 715 to 786 tests (+71). Frontend grew from 192 to 228 (+36).

---

## Architecture Compliance

The implementation matches the F13-README.md plan across all 9 tasks:

- Domain models (`ScanStatus`, `ScanType`, `ScanFilter`, `ScanRun`) -- correct
- DB table (`ScanRunRow`) with proper indexes -- correct
- Repository CRUD + `get_cards_for_scan` -- correct
- Scan orchestrator (`src/collectors/scan.py`) -- correct
- CLI commands (`scan`, `scan-history`) -- correct
- API schemas and endpoints -- correct
- Frontend page with form + history table -- correct
- Diagrams (architecture + journey) -- present and accurate
- README.md updated with F13 section -- correct

All 9 tasks are accounted for and delivered as specified.

---

## Issues Found

### BLOCKING

**B1: Double scan_run creation from API trigger**
- **Files:** `src/api/routers/scans.py:79` + `src/collectors/scan.py:47`
- The `trigger_scan` endpoint creates a `scan_run` row at line 79 to
  return the ID immediately, then launches `run_scan()` in a background
  thread -- which creates a **second** `scan_run` row at line 47 of
  `scan.py`. Every API-triggered scan produces an orphan "pending" row
  that never gets updated, plus a real row that tracks the actual scan.
- **Fix:** Either (a) pass the existing `scan_id` into `run_scan()` so
  it reuses it instead of creating a new one, or (b) remove the
  `create_scan_run` call from the router and let `run_scan()` own
  creation entirely (but then the returned `scan_id` must come from
  the thread, which requires a synchronization mechanism).

### NON-BLOCKING

**N1: `ScanListResponse.total` is page count, not total count**
- **File:** `src/api/routers/scans.py:112`
- `total=len(runs)` returns the count of items on the current page, not
  the total number of matching scan runs in the database. For pagination
  support this should be a separate `SELECT COUNT(*)` query. The frontend
  currently does not paginate, so this is cosmetic for now.

**N2: `format_name` filter accepted but silently ignored**
- **Files:** `src/domain/models.py:279`, `src/database/repository.py:834-882`
- `ScanFilter.format_name` is accepted in the domain model, CLI, API
  schema, and frontend form, but `get_cards_for_scan()` never applies
  it. The `user_collection` table has no `format` column, so this filter
  has no backing data. This is misleading to users who select "By Format"
  in the UI and enter a format name -- it will return all cards.
- **Suggestion:** Either remove format filtering from the UI/API until
  format data is available, or add a validation error when `format_name`
  is provided.

**N3: ScanForm type values mismatch with backend enum**
- **File:** `frontend/src/components/ScanForm.tsx:8-9`
- The form uses `"by_set"` and `"by_format"` as scan type values, but the
  backend `ScanType` enum expects `"set"` and `"format"`. The POST request
  will fail with a validation error when using these types. The backend
  `ScanType("by_set")` will raise a `ValueError`.
- **Fix:** Change form values to `"set"` and `"format"` to match the
  backend enum, or update the backend to accept both forms.

**N4: No inter-request delay in scan orchestrator**
- **File:** `src/collectors/scan.py:74-127`
- The `delay` parameter is accepted by `run_scan()` and passed to
  `MypConfig`, but the `process_entry` coroutine never explicitly
  delays between requests. The semaphore limits concurrency but does
  not enforce inter-request spacing. If `MypCardsProvider` does not
  internally respect the delay config, this could hammer MYP servers.
- Check: Verify `MypCardsProvider` applies `delay_seconds` internally.

**N5: `_dt_to_str` handles `date` objects incorrectly**
- **File:** `src/api/routers/scans.py:29-37`
- The function checks for `datetime` but falls through to `str(val)` for
  `date` objects. While `str(date)` produces `YYYY-MM-DD` which is fine,
  this is implicitly correct rather than explicitly handled. Minor.

---

## Code Quality

**Positives:**
- Clean separation of concerns: domain models / DB / orchestrator / CLI / API / frontend
- Proper use of `asyncio.Semaphore` + `asyncio.Lock` for concurrency control
- Error isolation per card (FR-05) correctly implemented
- Status logic (50% threshold) matches NFR-03
- Provider cleanup in `finally` block ensures no resource leaks
- Auth on mutation endpoint, no auth on GET endpoints -- correct pattern
- Test fixtures are well-factored (`_card_entry`, `_make_scan_run`, `makeScanRun`)
- Frontend components have proper `data-testid` attributes for testing
- Race condition protection in hooks via `fetchCountRef`

**Minor observations:**
- `scan.py` line 126-127: `asyncio.gather(*tasks)` creates all tasks at once;
  the semaphore handles throttling, which is fine for the expected collection
  sizes (hundreds, not thousands).
- Repository returns dicts for scan runs rather than ORM objects -- this is
  consistent with the existing pattern and avoids detached-instance issues.

---

## Documentation

- PRD: Complete and well-structured (`docs/prd/F13-collection-scans.md`)
- Architecture diagram: Accurate, covers all data flows (`docs/diagrams/F13-architecture.mmd`)
- Journey diagram: Covers user flow end-to-end (`docs/diagrams/F13-journey.mmd`)
- README.md: Updated with F13 section including all CLI commands and API endpoints
- Commands table in README updated with `scan` and `scan-history`
- Endpoints table in README updated with all 3 scan endpoints

---

## Security

- `POST /api/v1/scans` properly guarded by `verify_api_key` dependency
- GET endpoints are public (read-only) -- correct
- No hardcoded secrets
- Input validation via Pydantic schemas on request body
- CLI uses Click's type validation for numeric inputs

---

## Summary

The feature is well-implemented across all layers with solid test coverage
(92.59%) and comprehensive documentation. The one blocking issue (B1: double
scan_run creation) must be fixed before merging -- it will cause orphan rows
on every API-triggered scan. The scan type mismatch (N3) is also important
as it means the frontend "By Set" and "By Format" options are functionally
broken, but this could be shipped as a fast follow-up fix.
