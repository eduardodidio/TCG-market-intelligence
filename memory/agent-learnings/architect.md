# Architect Learnings

(QA appends to this file at the end of every feature retrospective.
Each entry is a lesson that generalizes beyond a single bug.)

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
