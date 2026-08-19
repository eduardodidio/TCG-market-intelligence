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
