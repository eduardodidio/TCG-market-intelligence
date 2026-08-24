# Tech Lead Review -- F55 Orphan Card Auto-Fix

**Reviewer:** Tech Lead
**Date:** 2026-08-24
**Test suite:** 1728 passed, 91.45% coverage

---

## Verdict: APPROVED

The feature is well-scoped, minimal, and solves a real data gap. Both tasks
are correctly implemented with adequate test coverage. One piece of dead code
should be cleaned up (non-blocking).

---

## Findings Per File

### 1. `src/collection/matcher.py` -- Matcher best-effort logic

**Status:** Clean

- The two new best-effort branches (lines 156-171 for multiple name+set,
  lines 183-198 for multiple name-only) are correctly positioned in the
  priority chain: SKU > name_set (single) > name_set (multi, best_effort) >
  name_only (single) > name_only (multi, best_effort) > unmatched.
- structlog logging is appropriate and auditable -- logs picked ID and
  candidate count.
- The docstring (lines 43-57) was updated to document the new priority level
  4 (Best-effort). Good.
- The `MatchResult.status` docstring (line 33) now says `"matched" | "unmatched"`
  which is accurate -- `"ambiguous"` is no longer a possible value.
- Adding structlog to a previously-pure module is acceptable since it is
  already a project dependency and only adds observability.

No issues.

### 2. `src/api/routers/collection.py` -- Refresh auto-canonize (lines 726-790)

**Status:** Clean, one minor observation

- The auto-canonize block correctly mirrors the pattern from `canonize_card()`.
- EN-first, PT-fallback search is implemented correctly (lines 736-739).
- Exception handling is solid: HTTPException re-raised, generic exceptions
  caught and wrapped in 422 with descriptive message, provider closed in
  `finally` block.
- The `get_card_details returns None` edge case is handled correctly --
  re-fetches source cards and raises 422 if still empty.
- The two-provider pattern (one for canonize, one for price fetch) is slightly
  wasteful but correct and matches the existing code structure. Refactoring
  to share a provider would add complexity for marginal benefit -- acceptable
  as-is.

**Observation (non-blocking):** The inline imports (lines 728-730) inside the
`if not myp_sources:` block are fine for avoiding circular imports, but
`SourceCard` is imported from `src.domain.models` which is already used
elsewhere in this file. Could be moved to the top-level imports, though this
is a style preference, not a bug.

### 3. `src/collectors/match_report.py` -- Best-effort as ambiguous counter

**Status:** Clean

- Line 141-142: `best_effort` confidence is routed to `summary.ambiguous += 1`.
  This is a reasonable semantic choice -- from the match report's perspective,
  best-effort picks are "ambiguous" matches that we now resolve optimistically.
  The report label "Ambiguous" still conveys "multiple candidates existed."
- The `matched_total` property (line 38) correctly excludes best-effort/ambiguous
  from the high-confidence match count. This is the right accounting: you can
  see how many are confidently matched vs. best-effort.

No issues.

### 4. `tests/collection/test_matcher.py` -- Updated + new tests

**Status:** Excellent coverage

- All 4 existing ambiguous tests correctly updated to assert
  `status="matched"`, `confidence="best_effort"`, `myp_result is results[0]`.
- New `TestBestEffortMatch` class (lines 725-892) covers 7 scenarios:
  first-candidate pick, candidates preservation, no override of sku_exact,
  no override of name_set, no override of name_only, multiple name+set
  matches. This is thorough.
- Test naming is clear and descriptive.

No issues.

### 5. `tests/api/test_refresh_autocanonize.py` -- New test file

**Status:** Excellent coverage

- 8 tests covering: happy path, match failure, provider error, existing source
  (skip auto-canonize), no card_id, PT fallback, full flow with price fetch,
  get_details returns None.
- Mock setup is well-structured with helper functions. The `side_effect` lists
  for `get_source_cards_for_card` correctly model the state transitions
  (empty -> populated after canonize).
- Provider close assertions verify resource cleanup in all paths.

No issues.

### 6. `tests/collectors/test_sync_collection.py` -- Updated test

**Status:** Clean

- `test_ambiguous_card_not_stored` correctly renamed to
  `test_best_effort_card_is_stored` (line 568) and assertions flipped: now
  expects `matched == 1`, `ambiguous == 0`, and verifies repo writes happen.
- `test_summary_counts_accuracy` (line 413) updated: card 4 now matched via
  best_effort, `summary.ambiguous == 0`, `summary.matched == 3`.

No issues.

### 7. `tests/collectors/test_match_report.py` -- Ambiguous counted test

**Status:** Clean

- `test_ambiguous_counted` (line 277) still passes because match_report.py
  routes `best_effort` confidence to `summary.ambiguous`. The test name and
  semantics remain correct for the report's perspective.

No issues.

---

## Concerns

### Dead code in `src/collectors/sync_collection.py` (LOW severity)

Lines 290-308 handle `match_result.status == "ambiguous"`, but the matcher
now never returns that status. This branch is dead code. It is harmless
(unreachable), but should be removed in a follow-up cleanup to avoid
confusion.

The test `test_summary_counts_accuracy` already asserts `summary.ambiguous == 0`,
confirming this branch is never hit.

**Recommendation:** Remove the dead `"ambiguous"` branch in sync_collection.py
in the next cleanup pass. Also update the `SyncResult.status` type comment in
`src/domain/models.py` (line 241) to remove `"ambiguous"` from the union.

### Semantic ambiguity in match_report.py accounting (INFORMATIONAL)

The match report routes `best_effort` to the `ambiguous` counter, which means
`matched_total` (sku + name_set + name_only) does NOT include best-effort
matches. This is intentional and documented, but users of `format_report()`
should understand that "Ambiguous" now means "matched with best-effort" rather
than "could not match." The report text could be clarified in a future pass.

---

## Summary

| Area | Assessment |
|------|-----------|
| Architecture | Minimal, well-structured, no over-engineering |
| Tests | 15+ new/updated tests, edge cases covered |
| Code quality | Clean naming, good logging, proper error handling |
| Regressions | None detected (dead code is harmless) |
| Security | No new attack surface introduced |

Both tasks deliver exactly what was planned with no scope creep. The matcher
change is backward-compatible (downstream consumers check `status == "matched"`
which is unchanged), and the refresh auto-canonize gracefully degrades on
failure. Good work.

---

DIDIO_DONE: techlead F55
