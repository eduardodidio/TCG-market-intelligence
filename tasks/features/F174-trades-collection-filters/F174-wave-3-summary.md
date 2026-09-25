# F174 — Wave 3 summary

**Status:** completed
**Tasks:** F174-T13, F174-T14
**Generated:** 2026-09-24T21:15:00Z

## Files touched
- `docs/diagrams/F174-architecture.mmd` (T13: new — shared kit, 4 pages, API clients, routers, `TradeQueries`, DB)
- `docs/diagrams/F174-journey.mmd` (T13: new — swimlanes, server/client filter split, empty-result and error/retry paths)
- `README.md` (T14: appended a 10-line `### F174 -- Trade Pages Adopt the Collection Filter Bar (2026-09-24)` note under the existing feature-delivery section, before `## Deployment`)

## Decisions
- _none_ (both tasks were purely mechanical: draw-what-shipped diagrams and an append-only README note)

## Notes for next Wave
- README.md and both diagrams are staged as uncommitted working-tree changes; the F174 feature branch (`wt/F174` or the orchestrator worktree) still needs a commit for this Wave.
- `git diff README.md` confirms the edit is append-only (no lines removed), satisfying T14's AC.
- Governance amendment G-D-20260924-005 (dedupe `cardListFilter.ts` vs any F177 equivalent) is **not yet addressed** — F177 has already merged to `homol` (see `git log`: `F177 Wave 3`, `F177 TechLead + QA`), so TechLead/QA for F174 should check whether F177 introduced an overlapping helper before final approval.
