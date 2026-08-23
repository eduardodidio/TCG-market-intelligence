# Developer Learnings

(QA appends to this file at the end of every feature retrospective.
Each entry is a lesson that generalizes beyond a single bug.)

## F16 -- Explore Cards Sorting (2026-08-21)

- **Name tests to reflect actual behavior, not plan expectations.** The developer correctly named `test_null_name_en_sorts_to_beginning_asc` to match the real behavior (NULL coalesces to '' = sorts first), even though the test plan said "sorts last." This is the right approach -- test names are documentation. When the plan is wrong, the test name should document reality.
- **Validate URL-sourced state on the frontend.** The `MyCollection` page reads `sort` from URL search params and passes it directly to the API. If the URL contains an invalid sort value (e.g., `?sort=invalid`), the API returns 422 and the user sees an error. Adding a guard like `COLLECTION_SORT_OPTIONS.some(o => o.sortBy === urlSort) ? urlSort : "name"` would prevent this edge case.

## F01 -- MYP Cards Backfill (2026-08-18)

- **Use `curl_cffi` with `impersonate="chrome"` for Cloudflare-protected sites.** `httpx` and `requests` get 403 from MYP Cards. This is a hard requirement -- do not attempt other HTTP libraries without testing Cloudflare bypass first.
- **Design for idempotency from day one.** The upsert pattern with unique constraints on `(external_id, source, observed_at)` ensured re-running backfill inserts 0 duplicates. Always add unique constraints before the first data load, not after.
- **Include a data validation task after any bulk data operation.** F01-T02's SQL queries (card count, observation count, date range, encoding check) caught issues that unit tests alone would not have revealed. Make this a standard pattern.

## F02 -- Reproducibility & Living Documentation (2026-08-18)

- **Verify actual filenames on disk before writing cross-links.** Three broken links shipped because the developer used assumed filenames from the task spec instead of checking what earlier waves actually created (e.g., `0002-web-stack-fastapi.md` vs `0002-web-stack-decision.md`). A quick `ls` after writing cross-links catches this class of bug.
- **For docs in the same directory, use bare filenames.** Relative paths like `./adr/` or `../CONTRIBUTING.md` are error-prone when source and target live in the same `docs/` folder. Always use `ARCHITECTURE.md`, not `./ARCHITECTURE.md`.

## F03 -- Analytics Engine (2026-08-18)

- **Move all imports to the top of the file.** Inline `from datetime import timedelta` inside function bodies (indicators.py:117, 171) works but is inconsistent with the rest of the codebase. Top-level imports are easier to audit and follow PEP 8.
- **Add explicit tests for division-by-zero guards.** The `past_price == 0` guard in `compute_momentum` is correct but untested. When writing a guard clause, immediately write the test -- it serves as documentation of intent and prevents future regressions if the guard is accidentally removed.

## F05 -- Technical Debt Cleanup (2026-08-18)

- **Run `ruff check` on every new file before declaring a task done.** F05 introduced 6 lint violations across 3 new test files (unused imports, unsorted imports, line too long). Pre-commit hooks would catch these at commit time, but running lint during development avoids rework and keeps the QA pass clean.
- **Name test methods accurately for the behavior they test.** Two test methods named `test_generic_4xx_*` actually tested 5xx status codes. Misleading names erode trust in test suites -- future readers will question whether the test is wrong or the name is wrong.
- **Remove dead code blocks from tests.** A `with patch(...) as mock_bf: pass` block in `test_backfill_with_options` does nothing and triggers an F841 lint violation. If a mock setup is not needed, delete it rather than leaving an empty block.

## F07 -- Front-end Dashboard (2026-08-18)

- **Include coverage tooling in Wave 0 scaffolding.** `@vitest/coverage-v8` was missing from devDependencies, forcing QA to install it. Always add the coverage provider alongside the test framework in the initial project setup.
- **Do not export constants that have no consumer.** `PERIOD_OPTIONS` in constants.ts was exported but never imported -- dead code that confuses future developers about project conventions. If a constant is only used locally, keep it local.
- **Do not configure features you do not use.** The `@/` path alias was configured in both tsconfig.json and vite.config.ts but no import in the codebase used it. Unused configuration signals intent without follow-through and creates confusion about project conventions.

## F08 -- Data Enrichment (2026-08-19)

- **When a test plan exists with numbered cases, implement all of them.** F08's test plan had 18 unit test cases (U-01 through U-18). The developer shipped 15, missing U-04, U-11, and U-16. QA had to fill those gaps. Treat test plan IDs as a checklist -- mark each one off as you implement it.
- **Always test default parameter values with URL assertions.** Changing a UI default (e.g., movers period from 7d to 30d) must have a corresponding test that asserts the fetch URL contains the new default. Component rendering tests alone do not catch regressions to the default value.

## F09 -- Scheduled Collection (2026-08-19)

- **Exceed the test plan with edge-case tests for status determination logic.** The boundary test (50% stale = healthy, not stale) and error-priority-over-stale test were not in the original test plan but both test non-obvious business logic. When implementing status/state-machine logic, always test the boundaries and priority ordering -- these are the most common sources of future bugs.
- **Use `data-testid` attributes for all testable frontend components.** The `FreshnessIndicator` used `data-testid="freshness-indicator"` and `data-testid="freshness-dot"` which made Dashboard integration tests straightforward. This pattern avoids brittle text-based selectors and should be standard for all new components.
- **Keep optional UI elements independent of critical data flows.** The freshness indicator is fetched via a separate `useApi` call that does not contribute to the `loading` or `error` state of the dashboard. This prevents a health endpoint failure from blocking the entire dashboard. Apply this pattern to any "nice-to-have" UI element.

## F10 -- Collection-Centric Pivot (2026-08-19)
- **Extract shared helpers immediately when two modules copy the same function.** The `_row_to_entry` function was identically defined in both `match_report.py` and `sync_collection.py`. This duplication was flagged by the Tech Lead as IMPORTANT risk. When a helper is needed in a second module, extract it to a shared location on the first copy -- do not let the duplication happen.
- **API routers should never open raw database sessions.** The `collection_summary` endpoint imported `sqlalchemy` and opened a `Session(repo.engine)` directly, bypassing the Repository layer. This violates the layering pattern and makes the endpoint harder to test. All database queries should live in Repository methods.
- **Remove dead code before shipping.** `BASE_URL = "https://mypcards.com"` in `sync_collection.py` was defined but never referenced. Dead constants mislead future developers about where URL construction happens. If a variable is not used by any code path, delete it.

## F11 -- Post-F10 Operationalization (2026-08-20)

- **Use fallback chains when parsing external API responses.** The MYP search API changed field names (`id` to `idproduto`, `nome` to `nomeenproduto`). The fix uses `item.get("new_name") or item.get("old_name")` fallback chains that support both formats. This pattern is essential for any parser consuming an API you do not control -- always support at least the current and previous field name.
- **Test parser changes with inline data for the new format, not just fixture updates.** The 4 new tests in `TestParseSearchResultsNewFieldNames` use inline `json.dumps()` to construct test payloads with the new field names, while existing fixtures retain the old format. This approach validates both code paths (new and legacy) without modifying fixtures that other tests depend on. When fixing parser regressions, keep old fixtures intact and add new inline tests.

## F13 -- Collection Scans (2026-08-20)

- **Accept an optional `run_id` parameter when the caller pre-creates the tracking row.** The API router creates the `scan_runs` row before spawning the background thread so it can return the ID immediately. The `run_scan()` function must accept this pre-created ID to avoid creating a duplicate row. When designing functions that will be called from both CLI (creates its own row) and API (pre-creates), use `run_id: int | None = None` and branch on it.
- **Use `asyncio.Lock` for shared mutable counters in concurrent scan processing.** The scan orchestrator uses `asyncio.Semaphore` for request concurrency and `asyncio.Lock` for safely incrementing `cards_processed`, `cards_failed`, and `observations_saved` from concurrent tasks. Without the lock, race conditions on counter increments could produce incorrect final metrics.

## F15 -- Collection Display Fixes (2026-08-20)

- **When creating a mapping utility shared between frontend and backend, keep lookup tables identical.** The `set_code_map` module was mirrored exactly between Python and TypeScript with the same keys, values, prefix list, and regex. This 1:1 parity made review trivial and eliminated cross-layer inconsistency risks. Do not introduce language-specific optimizations that would cause the two implementations to diverge.
- **Documentation deliverables (diagrams, README) are part of Definition of Done, not follow-ups.** F15 shipped code and tests but omitted the required Mermaid diagrams and README update, both of which are mandatory per CLAUDE.md. QA had to fill these gaps. Treat documentation as a task within the feature, not as an afterthought.
- **URL-encode user-facing search URLs built with f-strings.** The `scryfall_url` in `get_collection_entry` uses `f"https://scryfall.com/search?q={scryfall_q}"` without encoding. Card names with commas, ampersands, or plus signs produce technically malformed URLs. Use `urllib.parse.quote()` for query parameters in any URL that will be rendered as a clickable link.

## P2 Market Intelligence (F32-F44, 2026-08-22)

- **When a shared caching module exists, use it instead of writing ad-hoc caches.** market.py introduced `_endpoint_cache` (a plain dict with datetime TTL) despite F44's `AggregateCache` existing with thread safety, tag invalidation, and stats. This created a dual-cache situation where scan hooks invalidate `AggregateCache` but not `_endpoint_cache`, meaning stale data can survive invalidation. When a shared cache exists, use it for all new caching needs. Do not introduce a second cache layer in a router file.
- **Pure-function modules scale perfectly across a phase.** `analytics/trending.py` (compute_trending_score, rank_trending) and `decks/valuation.py` (compute_deck_value, compute_deck_value_series, compute_deck_value_change) both followed the P1-established pattern of zero-import, zero-side-effect pure functions. Both modules were trivially testable. This pattern is now proven across 5+ modules and should be the mandatory architecture for any domain logic.
- **Cache BRL-denominated values and convert on read.** TrendingService caches raw BRL results and applies currency conversion on each request. This means one cached dataset serves BRL, USD, and PILA users. When implementing a cached service that supports multi-currency, always cache in the base currency and convert at read time -- never cache per-currency variants.
- **Downsampling long time series to a fixed max point count prevents frontend performance issues.** `compute_deck_value_series` caps output at 30 points via uniform sampling. This prevents the chart from receiving 365+ data points for yearly views. When building any time-series API, include a downsample step with a configurable max-points parameter.
- **Ship i18n keys in the same PR as the component.** P2 shipped ~85+ new i18n keys across 13 features with zero missing translations at the end. The discipline of adding keys to both `en.json` and `pt-BR.json` in the same task that creates the component eliminates the "translation sprint" anti-pattern.
- **Use `from decimal import Decimal` at the top of the file, not inline.** TrendingService has `from decimal import Decimal` inside the `_apply_currency` method (line 130). Inline imports are harder to audit and violate PEP 8. This was a P1 lesson (F03) that was not followed.

## F49 -- Auto-Canonize Collection (2026-08-22)
**What worked:** Clean service/consumer separation -- `bulk_canonize.py` is reused by API, CLI, and background task without modification. BackgroundTasks integration for post-import canonization is non-blocking and communicates status via response fields.
**What to avoid:** Calling `async def close()` from synchronous CLI code without `asyncio.run()`. The line `provider.close()` in a `finally` block looks correct but returns an unawaited coroutine when the method is async. Always wrap async cleanup in `asyncio.run()` when calling from sync context, or restructure to include cleanup inside the async function passed to `asyncio.run()`.
**Pattern to repeat:** When a service needs cleanup of an async resource from CLI (sync) context, include the cleanup inside the coroutine passed to `asyncio.run()` rather than after it. Example: make `bulk_canonize` accept an `auto_close_provider: bool` parameter, or create a wrapper coroutine that does `try/finally` with `await provider.close()`.

## F50 -- Manual Price Entry (2026-08-23)
**What worked:** Reusing `PriceObservationRow` with `source="manual"` kept the implementation simple. Auto-creation of `CardRow` for unlinked entries was a good UX decision that avoids forcing canonization before manual pricing.
**What to avoid:** Using different identifiers in computed keys across write and read paths. `f"manual_{entry_id}"` in the write method and `f"manual_{card_id}"` in the read method are silently incompatible. When two methods share a key format, extract the key derivation into a shared helper function (e.g., `def manual_external_id(card_id: int) -> str`) to make the contract explicit and impossible to diverge.
**Pattern to repeat:** For any feature that writes data via one repository method and reads it via another using a computed key, add a round-trip integration test that calls write then read. Test both methods in the same test function using the same seed data -- do not construct fixture data independently for each side.

## F51/F52/F53 -- Explore Cards Fix, Dashboard Trending Fix, Pila Easter Eggs (2026-08-23)
- **Always verify custom Tailwind classes are defined before using them.** `animate-fade-in-up` was used in GauchoDialog but never added to `tailwind.config.ts`. Tailwind silently drops unknown classes with no build error. Before using any class that is not part of the default Tailwind palette, check the config file or add the definition in the same commit.
- **Thread AbortSignal through every layer of the fetch chain.** When using a hook like `useApi` that provides a `signal`, the fetcher function must forward it: `(signal) => fetchFn(params, { signal })`. Omitting it causes the request to ignore component unmount/re-render signals, leading to stale data or silent failures that are hard to reproduce in tests.
