# F12 Test Plan -- JSON-LD Price Snapshot

**Feature:** F12-jsonld-price-snapshot
**Date:** 2026-08-20
**Coverage target:** >= 90% (backend), maintain existing frontend coverage
**Frameworks:** pytest + pytest-asyncio (backend), Vitest + React Testing Library (frontend)

---

## 1. Test Strategy

### Approach

The test strategy mirrors the established patterns in this codebase:

- **Unit tests** for pure functions and dataclasses: parser (`parse_jsonld_price`),
  domain models (`JsonLdPrice`, `SnapshotSummary`), and helper logic. These tests
  use inline HTML strings and require no mocking.
- **Integration tests** for the collector orchestrator (`run_snapshot_prices`):
  mock the Repository and Provider at the module level (via `@patch`), verify
  orchestration logic including idempotency, error handling, dry-run, and limit.
  Follow the pattern established in `tests/collectors/test_sync_collection.py`.
- **Repository tests** for the two new methods (`get_linked_collection_with_source`,
  `has_snapshot_for_date`): use an in-memory SQLite database with real schema
  creation, following the pattern in `tests/database/test_repository_api.py`.
- **API tests** for the new endpoint: use FastAPI TestClient with dependency
  overrides, mock `asyncio.create_task`, and test auth / validation / response
  schema. Follow the pattern in `tests/api/test_collection_sync.py`.
- **CLI tests** for the new command: use Click CliRunner with mocked
  `asyncio.run`, verify output formatting. Follow the pattern in
  `tests/cli/test_sync_collection.py`.
- **Frontend tests** for PriceChart sparse data: use Vitest with mocked
  Recharts ResponsiveContainer and mocked fetch, following the pattern in
  `frontend/tests/components/PriceChart.test.tsx`.
- **Cron script**: `bash -n` syntax validation plus grep-based assertions.
  No dedicated test file -- validated in CI or manually.

### Coverage Gate

All new code must be covered. The project-wide coverage floor is 90%
(`--cov-fail-under=70` in pyproject.toml, but actual coverage is 90.69%).
No regression allowed.

### Test Isolation

- All async tests use `@pytest.mark.asyncio`.
- All tests are isolated -- no shared state between tests.
- All provider/collector tests mock HTTP calls -- no real network traffic.
- Database tests use `sqlite:///:memory:` for in-memory isolation.

---

## 2. Unit Tests

### 2.1 `JsonLdPrice` Dataclass

**File:** `tests/domain/test_snapshot_models.py` (new file)

| # | Test Case | Expected |
|---|-----------|----------|
| U01 | `JsonLdPrice()` with all defaults | `price=None`, `currency="BRL"`, `availability="Unknown"` |
| U02 | `JsonLdPrice(price=Decimal("12.50"))` explicit price | `price=Decimal("12.50")` |
| U03 | `JsonLdPrice(price=Decimal("0"))` zero price | `price=Decimal("0")` (dataclass stores it; parser normalizes) |
| U04 | `JsonLdPrice(currency="USD", availability="InStock")` custom fields | Fields set correctly |

### 2.2 `SnapshotSummary` Dataclass

**File:** `tests/domain/test_snapshot_models.py` (same file)

| # | Test Case | Expected |
|---|-----------|----------|
| U05 | `SnapshotSummary()` with all defaults | All counters at 0, `error_details=[]`, `started_at` auto-populated, `finished_at=None` |
| U06 | `SnapshotSummary(total_entries=10, fetched=8, stored=8)` | Fields set correctly |
| U07 | `started_at` auto-populates with current time | `started_at` is a `datetime`, roughly `datetime.now()` |
| U08 | `error_details` defaults to empty list | `error_details == []`, is a `list` |
| U09 | `SnapshotSummary` with `error_details` containing `CollectionError` | Error stored correctly |

### 2.3 `parse_jsonld_price()` Parser

**File:** `tests/parsers/test_myp_jsonld.py` (new file)

| # | Test Case | Input | Expected |
|---|-----------|-------|----------|
| U10 | Happy path -- InStock, valid price | JSON-LD with `price: "12.50"`, `priceCurrency: "BRL"`, `availability: ".../InStock"` | `JsonLdPrice(price=Decimal("12.50"), currency="BRL", availability="InStock")` |
| U11 | OutOfStock card | `availability: "https://schema.org/OutOfStock"`, `price: "5.00"` | `JsonLdPrice(price=Decimal("5.00"), availability="OutOfStock")` |
| U12 | Zero price normalized to None | `price: "0"` | `JsonLdPrice(price=None)` |
| U13 | Missing price field in offers | offers block with no `price` key | `JsonLdPrice(price=None)` |
| U14 | No JSON-LD block on page | Plain HTML without `<script type="application/ld+json">` | Returns `None` |
| U15 | Malformed JSON in script tag | `<script type="application/ld+json">{broken</script>` | Returns `None` |
| U16 | Missing offers block entirely | `{"@type": "Product", "name": "Test"}` (no `offers`) | `JsonLdPrice(price=None, currency="BRL", availability="Unknown")` |
| U17 | Multiple JSON-LD blocks, first non-Product | BreadcrumbList first, Product second with price | Extracts price from the Product block |
| U18 | Price with comma decimal (e.g., "12,50") | `price: "12,50"` | `JsonLdPrice(price=Decimal("12.50"))` via `_to_decimal` |
| U19 | Availability without URL (plain string) | `availability: "InStock"` | `availability="InStock"` |
| U20 | Empty availability string | `availability: ""` | `availability="Unknown"` |
| U21 | Price as integer (e.g., `"10"`) | `price: "10"` | `JsonLdPrice(price=Decimal("10"))` |
| U22 | Reuses existing `parse_json_ld_product` | (structural) Verify function calls `parse_json_ld_product` internally | Covered implicitly by behavior tests |

### 2.4 `SnapshotRequest` Pydantic Schema

**File:** `tests/api/test_snapshot_schemas.py` (new file)

| # | Test Case | Expected |
|---|-----------|----------|
| U23 | `SnapshotRequest()` default | `limit=None` |
| U24 | `SnapshotRequest(limit=10)` | `limit=10` |
| U25 | JSON round-trip `{}` | Parses to `SnapshotRequest(limit=None)` |
| U26 | JSON round-trip `{"limit": 5}` | Parses to `SnapshotRequest(limit=5)` |
| U27 | Invalid limit type `"abc"` | Validation error |

---

## 3. Integration Tests

### 3.1 Repository: `get_linked_collection_with_source()`

**File:** `tests/database/test_repository_snapshot.py` (new file)

| # | Test Case | Setup | Expected |
|---|-----------|-------|----------|
| I01 | Returns linked entries with source card info | 2 collection rows (1 linked, 1 unlinked), 1 source_card row | Returns list with 1 dict containing `entry_id`, `card_id`, `external_id`, `slug`, `url` |
| I02 | Filters by source | 2 source_cards with different sources ("myp", "other") | Only returns entries linked through the requested source |
| I03 | No linked entries | All collection entries have `card_id=NULL` | Returns empty list |
| I04 | Slug extracted from URL | source_card.url = `".../produto/123/my-slug"` | Dict contains `slug="my-slug"` |
| I05 | Multiple entries for same card | 2 collection entries linked to same card_id | Returns both entries |

### 3.2 Repository: `has_snapshot_for_date()`

**File:** `tests/database/test_repository_snapshot.py` (same file)

| # | Test Case | Setup | Expected |
|---|-----------|-------|----------|
| I06 | Returns True when snapshot exists for date | 1 observation with `source="jsonld_snapshot"`, `external_id="123"`, `observed_at=today` | `True` |
| I07 | Returns False when no snapshot for date | No matching observations | `False` |
| I08 | Returns False when observation exists for different date | Observation for yesterday | `False` |
| I09 | Returns False when observation exists for different source | Observation with `source="myp"` for same date | `False` |
| I10 | Returns False when observation exists for different external_id | Observation for different card on same date | `False` |

### 3.3 Collector: `run_snapshot_prices()`

**File:** `tests/collectors/test_snapshot_prices.py` (new file)

| # | Test Case | Setup | Expected |
|---|-----------|-------|----------|
| I11 | Happy path -- 3 linked entries, all have prices | Mock 3 entries, provider returns valid JsonLdPrice for each | `summary.fetched=3`, `summary.stored=3`, `summary.errors=0` |
| I12 | Idempotency -- entry already snapshotted today | `has_snapshot_for_date` returns True | `summary.skipped_existing=1`, no fetch call for that entry |
| I13 | Zero price -- JSON-LD returns price=None | `fetch_current_price` returns `JsonLdPrice(price=None)` | `summary.skipped_zero_price=1` |
| I14 | Fetch returns None (no JSON-LD on page) | `fetch_current_price` returns `None` | `summary.skipped_zero_price=1` |
| I15 | Fetch error -- provider raises exception | `fetch_current_price` raises `RuntimeError` | `summary.errors=1`, error recorded in `error_details`, other entries still processed |
| I16 | Dry run -- no DB writes | `dry_run=True`, valid prices | `repo.insert_price_observations` never called, `summary.stored` still counted |
| I17 | Limit -- 10 entries, limit=3 | 10 entries returned from repo | Only 3 entries processed |
| I18 | No linked entries | `get_linked_collection_with_source` returns `[]` | `summary.total_entries=0`, all counters 0 |
| I19 | Mixed results -- accurate summary | 5 entries: 2 priced, 1 zero, 1 existing, 1 error | All counters match expected values |
| I20 | Provider closed on success | Successful run | `provider.close()` called |
| I21 | Provider closed on error | Repo raises exception | `provider.close()` still called |
| I22 | Observations stored with `source="jsonld_snapshot"` | Happy path, inspect `insert_price_observations` call args | `HistoricalPrice.source == "jsonld_snapshot"` |
| I23 | Observation uses today's date | Happy path | `HistoricalPrice.observed_at == date.today()` |
| I24 | Concurrency semaphore respected | Mock delay, concurrency=1 | Tasks run sequentially (verify ordering) |

---

## 4. API Tests

### 4.1 `POST /api/v1/collection/snapshot-prices`

**File:** `tests/api/test_collection_snapshot.py` (new file)

| # | Test Case | Setup | Expected |
|---|-----------|-------|----------|
| A01 | Happy path -- valid request, no API key env | No `TCG_API_KEY` set, POST `{}` | 200, response has `job_id`, `status="started"`, `message` contains "snapshot" |
| A02 | Auth required -- returns 401 without key | `TCG_API_KEY=prod-key`, no header | 401 |
| A03 | Auth required -- returns 401 with wrong key | `TCG_API_KEY=prod-key`, header `X-API-Key: wrong` | 401 |
| A04 | Auth passes with correct key | `TCG_API_KEY=prod-key`, header `X-API-Key: prod-key` | 200 |
| A05 | Dev mode -- works without key when env not set | No `TCG_API_KEY`, no header | 200 |
| A06 | With limit parameter | POST `{"limit": 5}` | 200, accepted (limit passed to background job) |
| A07 | Default -- empty body | POST `{}` | 200, `limit=None` |
| A08 | Invalid limit type | POST `{"limit": "abc"}` | 422 validation error |
| A09 | Background task created | Mock `asyncio.create_task` | `create_task` called once |
| A10 | Response schema matches `ApiResponse[JobStatus]` | Inspect response JSON | Has `data.job_id`, `data.status`, `data.message`, `meta`, `errors` keys |

---

## 5. CLI Tests

### 5.1 `snapshot-prices` Command

**File:** `tests/cli/test_snapshot_prices.py` (new file)

| # | Test Case | Setup | Expected |
|---|-----------|-------|----------|
| C01 | Help text | `snapshot-prices --help` | Exit 0, shows `--db`, `--limit`, `--dry-run`, `--delay`, `--concurrency` |
| C02 | Shows in top-level help | `--help` | `snapshot-prices` listed in commands |
| C03 | Default run -- summary printed | Mock `asyncio.run` returning SnapshotSummary | Exit 0, output contains "SNAPSHOT PRICES SUMMARY", all field labels |
| C04 | Dry run banner | `snapshot-prices --dry-run` | Output contains "DRY RUN" before "SNAPSHOT PRICES SUMMARY" |
| C05 | All options accepted | `--db sqlite:///x.db --limit 5 --dry-run --delay 2.0 --concurrency 1` | Exit 0 |
| C06 | Summary shows all fields | Mock summary with specific values | Output contains `Total entries:`, `Fetched:`, `Stored:`, `Skipped (existing):`, `Skipped (zero price):`, `Errors:` |
| C07 | Summary shows elapsed time | Summary with `finished_at` set | Output contains `Elapsed:` with seconds |
| C08 | Summary omits elapsed when unfinished | `finished_at=None` | `Elapsed:` not in output |
| C09 | Error details printed | Summary with 3 errors in `error_details` | Output contains error count and external_id |
| C10 | Many errors truncated | 25 errors in `error_details` | Shows first 20, then "... and 5 more" |

---

## 6. Frontend Tests

### 6.1 PriceChart Sparse Data Handling

**File:** `frontend/tests/components/PriceChart.test.tsx` (extend existing file)

| # | Test Case | Data | Expected |
|---|-----------|------|----------|
| FE01 | Empty data -- existing behavior preserved | `observations = []` | `empty-history` testid present, text "No price history available" |
| FE02 | 1 data point -- sparse notice shown | 1 observation | `sparse-data-notice` testid present, text contains "1 data point" |
| FE03 | 5 data points -- sparse notice shown | 5 observations | `sparse-data-notice` testid present, text contains "5 data points" |
| FE04 | 6 data points -- sparse notice shown | 6 observations | `sparse-data-notice` testid present (boundary: < 7) |
| FE05 | 7 data points -- no sparse notice | 7 observations | `sparse-data-notice` testid NOT present |
| FE06 | 30 data points -- no sparse notice | 30 observations | `sparse-data-notice` testid NOT present, `chart-container` present |
| FE07 | 1 data point -- chart still renders | 1 observation | `chart-container` testid present (not just empty state) |

---

## 7. Cron Script Validation

### 7.1 `scripts/cron_update.sh`

**Validation:** Manual / CI (no dedicated test file)

| # | Test Case | Command | Expected |
|---|-----------|---------|----------|
| CR01 | Syntax valid | `bash -n scripts/cron_update.sh` | Exit 0 |
| CR02 | Update endpoint still present | `grep "/collect/update" scripts/cron_update.sh` | Match found |
| CR03 | Snapshot endpoint added | `grep "/collection/snapshot-prices" scripts/cron_update.sh` | Match found |
| CR04 | Snapshot uses same API key header | `grep "X-API-Key.*TCG_API_KEY" scripts/cron_update.sh` | Multiple matches (update + snapshot) |
| CR05 | Snapshot failure is non-fatal | Inspect script structure | Snapshot curl uses `|| {` pattern with `WARNING`, not `exit 2` |

---

## 8. Edge Cases (Cross-Cutting)

| # | Edge Case | Layer | Expected Behavior |
|---|-----------|-------|-------------------|
| E01 | Card with `price=0` on JSON-LD | Parser + Collector | Parser returns `JsonLdPrice(price=None)`; collector increments `skipped_zero_price` |
| E02 | Card page has no JSON-LD at all | Parser + Collector | Parser returns `None`; collector increments `skipped_zero_price` |
| E03 | Network error during fetch | Provider + Collector | Provider returns `None` or raises; collector increments `errors`, continues |
| E04 | All cards already snapshotted today | Collector | `summary.skipped_existing == total_entries`, no fetches made |
| E05 | OutOfStock price vs InStock price | Parser | Both extracted correctly; availability field distinguishes them |
| E06 | Card has JSON-LD Product but no offers block | Parser | `JsonLdPrice(price=None, availability="Unknown")` |
| E07 | Multiple JSON-LD blocks, first is BreadcrumbList | Parser | Correctly finds Product block (reuses `parse_json_ld_product`) |
| E08 | Source card URL with unusual slug characters | Collector | Slug extraction via `rsplit("/", 1)[-1]` handles correctly |
| E09 | Large collection (>500 cards) | Collector | Semaphore limits concurrency; no memory issues |
| E10 | Duplicate card in collection (same card_id, different entries) | Collector | Both entries processed; second may be skipped by idempotency |
| E11 | API endpoint called concurrently twice | API | Both return job_id; each runs independently |
| E12 | PriceChart re-renders on period change with sparse data | Frontend | Notice text updates if point count changes (unlikely mid-session but safe) |

---

## 9. Test Matrix

Maps each task (T01-T10) to the test files and test case IDs that cover it.

| Task | Description | Test File(s) | Test Case IDs |
|------|-------------|-------------|---------------|
| **F12-T01** | Domain: `JsonLdPrice`, `SnapshotSummary` | `tests/domain/test_snapshot_models.py` | U01-U09 |
| **F12-T02** | Parser: `parse_jsonld_price()` | `tests/parsers/test_myp_jsonld.py` | U10-U22 |
| **F12-T03** | Provider: `fetch_current_price()` | `tests/providers/test_myp_fetch_price.py` | (see below) |
| **F12-T04** | Collector: `snapshot_prices.py` + Repository methods | `tests/collectors/test_snapshot_prices.py`, `tests/database/test_repository_snapshot.py` | I01-I24 |
| **F12-T05** | API Schema: `SnapshotRequest` | `tests/api/test_snapshot_schemas.py` | U23-U27 |
| **F12-T06** | Frontend: PriceChart sparse data | `frontend/tests/components/PriceChart.test.tsx` | FE01-FE07 |
| **F12-T07** | CLI: `snapshot-prices` command | `tests/cli/test_snapshot_prices.py` | C01-C10 |
| **F12-T08** | API: `POST /collection/snapshot-prices` | `tests/api/test_collection_snapshot.py` | A01-A10 |
| **F12-T09** | Cron: daily snapshot call | (inline validation / CI) | CR01-CR05 |
| **F12-T10** | Docs: PRD, diagrams, README | (manual review) | -- |

### F12-T03 Provider Tests (supplemental)

**File:** `tests/providers/test_myp_fetch_price.py` (new file)

| # | Test Case | Setup | Expected |
|---|-----------|-------|----------|
| P01 | Happy path -- mock `_fetch` returns valid HTML | Patch `_fetch` to return HTML with JSON-LD Product | Returns `JsonLdPrice` with correct price |
| P02 | Fetch failure -- `RuntimeError` | Patch `_fetch` to raise `RuntimeError` | Returns `None`, logs warning |
| P03 | Fetch failure -- `TimeoutError` | Patch `_fetch` to raise `TimeoutError` | Returns `None`, logs warning |
| P04 | Fetch failure -- `OSError` | Patch `_fetch` to raise `OSError` | Returns `None`, logs warning |
| P05 | No JSON-LD on page | Patch `_fetch` to return plain HTML | Returns `None` |
| P06 | URL construction | Inspect URL passed to `_fetch` | `https://mypcards.com/magic/produto/{product_id}/{slug}` |
| P07 | Reuses existing `_fetch()` | (structural) | `_fetch` is called, not a raw HTTP call |

---

## 10. Test File Summary

New test files to create:

| # | Path | Count | Framework |
|---|------|-------|-----------|
| 1 | `tests/domain/test_snapshot_models.py` | ~9 tests | pytest |
| 2 | `tests/parsers/test_myp_jsonld.py` | ~13 tests | pytest |
| 3 | `tests/providers/test_myp_fetch_price.py` | ~7 tests | pytest + pytest-asyncio |
| 4 | `tests/collectors/test_snapshot_prices.py` | ~14 tests | pytest + pytest-asyncio |
| 5 | `tests/database/test_repository_snapshot.py` | ~10 tests | pytest |
| 6 | `tests/api/test_snapshot_schemas.py` | ~5 tests | pytest |
| 7 | `tests/api/test_collection_snapshot.py` | ~10 tests | pytest |
| 8 | `tests/cli/test_snapshot_prices.py` | ~10 tests | pytest |

Existing files to extend:

| # | Path | Tests Added | Framework |
|---|------|-------------|-----------|
| 1 | `frontend/tests/components/PriceChart.test.tsx` | ~6 tests | Vitest + RTL |

**Estimated total new tests:** ~84 backend + ~6 frontend = ~90 tests.

This should bring the project from 604 backend + 187 frontend tests to
approximately 688 backend + 193 frontend = ~881 total tests.

---

## 11. Run Commands

```bash
# All new backend tests
python -m pytest tests/domain/test_snapshot_models.py tests/parsers/test_myp_jsonld.py tests/providers/test_myp_fetch_price.py tests/collectors/test_snapshot_prices.py tests/database/test_repository_snapshot.py tests/api/test_snapshot_schemas.py tests/api/test_collection_snapshot.py tests/cli/test_snapshot_prices.py -x -v

# Full backend suite (ensure no regressions)
python -m pytest --cov=src --cov-report=term-missing

# Frontend tests
cd frontend && npx vitest run tests/components/PriceChart.test.tsx

# Full frontend suite
cd frontend && npx vitest run

# Cron script syntax check
bash -n scripts/cron_update.sh
```
