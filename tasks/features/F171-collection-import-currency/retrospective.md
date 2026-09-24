# Retrospective — F171

## What worked
- Detection precedence (user > column > header > symbol > number-format > origin > default) was
  implemented exactly as specified and verified top-to-bottom by both TechLead and QA — no drift
  between PRD and code.
- The "resolve currency once, at the write boundary" architecture (`to_brl` as the single
  conversion point, reused unchanged by `importer.py`, `purchases.py`, `batch_add.py`, and
  `cli/main.py`) meant QA could verify the AC5 "no rate → never store USD as BRL" invariant by
  checking one pure function plus its 4 call sites, instead of 4 independent implementations.
- File-ownership sequencing for the two shared files (`routers/collection.py`,
  `schemas/collection.py` — T09 Wave 3 → T10 Wave 4) held with zero overlap, confirmed by
  TechLead's hunk-level diff read.
- 100% line coverage was actually hit on all 4 new pure modules (`money.py`, `import_conversion.py`,
  `csv_columns.py`, `batch_parser.py`), matching the test plan's stated requirement — not just
  claimed.

## What to avoid
- `batch_add.py` re-guarded a pure function's own short-circuit ("BRL never needs a rate") behind
  a `rate_lookup is None` check one layer up, silently reintroducing a narrow version of the bug
  this feature exists to fix, for one specific untested combination (BRL price + no rate_lookup).
  Not user-reachable today, but it's exactly the kind of foot-gun this feature was meant to
  eliminate everywhere.
- QA's full-suite run surfaced 109 pre-existing backend failures (vs. the "5" the TechLead review
  had cited from an earlier wave) — the discrepancy came from sibling features (F175/F176/F178)
  landing on the branch afterward, not from re-measurement error. Whoever runs the "full suite
  green" check should re-baseline against the current HEAD, not trust a wave-N cached count.

## Patterns to repeat
- Verifying a safety-critical invariant (AC5) by grepping all call sites for the specific warning
  string (`no_rate`) rather than trusting the AC checkbox — this is fast and caught nothing wrong
  here, but it's cheap insurance against a re-implementation drift.
- Hand re-deriving the trickiest pure-function branch (`money.py`'s number-format ambiguity rules)
  against the docstring's own worked examples before signing off, instead of only trusting that
  tests pass.

## Propagated to learnings
- memory/agent-learnings/developer.md — pure-function short-circuit invariants must not be
  re-guarded by callers; call the pure function unconditionally with a no-op fallback instead.
- memory/agent-learnings/qa.md — re-baseline "pre-existing failure" counts against current HEAD
  before citing an earlier wave's number, since sibling features can land in between.
