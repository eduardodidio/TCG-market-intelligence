# F211 — Batch Fix: Tests + Art Card + Purchases + BAT Audit

**Status:** planned
**Created:** 2026-11-19
**Type:** bugfix + maintenance + audit

## Summary

Batch of 8 independent tasks addressing:
1. Fix 53 failing tests across 5 root causes
2. Fix Mox Amber (smbro) art card showing wrong image
3. Review acquisition price state and re-import feasibility
4. Review BAT files and run price sweep with performance analysis

## Wave Plan

| Wave | Tasks | Parallelism |
|------|-------|-------------|
| 0 | T01, T02, T03, T04, T05, T06, T07, T08 | All 8 parallel (zero dependencies) |

## Tasks

| ID | Title | Files | Est. |
|----|-------|-------|------|
| T01 | Fix FK constraint test failures (41 tests) | 3 test files | S |
| T02 | Fix missing oracle_text column (1 test) | model + test | S |
| T03 | Fix config DB URL env override (2 tests) | 1 test file | S |
| T04 | Fix exchange rate date logic (4 tests) | 3 test files | S |
| T05 | Fix deck evaluation MagicMock (3 tests) | 1 test file | S |
| T06 | Fix Mox Amber art card image fallback | image_fallback.py + tests | M |
| T07 | Audit acquisition prices in collection | query + report | S |
| T08 | Review BATs + run push-all performance test | bats/*.bat + CLI run | M |

## Acceptance Criteria

- [ ] All 53 previously-failing tests pass
- [ ] No regressions in the remaining ~5100 tests
- [ ] Mox Amber (smbro/98) displays correct card image
- [ ] Acquisition price report generated
- [ ] BAT review documented + push-all performance measured
