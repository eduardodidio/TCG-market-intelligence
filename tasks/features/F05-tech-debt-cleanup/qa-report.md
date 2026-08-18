# QA Report -- F05

**Verdict:** PASS
**Validated at:** 2026-08-18T15:00:00

## Test Results

- Total tests: 213
- Passed: 213
- Failed: 0
- Coverage: 97.21% (was 86%)

Per-file coverage (targets in parentheses):

| File | Coverage | Target | Status |
|------|----------|--------|--------|
| `providers/myp/provider.py` | 100% | >= 85% | PASS |
| `parsers/myp.py` | 100% | >= 90% | PASS |
| `cli/main.py` | 99% (line 192 only) | >= 85% | PASS |
| `collectors/backfill.py` | 89% | >= 90% | N/A (LOW priority, not an AC) |
| `analytics/indicators.py` | 99% (line 139 only) | -- | -- |
| Overall | 97.21% | >= 90% | PASS |

## AC Verification

- [x] AC1: Overall coverage >= 90% -- **PASS** (97.21%, confirmed via `pytest --cov=src`)
- [x] AC2: `provider.py` >= 85% -- **PASS** (100%, 115/115 stmts covered)
- [x] AC3: `parsers/myp.py` >= 90% -- **PASS** (100%, 135/135 stmts covered)
- [x] AC4: `cli/main.py` >= 85% -- **PASS** (99%, 120/121 stmts covered, only `__main__` guard uncovered)
- [x] AC5: All existing tests still pass -- **PASS** (213 passed, 0 failed, includes original 131+)
- [x] AC6: PRDs exist for F02, F03, F04 -- **PASS** (verified: `docs/prd/F02-reproducibility-docs.md`, `docs/prd/F03-analytics-engine.md`, `docs/prd/F04-collector-scaling.md`)
- [x] AC7: F04 diagrams exist -- **PASS** (verified: `docs/diagrams/F04-architecture.mmd`, `docs/diagrams/F04-journey.mmd`)
- [x] AC8: `.coverage` in `.gitignore` -- **PASS** (line 10 of `.gitignore`)
- [x] AC9: F03-README status is "done" -- **PASS** (line 3: `**Status:** done`)

## Diagram Validation

- `docs/diagrams/F04-architecture.mmd`: Valid Mermaid `flowchart TB`. 86 lines, uses subgraphs for CLI/collector/provider/database layers. Accurately represents the codebase structure.
- `docs/diagrams/F04-journey.mmd`: Valid Mermaid `flowchart TD`. 48 lines, BPMN-style user journey with decision nodes for resume, limit, and error handling. Flow logic matches the implementation.

## Lint Results

6 ruff violations found in the 3 new test files (all untracked, not yet committed):

1. `tests/unit/test_provider.py:5` -- F401: `asyncio` imported but unused
2. `tests/unit/test_provider.py:3` -- I001: import block unsorted
3. `tests/unit/test_provider.py:283` -- F841: `slugs` assigned but never used
4. `tests/unit/test_parsers_edge.py:3` -- I001: import block unsorted
5. `tests/unit/test_cli_collector.py:93` -- F841: `mock_bf` assigned but never used
6. `tests/unit/test_cli_collector.py:192` -- E501: line too long (106 > 100)

All 6 are auto-fixable (`ruff check --fix` for 3, `--unsafe-fixes` for 2 more, manual wrap for 1). Pre-commit hooks would block committing these files as-is. **These must be fixed before the commit but do not block the QA verdict** since all ACs are met and the fixes are trivial.

## Test Gaps Found

- **ResourceWarning: unclosed database connections** -- 26 warnings from integration and repository tests. Not a test gap per se, but indicates SQLAlchemy sessions are not being properly closed in test teardown. Worth addressing in a future cleanup to keep test output clean.
- **RuntimeWarning: coroutine never awaited** -- 4 warnings in CLI tests (`run_backfill`, `run_update`, `run_retry_failed`). These arise because Click commands wrap async functions and the test patches `asyncio.run` without invoking the coroutine. Cosmetic, does not affect test correctness.
- **`collectors/backfill.py` at 89%** -- Lines 56-57, 129, 196-207, 257-269 remain uncovered. These are the `update` and `retry-failed` orchestrator paths. Not an AC for F05 but worth noting as future coverage targets.

## Regressions

- None. All 213 tests pass. No functionality was removed or altered.

## Final Notes

F05 successfully resolves the tech debt it set out to address. Coverage jumped from 86% to 97.21%, with all three target files reaching 99-100%. The retroactive PRDs accurately document F02/F03/F04. The F04 diagrams faithfully represent the architecture and user journey.

The only action item before committing is fixing the 6 ruff lint violations in the new test files -- all are trivially fixable and the pre-commit hooks would catch them regardless.

TechLead's cosmetic observations (misleading "4xx" test names for 5xx status codes, dead code block in `test_backfill_with_options`) are confirmed but non-blocking. They are good candidates for a quick cleanup pass.
