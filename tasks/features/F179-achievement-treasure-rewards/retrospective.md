# Retrospective — F179

## What worked

- The Waves split (docs/backend/frontend in Wave 0, backend+CLI+frontend
  in Wave 1, integration test + shared wiring in Wave 2) kept the
  high-risk shared files (`main.py`, `Layout.tsx`, `README.md`) isolated
  to a single last-Wave task (T09), so no merge conflicts or accidental
  overlap with other in-flight features (F171–F178) occurred.
- ADR-0020 stated the exact lock-then-check operation order needed for
  idempotent crediting. When the implementation shipped with that order
  reversed, TechLead's rejection cited the ADR section directly and gave
  a line-level fix, which let the Developer ship a minimal, scoped fix
  commit (11 lines in one file) and let both TechLead and QA re-verify it
  as a fast, targeted pass instead of a full re-review.
- The fix commit paired the correction with a statement-order test
  (`TestCreditLockOrdering`) that pins the lock-before-check ordering even
  though SQLite can't reproduce the actual race — this closes the "test
  passes on SQLite, breaks on Postgres" gap for regressions, if not for
  the original discovery.

## What to avoid

- Don't trust "a `with_for_update()` call exists somewhere in the
  function" as evidence of concurrency safety. The original
  `credit_reward_in_session` had the lock call present but in the wrong
  position (check-then-lock instead of lock-then-check), and it passed
  every test because the full suite runs on SQLite, whose single-writer
  file lock masks check-then-lock TOCTOU races entirely. This shipped
  past Wave 2 and the first TechLead pass undetected until a dedicated
  ADR-diff review caught it.
- Don't accept a summary's claim that a failure is "pre-existing/
  unrelated" without one line of evidence (a `git diff` against the
  pre-feature commit, or a reproduction on that commit). This feature's
  Wave summaries got this right eventually (QA's report cites the exact
  commit diffed), but it took an explicit ask in a prior retro to make it
  routine — keep enforcing it.

## Patterns to repeat

- When an ADR specifies a precise operation order for concurrency safety,
  have the reviewer (TechLead or QA) diff the implementation against the
  ADR's stated steps line-by-line, not just check that the right API call
  is present.
- Scope a rejection-driven fix commit to exactly the statements the ADR/
  review named, plus a pinning test — this turns re-review into a direct
  verification pass instead of a full re-review, saving a round trip.
- For a Postgres-specific concurrency invariant that SQLite's test suite
  can't exercise, add a statement-order/mock-based test that at least
  catches a regression back to the wrong ordering, and say so explicitly
  in the test's docstring so future readers don't mistake it for a real
  concurrency test.

## Propagated to learnings

- memory/agent-learnings/developer.md — ADR-mandated lock ordering must
  match the ADR's stated steps exactly, not just include the right API
  call; ship a statement-order test alongside any fix to a concurrency
  ordering bug since SQLite can't reproduce the real race.
- memory/agent-learnings/techlead.md — diff concurrency-critical code
  against the ADR's stated operation order line-by-line rather than
  checking for API-call presence; SQLite-only test suites give false
  confidence for Postgres-specific races.
- memory/agent-learnings/qa.md — when validating a fix for a previously
  rejected concurrency defect, independently re-read the fixed code
  against the ADR (don't just trust the review verdict), and re-run the
  targeted test files to confirm the specific pinning test exists and
  passes.
