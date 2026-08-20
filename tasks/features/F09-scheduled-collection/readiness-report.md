# F09 Readiness Report

**Feature:** F09 — Scheduled Price Collection
**Audited at:** 2026-08-19
**Auditor:** Readiness Gate (pre-Wave audit)

## 1. Plan Completeness

| Check | Result |
|-------|--------|
| README with Wave manifest | PASS — 3 Waves (0, 1, 2), 5 tasks |
| All tasks have user stories | PASS — T01–T05 each have a user story |
| All tasks have acceptance criteria | PASS — T01–T05 each have explicit AC |
| All tasks have testing notes | PASS — T01, T02, T04 have unit/integration tests; T03 manual; T05 validation only |
| All tasks have "Files to Change" | PASS — each task lists files to create/change/not touch |
| Estimates present | PASS — T01(M), T02(S), T03(S), T04(S), T05(S) |

## 2. Wave Independence

| Wave | Tasks | Independent? | Notes |
|------|-------|-------------|-------|
| 0 | T01, T02 | PASS | T01 adds GET route + repo methods; T02 adds auth dependency to POST routes. Both touch `collect.py` router but T01 adds a new GET endpoint while T02 modifies existing POST endpoints — no overlap. T02 explicitly notes health endpoint does NOT get auth. |
| 1 | T03, T04 | PASS | T03 creates a shell script (no Python/frontend). T04 modifies frontend only. Zero file overlap. |
| 2 | T05 | PASS | Single task, docs only. |

**Concern (minor):** T01 and T02 both modify `src/api/routers/collect.py`. T01 adds a new `@router.get("/collect/health")` endpoint, T02 adds `Depends(verify_api_key)` to existing POST endpoints. These are different functions in the same file. Risk of merge conflict is low but non-zero. Acceptable for Wave 0 — developer should apply T01 first, then T02.

## 3. Dependency Verification

| Dependency | Status |
|-----------|--------|
| `src/api/routers/collect.py` exists | PASS |
| `src/api/deps.py` exists | PASS |
| `src/api/schemas/collect.py` exists | PASS |
| `src/database/repository.py` exists | PASS |
| `src/database/models.py` has `CollectionErrorRow` / `collection_errors` table | PASS |
| `frontend/src/pages/Dashboard.tsx` exists | PASS |
| `frontend/src/types/api.ts` exists | PASS |
| F06 REST API shipped | PASS |
| F07 Frontend Dashboard shipped | PASS |
| No new Python dependencies required | PASS (NFR-04) |

## 4. Risk Assessment

| Risk | Severity | Mitigation |
|------|----------|------------|
| T01+T02 same-file edit in Wave 0 | Low | Apply T01 first, T02 second. Different functions. |
| `get_stale_cards_count` query performance | Low | Simple aggregation on indexed columns. NFR-01 requires <500ms for 10k obs — well within SQLite capability. |
| Auth guard breaking existing tests | Low | T02 design makes guard a no-op when `TCG_API_KEY` unset. Existing tests run without env var. |
| Frontend health call failure | Low | T04 specifies graceful degradation — show "Unknown" on error. |

## 5. Blockers

None identified.

## 6. Verdict

**Verdict:** READY

All 5 tasks are well-specified with clear acceptance criteria, file boundaries, and testing strategies. Wave independence is confirmed with a minor same-file note for Wave 0. All referenced files and dependencies exist. No blockers found.
