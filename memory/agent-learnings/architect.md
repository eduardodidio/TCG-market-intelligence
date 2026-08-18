# Architect Learnings

(QA appends to this file at the end of every feature retrospective.
Each entry is a lesson that generalizes beyond a single bug.)

## F03 -- Analytics Engine (2026-08-18)

- **Pure-function modules pay off in testability.** Separating `src/analytics/` from all DB imports made it trivial to write 46 unit tests with zero mocking of database internals. When designing new modules, default to pure functions that receive data as arguments rather than fetching it themselves.
- **Wave structure worked well for dependency ordering.** Wave 0 (domain models + repository queries) before Wave 1 (analytics logic) before Wave 2 (CLI + docs) ensured each wave had stable inputs. Keep this pattern for features with layered dependencies.
