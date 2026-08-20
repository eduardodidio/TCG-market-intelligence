# F11 Test Plan -- Post-F10 Operationalization

**Feature:** F11 -- Post-F10 Operationalization
**TEA:** Claude Opus 4.6
**Date:** 2026-08-20
**Baseline:** 604 backend tests, 90.69% coverage, 187 frontend tests

---

## 1. Test Strategy Overview

F11 is a hybrid feature: half operational execution (running existing scripts
and CLI commands against the production DB) and half minor code refactors (tech
debt cleanup with no behavioral changes). The test strategy reflects this
duality.

### Test Types

| Type | Applies To | Rationale |
|------|-----------|-----------|
| **Unit tests** | T03, T04 | New code paths: `row_to_collection_entry()` in converter.py, `get_collection_total_value()` in repository.py |
| **Integration tests** | T03, T04 | Verify that match_report and sync_collection still work after import changes; verify endpoint response shape is preserved |
| **Regression (full suite)** | T03, T04, T05 | Any refactor must pass the existing 604 tests with coverage >= 90% |
| **Operational verification** | T01, T02, T06, T07 | Manual/scripted checks against real DB and running services -- not automated pytest |
| **Lint verification** | T03, T04, T05 | `ruff check` must stay clean after all code changes |

### Key Principle

Since T03, T04, and T05 are pure refactors with **no behavioral changes**,
the primary safety net is the existing test suite. New tests target only the
new abstractions (the shared converter function and the new repository method).
Operational tasks (T01, T02, T06, T07) rely on verification checklists rather
than new automated tests, because they interact with the live MYP service and
production database.

---

## 2. Test Coverage Matrix

| Task | Type | New Tests | Modified Tests | Existing Coverage |
|------|------|-----------|----------------|-------------------|
| T01 -- Normalize set codes | infra | 0 | 0 | Script has no automated tests (F11-T01 notes "tests use in-memory SQLite, not production DB"); existing suite serves as regression gate |
| T02 -- Match report (dry-run) | infra | 0 | 0 | 26 tests in `tests/collectors/test_match_report.py` cover all orchestrator logic |
| T03 -- Extract `_row_to_entry` | backend | 3-4 | 2 files modified | 26 tests (match_report) + 20 tests (sync_collection) import `_row_to_entry` directly |
| T04 -- Move SQLAlchemy to Repository | backend | 4-5 | 0 | 40 tests in `tests/database/test_repository_api.py`, 10 in `tests/api/test_collection_sync.py`; no existing test for `/summary` endpoint |
| T05 -- Remove dead `BASE_URL` | backend | 0 | 0 | 20 tests in `tests/collectors/test_sync_collection.py` (none reference `BASE_URL`) |
| T06 -- Sync collection | infra | 0 | 0 | 20 tests in `tests/collectors/test_sync_collection.py` |
| T07 -- Verify dashboard KPIs | frontend | 0 | 0 | 187 frontend tests (Vitest); manual verification against live servers |
| T08 -- Documentation | docs | 0 | 0 | N/A (documentation only) |

**New test count estimate:** 7-9 new tests across 2 new/extended test files.
**Expected total after F11:** ~611-613 backend tests.

---

## 3. Unit Test Plan

### T03: `tests/collection/test_converter.py` (NEW FILE)

Tests for the extracted `row_to_collection_entry()` function in
`src/collection/converter.py`.

| # | Test Name | Scenario | Input | Expected Output |
|---|-----------|----------|-------|-----------------|
| 1 | `test_converts_full_row` | Happy path: all fields populated | `UserCollectionRow(set_code="ltr", collector_number="42", name_en="Gandalf")` | `CollectionEntry(set_code="ltr", collector_number="42", name_en="Gandalf")` |
| 2 | `test_none_name_en` | Edge case: name_en is None | `UserCollectionRow(name_en=None)` | `CollectionEntry(name_en=None)` |
| 3 | `test_empty_set_code` | Edge case: empty string set_code | `UserCollectionRow(set_code="")` | `CollectionEntry(set_code="")` |
| 4 | `test_returns_collection_entry_type` | Type check | Any valid row | `isinstance(result, CollectionEntry)` is True |

**Notes:**
- These tests mirror the existing `TestRowToEntry` classes in both
  `test_match_report.py` and `test_sync_collection.py`, but test the new
  public function at its canonical location.
- The existing `TestRowToEntry` classes in both test files will need their
  imports updated from `_row_to_entry` to `row_to_collection_entry` (or
  removed if deemed redundant -- see Modified Tests below).

### T04: `tests/database/test_repository.py` or `tests/database/test_repository_api.py` (EXTEND)

Tests for the new `Repository.get_collection_total_value()` method.

| # | Test Name | Scenario | Setup | Expected |
|---|-----------|----------|-------|----------|
| 1 | `test_linked_cards_with_prices_returns_total` | Happy path | 2 linked UserCollectionRows with prices (qty=1 at R$10, qty=2 at R$5) | `Decimal("20.00")` |
| 2 | `test_no_linked_cards_returns_none` | No linked cards | UserCollectionRows all with `card_id=None` | `None` |
| 3 | `test_linked_cards_no_prices_returns_none` | Linked but no price data | Linked UserCollectionRows, no PriceObservationRows | `None` |
| 4 | `test_mixed_priced_and_unpriced` | Partial prices | 3 linked rows, only 2 have prices | Sum of the 2 priced cards only |
| 5 | `test_respects_quantity` | Quantity multiplier | 1 linked row with qty=3, price=R$10 | `Decimal("30.00")` |

**Notes:**
- These tests require seeding `UserCollectionRow`, `CardRow`, `SourceCardRow`,
  and `PriceObservationRow` in the in-memory DB -- similar pattern to the
  existing `seeded_repo` fixture in `test_repository_api.py`.
- The method signature is `get_collection_total_value(user_id: str) -> Decimal | None`.

### T05: No New Tests

The deletion of `BASE_URL` from `sync_collection.py` is a one-line removal
of dead code. No test references `BASE_URL`. The existing 20 tests in
`tests/collectors/test_sync_collection.py` provide full regression coverage.
A `grep -r "BASE_URL" src/collectors/` returning empty is sufficient
verification.

---

## 4. Integration Test Plan

### T03: Verify match_report and sync_collection still work with shared import

**What changes:** Both `src/collectors/match_report.py` and
`src/collectors/sync_collection.py` will replace their local `_row_to_entry`
with an import from `src.collection.converter.row_to_collection_entry`.

**Impact on existing tests:**

1. **`tests/collectors/test_match_report.py`** (26 tests)
   - `TestRowToEntry` class (2 tests, lines 76-92) imports `_row_to_entry`
     from `src.collectors.match_report`. After T03, this import will break.
   - **Required change:** Update import to
     `from src.collection.converter import row_to_collection_entry` and rename
     references, OR delete `TestRowToEntry` from this file entirely (since the
     new `test_converter.py` covers the same logic).
   - The remaining 24 tests in this file use `_row_to_entry` indirectly
     (via `run_match_report`) and should pass without modification once the
     source module is updated.

2. **`tests/collectors/test_sync_collection.py`** (20 tests)
   - `TestRowToEntry` class (2 tests, lines 118-134) imports `_row_to_entry`
     from `src.collectors.sync_collection`. Same situation as above.
   - **Required change:** Update import or delete the class.
   - The remaining 18 tests call `run_sync_collection` which internally uses
     the function -- these pass as long as the source module import is correct.

**Verification command:**
```bash
python -m pytest tests/collectors/test_match_report.py tests/collectors/test_sync_collection.py -x -v
```

### T04: Verify `GET /api/v1/collection/summary` endpoint response shape

**What changes:** The `collection_summary` endpoint in
`src/api/routers/collection.py` will replace inline SQLAlchemy with a call to
`repo.get_collection_total_value()`. The response schema (`CollectionSummary`)
must remain identical.

**Current test gap:** There is NO existing test for `GET /collection/summary`.
The 10 tests in `tests/api/test_collection_sync.py` only cover `POST /collection/sync`.

**Recommended integration test** (add to `tests/api/test_collection_sync.py` or
a new `tests/api/test_collection_summary.py`):

| # | Test Name | Scenario | Expected |
|---|-----------|----------|----------|
| 1 | `test_summary_returns_200_with_correct_shape` | Mock repo returns summary dict + total_value | 200, body has `total_unique`, `total_cards`, `total_value`, `linked_count`, `sets_count` |

**Verification command:**
```bash
python -m pytest tests/api/ -x -v -k "collection"
```

---

## 5. Operational Verification Plan

These tasks run against the production database and live MYP service. They
cannot be automated via pytest. Each task has a verification checklist.

### T01: Normalize Set Codes

**Pre-conditions:**
- Production DB exists at `tcg_market.db`
- DB backup created via `python -m src.cli.main db-backup`

**Execution:**
```bash
python scripts/normalize_set_codes.py
```

**Verification steps:**

| # | Check | Command | Expected |
|---|-------|---------|----------|
| 1 | Backup exists | `ls backups/` | Recent `.db` file present |
| 2 | Script exits 0 | Check exit code | 0 (no duplicate conflicts) |
| 3 | Output shows counts | Read stdout | `Normalized N cards, M source_cards` |
| 4 | All cards lowercase | `sqlite3 tcg_market.db "SELECT COUNT(*) FROM cards WHERE set_code != LOWER(set_code) AND set_code IS NOT NULL"` | `0` |
| 5 | All source_cards lowercase | `sqlite3 tcg_market.db "SELECT COUNT(*) FROM source_cards WHERE set_code != LOWER(set_code) AND set_code IS NOT NULL"` | `0` |
| 6 | Spot-check | `sqlite3 tcg_market.db "SELECT DISTINCT set_code FROM cards LIMIT 20"` | All lowercase |
| 7 | Regression suite passes | `python -m pytest tests/ -x -q` | 604+ tests pass |

### T02: Match Report Output

**Pre-conditions:**
- T01 completed (set codes normalized)

**Execution:**
```bash
mkdir -p reports
python -m src.cli.main match-report --output reports/match-report.json
```

**Verification steps:**

| # | Check | Command | Expected |
|---|-------|---------|----------|
| 1 | Command exits 0 | Check exit code | 0 |
| 2 | Console output shows coverage | Read stdout | Shows matched %, unmatched %, ambiguous count |
| 3 | JSON file created | `ls -la reports/match-report.json` | File exists, non-empty |
| 4 | JSON is valid | `python -c "import json; json.load(open('reports/match-report.json'))"` | No error |
| 5 | Coverage acceptable | Check `matched_total / total` | >= 70% |
| 6 | Review problematic cards | Inspect `unmatched` entries in JSON | Note sets with high unmatched count |

### T06: Sync Collection

**Pre-conditions:**
- T01 completed (set codes normalized)
- T02 completed (match report reviewed, coverage acceptable)
- DB backed up

**Execution:**
```bash
python -m src.cli.main db-backup
python -m src.cli.main sync-collection --limit 5    # smoke test first
python -m src.cli.main sync-collection               # full run (~35-40 min)
```

**Verification steps:**

| # | Check | Command | Expected |
|---|-------|---------|----------|
| 1 | Backup created | `ls backups/` | Fresh backup file |
| 2 | Smoke test (--limit 5) succeeds | Check stdout | 5 entries processed, some matched |
| 3 | Full sync completes | Check stdout | Summary with matched/unmatched/errors |
| 4 | Collection entries linked | `sqlite3 tcg_market.db "SELECT COUNT(*) FROM user_collection WHERE card_id IS NOT NULL"` | > 0 |
| 5 | Observations stored | `sqlite3 tcg_market.db "SELECT COUNT(*) FROM price_observations"` | Increased from pre-sync count |
| 6 | Error rate acceptable | Check `errors` count in summary | < 10% of total |
| 7 | Regression suite passes | `python -m pytest tests/ -x -q` | 604+ tests pass |

### T07: Dashboard KPI Verification

**Pre-conditions:**
- T06 completed (collection synced)

**Execution:**
```bash
python -m src.cli.main serve &                      # API on port 8000
cd frontend && npm run dev &                        # Frontend on port 5173
```

**Verification steps:**

| # | Check | Method | Expected |
|---|-------|--------|----------|
| 1 | API summary endpoint | `curl http://localhost:8000/api/v1/collection/summary` | JSON with `total_value > 0`, `linked_count > 0` |
| 2 | Dashboard page | Open `http://localhost:5173` | Collection value displayed, non-zero |
| 3 | Cards page | Navigate to Cards | Cards with prices visible |
| 4 | CardDetail page | Click a card | Scryfall HD image loads, price chart shows data |
| 5 | Set coverage | Dashboard or API | Sets with price data shown |
| 6 | Backend tests | `python -m pytest tests/ -x -q` | 604+ pass, coverage >= 90% |
| 7 | Frontend tests | `cd frontend && npm test` | 187+ pass |

---

## 6. Risk Assessment

### Critical Tests (Must Not Fail)

| Priority | Test Area | Risk | Mitigation |
|----------|-----------|------|------------|
| **P0** | Full backend suite (604 tests) | Any refactor in T03/T04/T05 could break imports or behavior | Run `pytest -x` after each change; do NOT batch commits |
| **P0** | T03 import updates in test files | `TestRowToEntry` in 2 test files imports `_row_to_entry` directly -- will break after extraction | Update test imports in the same commit as the source change |
| **P1** | T04 endpoint response shape | Moving logic to Repository could subtly change edge case behavior (e.g., Decimal precision, None vs 0) | Add dedicated endpoint test before refactoring; compare response shapes |
| **P1** | Coverage threshold (>= 90%) | Removing code (T05) could paradoxically drop coverage if it was counted as covered | Run `pytest --cov` after T05 to verify; current 90.69% has ~0.69% margin |
| **P2** | T01 production DB | Normalize script could fail on duplicate conflicts | Script has built-in safety check; backup taken first |
| **P2** | T06 MYP rate limiting | Full sync (~548 cards) could hit rate limits or timeouts | Use `--limit 5` smoke test first; sync has built-in retry and error isolation |

### What Could Break During Refactors

1. **T03 (extract `_row_to_entry`):**
   - Both `test_match_report.py` and `test_sync_collection.py` import
     `_row_to_entry` by name. After extraction, these imports will fail with
     `ImportError`. The developer MUST update these test files in the same
     change.
   - Risk: if the developer forgets to update the test imports, 4 tests will
     fail (2 in each file).

2. **T04 (move SQLAlchemy to Repository):**
   - The `collection_summary` endpoint currently has NO test. This means
     there is no automated safety net for the refactor. The developer should
     add at least one endpoint test before or alongside the refactor.
   - Risk: the inline logic multiplies `median_price * r.quantity` -- if the
     Repository method forgets the quantity multiplier, the bug would go
     undetected without a new test.

3. **T05 (remove `BASE_URL`):**
   - Lowest risk. `BASE_URL` is confirmed unused via grep. Deletion is safe.

### Coverage Target

- **Current:** 90.69%
- **Target:** >= 90%
- **Margin:** 0.69% (~6-7 lines of room)
- **Impact:** T05 removes 1 line of source code (net positive for coverage).
  T03 adds ~6 lines (converter.py) and removes ~14 lines (duplicated function
  in 2 files) -- net reduction in source, likely neutral or positive for
  coverage. T04 adds ~15 lines (repository method) and simplifies ~20 lines
  (router) -- neutral. New tests add to the numerator. Coverage should remain
  above 90%.

---

## 7. Test Execution Order

Aligned with the wave structure. Each wave gate must pass before the next
wave begins.

### Wave 0 -- T01 (Normalize Set Codes)

```bash
# 1. Backup production DB
python -m src.cli.main db-backup

# 2. Run normalize script
python scripts/normalize_set_codes.py

# 3. Verify normalization (see T01 checklist in Section 5)
sqlite3 tcg_market.db "SELECT COUNT(*) FROM cards WHERE set_code != LOWER(set_code) AND set_code IS NOT NULL"

# 4. Regression gate: full test suite
python -m pytest tests/ -x -q
```

**Gate:** Script exits 0, all set codes lowercase, 604 tests pass.

### Wave 1 -- T02, T03, T04, T05 (Parallel)

These four tasks are independent and can be executed in parallel. However,
test execution should follow this order for fastest feedback:

```bash
# T05 first (trivial, fastest to verify)
# After deleting BASE_URL:
ruff check src/collectors/sync_collection.py
python -m pytest tests/collectors/test_sync_collection.py -x -v

# T03 next (refactor with test file changes)
# After creating converter.py and updating imports:
python -m pytest tests/collection/test_converter.py -x -v          # new tests
python -m pytest tests/collectors/test_match_report.py -x -v       # updated imports
python -m pytest tests/collectors/test_sync_collection.py -x -v    # updated imports

# T04 next (refactor with new repo method)
# After adding get_collection_total_value and simplifying router:
python -m pytest tests/database/ -x -v                             # new repo test
python -m pytest tests/api/ -x -v -k "collection"                  # endpoint test

# T02 (operational -- run match report)
python -m src.cli.main match-report --output reports/match-report.json

# Wave 1 gate: full suite
python -m pytest tests/ -x -q --cov=src --cov-report=term-missing
```

**Gate:** All new + modified tests pass, full suite passes (604+ tests),
coverage >= 90%, match report generated.

### Wave 2 -- T06 (Sync Collection)

```bash
# 1. Backup
python -m src.cli.main db-backup

# 2. Smoke test
python -m src.cli.main sync-collection --limit 5

# 3. Full sync
python -m src.cli.main sync-collection

# 4. Verify (see T06 checklist in Section 5)
sqlite3 tcg_market.db "SELECT COUNT(*) FROM user_collection WHERE card_id IS NOT NULL"

# 5. Regression gate
python -m pytest tests/ -x -q
```

**Gate:** Sync completes, linked count > 0, observations stored, 604+ tests pass.

### Wave 3 -- T07, T08 (Verify + Document)

```bash
# T07: Start servers and verify dashboard
python -m src.cli.main serve &
cd frontend && npm run dev &
curl http://localhost:8000/api/v1/collection/summary
# Manual: verify dashboard KPIs in browser (see T07 checklist)

# T07: Final regression gate
python -m pytest tests/ -x -q --cov=src --cov-report=term-missing
cd frontend && npm test

# T08: Documentation (no tests -- manual review of PRD, diagrams, README)
```

**Gate:** Dashboard shows non-zero collection value, all backend tests pass
(604+ tests, >= 90% coverage), all frontend tests pass (187+), documentation
complete.

---

## Summary

| Metric | Before F11 | After F11 (Expected) |
|--------|-----------|---------------------|
| Backend tests | 604 | 611-613 |
| Coverage | 90.69% | >= 90% (likely ~91%) |
| Frontend tests | 187 | 187 (unchanged) |
| New test files | -- | `tests/collection/test_converter.py` |
| Modified test files | -- | `tests/collectors/test_match_report.py`, `tests/collectors/test_sync_collection.py` |
| Extended test files | -- | `tests/database/test_repository_api.py` (or `test_repository.py`) |
