# F15 Readiness Report

**Date:** 2026-08-20
**Verdict:** READY

## Checklist
- [x] All tasks have acceptance criteria
- [x] All tasks have test scenarios
- [x] Wave dependencies are valid
- [x] Referenced files exist
- [x] No circular dependencies
- [x] No missing prerequisites

## Task-by-Task Summary

### F15-T01 -- MYP Variant Set Code Mapping Utility (Wave 0)
- **Acceptance criteria:** 5 items, clear and testable
- **Test scenarios:** 5 scenarios covering known mappings, pass-through, unknown codes, case sensitivity, SLD numeric suffixes
- **Dependencies:** None (correct for Wave 0)
- **Files:** Creates new `frontend/src/utils/setCodeMap.ts` and `src/utils/set_code_map.py`. The frontend `utils/` directory exists; the backend `src/utils/` directory does not yet exist and must be created by the developer. This is trivial and not a blocker.

### F15-T02 -- Fix Full-Art Card Images (Wave 1)
- **Acceptance criteria:** 7 items covering variant types, fallbacks, and regression
- **Test scenarios:** 7 scenarios (backend URL mapping, frontend rendering, fallback chain)
- **Dependencies:** F15-T01 (Wave 0) -- valid, T01 completes before Wave 1 starts
- **Files:** All referenced files exist: `src/api/routers/collection.py`, `frontend/src/utils/scryfall.ts`, `frontend/src/pages/MyCollection.tsx`

### F15-T03 -- BRL Currency Indicator in Sidebar (Wave 1)
- **Acceptance criteria:** 5 items including accessibility
- **Test scenarios:** 3 scenarios (render text, aria-label, presence on load)
- **Dependencies:** None -- independent of all other tasks
- **Files:** `frontend/src/components/Layout.tsx` exists

### F15-T04 -- Collection Card Detail View (Wave 1)
- **Acceptance criteria:** 10 items covering linked/unlinked cards, metadata, navigation
- **Test scenarios:** 12 scenarios (backend endpoint, frontend rendering, navigation)
- **Dependencies:** Declared as "none" in task header. Acceptance criterion #4 mentions "using mapped Scryfall URL from T01/T02" but this is a soft integration detail, not a blocking dependency -- T01 ships in Wave 0 before T04 starts
- **Files:** All existing files referenced exist: `src/api/routers/collection.py`, `src/api/schemas/collection.py`, `src/database/repository.py`, `frontend/src/pages/MyCollection.tsx`, `frontend/src/api/collection.ts`, `frontend/src/types/api.ts`, `frontend/src/App.tsx`. New files to create: `frontend/src/pages/CollectionCardDetail.tsx`

## Wave Dependency Validation

```
Wave 0: T01 (no deps)
Wave 1: T02 (depends on T01 -- Wave 0, valid)
         T03 (no deps, valid)
         T04 (no deps on other F15 tasks, valid)
```

No task depends on a task in the same or later wave. No circular dependencies.

## Issues Found

1. **Minor -- backend `src/utils/` directory does not exist.** T01 creates `src/utils/set_code_map.py` but the `src/utils/` directory is not yet present. The developer must create it (and an `__init__.py`). This is standard and not a blocker.

2. **Minor -- T04 test file path inconsistency.** T04 lists `tests/api/test_collection_router.py` for backend tests, which may overlap with T02's test file at the same path. Developers should coordinate or use the same file. Not a blocker since they are in the same wave and the file can accommodate both sets of tests.

## Verdict Rationale

All four tasks have clear acceptance criteria, well-defined test scenarios, identified files to change, and valid wave ordering. The two minor issues (missing `src/utils/` directory, shared test file) are routine implementation details that do not block planning or execution. The feature is ready for development.
