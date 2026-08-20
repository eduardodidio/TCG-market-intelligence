# QA Learnings

(QA appends to this file at the end of every feature retrospective.
Each entry is a lesson that generalizes beyond a single bug.)

## F01 -- MYP Cards Backfill (2026-08-18)

- **Every feature must have a QA report, no exceptions.** F01 shipped without any QA validation or retrospective, which meant zero learnings were captured. Even for a "just run the collector" feature, a QA pass validates data quality and captures patterns for future features.
- **Data validation queries are a form of acceptance testing.** F01-T02's SQL checks (count, coverage, encoding, anomalies) are effectively acceptance tests for data pipelines. Standardize these as a QA checklist for any feature that loads or transforms data.

## F02 -- Reproducibility & Living Documentation (2026-08-18)

- **Always write retrospective learnings to agent-learnings files.** The F02 QA report contained "Retrospective Seeds" but they were never propagated to the agent-learnings files. The retrospective ceremony is incomplete until learnings are appended to each role's file.
- **Validate cross-links as a dedicated QA check.** Broken links between docs are a recurring issue. Add "verify all cross-links resolve" as a standard QA checklist item for any feature that delivers documentation.

## F03 -- Analytics Engine (2026-08-18)

- **Always run smoke tests against a real database when one exists.** The live `analyze list` + `analyze card` smoke tests caught nothing that unit tests missed this time, but they validated the full stack (SQLite -> Repository -> Analytics -> CLI output) in a way mocked tests cannot. Make this a standard step.
- **When `pytest-cov` is unavailable, do a manual branch audit.** Walk through each function's conditionals and verify each branch has a corresponding test. This is slower but sufficient for a QA verdict. However, advocate for adding `pytest-cov` to dev deps so future QA runs can automate this.

## F04 -- Collector Scaling (2026-08-18)

- **Always verify that instrumented tracking variables are asserted against.** The integration concurrency test tracked `max_concurrent` via a counter but never asserted on it -- a computed-but-not-asserted variable is a common gap that gives false confidence. When reviewing tests, search for variables that are assigned but never appear in `assert` statements.
- **TechLead NITs are QA's gap backlog.** The TechLead review's NIT-03 directly mapped to a real test gap. Always cross-reference TechLead NITs with test coverage -- informational notes from review often point to missing assertions or weak test designs.

## F05 -- Technical Debt Cleanup (2026-08-18)

- **Always run lint as part of QA validation, even when not an explicit AC.** F05's ACs did not include "zero lint violations," but QA caught 6 ruff errors that would have blocked the commit. Lint checks should be a standard QA step for every feature, regardless of whether the ACs mention them.
- **ResourceWarnings in test output are future tech debt.** The 26 unclosed-database warnings are harmless today but accumulate noise that can mask real warnings. Flag these in QA reports so they enter the next tech debt inventory.

## F07 -- Front-end Dashboard (2026-08-18)

- **Install coverage tooling early and verify it works.** `@vitest/coverage-v8` was not in devDependencies, so QA had to install it to get coverage numbers. Coverage tooling should be part of Wave 0 scaffolding and verified in the first test run.
- **React 19 `act()` warnings in stderr are cosmetic, not blocking.** PriceChart and Cards tests emit `act()` warnings because state updates happen outside `act()` wrappers. All assertions pass correctly. These are a known React 19 testing pattern shift and should not delay a QA verdict.
- **TechLead minor notes are QA quick-wins.** Three of four TechLead minor notes (unused alias, dead export, version label) were fixed in under 5 minutes. Always check TechLead notes first -- they are pre-identified cleanup opportunities.

## F08 -- Data Enrichment (2026-08-19)

- **Cross-reference test plan IDs against actual test files systematically.** The developer implemented 15 of 18 test plan cases, but missed U-04 (empty response body in _fetch), U-11 (UnicodeEncodeError graceful handling), and U-16 (Dashboard fetches movers with period=30d). QA found and added all three. When a test plan exists with numbered cases, QA should check off each ID one-by-one against the test code rather than spot-checking.
- **Default parameter assertions prevent silent regressions.** The Dashboard test verified movers rendering but never asserted the fetch URL contained `period=30d`. Without this assertion, someone could revert the default to `7d` and all tests would still pass. Always assert on default parameters when the default value is a deliberate product decision.
- **Encoding tests require boundary coverage.** The fix_mojibake function has three code paths: successful roundtrip (latin-1 encode then UTF-8 decode), no-change (already correct), and exception (unencodable characters). All three paths must have explicit test coverage, not just the happy path.

## F09 -- Scheduled Collection (2026-08-19)

- **When the developer exceeds the test plan, verify the extras are correct, not just that the plan items are covered.** F09 had 22 planned scenarios but the developer shipped ~40 tests. The boundary test (50% stale = healthy) and error-priority-over-stale test are both non-obvious edge cases that would have been genuine gaps if missed. Cross-referencing the plan is necessary but not sufficient -- also audit the implementation logic for untested branches.
- **Graceful degradation in the frontend deserves a dedicated AC verification.** The Dashboard's health fetch is independent of stats/movers fetches. The test correctly verifies that the dashboard renders KPI cards even when the health endpoint returns 500. This is a pattern worth standardizing: for any optional/non-critical data source on a page, add a test that the page works when that source fails.
- **Shell scripts are an inherent test gap -- document what was manually verified.** The cron script has no automated tests (by design), but QA should record what was inspected: `set -euo pipefail`, `mktemp` + `trap` cleanup, exit codes, required env var check, log directory creation. This list becomes the manual QA checklist for future script changes.

## F10 -- Collection-Centric Pivot (2026-08-19)
- **Saruman conditions should be verified by tracing code flow, not just checking test existence.** For Condition #2 (backup before deletion), QA verified not just that a test asserts backup is called, but that the backup call in `cleanup.py` (line 208) occurs BEFORE the deletion session (line 212) in the actual source code. Test assertions confirm the contract; code flow analysis confirms the implementation honors it. Both are required for safety conditions.
- **When all test plan scenarios are covered, verify the extras too.** The developer exceeded the 54 test plan scenarios with additional edge cases (split card names, empty history still links, upsert returning None, duplicate entries sharing one CardRow). These extras test non-obvious code paths that the test plan did not anticipate. QA should verify these extras are correct, not just count them.
- **Three-layer safety models deserve a dedicated QA section.** The guard (empty collection check) + backup (sqlite3.backup) + dry-run (default via CLI) pattern in F10 is the standard for destructive operations. When a feature has an explicit safety architecture, QA should verify each layer independently and document the evidence chain -- not just say "tests pass."
