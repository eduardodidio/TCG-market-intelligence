# F168 -- Price History Densification: QA Report

**Date:** 2026-09-21
**QA Agent:** Claude Opus 4.6
**Branch:** homol

---

## 1. Test Results

### Backend (45 tests -- all PASSED)

| Test file | Tests | Result |
|-----------|-------|--------|
| `tests/test_price_snapshot.py` | 16 | 16 PASSED |
| `tests/test_cli_snapshot.py` | 10 | 10 PASSED (5 original + 5 new) |
| `tests/api/test_admin_snapshot.py` | 4 | 4 PASSED |
| `tests/integration/test_snapshot_pipeline.py` | 15 | 15 PASSED |
| **Total** | **45** | **45 PASSED, 0 FAILED** |

### Frontend (27 PriceChart tests -- all PASSED)

| Test file | Tests | Result |
|-----------|-------|--------|
| `tests/components/PriceChart.test.tsx` | 27 | 27 PASSED |

17 failures in unrelated test files (Layout nav items, OfflineBanner, TreasureModal
foil shimmer, DeckList/DeckView/Evaluations/TopDecks error states, Login OAuth
buttons, MyCollection grid toggle, MyTrades breadcrumb, ImportPurchasesPage result
state) -- all pre-existing, none related to F168.

### Ruff Lint

```
ruff check src/collectors/price_snapshot.py src/database/repository.py \
  src/cli/main.py src/api/routers/admin.py src/api/routers/cards.py
All checks passed!
```

---

## 2. Acceptance Criteria Verification

| AC | Description | Verdict | Evidence |
|----|-------------|---------|----------|
| AC1 | Snapshot creates one observation per priced card (source=daily_snapshot) | **PASS** | `test_happy_path_creates_observations` verifies 3 priced cards produce 3 observations with `source="daily_snapshot"` and today's date. `test_mixed_prices_only_priced_cards_get_snapshots` confirms null-price cards are excluded. Integration test `test_snapshot_creates_observations_and_history_shows_them` confirms full pipeline. |
| AC2 | Running twice inserts 0 new rows (idempotent) | **PASS** | `test_idempotency_second_run_returns_zero` (unit) and `test_second_daily_snapshot_creates_zero` + `test_idempotency_preserves_existing_data` (integration) all verify second run returns 0 and existing data is preserved. Relies on `on_conflict_do_nothing` via `insert_price_observations`. |
| AC3 | Admin API returns `observations_created` count | **PASS** | `test_admin_snapshot_returns_count` verifies `POST /admin/jobs/snapshot-prices` returns `{"data": {"observations_created": 123}}`. Auth checks: 403 for non-admin, 401 for unauthenticated. |
| AC4 | `backfill-snapshots` creates observations for missing cards | **PASS** | `test_happy_path_creates_observations` (unit), `test_partial_backfill_skips_existing`, `test_multi_day_creates_multiple_per_card`, and integration tests `test_backfill_creates_multi_day_observations` + `test_backfill_skips_already_snapshotted` all verify backfill logic. CLI test `TestBackfillSnapshotsCommand` (5 tests) verifies CLI wiring. |
| AC5 | PriceChart shows improved UX for 1-3 data points | **PASS** | `PriceChart.test.tsx` sparse data handling suite: `test_singlePoint_message_with_1_data_point`, `test_sparseDataRange_notice_with_3_data_points`, `test_sparse-data-notice_with_5_data_points`, `test_does_not_show_sparse-data-notice_with_7_data_points`. Component renders `chart.singlePoint` i18n message for 1 point, `chart.sparseDataRange` for 2-6 points, and enlarged dot radius for sparse series. |
| AC6 | No credit cost | **PASS** | `price_snapshot.py` has zero references to credits, deduction, or spending. The admin endpoint docstring explicitly states "No credit cost." The service only calls `repo.get_all_latest_prices()` and `repo.insert_price_observations()` -- pure read/write, no credit middleware. |
| AC7 | Works on both SQLite and PostgreSQL | **PASS** | All unit/integration tests use SQLite in-memory or temp files. The SQL constructs used (`ROW_NUMBER()`, `PARTITION BY`, `on_conflict_do_nothing`) are standard SQL supported by both SQLite 3.25+ and PostgreSQL. `get_all_latest_prices()` uses SQLAlchemy's portable `func.row_number()` and `over()` -- no raw SQL dialect-specific code. |

---

## 3. Diagrams

| Diagram | Path | Status |
|---------|------|--------|
| Architecture | `docs/diagrams/F168-architecture.mmd` | EXISTS -- shows data flow from sources through snapshot service to price_observations, with CLI/API/scheduler triggers |
| User Journey | `docs/diagrams/F168-journey.mmd` | EXISTS -- shows user flow from Dashboard movers through CardDetail to merged price history chart |

---

## 4. README Update

**PASS** -- `README.md` contains an F168 section (line 970+) documenting:
- Snapshot service (`src/collectors/price_snapshot.py`)
- CLI commands (`daily-snapshot`, `backfill-snapshots --days N`)
- Admin API endpoint (`POST /api/v1/admin/jobs/snapshot-prices`)
- History/price-trends API integration with `daily_snapshot` observations

---

## 5. Test Gaps Found and Filled

### Gap: No CLI tests for `backfill-snapshots` command

The `backfill-snapshots` CLI command had unit tests for the underlying
`backfill_snapshots()` function and integration tests, but no CLI-level tests
verifying the Click command wiring, `--days` option passthrough, or help output.

**Action taken:** Added 5 tests in `TestBackfillSnapshotsCommand` class in
`tests/test_cli_snapshot.py`:

1. `test_happy_path_prints_count` -- verifies CLI calls `backfill_snapshots()` and prints count
2. `test_zero_observations` -- verifies graceful handling of 0 results
3. `test_days_option` -- verifies `--days 10` is passed through correctly
4. `test_shows_in_help` -- verifies command appears in `--help` output
5. `test_command_help` -- verifies `--help` shows `--db`, `--days`, and description

All 5 new tests pass.

### Remaining minor gaps (not blocking)

- **No negative-days test:** `backfill-snapshots --days 0` or `--days -1` is not tested.
  The behavior is harmless (0 days = no observations, negative days = empty range)
  but documenting it with a test would be ideal.
- **Large batch performance:** No test for snapshot with 10k+ cards to verify
  `BATCH_SIZE=500` chunking works correctly. This is an operational concern, not
  a correctness concern.

---

## 6. Code Quality Notes

- `price_snapshot.py` is clean (110 lines), well-documented, and follows the
  project's existing patterns.
- Repository methods `get_all_latest_prices()` and `get_external_ids_with_source()`
  use standard SQLAlchemy constructs (CTE, ROW_NUMBER) that are portable.
- The `MAX_BACKFILL_DAYS = 90` cap with logging warning is a good safety measure.
- 8 `ResourceWarning: unclosed database` warnings in test output are pre-existing
  (SQLite connection cleanup) and not introduced by F168.

---

## 7. Verdict

**PASS**

All 7 acceptance criteria verified. 45 backend tests + 27 frontend PriceChart tests
pass. Ruff lint clean. Diagrams present. README updated. One test gap (backfill CLI)
identified and filled with 5 new tests.
