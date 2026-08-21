# TechLead Learnings

(QA appends to this file at the end of every feature retrospective.
Each entry is a lesson that generalizes beyond a single bug.)

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
