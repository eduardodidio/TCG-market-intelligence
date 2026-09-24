# Retrospective — F177

## What worked
- ADR 0018's compact-storage decision (banned/restricted + owned + previously-existing
  rows only, `scryfall_baseline` for first-run history) was documented precisely enough
  in Wave 0 that Wave 2's implementation (`_classify`/`should_store`) matched it exactly
  with no rework — a clean handoff from architecture doc to code.
- Pure new modules (`legality_writer.py`, `banlist_queries.py`) with zero edits to
  `models.py`/`repository.py` kept Wave 1 fully parallel-safe and let Wave 2 build on
  them without coordination overhead.
- T04's forward-compat choice (local `ModalEntry` type reading fields `BanListEntry`
  didn't have yet) avoided a hard Wave 1→Wave 2 dependency; by the time T08 extended
  `BanListEntry` in Wave 2, the modal's type composition absorbed it with no drift.
- TechLead re-verified claims instead of trusting summaries at face value (re-derived
  the "pre-existing Layout failure" root cause via git diff/show, re-ran the full
  backend+frontend suites rather than accepting the Wave 3 summary's word) — QA's own
  independent re-check reached the same conclusions, which is a good sign the review
  was accurate rather than rubber-stamped.

## What to avoid
- Three of ten task files (T02, T08, T10) shipped finished code+tests but left
  `Status: planned` in their headers — TechLead had to patch all three before sign-off.
  This is a recurring pattern worth fixing at the source.
- A Wave summary (Wave 3) asserted "confirmed via git stash" for a pre-existing-failure
  claim without attaching the actual diff/output, forcing TechLead to redo the
  investigation from scratch on a declared hotspot file.
- The README's global AC list (AC5) stated a simpler rule than the ADR's actual
  refined spec (`MATCH_CHECK_THRESHOLD`), which reads as a false discrepancy to anyone
  checking only the README.

## Patterns to repeat
- Batching format: docs/i18n (Wave 0) → pure new backend modules (Wave 1) → integration
  of sync/API/frontend that consumes those modules (Wave 2) → cross-cutting hotspots +
  ops/docs (Wave 3) — this ordering meant no file was touched by two waves in
  conflicting ways, and hotspots were deliberately isolated to the last wave.
- Scoping test doubles by "mock what's unreachable/expensive, hit what's real and
  load-bearing" (mock Scryfall httpx calls since the sandbox can't reach them; use a
  real temp-SQLite DB for writer/queries since dialect/ORM correctness is the point) —
  produced fast, deterministic, meaningful tests.

## Propagated to learnings
- memory/agent-learnings/developer.md — flip `Status:` to `done` as the last
  implementation step; attach diff/command evidence (not just a claim) when asserting
  a test failure is pre-existing.
- memory/agent-learnings/architect.md — when an AC in the feature README manifest is
  intentionally narrowed/qualified in the PRD/ADR, say so in the README itself
  (one-line pointer) so reviewers don't flag a false discrepancy.
- memory/agent-learnings/techlead.md — independently re-derive pre-existing-failure
  claims on declared hotspot files rather than trusting the summary; it caught a real
  gap in evidence this feature.
- memory/agent-learnings/qa.md — when a prior TechLead review already ran the full
  backend/frontend suites and cross-checked failures against touched-files, QA can
  re-verify via narrower targeted runs instead of repeating the full (17m+) suite,
  as long as results are consistent with the prior run.
