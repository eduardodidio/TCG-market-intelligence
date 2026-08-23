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

## F11 -- Post-F10 Operationalization (2026-08-20)

- **Validate parser field names against live API responses, not assumptions from documentation or code comments.** The `parse_search_results()` function used field names (`id`, `nome`, `slug`) that matched test fixtures but not the actual MYP API. The bug was only discovered when running the match report against the live API. For any parser, run at least one live smoke test before declaring it complete. Fixtures alone can mask field-name mismatches.
- **Upstream site changes are not code defects -- document them honestly.** F11's sync pipeline correctly linked 124 cards but collected 0 price observations because MYP changed their page structure. QA should distinguish between "code that does not work" (FAIL) and "code that works correctly but the external dependency changed" (PASS with documented blocker). The verdict should reflect the code quality, not the upstream availability.
- **Unchecked acceptance criteria checkboxes in task files are a cosmetic but distracting gap.** T03, T04, T05, and T08 had `- [ ]` checkboxes despite being status=done with all criteria verifiably met. Developers should tick these boxes when completing the task. QA should note the discrepancy but not block on it -- verify the actual artifacts rather than trusting checkboxes.

## F13 -- Collection Scans (2026-08-20)

- **Cross-reference TechLead review items against actual code as a first-priority QA step.** The TechLead flagged B1 (run_id double-creation bug) as a must-fix. QA verified the fix by tracing the `run_id` parameter through three files: the router creates it (line 79), passes it to `run_scan()` (line 89), and the orchestrator conditionally skips `create_scan_run()` when `run_id` is provided (line 48). Tracing the data flow across layers is more reliable than checking if a parameter exists in a function signature.
- **Count net-new tests against the pre-feature baseline to measure feature test investment.** F13 added 71 backend tests (786 - 715) and 36 frontend tests (228 - 192). Tracking net-new counts per feature helps identify under-tested features over time. For a feature touching 6+ new files across domain, database, collector, API, CLI, and frontend layers, 100+ net-new tests is a healthy signal.

## F15 -- Collection Display Fixes (2026-08-20)

- **Always test the boundary conditions of string-manipulation heuristics.** The prefix-stripping heuristic in `set_code_map.py` has implicit constraints (remainder must be 2-5 chars, alphanumeric). The developer tested known codes and unknown codes but did not test the boundaries (1-char remainder, 6-char remainder). QA added `test_single_char_remainder_not_stripped` and `test_long_remainder_not_stripped` to cover these edges. When a function has conditional logic on string length, always test at and around the thresholds.
- **Document URL-encoding gaps with explicit tests rather than silently fixing them.** The `scryfall_url` in the collection detail endpoint is built without `urllib.parse.quote()`. Rather than fixing it (which could change behavior), QA added a test that documents the current behavior with special characters. This makes the gap visible to future developers without risking a regression. When a MINOR issue is intentionally deferred, write a test that pins the current behavior.
- **TechLead MAJOR documentation items become QA deliverables when not addressed before review.** F15's two MAJOR review items (missing diagrams, missing README update) were both documentation gaps. QA had to create the diagrams and update the README. This is avoidable -- developers should treat CLAUDE.md documentation rules as part of the Definition of Done, not as optional follow-ups.

## F16 -- Explore Cards Sorting (2026-08-21)

- **Cross-reference test plan edge case descriptions against actual code behavior.** The test plan for B13 stated "NULL name sorted last in asc" but the implementation coalesces NULL to `""` which sorts FIRST. The developer wrote a correctly-named test (`test_null_name_en_sorts_to_beginning_asc`) documenting the actual behavior. QA should verify test plan text matches code behavior, not just that a test exists for each plan ID -- the plan document itself can be wrong.
- **Frontend URL param validation is a recurring gap.** When URL search params drive API calls, invalid param values can cause 422 errors that surprise users. Always check whether the frontend validates URL-sourced state against known-good values before sending to the API. This is especially important for sort/filter params where users can bookmark or share URLs with stale or invalid values.

## P2 Market Intelligence (F32-F44, 2026-08-22)

- **Enforce documentation gates as hard QA blocks, not soft recommendations.** P2 shipped 13 features with zero PRDs and only 10 of 26 required diagrams. CLAUDE.md mandates both. QA should have blocked each wave that was missing documentation deliverables. The cost of writing a PRD is 15 minutes; the cost of 13 missing PRDs is a documentation debt that compounds across future phases. For future phases, QA must check for PRD existence and diagram completeness as a pre-ship gate for every wave.
- **Coverage delta per phase is a meaningful metric.** P2 dropped backend coverage from 94.32% to 91.08% (-3.24pp). While still above the 70% floor, the trend signals that test investment did not fully keep pace with new code. QA should track coverage delta per phase (not just absolute number) and flag any phase that drops more than 2pp as needing targeted test backfill.
- **Verify cache invalidation flows end-to-end, not just at the component level.** P2 introduced three caching layers: `AggregateCache` (F44), `TrendingService._cache` (F36), and `_endpoint_cache` in `market.py` (F40). `ScanHookRegistry` invalidates `AggregateCache` via tags, but the other two caches are not invalidated. QA should test: "after a scan completes, does every cached endpoint return fresh data?" This requires an integration test that spans scan -> hook -> cache invalidation -> endpoint response. Component-level cache tests are necessary but not sufficient.
- **Count test files vs feature files to measure coverage breadth.** P2 delivered 33 new Python source files and 34 new TypeScript files. It also delivered 117 backend test files and 82 frontend test files total. The ratio of test files to source files (117/93 backend, 82/109 frontend) reveals that frontend test coverage breadth is lower. QA should flag when the frontend test-file-to-source ratio drops below 0.8.
- **Broad `except Exception` in routers should be reviewed for masking potential.** Eight router methods catch `Exception` broadly. For background operations (scans, sync), this is acceptable -- the alternative is crashing the process. But for synchronous endpoints like `/market/volatile` (market.py line 281), a broad catch masks connection errors, serialization bugs, and type mismatches behind a generic fallback. QA should distinguish between "catch-and-log for resilience" (acceptable) and "catch-and-fallback for convenience" (risky).
- **Stub implementations should be tracked as explicit tech debt items.** `BanImpactAnalysis` has `data_available: bool = False` and the `/banlist/impact/{card_id}` endpoint returns a stub response. This is correctly documented in the model, but QA should maintain a list of stubs so they do not become permanent. Every stub should have a corresponding backlog item.
- **When a retrospective covers a multi-feature phase, evaluate cross-feature integration, not just individual features.** P2's 13 features interact through shared services, caches, and domain models. Individual feature tests pass, but the interaction patterns (e.g., "does a new scan invalidate trending data?", "does a ban status change affect deck valuation?") are not tested. Future phases should include cross-feature integration scenarios in the QA plan.

## F49 -- Auto-Canonize Collection (2026-08-22)
**What worked:** The test plan was comprehensive (33 scenarios) and all were implemented with 61 tests. Backend-to-frontend contract alignment was verified (Pydantic vs TypeScript fields matched exactly). TechLead BLOCKING items were resolved before QA.
**What to avoid:** When a TechLead flags "provider not closed in CLI," verify whether the `close()` method is async. Calling `async def close()` from synchronous context (without `await` or `asyncio.run()`) returns an unawaited coroutine and silently leaks the resource. Always check the method signature, not just whether `close()` appears in a `finally` block.
**Pattern to repeat:** For any code path that creates an external-service provider (MypCardsProvider, HTTP clients), verify cleanup across all three consumption contexts: (1) API endpoint (async, `await provider.close()`), (2) background task (async, same), (3) CLI command (sync, needs `asyncio.run(provider.close())`). Each context has different async semantics and must be verified independently.

## F50 -- Manual Price Entry (2026-08-23)
**What worked:** TechLead caught the critical B1 bug (external_id mismatch between write and read paths) before QA. Test coverage exceeded the plan (90 tests vs 38 planned). Price source priority logic was well-tested at both repository and API levels.
**What to avoid:** When a feature stores data with a computed key (e.g., `f"manual_{x}"`), isolated write-side and read-side tests can both pass while the round-trip is broken. Hardcoded fixture values that happen to match each side's format mask the key mismatch. Always verify that test fixtures use the same key derivation as production code.
**Pattern to repeat:** For any feature that writes data via one repository method and reads it via another, add at least one round-trip integration test that calls the write method followed by the read method. This is the minimum viable test for key/format consistency and would have caught B1 without TechLead intervention.
