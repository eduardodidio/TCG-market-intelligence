# F176 — Wave 1 summary

**Status:** completed
**Tasks:** F176-T02, F176-T03, F176-T04, F176-T05
**Generated:** 2026-09-24T00:00:00Z (approximate — no per-wave timestamp source found; based on file mtimes/checkpoints)

## Files touched
- `docs/adr/0017-collection-price-history-keys.md` (N) (T02: root-cause + key-resolution contract, Status: Accepted)
- `docs/diagrams/F176-architecture.mmd` (N), `docs/diagrams/F176-journey.mmd` (N) (T02)
- `src/collection/price_history_keys.py` (N) (T03: `resolve_history_keys`, `merge_series_by_priority`, `SOURCE_PRIORITY`)
- `tests/collection/test_price_history_keys.py` (N, 300 lines) (T03)
- `src/api/schemas/collection.py`, `src/api/schemas/cards.py` (T04: added `PriceHistoryMeta`, `PriceObservation.source`, `currency_source` — additive only)
- `tests/api/test_price_history_schemas.py` (N, 120 lines) (T04)
- `src/collectors/price_snapshot.py` (T05: carry-forward capped by `MAX_CARRY_FORWARD_DAYS`, new `BACKFILL_SOURCE = "daily_snapshot_backfill"` marker, `backfill_snapshots(dry_run=...)`, +284/-96 lines net)
- `tests/test_price_snapshot.py`, `tests/integration/test_snapshot_pipeline.py`, `tests/collectors/test_price_snapshot_forward_fill.py` (N, 505 lines) (T05)

## Decisions
- T05 implements the Saruman amendment #5 marker exactly as specified: backfilled rows use `source="daily_snapshot_backfill"`, distinct from real `daily_snapshot` rows, so they can be identified/deleted separately.
- `price_history_keys.py` deliberately duplicates `SOURCE_PRIORITY` from `src/database/repository.py` (comment flags it as "keep in sync") rather than importing it, to keep the module free of DB/framework dependencies for pure unit testing.
- ADR 0017 is filed at the reserved number 0017 (confirmed via `ls docs/adr/`, no collision with 0012–0019 range used by other batch features).

## Notes for next Wave
- Wave 2 (T06 snapshot-after-sweep, T07 `build_history` service, T10 frontend) can rely on `price_history_keys.resolve_history_keys`/`merge_series_by_priority` and the new `PriceHistoryMeta`/`PriceObservation.source` schema fields — both are committed to disk but **not yet git-committed** (working tree has uncommitted changes for all Wave 1 files as of this summary).
- No git commit exists yet for Wave 1 work — everything is still in the working tree (`git status --short` shows all T02–T05 files as modified/untracked). Whoever runs Wave 2 should commit Wave 1 first or confirm the orchestrator handles it.
- Read the "Post-merge drift" section of `diagnosis.md` (per governance amendment #1) before editing — not verified in this summary pass whether root cause diverged from plan; ADR 0017 Decision section (line 68) should be checked against the H1–H6 hypothesis table (line 44) before Wave 2 starts.
