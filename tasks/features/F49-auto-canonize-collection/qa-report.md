# QA Report -- F49 Auto-Canonize Collection

**QA Agent:** QA
**Date:** 2026-08-22
**Verdict:** PASSED (with noted issues)

---

## 1. Acceptance Criteria Validation

| AC | Description | Status | Evidence |
|----|-------------|--------|----------|
| AC1 | POST /collection/canonize-all endpoint | PASS | Endpoint at `src/api/routers/collection.py:208-237`. Auth enforced via `require_auth_or_api_key`. Returns `BulkCanonizeResult` with total/canonized/failed/skipped/rate_limited. Provider cleanup via `try/finally`. Tests: 3 API integration + 4 schema + 8 unit = 15 tests. |
| AC2 | CSV import triggers background canonize | PASS | `import_collection` at line 761 checks `new_entry_ids`, schedules `_run_import_canonize` via `BackgroundTasks`. Response includes `canonize_scheduled: bool` and `new_entry_ids: list[int]`. Importer uses `session.flush()` to populate IDs. Tests: 10 importer + 4 API integration = 14 tests. |
| AC3 | CLI `canonize-all` with dry-run | PASS | Click command at line 710. Options: `--user-id` (required), `--limit`, `--concurrency` (default=3), `--dry-run`, `--db`. Dry-run queries unlinked count without processing. Summary printer at line 749. Tests: 5 CLI tests. |
| AC4 | Frontend "Canonize All" button | PASS | `BulkCanonizeButton.tsx` -- self-contained component with loading/result/error states. Hides when `unlinkedCount <= 0`. Shows spinner during request, result banner on success, error banner on failure. Integrated in `MyCollection.tsx` at line 533 with `unlinkedCount = summary.total_unique - summary.linked_count`. `onComplete` triggers `handleRefreshComplete` for data re-fetch. Tests: 13 component tests. |
| AC5 | i18n canonize keys | PASS | 6 new keys + 1 existing (`canonizing`) in both `en.json` and `pt-BR.json`. Keys: `canonizeAll`, `canonizeAllDescription`, `unlinkedCount`, `canonizeResult`, `canonizeFailed`, `canonizeScheduled`. Tests: 14 i18n tests. |

---

## 2. Test Execution Results

### Backend (34 tests -- ALL PASS)

```
tests/collectors/test_bulk_canonize.py         8 passed
tests/api/test_collection_canonize_all.py      3 passed
tests/unit/api/test_canonize_all_schema.py     4 passed
tests/unit/cli/test_canonize_all.py            5 passed
tests/collection/test_importer_canonize.py    10 passed
tests/api/test_collection_import_canonize.py   4 passed
```

### Frontend (27 tests -- ALL PASS)

```
tests/components/BulkCanonizeButton.test.tsx  13 passed
tests/i18n/canonize-keys.test.tsx             14 passed
```

### Total: 61 new tests, all passing

---

## 3. Test Plan Coverage

All 33 test plan scenarios (#1--#33) are covered by the 61 tests. Several scenarios have multiple tests for thorough coverage (e.g., #14 has two tests, #15 has four tests).

---

## 4. Security Review

| Check | Status | Notes |
|-------|--------|-------|
| Auth on canonize-all endpoint | PASS | `require_auth_or_api_key` dependency. Test verifies 401 without token. |
| IDOR prevention | PASS | `user_id` scoped from auth token, not from request body. |
| Input validation | PASS | `limit` query param has `ge=1` constraint via FastAPI `Query`. |
| Auth on import endpoint | PASS | Same `require_auth_or_api_key` dependency. |
| Provider cleanup (API) | PASS | `try/finally` with `await provider.close()` at line 228. |
| Background task cleanup | PASS | `_run_import_canonize` has `try/except/finally` with `await provider.close()`. |

---

## 5. Issues Found

### IMPORTANT: CLI provider session leak (NOT FIXED from TechLead review)

**File:** `src/cli/main.py:745`
**Issue:** `provider.close()` is called synchronously, but `MypCardsProvider.close()` is `async def`. The call returns an unawaited coroutine, leaking the HTTP session.

**Impact:** Low in practice -- the CLI process exits immediately after, so the OS reclaims resources. A `RuntimeWarning: coroutine ... was never awaited` is emitted. Not a data integrity risk.

**Fix:** Replace `provider.close()` with `asyncio.run(provider.close())` or restructure the bulk_canonize call to include provider cleanup inside the async context.

**QA Verdict on this issue:** Non-blocking. The CLI command functions correctly; the resource leak is cosmetic in a short-lived process. However, this should be addressed in the next maintenance pass.

### MINOR: Test plan says 202, implementation returns 200

**Issue:** Test plan scenario #10 says "returns 202 Accepted" but the endpoint returns 200. The implementation is correct -- the endpoint blocks until completion (synchronous result), so 200 is semantically more appropriate than 202. The test plan text is inaccurate.

### MINOR: `provider: object` type annotation

**File:** `src/collectors/bulk_canonize.py:100,173`
**Issue:** The `provider` parameter is typed as `object` instead of a Protocol or `MypCardsProvider`. Weakens type checking.

### MINOR: Redundant exception catch

**File:** `src/collectors/bulk_canonize.py:237`
**Issue:** `except (NotFoundError, ServerError, Exception)` -- `Exception` subsumes both specific types. Harmless but redundant.

---

## 6. Documentation Deliverables

| Deliverable | Status | Notes |
|-------------|--------|-------|
| `docs/diagrams/F49-architecture.mmd` | PRESENT | Accurately depicts Frontend -> API -> Service -> Provider -> Database flow. CLI path included. |
| `docs/diagrams/F49-journey.mmd` | PRESENT | Covers both CSV import and manual "Canonize All" paths, plus CLI dry-run flow. |
| `README.md` updated | PRESENT | F49 section at line 789 with feature description. |

All three TechLead BLOCKING documentation items have been resolved.

---

## 7. Architecture Observations

- **Diagrams match implementation.** The architecture diagram accurately shows the data flow from Frontend/CLI through API to bulk_canonize service to MYP provider and database. The journey diagram correctly captures the two entry points (CSV import, manual button) and the CLI dry-run path.

- **Backend-to-frontend contract alignment.** `BulkCanonizeResult` fields match exactly between Pydantic schema (`src/api/schemas/collection.py:83-91`) and TypeScript interface (`frontend/src/types/api.ts:509-515`): `total`, `canonized`, `failed`, `skipped`, `rate_limited`.

- **Import flow design.** The import endpoint correctly uses `BackgroundTasks` to schedule canonization after CSV import. The response includes `canonize_scheduled: bool` for frontend awareness. Background task canonizes ALL unlinked entries (not just new ones), which is documented and intentional.

---

## 8. Final Verdict

```
Verdict: PASSED
```

All 5 acceptance criteria are met. All 61 tests pass. Documentation deliverables are complete. Security checks pass. The CLI provider leak (IMPORTANT) is a real but non-blocking issue -- it affects resource cleanup in a short-lived CLI process, not data integrity or user-facing functionality. The two MINOR code quality items are noted for future cleanup.
