# QA Report -- F55 Orphan Card Auto-Fix

**QA Agent** | 2026-08-24
**Verdict: PASS**

---

## Test Results

**Command:**
```
python -m pytest tests/collection/test_matcher.py tests/api/test_refresh_autocanonize.py tests/collectors/test_match_report.py tests/collectors/test_sync_collection.py -v --tb=short
```

**Result:** 102 passed, 0 failed, 0 errors (2.17s)

| Test file | Tests | Status |
|-----------|-------|--------|
| `tests/collection/test_matcher.py` | 38 | All pass |
| `tests/api/test_refresh_autocanonize.py` | 8 | All pass |
| `tests/collectors/test_match_report.py` | 23 | All pass |
| `tests/collectors/test_sync_collection.py` | 33 | All pass |

## Linting

**Command:** `python -m ruff check src/collection/matcher.py src/api/routers/collection.py src/collectors/match_report.py`

**Result:** All checks passed (0 issues)

---

## T01 Acceptance Criteria -- Matcher Best-Effort

- [x] `match_collection_card()` never returns `status="ambiguous"` -- confirmed via grep: zero occurrences of `"ambiguous"` in `src/collection/matcher.py`
- [x] SKU-exact, name_set, and name_only priorities are unchanged -- priority chain verified in code: SKU (line 68-76) > name_set single (line 147-154) > name_set multi/best_effort (line 156-171) > name_only single (line 174-181) > name_only multi/best_effort (line 183-198) > unmatched
- [x] All existing tests pass with updated assertions for ambiguous cases -- 4 tests updated (`TestAmbiguousMatch` x2, `TestEdgeCases.test_multiple_name_set_matches_is_ambiguous`, `TestNamePtMatching.test_ambiguous_with_pt_and_en_matches`) now assert `status="matched"`, `confidence="best_effort"`, `myp_result is results[0]`
- [x] New best-effort tests pass -- `TestBestEffortMatch` class with 6 tests covering: first-candidate pick, candidates preservation, no override of sku_exact/name_set/name_only, multiple name+set matches
- [x] Best-effort matches are logged via structlog -- two `log.info("matcher_best_effort", ...)` calls at lines 158 and 185, logging entry_name, entry_set, picked_id, and candidate count

## T02 Acceptance Criteria -- Refresh Auto-Canonize

- [x] Refresh endpoint auto-canonizes orphan entries (card_id set, no MYP source) before attempting price fetch -- lines 726-790 of `collection.py`: when `not myp_sources`, runs MYP search + match + get_card_details + upsert flow
- [x] If auto-canonize fails (no match, provider error), returns 422 with descriptive message -- match failure: "No MYP source card linked and auto-match failed" (line 746); provider error: "No MYP source card linked and auto-canonize failed: {exc}" (line 787); get_details=None: "No MYP source card linked and auto-canonize failed" (line 768)
- [x] If auto-canonize succeeds, proceeds with normal price fetch flow -- after auto-canonize block, execution continues to line 792+ which creates a fresh provider and calls `fetch_current_price`
- [x] Existing refresh behavior for fully-linked cards is unchanged -- test `test_refresh_with_existing_source_skips_auto_canonize` confirms no `search_card` call when MYP source exists, normal price fetch proceeds
- [x] Existing refresh behavior for unlinked cards (card_id=None) is unchanged -- test `test_refresh_no_card_id_still_returns_422` confirms 422 "Card not linked to a price source" returned at line 722
- [x] Auto-canonize is logged via structlog -- `log.info("refresh_auto_canonized", ...)` at line 771; `log.warning("refresh_auto_canonize_failed", ...)` at line 783
- [x] All 8 new tests pass -- happy path, match failure, provider error, existing source skip, no card_id, PT fallback, full flow with price fetch, get_details=None

---

## Additional Checks

### match_report.py compatibility
- `best_effort` confidence correctly routed to `summary.ambiguous` counter (line 141-142). This is semantically reasonable: the report still distinguishes high-confidence matches (`matched_total` = sku + name_set + name_only) from best-effort picks.

### sync_collection.py dead code
- Lines 290-308 handle `match_result.status == "ambiguous"` which is now unreachable. Confirmed harmless (test `test_summary_counts_accuracy` asserts `summary.ambiguous == 0`). Noted by tech lead for follow-up cleanup.

### Edge cases covered
- PT fallback search (EN empty, PT returns results) -- tested
- get_card_details returns None (no source card created) -- tested
- Provider close in finally blocks (resource cleanup) -- asserted in all error path tests
- Two-provider pattern (canonize + price fetch) -- tested in happy path

### Potential gaps (non-blocking, informational)
- No test for the case where auto-canonize succeeds but the subsequent price fetch fails (provider.fetch_current_price raises). The existing code handles this gracefully (the price fetch has its own try/finally block), and the card still gets canonized. Low risk.
- No test for concurrent refresh requests on the same orphan entry. Not a realistic scenario given the endpoint is user-triggered and sequential.

---

## Summary

Both tasks are correctly implemented with thorough test coverage. The matcher eliminates the `"ambiguous"` status entirely, always picking a best-effort candidate when name matches exist. The refresh endpoint seamlessly auto-canonizes orphan entries before fetching prices. No regressions detected, no linting issues.

**Files reviewed:**
- `C:\Workspace\TCG-market-intelligence\src\collection\matcher.py`
- `C:\Workspace\TCG-market-intelligence\src\api\routers\collection.py`
- `C:\Workspace\TCG-market-intelligence\src\collectors\match_report.py`
- `C:\Workspace\TCG-market-intelligence\tests\collection\test_matcher.py`
- `C:\Workspace\TCG-market-intelligence\tests\api\test_refresh_autocanonize.py`
- `C:\Workspace\TCG-market-intelligence\tests\collectors\test_match_report.py`
- `C:\Workspace\TCG-market-intelligence\tests\collectors\test_sync_collection.py`

---

DIDIO_DONE: qa F55
