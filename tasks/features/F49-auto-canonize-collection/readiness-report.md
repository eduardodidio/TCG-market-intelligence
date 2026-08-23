# Readiness Report -- F49 Auto-Canonize Collection

**Generated:** 2026-08-22T12:00:00Z
**Feature dir:** tasks/features/F49-auto-canonize-collection/
**Total tasks audited:** 5
**Total ACs declared:** 5

## Check 1 -- AC coverage (every AC has >=1 task)

| AC ID | Status | Tasks covering | Detail |
|-------|--------|----------------|--------|
| AC1 | PASS | T01 | Bulk canonize service + endpoint |
| AC2 | PASS | T02 | Auto-canonize hook on CSV import |
| AC3 | PASS | T03 | Bulk canonize CLI command |
| AC4 | PASS | T04 | Frontend bulk canonize UI |
| AC5 | PASS | T05 | i18n keys for canonize UI |

## Check 2 -- Bidirectional traceability (every task cites >=1 AC)

| Task | Status | ACs cited | Detail |
|------|--------|-----------|--------|
| T01 | PASS | AC1 | |
| T02 | PASS | AC2 | |
| T03 | PASS | AC3 | |
| T04 | PASS | AC4 | |
| T05 | PASS | AC5 | |

## Check 3 -- File collision (same-Wave tasks don't share files)

| Wave | Status | Colliding paths | Tasks involved |
|------|--------|-----------------|----------------|
| 0 | PASS | (none) | T01 only |
| 1 | PASS | (none) | T02, T03, T04, T05 -- no shared files |

**Detail:** Wave 0 contains only T01, so no collision is possible. In Wave 1, T02 touches `src/collection/importer.py` + `src/api/routers/collection.py`, T03 touches `src/cli/main.py`, T04 touches `frontend/src/api/collection.ts` + `frontend/src/pages/MyCollection.tsx`, T05 touches `frontend/src/i18n/locales/en.json` + `frontend/src/i18n/locales/pt-BR.json`. No overlapping paths within either Wave.

## Check 4 -- Wave 0 completeness (deps/perms/scaffolding)

| Item needed by Wave>=1 | Status | Wave 0 covers? | Detail |
|------------------------|--------|----------------|--------|
| `src/collectors/bulk_canonize.py` (new module) | PASS | T01 creates it | T02, T03 depend on bulk_canonize function |
| `BulkCanonizeResult` schema | PASS | T01 creates it in `src/api/schemas/collection.py` | T04 needs the API response type |

No new directories, pip/npm dependencies, or permissions required. All Wave 1 tasks depend solely on artifacts created by T01 in Wave 0.

## Check 5 -- Testing section non-empty

| Task | Status | Detail |
|------|--------|--------|
| T01 | PASS | 7 test cases (5 unit + 2 integration) |
| T02 | PASS | 5 test cases (3 unit + 2 integration) |
| T03 | PASS | 3 unit test cases |
| T04 | PASS | 5 unit test cases |
| T05 | PASS | 3 unit test cases |

## Previous blocking issues -- resolution verification

| # | Issue | Status |
|---|-------|--------|
| 1 | Missing Global Acceptance Criteria + Maps to AC fields | RESOLVED -- README now declares AC1-AC5, all 5 tasks have `**Maps to AC:**` fields |
| 2 | T02 in Wave 0 caused file collision on `collection.py` with T01 | RESOLVED -- T02 moved to Wave 1 |
| 3 | T04 referenced `CollectionPage.tsx` instead of `MyCollection.tsx` | RESOLVED -- T04 now correctly references `MyCollection.tsx` |

## Source file existence check

| File | Exists | Note |
|------|--------|------|
| `src/collectors/bulk_canonize.py` | No (expected) | New file, created by T01 |
| `src/collection/importer.py` | Yes | Modified by T02 |
| `src/api/routers/collection.py` | Yes | Modified by T01 (Wave 0), T02 (Wave 1) |
| `src/api/schemas/collection.py` | Yes | Modified by T01 |
| `src/collectors/sync_collection.py` | Yes | Referenced by T02 (verify only) |
| `src/cli/main.py` | Yes | Modified by T03 |
| `frontend/src/pages/MyCollection.tsx` | Yes | Modified by T04 |
| `frontend/src/api/collection.ts` | Yes | Modified by T04 |
| `frontend/src/i18n/locales/en.json` | Yes | Modified by T05 |
| `frontend/src/i18n/locales/pt-BR.json` | Yes | Modified by T05 |

## Summary

- PASS: 5
- FAIL: 0

All 5 checks passed. All 3 previously reported blocking issues have been resolved.

**Verdict:** READY
