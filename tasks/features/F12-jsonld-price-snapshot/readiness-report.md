# F12 Readiness Report

**Date:** 2026-08-20
**Verdict:** READY (with one minor advisory)

## Checklist
- [x] All tasks have required sections (User Story, Objective, Dev Notes, Implementation Details, Acceptance Criteria, Testing)
- [x] Wave assignments consistent (with one advisory -- see Issues)
- [x] No file conflicts within waves
- [x] Dependencies valid (DAG is acyclic, all referenced tasks exist)
- [x] Referenced source files exist
- [x] No missing prerequisites

## Task-by-Task Verification

| Task | Wave | Depends On | Files Touched | Sections OK | Source Exists |
|------|------|------------|---------------|-------------|---------------|
| T01 | 0 | (none) | `src/domain/models.py` | Yes | Yes |
| T02 | 0 | (none) | `src/parsers/myp.py` | Yes | Yes |
| T03 | 1 | T01, T02 | `src/providers/myp/provider.py` | Yes | Yes |
| T04 | 2 | T01, T03 | `src/collectors/snapshot_prices.py` (new), `src/database/repository.py` | Yes | Yes (dir + repo) |
| T05 | 2 | (none) | `src/api/schemas/collection.py` | Yes | Yes |
| T06 | 2 | (none) | `frontend/src/components/PriceChart.tsx` | Yes | Yes |
| T07 | 3 | T04 | `src/cli/main.py` | Yes | Yes |
| T08 | 3 | T04, T05 | `src/api/routers/collection.py` | Yes | Yes |
| T09 | 3 | T08 | `scripts/cron_update.sh` | Yes | Yes |
| T10 | 4 | T01-T09 | docs (PRD, diagrams, README) | Yes | N/A (new files) |

## File Ownership Within Waves (Conflict Check)

- **Wave 0:** T01 -> `models.py`, T02 -> `myp.py` -- NO CONFLICT
- **Wave 1:** T03 -> `provider.py` -- single task, NO CONFLICT
- **Wave 2:** T04 -> `snapshot_prices.py` (new) + `repository.py`, T05 -> `schemas/collection.py`, T06 -> `PriceChart.tsx` -- NO CONFLICT
- **Wave 3:** T07 -> `cli/main.py`, T08 -> `routers/collection.py`, T09 -> `cron_update.sh` -- NO CONFLICT (files are different)
- **Wave 4:** T10 -> docs only -- NO CONFLICT

## Dependency DAG Validation

```
T01 (W0)  T02 (W0)
  \         |
   \        |
    v       v
     T03 (W1)        T05 (W2)   T06 (W2)
       \                |
        v               |
      T04 (W2)          |
      / |  \            |
     v  v   v           v
  T07  T08 <----------- T05
  (W3) (W3)
         |
         v
       T09 (W3)
         |
         v
       T10 (W4)
```

- No circular dependencies.
- All dependency targets exist.
- All dependencies point to equal or earlier waves (with one advisory below).

## Source File Existence Verification

| File | Exists | Relevant Internals Verified |
|------|--------|-----------------------------|
| `src/domain/models.py` | Yes | `MypSearchResult` (line 153), `SyncSummary` (line 210), `CollectionError` (line 82) -- insertion points confirmed |
| `src/parsers/myp.py` | Yes | `parse_json_ld_product()` (line 107), `_to_decimal()` (line 271), `parse_price_snapshot()` (line 187) -- all reuse targets exist |
| `src/providers/myp/provider.py` | Yes | `BASE_URL` (line 31), `_fetch()` (line 66), `close()` (line 61) -- all referenced methods exist |
| `src/collectors/` | Yes | Directory exists with `backfill.py`, `sync_collection.py`, `match_report.py` -- pattern files for T04 |
| `src/database/repository.py` | Yes | `insert_price_observations()` (line 99) -- reuse target exists |
| `src/cli/main.py` | Yes | Click group `cli` and `asyncio` import present |
| `src/api/routers/collection.py` | Yes | `job_tracker`, `verify_api_key`, `JobStatus`, `success_response` imports present; `trigger_sync` pattern (line 143) confirmed |
| `src/api/schemas/collection.py` | Yes | `SyncRequest` (line 43) -- pattern for `SnapshotRequest` confirmed |
| `src/api/schemas/collect.py` | Yes | `JobStatus` (line 16) confirmed |
| `frontend/src/components/PriceChart.tsx` | Yes | File exists |
| `scripts/cron_update.sh` | Yes | Update response logging at line 84, health check at line 89 -- insertion point between them confirmed |

## Issues Found

### 1. Advisory: T09 depends on T08, but both are Wave 3 (MINOR)

T09 (`Depends on: F12-T08`) and T08 are both assigned to Wave 3. Strictly, a task cannot depend on another task in the same wave, since wave-mates are meant to execute in parallel.

**Mitigating factors:** T09 only modifies `scripts/cron_update.sh` (a shell script), adding a curl command string that calls the endpoint T08 creates. There is no compile-time, import, or file-level dependency -- the curl target URL is a string literal. The developer can write the shell script addition without the Python endpoint existing. The dependency is purely a runtime/integration concern.

**Impact:** Low. The developer implementing T09 needs to know the endpoint path (`/api/v1/collection/snapshot-prices`), which is fully specified in T09's implementation details. No code import or build dependency exists.

**Recommendation:** Either (a) accept as-is since the dependency is runtime-only and the implementation details are self-contained, or (b) move T09 to Wave 4 alongside T10 if strict DAG purity is preferred. This does NOT block execution.

### 2. Note: `BASE_URL` in provider.py is flagged as tech debt

MEMORY.md lists "remove dead `BASE_URL` in sync_collection.py" as tech debt from F10. However, `BASE_URL` in `provider.py` (line 31) is alive and well-used (6 references). T03 correctly uses it for URL construction. No issue here -- the tech debt item refers to a different file (`sync_collection.py`), not `provider.py`.

## Recommendation

**Proceed.** The plan is thorough, well-structured, and all prerequisites are in place. Every referenced source file exists, insertion points are accurate, internal functions and classes cited for reuse are confirmed present, and there are no file ownership conflicts within waves.

The T09/T08 same-wave dependency is cosmetic -- the implementation details in T09 are fully self-contained (hardcoded URL string in a shell script), so parallel development within Wave 3 will work without issues. If the orchestrator prefers strict DAG compliance, T09 can be bumped to a Wave 3.5 or Wave 4 slot with zero impact on the overall plan.
