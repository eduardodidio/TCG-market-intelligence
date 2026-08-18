# Readiness Report -- F05

**Verdict:** READY
**Audited at:** 2026-08-18T12:00:00Z

## Checklist

### README (F05-README.md)

- [x] Goal is clearly stated -- resolve tech debt before REST API work
- [x] Debt inventory table with Current/Target/Priority -- all measurable
- [x] Global ACs (AC1-AC9) are specific and verifiable (coverage percentages, file existence checks)
- [x] Wave ordering is logical: Wave 0 (housekeeping) -> Wave 1 (tests, parallel) -> Wave 2 (docs, parallel)
- [x] No circular dependencies -- Wave 1 tasks are independent of each other, Wave 2 tasks are independent of each other

### F05-T01 (Wave 0 -- Housekeeping)

- [x] Has User Story -- developer wants clean repo and accurate metadata
- [x] Has Dev Notes -- 3 actionable steps (add .coverage to .gitignore, fix F03 status, verify other READMEs)
- [x] Has Testing section -- git status check + grep verification
- [x] Wave 0 assignment correct -- no dependencies, enables clean baseline
- [x] Spot-check: `.gitignore` exists and indeed lacks `.coverage` entry -- confirmed
- [x] Spot-check: `F03-README.md` exists and currently says `Status: planned` -- confirmed, needs fix

### F05-T02 (Wave 1 -- Provider test coverage)

- [x] Has User Story -- developer wants provider at >= 85% coverage
- [x] Has Dev Notes -- detailed gap analysis (line numbers), 12 specific test cases, code patterns
- [x] Has Testing section -- pytest commands with coverage thresholds
- [x] Wave 1 assignment correct -- independent of T03/T04
- [x] Spot-check: `src/providers/myp/provider.py` exists -- confirmed
- [x] Spot-check: No existing `tests/unit/test_provider.py` -- confirmed (task correctly says "Create")
- [x] Spot-check: `tests/fixtures/` has HTML fixtures available for mock responses -- confirmed (4 files)

### F05-T03 (Wave 1 -- Parser test coverage)

- [x] Has User Story -- developer wants parsers at >= 90% coverage
- [x] Has Dev Notes -- specific missing line numbers, 3-step approach with edge cases listed
- [x] Has Testing section -- pytest commands with coverage thresholds
- [x] Wave 1 assignment correct -- independent of T02/T04
- [x] Spot-check: `src/parsers/myp.py` exists -- confirmed
- [x] Spot-check: `tests/unit/test_parsers.py` exists -- confirmed (will add tests to existing file)

### F05-T04 (Wave 1 -- CLI test coverage)

- [x] Has User Story -- developer wants CLI at >= 85% coverage
- [x] Has Dev Notes -- missing line numbers, identifies likely untested commands, CliRunner pattern
- [x] Has Testing section -- pytest commands with coverage thresholds
- [x] Wave 1 assignment correct -- independent of T02/T03
- [x] Spot-check: `src/cli/main.py` exists -- confirmed
- [x] Spot-check: `tests/unit/test_cli_analytics.py` exists -- confirmed (partial CLI tests already present)

### F05-T05 (Wave 2 -- Missing PRDs)

- [x] Has User Story -- maintainer wants PRDs for all shipped features
- [x] Has Dev Notes -- 3 PRDs with problem/goals/non-goals outlined, format reference to F01 PRD
- [x] Has Testing section -- file existence and content validation
- [x] Wave 2 assignment correct -- docs depend on nothing in Wave 1
- [x] Spot-check: `docs/prd/F01-myp-cards-collector.md` exists as template reference -- confirmed
- [x] Spot-check: F02/F03/F04 README files exist for reference material -- confirmed

### F05-T06 (Wave 2 -- F04 Diagrams)

- [x] Has User Story -- maintainer wants F04 diagrams per living docs rules
- [x] Has Dev Notes -- describes both diagrams with component lists and flow steps
- [x] Has Testing section -- file existence + valid Mermaid syntax
- [x] Wave 2 assignment correct -- docs task, parallel with T05
- [x] Spot-check: `docs/diagrams/` has F01/F02/F03 diagrams for style reference -- confirmed (6 files)
- [x] Spot-check: No F04 diagrams exist yet -- confirmed (correctly identified as missing)

## Blockers

- None

## Notes

- F05-T02 references specific line numbers for coverage gaps. These may shift if any prior changes were made since the analysis. The developer should re-run `pytest --cov` at the start of the task to confirm current gaps. This is a minor implementation detail, not a blocker.
- F05-T04 Dev Notes reference `tests/unit/test_cli*.py` (glob pattern). Currently only `test_cli_analytics.py` exists. The developer may need to create a new `test_cli.py` or add to the existing file -- either approach works.
- The README line 8 has a minor typo: "before starting F05 (REST API)" should likely say "before starting F06 (REST API)" since F05 is this feature itself. This does not affect implementation.
- All 6 tasks have complete structure (User Story, Dev Notes, Testing). All referenced source files exist. Wave dependencies are acyclic and sensible. The plan is ready for execution.
