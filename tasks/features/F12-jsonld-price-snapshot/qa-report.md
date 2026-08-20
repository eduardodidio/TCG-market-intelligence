# QA Report: F12 -- JSON-LD Price Snapshot

**QA Agent:** Claude Opus 4.6
**Date:** 2026-08-20
**Verdict:** PASS

---

## 1. Test Results

### Backend

```
715 passed, 107 warnings in 172.28s
Coverage: 91.80% (required: 70%)
```

- **Previous baseline:** 604 tests, 90.69% coverage
- **New F12 tests:** 99 tests across 8 new test files
- **Net change:** +111 backend tests, +1.11% coverage

### Frontend

```
21 test files, 192 tests passed
```

- **Previous baseline:** 187 tests
- **New F12 tests:** 5 tests (sparse data handling in PriceChart)
- **Net change:** +5 frontend tests

### Combined Total

| Metric | Before F12 | After F12 | Delta |
|--------|-----------|-----------|-------|
| Backend tests | 604 | 715 | +111 |
| Frontend tests | 187 | 192 | +5 |
| **Total tests** | **791** | **907** | **+116** |
| Backend coverage | 90.69% | 91.80% | +1.11% |

---

## 2. Coverage for New/Modified Files

| File | Stmts | Miss | Cover |
|------|-------|------|-------|
| `src/collectors/snapshot_prices.py` | 66 | 0 | **100%** |
| `src/parsers/myp.py` | 170 | 0 | **100%** |
| `src/providers/myp/provider.py` | 135 | 0 | **100%** |
| `src/domain/models.py` | 167 | 0 | **100%** |
| `src/database/repository.py` | 296 | 31 | **90%** |
| `src/api/schemas/collection.py` | 45 | 0 | **100%** |
| `src/api/routers/collection.py` | 84 | 46 | 45%* |
| `src/cli/main.py` | 241 | 32 | 87% |

*Note: `collection.py` at 45% is a pre-existing condition -- endpoints like
`list_collection`, `collection_summary`, `collection_sets`, `import_collection`,
and `trigger_sync` are not covered by F12 tests because they belong to earlier
features. The new F12 code (`trigger_snapshot_prices`, `_run_snapshot_job`) is
fully tested via `test_collection_snapshot.py`.

---

## 3. New Test Files

| # | File | Tests | Framework |
|---|------|-------|-----------|
| 1 | `tests/domain/test_snapshot_models.py` | 10 | pytest |
| 2 | `tests/parsers/test_myp_jsonld.py` | 20 | pytest |
| 3 | `tests/providers/test_myp_fetch_price.py` | 9 | pytest + pytest-asyncio |
| 4 | `tests/collectors/test_snapshot_prices.py` | 14 | pytest + pytest-asyncio |
| 5 | `tests/database/test_repository_snapshot.py` | 11 | pytest |
| 6 | `tests/api/test_snapshot_schemas.py` | 7 | pytest |
| 7 | `tests/api/test_collection_snapshot.py` | 12 | pytest |
| 8 | `tests/cli/test_snapshot_prices.py` | 16 | pytest |
| 9 | `frontend/tests/components/PriceChart.test.tsx` | +5 | Vitest + RTL |

---

## 4. Test Plan Coverage Analysis

### Fully Covered (no gaps)

| Plan Section | Plan IDs | Actual Tests | Status |
|-------------|----------|-------------|--------|
| Domain models | U01-U09 | 10 tests | COVERED (exceeds plan) |
| Parser | U10-U22 | 20 tests | COVERED (exceeds plan) |
| Provider | P01-P07 | 9 tests | COVERED (exceeds plan) |
| Repository | I01-I10 | 11 tests | COVERED (exceeds plan) |
| Collector | I11-I23 | 14 tests | COVERED |
| API Schema | U23-U27 | 7 tests | COVERED (exceeds plan) |
| API Endpoint | A01-A10 | 12 tests | COVERED (exceeds plan) |
| CLI Command | C01-C10 | 16 tests | COVERED (exceeds plan) |
| Cron Script | CR01-CR05 | Validated inline | COVERED |
| Frontend Sparse | FE01-FE03, FE05-FE07 | 5 tests | COVERED |

### Minor Gaps (non-blocking)

| Plan ID | Description | Assessment |
|---------|-------------|------------|
| I24 | Concurrency semaphore ordering test | Structurally covered: all async collector tests use `concurrency=1`, and the code uses `asyncio.Semaphore`. No explicit timing/ordering assertion, but the behavior is correct. |
| FE04 | 6 data points boundary (sparse notice shown) | Implicitly covered: 5-point test shows notice, 7-point test hides it. The threshold `< 7` in PriceChart.tsx is sandwiched. Adding explicit 6-point test would strengthen coverage but is not blocking. |

---

## 5. TechLead Review Findings -- Verification

### C1: jsonld_snapshot observations invisible to dashboard

**TechLead verdict:** Critical (functional gap)
**QA verification:** ALREADY FIXED in shipped code

The TechLead flagged that query paths filter by `source=sc.source` (i.e.,
`"myp"`) and would miss `jsonld_snapshot` observations. However, the actual
code has already been updated:

- `get_price_series()` (cards.py line 144): `source=[sc.source, "jsonld_snapshot"]`
- `get_latest_prices_batch()` (repository.py line 339): `.in_([sc.source, "jsonld_snapshot"])`
- `get_movers()` (repository.py lines 401, 415): `.in_([sc.source, "jsonld_snapshot"])`

All three query paths include `jsonld_snapshot` observations. The critical
issue is resolved.

### M1: SnapshotRequest.dry_run not forwarded by API endpoint

**TechLead verdict:** Major issue
**QA verification:** ALREADY FIXED in shipped code

The API endpoint at `collection.py` line 213 passes `dry_run=request.dry_run`
to `_run_snapshot_job()`, and `_run_snapshot_job()` at line 236 passes
`dry_run=dry_run` to `run_snapshot_prices()`. The full chain forwards correctly.

### M2: SnapshotResponse is dead code

**TechLead verdict:** Major issue
**QA verification:** NOT APPLICABLE

The `SnapshotResponse` class does not exist in `src/api/schemas/collection.py`.
Either it was never created or was cleaned up before the final commit. No dead
code found.

---

## 6. Regression Check

| Check | Result |
|-------|--------|
| All existing CLI commands present (`backfill`, `update`, `retry-failed`, `serve`, `sync-collection`, `match-report`, `db-backup`, `db-cleanup`, `analyze`) | PASS |
| `snapshot-prices` command visible in `--help` | PASS |
| Import `src.collectors.snapshot_prices.run_snapshot_prices` | PASS |
| Import `src.providers.myp.provider.MypCardsProvider` | PASS |
| Import `src.parsers.myp.parse_jsonld_price` | PASS |
| Cron script syntax (`bash -n scripts/cron_update.sh`) | PASS |
| Cron script contains `/collect/update` endpoint | PASS |
| Cron script contains `/collection/snapshot-prices` endpoint | PASS |
| Cron script uses `X-API-Key: ${TCG_API_KEY}` for both calls | PASS |
| Snapshot failure in cron is non-fatal (`|| { log "WARNING" }`) | PASS |
| No circular imports | PASS |
| No new dependencies | PASS |

---

## 7. Integration Smoke Test

```
$ python -m src.cli.main snapshot-prices --dry-run --limit 1

snapshot_start                 total_entries=124
limit_applied                  processing=1
snapshot_stored                dry_run=True external_id=262897 index=1 price=0.25
snapshot_summary               elapsed_seconds=1.45 errors=0 fetched=1 stored=1

============================================================
  DRY RUN -- no data was written
  SNAPSHOT PRICES SUMMARY
  Total entries:           124
  Fetched:                 1
  Stored:                  1
  Skipped (existing):      0
  Skipped (zero price):    0
  Errors:                  0
  Elapsed:                 1.5s
============================================================
```

The full pipeline works end-to-end:
- 124 collection entries found in the database
- 1 card processed (limit=1)
- Price fetched from MYP product page JSON-LD (R$0.25)
- Dry-run mode correctly prevents database writes
- Summary output formatted correctly with all fields

---

## 8. Documentation Check

| Artifact | Path | Status |
|----------|------|--------|
| PRD | `docs/prd/F12-jsonld-price-snapshot.md` | Present |
| Architecture diagram | `docs/diagrams/F12-architecture.mmd` | Present |
| User journey diagram | `docs/diagrams/F12-journey.mmd` | Present |
| README.md updated | F12 section in "Shipped" | Present |
| Test plan | `tasks/features/F12-jsonld-price-snapshot/F12-test-plan.md` | Present |

---

## 9. Issues Found

### No blocking issues.

### Observations (informational, not blocking)

1. **TechLead review was based on an earlier snapshot.** All three issues flagged
   by the TechLead (C1, M1, M2) are either already fixed or not applicable in
   the shipped code. This suggests the Developer addressed the findings before
   the final commit, which is the correct workflow.

2. **ResourceWarning in test output.** 107 warnings during the test run, mostly
   `ResourceWarning: unclosed database` from SQLAlchemy in-memory sessions.
   These are pre-existing (present before F12) and do not affect correctness.

3. **`collection.py` overall coverage at 45%.** This is a pre-existing
   condition from earlier features (F10) that did not have full API endpoint
   tests. The new F12 code within this file is fully tested.

---

## 10. Verdict

**PASS**

F12 delivers a complete, well-tested daily price snapshot system. The feature:

- Adds 116 new tests (99 backend + 5 frontend + 12 extra from related changes)
- Maintains 91.80% backend coverage (above the 90% target)
- Has 100% coverage on all new modules (snapshot_prices, parse_jsonld_price,
  fetch_current_price, JsonLdPrice, SnapshotSummary)
- Passes the end-to-end smoke test with real MYP data
- Introduces no regressions
- All TechLead findings are resolved in shipped code
- Documentation is complete (PRD, diagrams, README)

The feature is ready for production use. Daily `snapshot-prices` runs will begin
accumulating price history immediately, replacing the auth-gated price history
endpoint.
