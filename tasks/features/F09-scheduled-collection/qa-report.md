# QA Report -- F09 Scheduled Price Collection

**QA Agent:** QA
**Date:** 2026-08-19
**Feature:** F09 -- Scheduled Price Collection

---

## 1. Test Execution Results

### Backend

```
435 passed, 65 warnings in 158.49s
Coverage: 96.47% (minimum: 70%)
```

All 435 tests pass, including 28 new tests for F09:
- `tests/api/test_collect_health.py` -- 7 tests
- `tests/api/test_collect_auth.py` -- 7 tests (4 unit + 3 integration + 1 combined)
- `tests/database/test_repository_api.py` -- 14 new tests across 4 new classes

### Frontend

```
21 test files passed (178 tests)
Duration: 4.32s
```

All 178 tests pass, including 12 new tests for F09:
- `tests/components/FreshnessIndicator.test.tsx` -- 10 tests
- `tests/components/Dashboard.test.tsx` -- 2 new tests (freshness renders, graceful degradation)

### Lint

```
ruff check src/ tests/ -- All checks passed!
```

Zero lint violations.

### TypeScript

```
npx tsc --noEmit -- No errors
```

Zero type errors.

---

## 2. Acceptance Criteria Verification

| AC | Description | Status | Evidence |
|----|-------------|--------|----------|
| AC1 | `GET /api/v1/collect/health` returns JSON with `last_collection_at`, `stale_cards_count`, `recent_errors_count` | **PASS** | `test_health_status_healthy` asserts all fields present. `CollectionHealth` Pydantic schema enforces the contract. Response envelope includes `data`, `meta`, `errors`. |
| AC2 | POST `/api/v1/collect/update` returns 401 when `TCG_API_KEY` is set but no `X-API-Key` header | **PASS** | `test_update_requires_key_when_configured` sends POST without header, asserts 401. Also tests wrong-key -> 401. |
| AC3 | POST with correct `X-API-Key` succeeds with 200 | **PASS** | Same test sends POST with correct key, asserts 200. `test_backfill_requires_key_when_configured` covers the backfill endpoint too. |
| AC4 | `scripts/cron_update.sh` exists, is executable, exits 0 on success / non-zero on failure | **PASS** | File exists at `scripts/cron_update.sh` with permissions `-rwxr-xr-x`. Script uses `set -euo pipefail`, exits 0 on HTTP 200, exit 1 on non-200, exit 2 on connection failure. `TCG_API_KEY` is required (`${TCG_API_KEY:?ERROR}`). |
| AC5 | Dashboard shows "Last updated: X ago" from health endpoint | **PASS** | `FreshnessIndicator` component renders "Last updated: {relative time}". Dashboard test `renders freshness indicator when health endpoint succeeds` asserts `data-testid="freshness-indicator"` is present with "Last updated:" text and green dot for healthy status. |
| AC6 | All new code has tests; existing tests still pass | **PASS** | 28 new backend tests + 12 new frontend tests. All 435 backend + 178 frontend tests pass. No regressions. |
| AC7 | Diagrams and README updated | **PASS** | `docs/diagrams/F09-architecture.mmd` (architecture/data-flow) and `docs/diagrams/F09-journey.mmd` (3-swimlane user journey) both exist with correct Mermaid syntax. `README.md` has F09 section with all 4 deliverables described. |

---

## 3. Test Plan Cross-Reference

All 22 test plan scenarios (TEA-generated `F09-test-plan.md`) are implemented:

- Scenarios 1-5 (repository methods): 14 tests in `test_repository_api.py` -- exceeds plan
- Scenarios 6-9 (health endpoint): 7 tests in `test_collect_health.py` -- exceeds plan (added boundary at 50%, error-priority-over-stale)
- Scenarios 10-17 (API key guard): 8 tests in `test_collect_auth.py` -- matches plan
- Scenarios 18-20 (FreshnessIndicator): 10 tests in `FreshnessIndicator.test.tsx` -- exceeds plan (added singular forms, just-now, slate fallback)
- Scenarios 21-22 (Dashboard integration): 2 tests in `Dashboard.test.tsx` -- matches plan

No test plan scenarios were missed.

---

## 4. Test Gaps Found and Filled

**No test gaps found.** The implementation exceeds the test plan coverage with additional edge-case tests:

- Boundary condition: exactly 50% stale is NOT treated as "stale" (strict `>`)
- Error priority: error status takes precedence over stale status
- Orphan source cards: cards with zero observations counted as stale
- Source filtering: all 4 repository methods support optional `source` parameter, tested
- FreshnessIndicator: singular forms ("1 minute ago"), just-now threshold, unknown status fallback to slate dot
- Dashboard graceful degradation: when health endpoint fails, dashboard KPIs and movers still render, no freshness indicator shown

---

## 5. Code Quality Observations

### Strengths

- **Clean separation of concerns.** Repository methods are pure data access, health endpoint is pure status logic, frontend component is pure rendering. Each layer is independently testable.
- **API key guard is simple and correct.** Dev-mode no-op pattern (unset env var = open access) prevents friction during development without compromising production security.
- **Cron script is production-quality.** Uses `set -euo pipefail`, `mktemp` + `trap` for cleanup, proper quoting, relative-to-absolute path resolution, structured logging with timestamps.
- **Frontend graceful degradation is well-designed.** Health data never blocks dashboard loading -- `loading` and `error` flags only track stats and movers, not health.
- **formatRelativeTime handles all edge cases.** NaN, negative diffs, zero seconds, singular forms -- all covered by tests.

### Minor Notes (non-blocking, from Tech Lead review)

- MINOR-01: Frontend mock uses datetime format but backend returns date-only. Cosmetic -- `new Date("2026-08-19")` parses correctly.
- MINOR-02: Simple string comparison for API key. Acceptable per PRD for single-user deployment.
- MINOR-03: `next_expected_at` is date-only, not full datetime. Cosmetic -- field is informational.

These are pre-existing observations from the Tech Lead review. None warrant blocking the feature.

---

## 6. Verdict

**PASSED**

F09 is complete, well-tested, and ready to ship. All 7 acceptance criteria are met. All 22 test plan scenarios are implemented with additional edge-case coverage. Backend (435 tests, 96.47% coverage), frontend (178 tests), lint (0 violations), and TypeScript (0 errors) are all green. No test gaps found. No regressions detected.
