# Agent Learnings — TEA

_Placeholder. QA acrescenta seções `## <FXX> — <YYYY-MM-DD>` aqui durante a
ceremony de retrospectiva (ver `templates/agents/prompts/qa.md`)._

## F16 -- Explore Cards Sorting (2026-08-21)

- **Verify edge case descriptions against the implementation, not assumptions.** B13 stated "NULL name sorted last in asc" but `func.coalesce(col, '')` sorts NULL-as-empty-string FIRST. B16 stated "offset takes precedence over after_id" but the code checks `after_id` first. Test plan edge case descriptions should be validated against the actual code before finalizing, not written from assumptions about how the code "should" behave.
- **Mark client-side-only edge cases (E09-E13) as requiring specific test approaches.** Edge cases like "all prices null in client-side sort" or "in-flight fetch abort" require different test setups than server-side tests. Tag them with their test layer (frontend unit, integration, manual) so developers know what kind of test to write.

## F13 — 2026-04-27

**What worked:** TEA boundary with QA is the load-bearing design decision — "do not write tests, do not replace QA" stated explicitly in the prompt prevents scope creep. The 7-section output contract tied 1:1 to `docs/F13-test-plan-spec.md` makes TEA output structurally verifiable by a smoke script without a live model run.

**What to avoid:** TEA writing actual test code (assertions, mocks, setup/teardown). That belongs to the Developer task; TEA only writes the plan (fixtures needed, harness type, perf budgets, mock rationale, test scenarios as prose). Any crossing of this line makes QA's job ambiguous.

**Pattern to repeat:** Task annotation (`**Test plan:** ver <FXX>-test-plan.md (fixtures: ...)`) at the end of TEA's run is the integration point with downstream Developer and QA agents — it makes the test plan discoverable without a directory scan. TEA must always edit task files to add this line after writing the plan.

## F09 -- Scheduled Collection (2026-08-19)

- **22 numbered test scenarios mapped cleanly to implementation.** The developer implemented all 22 scenarios and exceeded them with ~40 total tests. Numbered scenario IDs (1-22) make cross-referencing between plan and code trivial for QA. Keep this format.
- **Explicit "manual testing only" callout for shell scripts prevents false expectations.** Marking F09-T03 (cron script) as manual-only in the test plan prevented the developer from wasting time on shell script unit tests and gave QA a clear signal to inspect the script by reading rather than expecting automated coverage. When a component is inherently untestable in the project's test framework, state that explicitly in the plan rather than omitting it.
- **Mock vs real decision table was accurate and useful.** All 5 decisions (real SQLite, real TestClient, mock env vars, mock fetch, mock Date.now) were followed exactly by the developer. This table reduces ambiguity and prevents over-mocking. Continue including it in every test plan.

## F10 -- Collection-Centric Pivot (2026-08-19)
- **54 numbered scenarios with task cross-references enabled complete coverage verification.** Every test plan scenario was mapped to a specific task (F10-T01 through F10-T12) and the developer implemented all 54. QA cross-referenced each ID against actual test files and confirmed zero gaps. The numbered-ID format continues to be the most effective tool for test coverage accountability.
- **Integration test scenarios should explicitly specify what DB state to assert.** Scenarios 49-53 specified not just "sync completes" but "assert cards table has N rows, user_collection.card_id is not NULL, price_observations has data." These concrete assertions made the integration tests high-value and prevented developers from writing tests that only check the return value while ignoring DB side effects.
