# F67 Readiness Report

**Verdict: READY**

**Date:** 2026-08-26
**Auditor:** Readiness Agent

## 1. Acceptance Criteria

All three tasks have clear, testable acceptance criteria:

- **T01** (Wave 0): 6 acceptance criteria covering preview endpoint, per-card cost, max_age_days threading, admin bypass, BULK_SCAN_COST removal, and test updates.
- **T02** (Wave 0): 6 acceptance criteria covering get_admin_user_ids, admin scan orchestrator, seed schedule extension, scheduler handler, existing schedule preservation, auto-pause behavior.
- **T03** (Wave 1): 7 acceptance criteria covering API client, CreditConfirmModal updates, max_age_days selector, useCollectionRefresh passthrough, admin display, i18n, and tests.

**Status: PASS**

## 2. File Existence Verification

All referenced source files exist:

| File | Status |
|------|--------|
| `src/collectors/scan.py` | OK |
| `src/collectors/liga_scan.py` | OK |
| `src/credits/constants.py` | OK (BULK_SCAN_COST=5, CARD_REFRESH_COST=1 confirmed) |
| `src/credits/service.py` | OK |
| `src/api/routers/scans.py` | OK (imports BULK_SCAN_COST, uses it in trigger_scan) |
| `src/api/schemas/scans.py` | OK (ScanRequest class exists) |
| `src/scheduler/service.py` | OK (_execute_scheduled_scan exists at line 152) |
| `src/database/repository.py` | OK (get_cards_for_liga_scan at line 1266, seed_default_liga_schedules at line 2086) |
| `src/domain/models.py` | OK (ScanFilter with card_ids field confirmed) |
| `frontend/src/hooks/useCollectionRefresh.ts` | OK |
| `frontend/src/components/CreditConfirmModal.tsx` | OK |
| `frontend/src/api/scans.ts` | OK |
| `frontend/src/types/api.ts` | OK |
| `frontend/src/pages/MyCollection.tsx` | OK |
| `frontend/src/i18n/locales/en.json` | OK |
| `frontend/src/i18n/locales/pt-BR.json` | OK |
| `tests/unit/api/test_scan_endpoints.py` | OK |
| `tests/api/test_credit_guards.py` | OK |
| `tests/unit/scheduler/test_liga_scheduling.py` | OK |
| `frontend/tests/components/CreditConfirmModal.test.tsx` | OK |

**Status: PASS**

### Minor Note

T03 references `frontend/tests/hooks/useCollectionRefresh.test.tsx` but the actual file is `useCollectionRefresh.test.ts` (`.ts` not `.tsx`). This is cosmetic and does not block implementation -- the developer should use the correct extension.

## 3. Wave 0 Same-File Conflicts

T01 and T02 both run in Wave 0. File overlap analysis:

| File | T01 | T02 | Conflict? |
|------|-----|-----|-----------|
| `src/api/schemas/scans.py` | Modify | -- | No |
| `src/api/routers/scans.py` | Modify | -- | No |
| `src/credits/constants.py` | Modify | -- | No |
| `src/database/repository.py` | -- | Modify (add get_admin_user_ids, extend seed) | No |
| `src/collectors/admin_scan.py` | -- | NEW | No |
| `src/scheduler/service.py` | -- | Modify | No |

**No file is modified by both T01 and T02.** They touch disjoint sets of files.

**Status: PASS**

## 4. Wave Dependencies

- **Wave 0 (T01, T02):** Independent of each other. T01 modifies the scan API and credit model. T02 adds the admin daily job and scheduler handler. No cross-dependency within Wave 0.
- **Wave 1 (T03):** Depends on T01. T03's frontend consumes the `GET /scans/preview` endpoint and `max_age_days` field on `ScanRequest`, both created by T01. T03 does NOT depend on T02. Dependency is correctly declared ("Depends on: T01").

**Status: PASS**

## 5. Infrastructure References

All infrastructure assumptions verified against current codebase:

| Assumption | Verified |
|-----------|----------|
| `BULK_SCAN_COST = 5` in constants.py | Yes (line 7) |
| `CARD_REFRESH_COST = 1` in constants.py | Yes (line 6) |
| `get_cards_for_liga_scan(scan_filter, user_id, max_age_days)` signature | Yes (line 1266, accepts user_id and max_age_days) |
| `run_liga_scan` accepts `max_age_days` | Yes (line 25 of liga_scan.py) |
| `run_scan` accepts `max_age_days` | Yes (line 77 of scan.py) |
| `ScanFilter` has `card_ids` field | Yes (line 314 of models.py) |
| `_execute_scheduled_scan` in ScanScheduler | Yes (line 152 of service.py) |
| `seed_default_liga_schedules` in repository | Yes (line 2086) |
| `is_admin` on UserRow | Yes (line 207 of models.py) |
| `filters_json` stored in scan runs | Yes (line 162 of scans.py router) |
| `trigger_scan` uses BULK_SCAN_COST for credit check | Yes (lines 128-139 of scans.py) |

**Status: PASS**

## Summary

All five checks pass. The plan is well-structured, references existing infrastructure correctly, has no file conflicts within Wave 0, and wave dependencies are properly ordered. The single minor note (test file extension `.ts` vs `.tsx`) is non-blocking.

**Verdict: READY -- proceed with Wave 0 (T01 + T02 in parallel).**
