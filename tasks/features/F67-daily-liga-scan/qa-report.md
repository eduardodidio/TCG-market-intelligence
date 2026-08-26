# F67 QA Report -- Daily Liga Collection Scan

**QA Agent** | **Date:** 2026-08-26 | **Verdict:** PASSED

---

## Test Results

| Suite | Tests | Status |
|-------|-------|--------|
| Backend (pytest) | 2215 passed, 0 failed | PASS |
| Frontend (vitest) | 1109 passed across 107 files, 0 failed | PASS |

---

## Acceptance Criteria Verification

### AC1. Per-card credit cost replaces flat BULK_SCAN_COST

- **PASS.** `BULK_SCAN_COST` has zero references in `src/` or `tests/`.
- `src/api/routers/scans.py` (line 167): `cost = len(eligible) * CARD_REFRESH_COST` computes per-card cost for non-admin users.
- Admin users get `cost=0` (line 130 in preview, line 162 bypass in trigger).
- Credit deduction happens upfront before scan thread launch (line 179).
- Tests: `tests/api/test_credit_guards.py` covers non-admin deduction (7 cards = 7 credits) and insufficient balance (402 response with correct balance/cost fields).

### AC2. GET /scans/preview endpoint

- **PASS.** `src/api/routers/scans.py` lines 116-135: `GET /preview` returns `ScanPreviewResponse` with `card_count`, `skipped_count`, `credit_cost`.
- Schema: `src/api/schemas/scans.py` lines 41-44 define `ScanPreviewResponse` with correct field types.
- Preview is auth-protected (`user: User = Depends(get_current_user)`).
- Preview is scoped to current user (`user_id=str(user.id)` on both repo calls).
- Tests: `tests/unit/api/test_scan_endpoints.py` has 3 preview tests (admin, no-max-age, non-admin cost), `tests/unit/api/test_scan_schemas.py` has 2 schema tests.

### AC3. max_age_days filter

- **PASS.** `ScanRequest` schema has `max_age_days: int | None = None` field.
- Preview endpoint accepts `max_age_days` as query param (`Query(None, ge=1)`).
- Trigger endpoint threads `request.max_age_days` to `get_cards_for_liga_scan`.
- Frontend: `MaxAgeDaysSelect` component with 4 options (1d, 3d, 7d, all), integrated into `MyCollection.tsx`.
- i18n: 5 keys in both EN and PT-BR locales (`maxAgeDays`, `maxAgeDaysOption1/3/7/All`).
- Tests: `frontend/tests/components/MaxAgeDaysSelect.test.tsx` (8 tests covering rendering, selection, disabled state).

### AC4. Frontend-backend field name contract

- **PASS.** `frontend/src/types/api.ts` lines 233-237: `ScanPreviewResponse` matches backend exactly (`card_count`, `skipped_count`, `credit_cost`).
- `MyCollection.tsx` uses `res.data.credit_cost`, `res.data.card_count`, `res.data.skipped_count`.
- `frontend/src/api/scans.ts` has `fetchScanPreview` function.

### AC5. Admin daily Liga scan job

- **PASS.** `src/collectors/admin_scan.py`: `run_admin_daily_liga_scan` collects all admin users' entries, deduplicates by `card_id`, delegates to `run_liga_scan`.
- No credit deduction for admin scans (system-level job).
- Handles edge cases: no admins, all cards fresh, orphan entries without `card_id`.
- `src/scheduler/service.py` lines 191-203: routes `admin_daily_liga` scan type correctly with `on_complete=default_registry.notify` for cache invalidation.
- `src/database/repository.py`: `get_admin_user_ids()` queries `is_admin=1` users; `seed_default_liga_schedules()` seeds the schedule.
- Tests: `tests/collectors/test_admin_scan.py` (6 async tests: no admins, all fresh, card collection from multiple admins, deduplication, max_age_days threading, on_complete callback passthrough).

### AC6. Diagrams

- **PASS.** Both required diagrams exist:
  - `docs/diagrams/F67-architecture.mmd`
  - `docs/diagrams/F67-journey.mmd`

---

## Documentation Gap (non-blocking)

- **README.md not updated.** Per CLAUDE.md rules, every shipped feature must update the project README.md. F67 is not mentioned in the README. This should be addressed before final merge but does not block the feature verdict since it is a documentation-only gap with no code or test impact.

---

## Test Coverage Summary

| Area | Test File | Tests |
|------|-----------|-------|
| Admin scan orchestrator | `tests/collectors/test_admin_scan.py` | 6 |
| Scan preview endpoint | `tests/unit/api/test_scan_endpoints.py` (TestPreviewScan) | 3 |
| Scan schemas (preview + max_age_days) | `tests/unit/api/test_scan_schemas.py` | 2 |
| Credit guards (per-card bulk) | `tests/api/test_credit_guards.py` | 2+ |
| Scheduler Liga routing | `tests/unit/scheduler/test_liga_scheduling.py` | multiple |
| MaxAgeDaysSelect component | `frontend/tests/components/MaxAgeDaysSelect.test.tsx` | 8 |

No test gaps identified. All three feature pillars (preview endpoint, per-card cost, admin daily scan) have dedicated backend and frontend tests.

---

## TechLead Review Issues -- Verification

All 3 critical and 1 moderate issues from the TechLead first review are confirmed resolved:

1. **C1 (field name mismatch)** -- Verified: frontend types match backend schema exactly.
2. **C2 (preview not scoped by user_id)** -- Verified: both preview and trigger pass `user_id=str(user.id)`.
3. **C3 (no non-admin tests)** -- Verified: `test_credit_guards.py` covers non-admin path.
4. **M1 (BULK_SCAN_COST removal)** -- Verified: zero matches in `src/` and `tests/`.

---

## Verdict: PASSED

F67 delivers all three planned capabilities (per-card credit cost, scan preview, admin daily Liga job) with correct implementation, adequate test coverage, and resolved TechLead review findings. The README.md gap should be addressed as a follow-up.
