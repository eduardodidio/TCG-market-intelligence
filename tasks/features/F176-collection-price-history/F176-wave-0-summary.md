# F176 — Wave 0 summary

**Status:** completed
**Tasks:** F176-T01
**Generated:** 2026-09-24T14:30:00Z (approx, from checkpoint/log timestamps)

## Files touched
- `scripts/diagnose_collection_history.py` (T01: read-only diagnosis script, per-entry + `--json`, 493 lines)
- `scripts/diagnose_collection_history_neon.sql` (T01: 6 read-only SELECTs for user to run against Neon, `BEGIN ... READ ONLY ... ROLLBACK`)
- `tests/scripts/test_diagnose_collection_history.py` (T01: 22 tests, 97% coverage of the script)
- `tasks/features/F176-collection-price-history/diagnosis.md` (T01: H1–H6 findings + post-merge drift + Neon instructions, 176 lines)
- `tasks/features/F176-collection-price-history/F176-T01.md` (status update, unstaged)
- `didio.config.json` (unstaged, minor)

## Decisions
- H1–H6 all **confirmed** with numbers from a SQLite/Postgres fixture (local DB and Neon are both empty/unreachable in this environment — no `.env`/`DATABASE_URL`). Plan's root-cause hypothesis (key resolver + merge) stands unchanged.
- Post-merge drift check (G-D-20260924-004): `collection.py`'s `get_collection_history`/`get_entry_metrics` are untouched by the F171/F175/F178 merge (`2b87481`); only line numbers shifted. **No re-plan needed.**
- New findings to fold into ADR 0017 (T02), out of scope for F176 itself:
  1. Liga sweep writes `mid` but collection refresh/scan write `low→mid→high` into the *same* `liga_{id}` key → serrated series even after per-day merge (follow-up, not fixed here).
  2. `backfill_snapshots` can contaminate the wrong foil/normal variant because it partitions by `external_id` alone.
  3. `/metrics` has the identical H1/H2/H4/H5 defect as `/history` (already covered by T08).
  4. `get_all_latest_prices` ignores `source`, so `daily_snapshot` carry-forward can blend `myp`/`jsonld_snapshot` — acceptable, resolver already gives `daily_snapshot` lowest priority (9).
- F175 precedent confirmed: `trending_queries.parse_direct_card_id` already unions `source_cards` with direct `liga_{id}`/`manual_{id}` keys (excluding `_foil`) for market trending — same key convention T03's resolver should follow. ADR 0017 should cite it.

## Notes for next Wave
- **AC1/Neon evidence is pending-user**: `diagnosis.md` numbers come from a fixture (local DB and Neon both unreachable here). Wave 1+ devs must not treat diagnosis.md's specific counts as production-verified; the user still needs to run `scripts/diagnose_collection_history_neon.sql` / the Python script against Neon per Governance amendment 3.
- Every Wave 1–4 developer must read the "Post-merge drift" section (§4) of `diagnosis.md` before editing `collection.py` or `trending_queries.py`.
- T05 (snapshot/backfill) must use a distinct `source` marker (e.g. `daily_snapshot_backfill`) per Governance amendment 5, and must treat `observed_at < date(created_at)` as the backfill-detection heuristic already used in the diagnosis.
- T03's resolver: normal-variant key set = `source_cards ∪ liga_{id} ∪ manual_{id}` (no `_foil`); foil-variant key set = `liga_{id}_foil` (+ its own snapshots/manual), never mixing with the normal `liga_{id}`.
- Working branch confirmed as `claude/stoic-mccarthy-nv2690` (not `main`), based on `54411cb`.
