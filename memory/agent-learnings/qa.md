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
