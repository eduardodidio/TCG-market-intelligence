# F168 Tech Lead Review -- Price History Densification

**Reviewer:** Tech Lead Agent
**Date:** 2026-09-21
**Verdict:** APPROVED

---

## Summary

F168 introduces a daily price snapshot mechanism that records a
`price_observations` row (source=`daily_snapshot`) for every card with a
known price, a backfill CLI for seeding initial history, an admin API
trigger, and improved frontend chart UX for sparse data. The implementation
is clean, well-tested, and fits the existing architecture.

---

## Findings

### CRITICAL

None.

### WARNING

**W1 -- Memory pressure on backfill with large card counts and many days**

`backfill_snapshots()` builds the full list of `HistoricalPrice` objects
in memory before passing them to `insert_price_observations()`. With
100k cards and `days=90`, that is 9 million objects allocated at once.
The current `MAX_BACKFILL_DAYS=90` cap helps, and
`insert_price_observations` already batches the DB writes in groups of
500, but the Python list itself could consume significant memory.

Mitigation is acceptable for now because:
- First backfill is the only time this runs at scale (subsequent runs
  are no-ops due to the `already_have` filter).
- The cap at 90 days is enforced.
- In practice the card count is ~100k and 90 days would mean ~9M
  lightweight dataclass instances (~1-2 GB), which fits in a CLI
  context.

If card counts grow beyond 200k, consider chunking the outer loop and
calling `insert_price_observations` per chunk instead of building the
full list first.

**W2 -- `get_all_latest_prices()` does not exclude `daily_snapshot` source from its own output**

When `run_daily_snapshot()` runs, `get_all_latest_prices()` uses
`ROW_NUMBER() OVER (PARTITION BY external_id ORDER BY observed_at DESC)`
across ALL sources. If a `daily_snapshot` row from yesterday is the most
recent observation for a card (because the original liga/myp source has
no newer data), the snapshot will re-snapshot the snapshot price. This is
functionally harmless -- the price value is correct and idempotency
prevents same-day duplicates -- but it means the snapshot source feeds
back into itself. This is an acceptable trade-off (simpler query, correct
prices), but worth documenting as a design decision.

### NOTE

**N1 -- CLI command naming: `daily-snapshot` vs existing `snapshot-prices`**

There is an existing `snapshot-prices` CLI command (line 419 of
`main.py`) that does JSON-LD product page snapshots via HTTP. The new
`daily-snapshot` command does DB-only reads. The names are close enough
to cause confusion. Consider adding a help text clarification or
renaming the older command in a future cleanup. Not a blocker.

**N2 -- `sparseData` i18n key defined but unused in PriceChart.tsx**

The i18n keys `chart.sparseData` and `chart.sparseData_other` (with
pluralization) are defined in both en.json and pt-BR.json but are never
referenced in `PriceChart.tsx`. The component uses `chart.singlePoint`
and `chart.sparseDataRange` instead. These are dead keys. Low priority
cleanup.

**N3 -- Backfill CLI `--days` default is 1**

The `backfill-snapshots` CLI defaults to `--days 1` (today only), which
is the same as `daily-snapshot`. The README says backfill "creates 1
observation per card for today," so this matches intent. Users who want
multi-day seeding must pass `--days N` explicitly, which is documented
in the `--help`. Fine as-is.

**N4 -- Diagrams are clear and accurate**

Both `F168-architecture.mmd` and `F168-journey.mmd` correctly represent
the data flow and user journey. The architecture diagram properly shows
the three trigger paths (CLI, backfill CLI, admin API) and how they
converge on the snapshot service.

**N5 -- Test coverage is thorough**

- `test_price_snapshot.py`: 16 tests covering happy path, idempotency,
  null prices, multi-source latest-price resolution, backfill with
  partial existing data, day cap, and repository methods.
- `test_cli_snapshot.py`: 5 tests covering CLI invocation, zero count,
  auto-detect DB URL, help output.
- `test_admin_snapshot.py`: 4 tests covering admin 200, idempotent 200,
  non-admin 403, unauthenticated 401.
- `test_snapshot_pipeline.py`: 12 integration tests covering the full
  pipeline (create -> snapshot -> query history), sparkline integration,
  admin auth, backfill+snapshot interaction, idempotency, empty DB.

Edge cases well covered: null median_price exclusion, multi-source
latest-price picking, second-run idempotency, backfill skip logic.

---

## Architecture Assessment

1. **Pattern fit:** The new `price_snapshot.py` follows the same
   collector pattern as `snapshot_prices.py` and `liga_sweep.py`. It
   correctly depends on `Repository` (not raw DB access) and
   `HistoricalPrice` domain model.

2. **Source string integration:** `daily_snapshot` is properly added to
   the source list in `cards.py` (line 232) alongside `jsonld_snapshot`,
   ensuring the history and price-trends endpoints pick up snapshot
   data.

3. **Idempotency:** Relies on the existing `UniqueConstraint("source",
   "external_id", "observed_at")` on `PriceObservationRow` plus
   `on_conflict_do_nothing` in `insert_price_observations`. Correct and
   proven pattern.

4. **Security:** Admin endpoint uses `Depends(require_admin)` which
   raises 403 for non-admins and 401 for unauthenticated. Tests verify
   both cases.

5. **DB compatibility:** `get_all_latest_prices()` uses standard SQL
   `ROW_NUMBER()` CTE which works on both SQLite and PostgreSQL.
   `insert_price_observations` uses `dialect_insert` from `compat.py`
   for cross-dialect upsert.

6. **Performance:** The `ROW_NUMBER()` CTE in `get_all_latest_prices()`
   scans the full `price_observations` table once with a window
   function. With the existing index
   `ix_price_obs_extid_date(external_id, observed_at)`, the partition
   + ordering is efficient. For ~100k unique external_ids this will
   be fast (sub-second on PostgreSQL, a few seconds on SQLite).

7. **Frontend:** Sparse data handling is well-designed -- single-point
   shows a reference line with current price, 2-6 points show enlarged
   dots with a context message, 7+ renders normally. The threshold of
   7 is reasonable.

---

## Conclusion

The feature is well-implemented with clean separation of concerns,
proper security, thorough tests, and no breaking changes. The warnings
are informational and do not require changes before merge.

**APPROVED** -- ready to merge.
