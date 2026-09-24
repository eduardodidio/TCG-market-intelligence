# Retrospective — F175

## What worked
- Test-first discipline on the frontend task (T05): the Developer ran the new regression test before touching any source, confirmed the toggle/race-condition behavior already worked, and left `TrendingSection.tsx`/`useApi.ts` untouched. Zero speculative diffs.
- T07 chose a file-backed SQLite `Repository` instead of `:memory:` for FastAPI `TestClient`-based API tests, avoiding a known class of flaky "works locally, fails under threaded test client" bugs.
- Clean layering held up under review: query logic isolated in a new `src/database/trending_queries.py` module, `repository.py` reduced to a one-method delegate, cache policy confined to `src/services/trending.py`, no leakage into the API router.
- README edit (T08, a shared high-risk file in the F171–F179 batch) was additions-only and isolated to a single dedicated task in the last Wave — no merge conflicts with sibling features.

## What to avoid
- Tech Lead review asserted "the architecture diagram accurately reflects the actual code" without diffing the regex string against the real implementation. It didn't: the diagram showed `^(?:liga|manual)_(\d+)(?:_foil)?$` (foil optionally matching) while the code is `^(?:liga|manual)_(\d+)$` (foil never matches). A diagram claim about a specific regex/algorithm detail needs to be checked against the source line, not just the high-level data-flow shape.
- AC5 (Neon query timing <12s) was written as a hard acceptance criterion but is only checkable against the real production database — no sandbox/CI path can verify it before merge. Task manifests should flag AC5-style criteria as "verify at promotion time" rather than leaving them ambiguous about when/how they get checked.

## Patterns to repeat
- "Test first, then decide if a code fix is needed" as an explicit task-file instruction (used for T05) — keeps diffs minimal and avoids unnecessary review surface.
- File-backed SQLite (not `:memory:`) for any new API-level test exercising FastAPI's `TestClient`.
- Isolating shared high-risk file edits (like `README.md`) into their own dedicated task in the last Wave of a batch, rather than letting multiple feature tasks touch it concurrently.

## Propagated to learnings
- memory/agent-learnings/techlead.md — verify specific quoted implementation details (regexes, formulas) referenced in diagrams against the actual source line, not just the diagram's overall shape, before approving "diagram matches code."
- memory/agent-learnings/architect.md — acceptance criteria that can only be verified against production infrastructure (e.g. Neon-only timing) should be marked as "verify at promotion" so QA/Tech Lead don't treat them as sandbox-blocking.
- memory/agent-learnings/developer.md — reinforced: file-backed SQLite for FastAPI TestClient tests; test-first before touching frontend source on a "fix only if a test reveals a bug" task.
