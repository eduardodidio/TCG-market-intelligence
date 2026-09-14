# Retrospective — F124

## What worked
- The file-conflict map in `F124-README.md` (sole-owner rule for i18n, sequential
  Wave ordering for shared files like `collection.py`) prevented any merge
  conflicts across 4 Waves / 10 tasks touching overlapping files.
- Pre-adding i18n keys in Wave 0 (T05) that a later Wave's component (T04)
  consumes avoided any i18n-ownership churn.
- Regression triage via `git stash` + baseline re-run (done in T10, repeated
  independently by QA) is a reliable way to separate branch-introduced
  failures from pre-existing ones without spending time "fixing" unrelated
  tests.
- Foil-aware P&L and `unpriced_card_count` semantics were fully covered by
  targeted unit tests from the task that introduced them (T03) — no gaps
  found later.

## What to avoid
- Letting an entire feature (10 tasks, 55 files) sit uncommitted on `main`
  through all 4 Waves. `CLAUDE.md` requires feature work on `homol`; nobody
  in the pipeline (Architect → Developer → TechLead → QA) stopped to commit
  to the correct branch, so the Gitflow violation persisted from Wave 0
  through QA. This should be caught at Wave 0 setup, not left as a
  "confirm with user" note in every Wave summary.

## Patterns to repeat
- Sharded brief + wave-summary carry-forward reading discipline: QA validated
  all 7 global ACs using only `F124-README.md` + task/wave summaries + direct
  test-file inspection, without needing to open the full PRD/ADR/brief.
- Verifying "pre-existing failure" claims independently (not just trusting
  the Developer's summary) via `git stash` — cheap, and confirms the claim
  before signing off a PASSED verdict.

## Propagated to learnings
- memory/agent-learnings/architect.md — Wave 0 setup should include an
  explicit "confirm/create the correct branch" step when CLAUDE.md pins
  feature work to a non-default branch (e.g. `homol`), not just a note in
  the manifest.
- memory/agent-learnings/qa.md — When a Developer/TechLead summary claims
  test failures are "pre-existing," verify with `git stash` + re-run before
  accepting it in the QA report.
