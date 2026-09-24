# Retrospective — F174

## What worked
- Isolating the new query surface in a **new** module
  (`src/marketplace/trade_queries.py`) instead of editing
  `repository.py` avoided any conflict with the parallel F171–F179 batch
  and made the new code trivially testable in isolation (100% coverage,
  31 focused tests).
- Additive, backward-compatible endpoint design (`sort_by`/`sort_dir`
  optional with defaults matching current behavior, whitelist + regex
  `Query(...)` validation → 422 on invalid input) meant zero changes were
  needed to existing callers or their tests.
- Extracting `CardFilterBar` and moving only the sticky-bar JSX into it
  (not MyCollection's state/URL logic) delivered a truly shared
  component with a verifiable, narrow diff — TechLead could confirm
  byte-for-byte that `MyCollection.tsx`'s only pre-existing failure was
  unchanged before/after.
- The fix for the Wave 1 regression (TradeCard rendering translated text
  where a raw status string used to be) added a `data-status` attribute
  alongside the translated label rather than reverting the i18n change or
  leaving the legacy test broken — a minimal, targeted fix.

## What to avoid
- Validating a "no new failing test file" gate by **count** alone. The
  Wave 1/2 summaries reported 13 failing files before and after and
  concluded "no regression," but a flaky file (`Layout.test.tsx`) flipped
  from failing to passing in the same run that `TradeCard.test.tsx` broke,
  masking a real regression until the TechLead diffed file **names**
  against a fresh pre-feature worktree baseline.
- Assuming a file-level "no new failures" gate is sufficient. T10's
  `MyTrades.tsx` rewrite left the already-failing legacy
  `tests/pages/MyTrades.test.tsx` with 2 additional failing assertions
  inside it (3 total vs. 1 at baseline) — invisible to a file-name diff,
  a real coverage regression that shipped anyway because no task owned
  that legacy file.
- Relying on `pytest` from `$PATH` in this sandbox: it resolves to a
  `uv`-managed tool install without `pytest-cov`, so it errors on the
  project's `--cov` addopts. `python3 -m pytest` resolves correctly.

## Patterns to repeat
- New query/service module instead of touching a shared, high-traffic
  file (`repository.py`) when working inside a parallel batch — enables
  independent testing and avoids merge/regression risk with sibling
  features (F171–F179).
- When a component starts rendering translated text where a raw value
  used to be, add a `data-*` attribute carrying the raw value so
  language-independent assertions don't couple to i18n copy.
- Diff **failing test file names** (not counts) against a fresh worktree
  built at the pre-feature commit whenever an AC defines a "no new
  failures" gate — for both frontend and backend suites.

## Propagated to learnings
- `memory/agent-learnings/developer.md` — data-status pattern for i18n
  text changes; new-module-over-shared-file pattern; MyTrades legacy-test
  spot-check reminder.
- `memory/agent-learnings/techlead.md` — already carries the file-name
  diff lesson from the prior review; not duplicated here.
- `memory/agent-learnings/qa.md` — appended: when an AC7-style gate is
  file-level, also spot-check whether an already-failing legacy file
  gained additional failing tests within it; use `python3 -m pytest` not
  bare `pytest` in this sandbox; full backend suite in this sandbox has
  ~109 pre-existing/environmental failures (Liga/MYP/Scryfall network
  egress blocked + a pre-existing currency-fallback regression) unrelated
  to any single feature — confirm via a pre-feature worktree diff rather
  than treating a nonzero full-suite failure count as a blocker.
