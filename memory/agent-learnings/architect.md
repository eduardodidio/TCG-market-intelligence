# Architect Learnings

(QA appends to this file at the end of every feature retrospective.
Each entry is a lesson that generalizes beyond a single bug.)

## F16 -- Explore Cards Sorting (2026-08-21)

- **Specify NULL ordering expectations explicitly in the PRD.** F16's PRD did not specify where NULL values should appear in sorted results (first vs last). The developer chose `coalesce(name_en, '')` which puts NULLs first in ascending order. The test plan then incorrectly stated "None sorted last." Ambiguity in the PRD propagates through the entire pipeline. When a sort feature touches nullable columns, the PRD should state "NULL values sort [first|last] in ascending order."
- **Document precedence rules when introducing overlapping parameters.** F16 introduced `offset` alongside the existing `cursor`/`after_id`. The PRD said "cursor is ignored when offset is provided" but the implementation gives `after_id` precedence (which is arguably safer for backward compatibility). Either approach is valid, but the PRD should be unambiguous about which parameter wins.

## F01 -- MYP Cards Backfill (2026-08-18)

- **Start with a single small set for validation.** Using Dominaria Remastered (30 cards) as a pilot allowed catching parser, encoding, and idempotency issues before scaling to 48 pages of editions. Always scope Wave 0 to a single representative sample.
- **Separate parsing from network I/O in the architecture.** Putting parsers in `src/parsers/` and providers in `src/providers/` made unit testing possible without network calls (27 tests, no mocking of HTTP). This separation should be maintained for any new data source.

## F02 -- Reproducibility & Living Documentation (2026-08-18)

- **Docs-heavy features need a cross-link verification task.** F02 shipped 3 broken links because no task explicitly required validating cross-references. For any feature delivering 5+ interconnected docs, include a dedicated task (or acceptance criterion) for link verification.

## F03 -- Analytics Engine (2026-08-18)

- **Pure-function modules pay off in testability.** Separating `src/analytics/` from all DB imports made it trivial to write 46 unit tests with zero mocking of database internals. When designing new modules, default to pure functions that receive data as arguments rather than fetching it themselves.
- **Wave structure worked well for dependency ordering.** Wave 0 (domain models + repository queries) before Wave 1 (analytics logic) before Wave 2 (CLI + docs) ensured each wave had stable inputs. Keep this pattern for features with layered dependencies.

## F05 -- Technical Debt Cleanup (2026-08-18)

- **Schedule tech debt features periodically to prevent coverage drift.** Between F01 and F04, coverage dropped from an implicit "good enough" to 86% with three files below 85%. A dedicated tech debt sprint (F05) brought it to 97%. Plan a debt cleanup every 3-4 features.
- **Include retroactive PRDs in the debt inventory.** F02, F03, and F04 shipped without PRDs. Listing them explicitly in the debt inventory ensured they were created. Make "PRD exists" a gate in the feature workflow to prevent this accumulation.

## F07 -- Front-end Dashboard (2026-08-18)

- **Only configure what you use in scaffolding tasks.** The `@/` path alias was configured in Wave 0 but never adopted by any developer task. Unused configuration creates ambiguity about project conventions -- either use it consistently or remove it. When planning Wave 0, list only the tooling that subsequent waves will consume.

## F09 -- Scheduled Collection (2026-08-19)

- **External cron + script is the right initial automation pattern.** Choosing an external scheduler (crontab / Task Scheduler) over an in-process scheduler (APScheduler) avoided a new dependency, kept the API process stateless, and made the trigger mechanism OS-native and debuggable. This is the correct choice for single-user/local deployments. Reserve in-process scheduling for when a deployment target (Docker, cloud) makes external cron impractical.
- **Separating observability from mutation endpoints pays off.** The health endpoint (GET, no auth) is independent of the collect endpoints (POST, auth required). This allowed the frontend to show freshness without needing an API key, and the cron script to do a post-update health check without additional auth setup. When designing API features, keep read-only observability endpoints separate from mutation endpoints in both routing and security.

## F10 -- Collection-Centric Pivot (2026-08-19)
- **Front-loading a read-only dry-run wave before destructive operations is the correct safety pattern.** Wave 0 (match report) produced a coverage report that the user reviews before Wave 1 (cleanup) deletes any data. This gave confidence that the sync pipeline would have acceptable match rates before committing to an irreversible operation. For any feature with destructive operations (DELETE, DROP, file removal), plan a read-only preview wave first.
- **Pure matcher modules are the gold standard for testability.** `src/collection/matcher.py` has zero dependencies on DB, network, or framework -- only domain models. This produced 26 tests with 100% coverage and zero mocking. Future features with matching, scoring, or classification logic should follow this exact pattern: pure functions that take domain objects in and return domain objects out.

## F11 -- Post-F10 Operationalization (2026-08-20)

- **Operational features should include a "live validation" wave before the full run.** F11's match-report wave (dry-run) discovered a parser bug before the sync wave committed any data. Without this sequencing, the sync would have silently matched 0 cards and the bug would have been harder to diagnose. For any feature that runs existing pipelines against production data, plan a read-only validation step first.
- **Plan for upstream API changes as a first-class risk.** MYP changed both field names and page structure between F10 and F11 (days apart). Architect should include "parser resilience" tasks (fallback chains, field name mapping tables) when the feature depends on external scraped APIs. Assume the API will change.

## F13 -- Collection Scans (2026-08-20)

- **Reuse existing collector logic rather than rebuilding.** F13's scan orchestrator wraps the same `fetch_current_price` + `insert_price_observations` pattern from F12's snapshot collector into a generic, filterable framework. The architecture correctly avoided duplicating fetch/store logic and instead composed it behind a new orchestration layer. When planning features that extend existing pipelines, design the new layer as composition over the old, not replacement.
- **Pre-creating DB rows for async operations enables clean API responses.** The architecture decision to create the `scan_runs` row before launching the background thread meant the API could return a stable `scan_id` immediately. This pattern (create tracking row -> return ID -> update row asynchronously) should be the standard for any background job API.

## F15 -- Collection Display Fixes (2026-08-20)

- **Static lookup + heuristic fallback is the right pattern for external code mappings.** The set code mapping utility uses a three-tier resolution (static table, regex, prefix heuristic) that handles all known codes deterministically while degrading gracefully for unknown codes. This pattern works well when the mapping space is large but partially predictable. The static table handles the known universe, and the heuristic catches new codes without requiring code changes.
- **Dedicated detail routes eliminate dead-end navigation.** Creating `/collection/:id` as a dedicated route (rather than overloading the existing `/cards/:id` route or using query params) ensured that every collection card has a guaranteed clickable destination, regardless of whether it is linked to a canonical card. When two entity types share visual similarity but differ in data availability, separate routes with separate pages produce a cleaner UX than conditional rendering on a shared page.
