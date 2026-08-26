# TechLead Learnings

(QA appends to this file at the end of every feature retrospective.
Each entry is a lesson that generalizes beyond a single bug.)

## F16 -- Explore Cards Sorting (2026-08-21)

- **Check for input validation gaps at the frontend-to-API boundary.** TechLead review verified API-level validation (regex patterns, ge=0) but did not flag that the frontend passes URL params to the API without validation. The API correctly rejects invalid values with 422, but the user experience is poor (error banner). A TechLead review should verify that each layer validates its inputs independently -- the frontend should not rely solely on the API for input sanitization of user-facing state like URL params.

## F01 -- MYP Cards Backfill (2026-08-18)

- **Enforce lint cleanliness from the first feature.** F01 left 10 lint errors (9 unused imports, 1 line-length) that were only discovered during F02. Adding `ruff check` to the dev workflow from project setup prevents accumulation of technical debt.
- **Require QA report and retrospective for every feature, even the first.** F01 shipped without a QA report or TechLead review, so no learnings were captured. The framework ceremonies must be enforced from feature #1.

## F02 -- Reproducibility & Living Documentation (2026-08-18)

- **Spot-check relative link paths in docs-heavy features.** Three broken cross-links shipped in F02 because link hrefs didn't match actual filenames or used wrong relative paths. In any feature that delivers multiple docs, verify every cross-link resolves to a real file.
- **Verify ADR index tables are updated when new ADRs are added.** ARCHITECTURE.md's ADR table only listed ADR-0001 after ADR-0002 was delivered in a later wave. When tasks span multiple waves, check that index tables reflect all delivered artifacts.

## F03 -- Analytics Engine (2026-08-18)

- **Document statistical methodology choices in docstrings.** The choice of population std dev (`/ n`) vs. sample std dev (`/ (n-1)`) is defensible but not documented. For domain-specific decisions like this, a one-line note in the docstring prevents future confusion.
- **Flag missing dev tooling early.** `pytest-cov` was not in dev dependencies, so automated branch coverage could not be measured during review. Add coverage tooling to `pyproject.toml` dev deps as part of project setup (Wave 0) rather than discovering the gap at review time.

## F05 -- Technical Debt Cleanup (2026-08-18)

- **Verify lint cleanliness of new test files during review.** The TechLead review approved F05 but missed 6 ruff violations in the new test files. Add "run `ruff check` on all new/modified files" as a checklist item in every TechLead review.
- **Cross-check test method names against the behavior they exercise.** Two tests named `test_generic_4xx_*` actually tested HTTP 500 responses. Catching naming mismatches during review prevents confusion for future developers reading the test suite.

## F07 -- Front-end Dashboard (2026-08-18)

- **Minor notes in reviews become QA quick-wins.** Three of four minor notes (unused path alias, dead export, version label mismatch) were fixed by QA in under 5 minutes. Tagging fixable items as MINOR with clear descriptions makes them actionable for the next agent in the pipeline.
- **Verify coverage tooling is functional, not just installed.** The test framework (Vitest) was configured but `@vitest/coverage-v8` was missing from devDependencies. During review, attempt to run coverage and flag if the provider is absent -- this is a one-line fix in Wave 0 but becomes QA friction later.

## F10 -- Collection-Centric Pivot (2026-08-19)
- **Layering violations in API routers should be flagged as IMPORTANT, not MINOR.** The `collection_summary` endpoint bypassed Repository with raw SQLAlchemy session access. This was correctly flagged as IMPORTANT because it sets a bad precedent -- once one endpoint breaks the pattern, future developers will copy it. Any direct database access from the API layer should be caught and escalated during review.
- **Integration tests with real DB + mocked provider are the highest-value test tier for pipeline features.** The 9 integration tests in `test_sync_integration.py` verified actual DB state (card rows created, collection entries linked, no duplicate observations on resume) that unit tests with fully mocked Repository cannot catch. For any feature with a multi-step data pipeline, require at least one integration test tier that exercises real DB writes.

## F13 -- Collection Scans (2026-08-20)

- **Catch the double-creation bug pattern in background job APIs.** When a router pre-creates a DB row and then spawns a background worker, the worker must receive the pre-created ID. Without this, the worker creates a second row and the API-returned ID points to an orphan. This was caught as B1 in the TechLead review. Always check: does the background function accept and reuse the tracking ID that the router created?
- **Verify enum values match across all layers during review.** Frontend scan type values ("set", "format") must match backend `ScanType` enum values exactly. A mismatch (e.g., "by_set" vs "set") would cause silent 422 errors. Add cross-layer enum consistency as a standard review checklist item for any feature that introduces new enum types used by both frontend and backend.

## F15 -- Collection Display Fixes (2026-08-20)

- **Escalate missing documentation deliverables to MAJOR in review.** The review correctly flagged missing diagrams and README update as MAJOR items, which ensured QA addressed them. Documentation gates in CLAUDE.md exist for a reason -- downgrading them to MINOR would allow documentation debt to accumulate silently across features.
- **When reviewing string-building code for URLs, always check for URL encoding.** The `scryfall_url` f-string in `get_collection_entry` was flagged as a MINOR URL-encoding concern. This is the right severity -- Scryfall tolerates unencoded queries -- but the pattern should be caught consistently. Add "URL parameters are encoded" as a standard review checklist item for any endpoint that constructs external URLs.

## P2 Market Intelligence (F32-F44, 2026-08-22)

- **Catch dual-caching patterns during review.** market.py has its own `_endpoint_cache` (plain dict, 30-min TTL) sitting on top of `MarketDataService`'s `AggregateCache` and `TrendingService`'s internal cache. This creates a three-layer cache where invalidation at one layer does not propagate to the others. The `ScanHookRegistry` invalidates `AggregateCache` tags, but `_endpoint_cache` and `TrendingService._cache` remain stale. During review, when a new caching mechanism is introduced, verify it integrates with the existing invalidation flow. If it does not, flag it as MAJOR.
- **Singleton management should be centralized in one module.** P2 has three different singleton patterns: (1) `deps.py` uses function-attribute caching (`hasattr(_create_market_data_service, "_instance")`), (2) `market.py` uses `global _trending_service`, (3) `scan_hooks.py` uses module-level `default_registry = ScanHookRegistry()`. Having three patterns for the same concern makes review harder and introduces inconsistency risk. Consolidate all singletons into `deps.py` or a dedicated `lifecycle.py`.
- **Flag router files exceeding 300 lines as candidates for splitting.** `collection.py` reached 814 lines during P2 (handling list, summary, sync, detail, refresh, banned, history, metrics). This file should have been flagged for splitting when it crossed the 400-line threshold. Sub-routers like `collection_analytics.py` (metrics, history) and `collection_bans.py` (banned) would improve navigation and testability.
- **Verify that services in `src/services/` follow a consistent pattern.** `ban_analyzer.py` is a module of pure functions that take `repo` as a parameter, while `TrendingService` and `MarketDataService` are stateful classes with internal caches. Both are valid patterns, but the directory name `services/` implies stateful classes. Either (a) move pure-function modules to `src/analytics/` where `trending.py` already lives, or (b) document in a README that `services/` allows both patterns. Undocumented mixed patterns cause confusion.
- **The facade pattern (MarketDataService) is the correct abstraction for combining cache + currency + repo.** Review should push for all new endpoints to use the facade rather than importing repo + converter + cache individually. The `/market/summary` endpoint correctly uses the service for basic stats but then bypasses it by calling `repo.get_movers(days=days, limit=9999)` directly (market.py line 192). This partial adoption of the facade defeats its purpose.
- **Domain model files should be split before they exceed 500 lines.** `src/domain/models.py` reached 579 lines with P2 additions (TrendingScore, DeckValuation, DeckValuePoint, DeckValueChange, BanImpactAnalysis, ScheduledScan). A split into `models/market.py`, `models/bans.py`, `models/decks.py` would improve discoverability without any import changes if `models/__init__.py` re-exports everything.

## F54 -- Trending List Layout + Gaucho Orthography + Ticker Animation (2026-08-23)

- **Validate CSS animation speed with concrete examples in the review.** The ticker speed formula change from `max(20, len*80/60)` to `max(10, len*60/60)` was validated by computing actual durations for typical item counts (5 items = 10s, 20 items = 20s). Always include worked examples with real numbers when reviewing animation/timing formula changes -- abstract formulas are hard to evaluate for visual correctness.
- **Non-blocking observations should be tracked as backlog items, not just review comments.** The loading skeleton mismatch (card skeletons shown during list-variant loading) and the DRY currency formatting opportunity were correctly flagged as non-blocking but have no tracking mechanism. Consider maintaining a lightweight backlog file for non-blocking review observations so they are not lost.

## F65 -- Credit Token System (2026-08-26)

- **Always diff backend response keys against frontend TypeScript interfaces during review.** B1 (claim-bonus field mismatch) was caught because the TechLead compared the router's return dict keys against the frontend interface fields. This should be a standard checklist item for any feature that adds new API endpoints consumed by the frontend. TypeScript does not fail at build time on missing JSON fields -- the only defense is manual cross-referencing during review.
- **When reviewing credit/deduction logic, verify all provider paths have symmetric guards.** B2 (MYP deducting on no-price) was found because the TechLead compared the Liga refresh path (which had an early-return guard) against the MYP refresh path (which did not). When multiple code paths perform the same logical operation (deduct credits after provider success), review each path side by side for guard symmetry.
