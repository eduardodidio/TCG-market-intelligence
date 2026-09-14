# F124 — Wave 3 summary

**Status:** completed
**Tasks:** F124-T10
**Generated:** 2026-09-13T00:00:00Z (approximate; work is uncommitted on `main`, no per-Wave commit markers found)

## Files touched
- `docs/diagrams/F124-architecture.mmd` (T10: new — component/data-flow diagram, adjusted from stub after grep-verifying real components/endpoints; notes `DashboardInvestmentSummary`/`PortfolioDashboard` call `GET /collection/portfolio-summary` directly, `Dashboard.tsx` keeps its own `GET /collection/summary` call)
- `docs/diagrams/F124-journey.mmd` (T10: new — BPMN-style user journey for paid-price edit, dashboard view, Liga link click)
- `README.md` (T10: added `### F124 -- Collection Valuation Panel & Liga Link Fix (2026-09-13)` section — grid paid-price quick edit, list/detail acquisition fields, P&L semantics (priced-only, foil-aware, `unpriced_card_count`), slimmed dashboard, Liga link fetched-URL fix with ADR 0012 reference)
- `tests/collectors/test_liga_sweep.py` (T10: removed a dangling `mock_sleep` assertion in `test_provider_error_does_not_record_url` left over from a copy-paste — the only branch-unique test failure found during regression triage; fixed, not weakened)

## Decisions
- `docs/diagrams/README.md` and `docs/README.md` link only to the `diagrams/`, `prd/`, `adr/` directories (no per-feature index), so no edits needed there.
- Regression triage compared this branch (67 failed/3369 passed) against an unmodified baseline via `git stash` (80 failed/3338 passed); only one failure was unique to this branch (the `mock_sleep` leftover, fixed above). The other ~66 pre-existing failures (marketplace, decks, currency, liga_coverage, repository_api, sync_collection, error_codes, seed_users, provider_windows, cards_router history) reproduce identically on baseline and were left untouched as out of scope — many share a `FOREIGN KEY constraint failed` pattern on fresh per-test sqlite DBs, worth a separate bug ticket. `test_fetch_liga_price_prefers_low_over_mid` is also pre-existing and its assertion contradicts the `CLAUDE.md` guardrail (Liga sweep uses `mid`, not `low`) — flagged as stale rather than "fixed" here.
- New modules coverage: `src/collectors/liga_url_recorder.py` 100%, `src/providers/liga/urls.py` 91% (both meet the ≥90% AC).
- Frontend: `npm test` green (201 files / 1958 tests); one pre-existing jsdom `window.scrollTo` warning in `MyCollectionSort.test.tsx` (reproduces on baseline, not an assertion failure). `npm run build` and `ruff check src/` both clean.

## Notes for next Wave
- This was the final Wave (F124-README lists only Waves 0–3); no Wave 4 exists.
- Nothing from F124 (Waves 0–3) is committed yet — `git status` still shows all touched files as modified/untracked on `main`. Confirm commit/PR strategy with the user before considering F124 shipped; per `CLAUDE.md` Gitflow, feature work belongs on `homol` and only promotes to `main` with explicit user confirmation, but the current branch is `main`.
- The pre-existing failing-test cluster (FK constraint failures, stale `mid`/`low` assertion) identified during T10's regression triage is unrelated to F124 and should be tracked as a separate bug/ticket.
