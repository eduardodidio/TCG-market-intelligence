# F67 Tech Lead Review -- Daily Liga Collection Scan (Re-review)

**Reviewer:** Tech Lead Agent
**Date:** 2026-08-26
**Previous verdict:** REJECTED (3 critical, 1 moderate)
**Verdict:** APPROVED

---

## Summary

F67 delivers per-card credit cost for bulk scans, a scan preview endpoint, and an admin daily Liga cron job. All three critical issues and the moderate issue from the first review have been resolved. The feature is ready to ship.

---

## Verification of Previous Issues

### C1. Frontend-backend field name mismatch -- RESOLVED

`frontend/src/types/api.ts` (lines 233-237) now matches the backend schema exactly:

```typescript
export interface ScanPreviewResponse {
  card_count: number;
  skipped_count: number;
  credit_cost: number;
}
```

`frontend/src/pages/MyCollection.tsx` (lines 325-327) uses the correct field names:

```typescript
setPreviewCost(res.data.credit_cost);
setPreviewCardCount(res.data.card_count);
setPreviewSkipped(res.data.skipped_count);
```

No mismatch remains.

### C2. Preview not scoped by user_id -- RESOLVED

Both endpoints in `src/api/routers/scans.py` now pass `user_id=str(user.id)`:

- **Preview** (lines 125-127): `repo.get_cards_for_liga_scan(scan_filter, user_id=user_id_str, max_age_days=...)` -- both calls use `user_id_str = str(user.id)`.
- **Trigger** (lines 164-165): `repo_for_count.get_cards_for_liga_scan(scan_filter, user_id=str(user.id), max_age_days=request.max_age_days)`.

Users can no longer see or be charged for other users' collection entries.

### C3. No non-admin tests -- RESOLVED (pre-existing)

Tests in `tests/api/test_credit_guards.py` cover the non-admin path:

- `test_successful_scan_deducts_per_card_before_launch` (line 409): uses `_make_user(is_admin=False)` with 7 cards, balance=10, verifies `deduct(user_id, 7, "bulk_scan", ...)`.
- `test_insufficient_credits_returns_402` (line 363): uses `_make_user(is_admin=False)` with balance=3, 5 cards, verifies 402 response with correct `balance` and `cost` in detail.

These tests existed in the credit guards test file (not `test_scan_endpoints.py`), which is why they were missed in the first review. Coverage is adequate.

### M1. BULK_SCAN_COST removal -- VERIFIED

Grep across `src/` and `tests/` returns zero matches. The only remaining references are in documentation/task files (this review, F65 task files, F67 README), which is expected and harmless.

### M3. Admin daily scan on_complete hook -- RESOLVED

`src/scheduler/service.py` (lines 196-202) now passes `on_complete=default_registry.notify`:

```python
asyncio.run(
    run_admin_daily_liga_scan(
        db_url=self._db_url,
        run_id=scan_id,
        max_age_days=max_age_days,
        on_complete=default_registry.notify,
    )
)
```

Cache invalidation (trending, market data) will fire after admin daily scans.

---

## Diagrams -- VERIFIED

Both required diagrams exist:

- `docs/diagrams/F67-architecture.mmd` -- component/data-flow graph covering Scheduler, AdminScan, ScanEndpoints, LigaScan, and Credits subgraphs with clear edge labels.
- `docs/diagrams/F67-journey.mmd` -- user journey for manual refresh (preview -> modal -> confirm -> poll) and system journey for daily cron (admins -> collect -> dedup -> scan -> hooks), plus credit flow.

Both are well-structured and accurately reflect the implementation.

---

## Remaining Observations (non-blocking)

### M2. Preview calls get_cards_for_liga_scan twice (carried forward)

The preview endpoint still makes two full queries (all entries + eligible entries) to compute `skipped_count`. For large collections, a `COUNT(*)` variant would be more efficient. Not blocking -- current collection sizes are small enough that this is negligible.

---

## Checklist

| Item | Status |
|------|--------|
| Preview endpoint auth-protected | PASS |
| Admin daily scan has no credit deduction | PASS |
| Per-card cost deducted upfront (non-admin) | PASS |
| Preview scoped to current user | PASS |
| Trigger credit guard scoped to current user | PASS |
| Frontend-backend field contract | PASS |
| Non-admin credit deduction tested | PASS |
| Diagrams | PASS |
| BULK_SCAN_COST fully removed | PASS |
| Cache invalidation on admin scan | PASS |

---

## Positive Observations (carried forward)

1. Admin scan orchestrator has clean separation of concerns with deduplication across admin users.
2. Admin scan tests are thorough (6 async tests covering edge cases).
3. Seed schedule is idempotent (checks for existing before creating).
4. Scheduler routing correctly branches on `admin_daily_liga` scan type.
5. Frontend MaxAgeDaysSelect is well-designed with i18n support.
6. CreditConfirmModal extension is backward-compatible.
7. Schema tests exist for ScanPreviewResponse and max_age_days.
