# QA Report: F11 -- Post-F10 Operationalization

**QA Agent:** Claude Opus 4.6
**Date:** 2026-08-20
**Verdict:** PASS

---

## 1. Test Results Summary

### Backend Tests

| Metric | Value |
|--------|-------|
| Tests passed | 616 |
| Tests failed | 0 |
| Warnings | 86 (pre-existing ResourceWarning: unclosed database) |
| Coverage | 91.44% |
| Coverage threshold (70%) | MET |
| Execution time | 173.29s |

### Frontend Tests

| Metric | Value |
|--------|-------|
| Test files | 21 |
| Tests passed | 187 |
| Tests failed | 0 |
| Execution time | 4.45s |

### Lint

| Tool | Errors |
|------|--------|
| ruff check src/ tests/ | 0 |

---

## 2. Verification Checklist

### Tech Debt: Duplicate `_row_to_entry` Extraction (T03)

| # | Check | Result |
|---|-------|--------|
| 1 | `src/collection/converter.py` exists with `row_to_collection_entry()` | PASS -- single function definition at line 9 |
| 2 | No `_row_to_entry` function definitions in `src/` | PASS -- grep returns zero matches |
| 3 | No `_row_to_entry` references in `tests/` | PASS -- grep returns zero matches |
| 4 | `match_report.py` imports from `src.collection.converter` | PASS -- line 13 |
| 5 | `sync_collection.py` imports from `src.collection.converter` | PASS -- line 11 |
| 6 | `tests/collection/test_converter.py` has 3 test cases | PASS -- happy path, None name_en, empty set_code |

### Tech Debt: Move SQLAlchemy to Repository (T04)

| # | Check | Result |
|---|-------|--------|
| 1 | `Repository.get_collection_total_value()` exists | PASS -- line 664 in repository.py |
| 2 | No `from sqlalchemy` imports in `src/api/` | PASS -- grep returns zero matches |
| 3 | `collection_summary` endpoint uses `repo.get_collection_total_value()` | PASS -- line 103 in collection.py |
| 4 | 5 test cases in `TestGetCollectionTotalValue` | PASS -- happy path, no linked, no prices, mixed, unlinked |

### Tech Debt: Remove Dead `BASE_URL` (T05)

| # | Check | Result |
|---|-------|--------|
| 1 | `grep -rn "BASE_URL" src/collectors/` returns nothing | PASS -- zero matches |

### Parser Fix (discovered during T02)

| # | Check | Result |
|---|-------|--------|
| 1 | `parse_search_results()` supports new field names via fallback chain | PASS -- `idproduto`, `nomeenproduto`, `slugnomeenproduto`, `codigoproduto` at lines 62-75 |
| 2 | Backward compatibility with old field names preserved | PASS -- existing fixture-based tests still pass |
| 3 | 4 new tests in `TestParseSearchResultsNewFieldNames` | PASS -- new field names parsed, multiple results, PT name fallback, PT slug fallback |

### Documentation (T08)

| # | Check | Result |
|---|-------|--------|
| 1 | PRD exists at `docs/prd/F11-post-f10-operationalization.md` | PASS |
| 2 | Architecture diagram at `docs/diagrams/F11-architecture.mmd` | PASS -- 71 lines, shows all 4 waves with blocked state |
| 3 | Journey diagram at `docs/diagrams/F11-journey.mmd` | PASS -- 28 lines, operator flow with parser-fix feedback loop |
| 4 | README.md updated with F11 section | PASS -- "F11 -- Post-F10 Operationalization (2026-08-20)" |

### Operational Tasks (T01, T02, T06, T07)

| Task | Status | Evidence |
|------|--------|----------|
| T01: Normalize set codes | done | Documented in task file -- all set codes lowercase |
| T02: Match report | done | 94.7% match rate (519/548), JSON report saved |
| T06: Sync collection | partial | 124 cards linked, 0 observations (MYP site changed) |
| T07: Verify dashboard | done (partial) | Card counts valid, total_value=None due to zero price overlap |

---

## 3. Acceptance Criteria Review by Task

### T01 -- Normalize Set Codes
- [x] DB backup created
- [x] Script ran without errors
- [x] All set codes lowercase
- **Verdict:** MET

### T02 -- Match Report
- [x] Report completes without errors
- [x] 94.7% coverage (exceeds 70% target)
- [x] JSON report saved
- **Verdict:** MET

### T03 -- Extract `_row_to_entry`
- [x] `converter.py` exists with `row_to_collection_entry()`
- [x] `_row_to_entry` removed from both source modules
- [x] Both modules import from `src.collection.converter`
- [x] All existing tests pass
- [x] 3 new unit tests in `test_converter.py`
- **Verdict:** MET

### T04 -- Move SQLAlchemy to Repository
- [x] `Repository.get_collection_total_value()` exists, returns `Decimal | None`
- [x] No inline `sqlalchemy` imports in `collection.py` router
- [x] Endpoint behavior preserved (same response shape)
- [x] 5 new unit tests in `TestGetCollectionTotalValue`
- [x] All existing tests pass
- **Verdict:** MET

### T05 -- Remove Dead `BASE_URL`
- [x] `BASE_URL` no longer exists in `sync_collection.py`
- [x] No references anywhere in codebase
- [x] All tests pass
- [x] Lint clean
- **Verdict:** MET

### T06 -- Sync Collection
- [x] DB backup created before sync
- [x] Sync completed without fatal errors
- [x] 124 collection entries linked (card_id populated)
- [ ] ~~New price observations stored~~ (BLOCKED: MYP site changed)
- **Verdict:** PARTIAL -- sync code works correctly; MYP upstream site changed format. Documented honestly as blocker. Not a code defect.

### T07 -- Verify Dashboard KPIs
- [x] Linked card count matches sync results (124)
- [x] API summary endpoint returns valid data
- [x] Backend tests pass (616, 91.44%)
- [x] Frontend tests pass (187)
- [ ] ~~Dashboard shows non-zero collection value~~ (expected: requires price data which MYP no longer provides)
- **Verdict:** PARTIAL -- code is correct; data gap due to upstream dependency. Not a code defect.

### T08 -- Documentation
- [x] PRD exists with honest partial-success outcomes
- [x] Architecture diagram exists and reflects blocked state
- [x] Journey diagram exists with parser-fix feedback loop
- [x] README updated with F11 delivery notes
- **Verdict:** MET

---

## 4. New Tests Added by F11

| File | Tests | Coverage Area |
|------|-------|--------------|
| `tests/collection/test_converter.py` | 3 | `row_to_collection_entry()` happy path, None name, empty set_code |
| `tests/database/test_repository_api.py` | 5 | `get_collection_total_value()` happy path, no linked, no prices, mixed, unlinked |
| `tests/parsers/test_myp_search.py` | 4 | New MYP field names, multiple results, PT name fallback, PT slug fallback |
| **Total new** | **12** | |

Test count: 604 (baseline) + 12 (new) = 616 (actual).

---

## 5. Test Gaps

No actionable test gaps found. Two observations for future reference:

1. **T03 acceptance criteria checkboxes not ticked in task file.** All 5 ACs
   for T03 are `- [ ]` (unchecked) in `F11-T03.md` despite the task being
   marked as `done`. Same for T04, T05, and T08. This is a cosmetic oversight
   in the task files -- the actual code and tests confirm all criteria are met.

2. **No fixture file for new MYP API format.** As the TechLead noted (MINOR 1),
   the new field names are tested via inline `json.dumps()` in
   `TestParseSearchResultsNewFieldNames`. A fixture file
   (`myp_search_new_format.json`) would improve consistency with the existing
   fixture-based test pattern. Not blocking.

---

## 6. Verdict: PASS

F11 is approved for shipping. All automated checks pass (616 backend tests,
187 frontend tests, zero lint errors, 91.44% coverage). All three tech debt
items are properly resolved. The parser fix is backward-compatible and well-tested.
The partial results on T06/T07 are due to upstream MYP site changes, not code
defects -- the feature documents this honestly in the PRD and task files.

---

## 7. Summary

| Metric | Before F11 | After F11 |
|--------|-----------|-----------|
| Backend tests | 604 | 616 |
| Frontend tests | 187 | 187 |
| Coverage | 90.69% | 91.44% |
| Lint errors | 0 | 0 |
| Duplicated `_row_to_entry` | 2 copies | 1 shared |
| Raw SQLAlchemy in API layer | 1 endpoint | 0 |
| Dead `BASE_URL` | 1 | 0 |
| MYP parser field support | old only | old + new (fallback chain) |
