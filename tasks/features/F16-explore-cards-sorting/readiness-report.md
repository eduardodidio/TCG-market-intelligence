# F16 Readiness Report

**Date:** 2026-08-21
**Auditor:** Readiness Auditor Agent

---

## Checklist

### 1. Does the README have a clear Wave manifest?

**PASS** -- `F16-README.md` defines three Waves clearly:
- Wave 1: F16-T01, F16-T02 (backend)
- Wave 2: F16-T03, F16-T04 (frontend)
- Wave 3: F16-T05 (tests + docs)

Global acceptance criteria are also listed.

### 2. Do all tasks have acceptance criteria?

**PASS** -- All five tasks (T01 through T05) include explicit acceptance criteria sections with checkboxes. Each also has a "Test scenarios" section with happy path, edge case, and boundary coverage.

### 3. Are file paths specified in task dev notes?

**PASS** -- Every task lists the relevant files in its Dev Notes section:
- T01: `src/database/repository.py`, `src/database/models.py`
- T02: `src/api/routers/collection.py`, `src/api/schemas/collection.py`, `src/api/schemas/envelope.py`
- T03: `frontend/src/components/`, `frontend/src/pages/MyCollection.tsx`
- T04: `frontend/src/pages/MyCollection.tsx`, `frontend/src/api/collection.ts`, `frontend/src/types/api.ts`
- T05: `tests/`, `frontend/src/`, `README.md`

### 4. Are there circular dependencies between tasks in the same Wave?

**FAIL** -- Wave 1 contains T01 and T02, but T02 declares `Depends on: F16-T01`. This means they cannot run in parallel. T02 must wait for T01 to complete. The Wave manifest should either:
- (a) Move T02 to its own Wave (Wave 1: T01, Wave 2: T02, Wave 3: T03+T04, Wave 4: T05), or
- (b) Acknowledge that Wave 1 is sequential (T01 then T02).

This is not a circular dependency, but it is a **serial dependency within a parallel Wave**, which is a manifest inconsistency.

Similarly, Wave 2 has T03 and T04, but T04 depends on T03. Same issue -- these cannot truly run in parallel.

### 5. Do tasks in the same Wave touch the same files? (conflict risk)

**PASS** -- No file conflicts:
- Wave 1: T01 modifies `repository.py`, T02 modifies `collection.py` (different files).
- Wave 2: T03 creates new `SortSelect.tsx`, T04 modifies `MyCollection.tsx` (different files).
- Wave 3: T05 is alone.

However, since T02 depends on T01 and T04 depends on T03, parallel execution within those Waves is not possible anyway (see item 4).

### 6. Is the PRD consistent with the task breakdown?

**PASS** -- The PRD and tasks are well aligned:
- Sort fields match: name, set, number, added (server-side), price (client-side).
- Pagination migration from cursor to offset is consistent.
- API parameter names (`sort_by`, `sort_dir`, `offset`) match across PRD, T01, and T02.
- Frontend `SortSelect` component and URL param syncing match PRD requirements.
- Price sorting caveat (client-side only) is consistently documented in PRD, T03, and T04.

One minor note: the PRD says "Default depends on `sort_by` (see table)" for `sort_dir`, but T01/T02 hardcode default `sort_dir` to `"asc"`. The table shows `price` defaults to `desc` and `added` defaults to `desc`. Since price is client-side and the frontend handles the composite value, this is acceptable but worth noting during implementation.

### 7. Are there missing tasks or gaps?

**PASS** -- No critical gaps. The task breakdown covers:
- Backend repository changes (T01)
- Backend API changes (T02)
- Frontend component (T03)
- Frontend integration (T04)
- Tests and documentation (T05)

Minor observations (non-blocking):
- No explicit task for updating `frontend/src/api/collection.ts` to add sort/offset params to the fetch call. T04 mentions it in dev notes but it could be easy to overlook.
- No diagram update task, but the README correctly notes "No new diagrams required" and only conditionally mentions updating an existing one.

---

## Codebase Verification

| File | Exists | Notes |
|------|--------|-------|
| `src/database/repository.py` | YES | `list_collection` at line 569, `count_collection` at line 596 |
| `src/api/routers/collection.py` | YES | Endpoint file exists |
| `src/api/schemas/envelope.py` | YES | Pagination helper exists |
| `frontend/src/pages/MyCollection.tsx` | YES | Page file exists |
| `frontend/src/components/` | YES | 15 existing components (SearchBar, FilterChips, CardTile, etc.) |
| `frontend/src/api/collection.ts` | YES | Fetch function exists |
| `frontend/src/types/api.ts` | YES | Type definitions exist |

All referenced files are present in the codebase at the expected locations.

---

## Verdict: READY

The feature is ready to execute with one advisory finding:

**Advisory (non-blocking):** Waves 1 and 2 each contain two tasks with a serial dependency between them (T02 depends on T01; T04 depends on T03). The developer executing these Waves should treat them as sequential pairs rather than truly parallel tasks. This does not block execution -- it just means each Wave is effectively a two-step sequence rather than a parallel batch.
