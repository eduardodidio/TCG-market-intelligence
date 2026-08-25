# F60 Test Plan — LigaMagic Primary Provider Migration

## 1. Scope

### In scope
- Scan orchestrator refactor: generic provider support (Liga + MYP paths)
- New `ScanType` enum values (`LIGA_FULL`, `LIGA_PARTIAL`)
- Repository: `get_cards_for_liga_scan()`, `get_liga_coverage_stats()`, `get_liga_missing_cards()`
- Price priority reordering in `get_latest_prices_batch()` (manual > liga > jsonld_snapshot/myp)
- `clear_prices_by_source()` cleanup function + `db-clear-prices` CLI command
- Liga scan orchestrator (`run_liga_scan`) and sweep (`run_liga_sweep`)
- API changes: `POST /scans` provider field, `GET /collection/liga-status`, `GET /collection/liga-missing`
- CLI: `liga-sweep` command, `scan --provider` flag
- Frontend: AdminLigaStatus page, card detail Liga/MYP button hierarchy, PriceSourceBadge colors, default refresh endpoint change, i18n keys
- Scheduled Liga scans (APScheduler provider routing, default schedules seeding)

### Out of scope
- Real Playwright browser sessions (all mocked)
- LigaMagic HTML parser tests (covered by existing F57 tests in `tests/providers/test_liga_provider.py` and `tests/parsers/`)
- MYP provider internals (unchanged)
- Exchange rate / currency conversion logic (unchanged)
- Deck valuation, trending, ban engine (unchanged)

## 2. Test Strategy

### Unit tests (~80% of new tests)
- Pure functions, repo methods, CLI commands, API endpoints tested in isolation
- All provider calls mocked via `unittest.mock.AsyncMock` / `MagicMock`
- Database tests use in-memory SQLite (`sqlite:///:memory:`) with SQLAlchemy
- API tests use `FastAPI.TestClient` with dependency overrides (`get_db`, `require_auth_or_api_key`)

### Integration tests (~15% of new tests)
- Cross-module flows: liga scan orchestrator with mock provider + real repo + real DB
- Sweep batching with mock provider verifying observation persistence
- Scheduler job execution routing (liga vs myp)

### Frontend tests (~5% of new tests, but high count due to component coverage)
- Vitest + React Testing Library
- API calls mocked via `vi.mock("../api/scans")` or `vi.mock("../api/client")`
- i18n tested via key presence checks (pattern from `tests/i18n/`)
- No E2E / Playwright browser tests on frontend side

### Mock strategy for LigaMagicProvider
- **Never** instantiate a real `LigaMagicProvider` in tests (requires Playwright + Chromium)
- Mock at the provider level: `AsyncMock(spec=LigaMagicProvider)`
- `search_card()` returns `{"normal": {"mid": Decimal("5.50"), "low": Decimal("4.00")}}` or raises `LigaNotFoundError` / `LigaRateLimitError`
- For scan orchestrator tests: inject mock provider via constructor/parameter
- For API tests: patch `src.collectors.liga_scan.LigaMagicProvider` at module level

## 3. Unit Tests

### T01 — Scan orchestrator refactor
File: `tests/collectors/test_scan_liga.py`

| Test function | Verifies |
|---|---|
| `test_run_scan_liga_provider_concurrency_forced_to_1` | When provider_name="liga", concurrency is capped at 1 regardless of param |
| `test_run_scan_liga_delay_default_5s` | Liga path uses 5s inter-card delay |
| `test_run_scan_liga_not_found_skips_card` | `LigaNotFoundError` -> card skipped, not retried |
| `test_run_scan_liga_rate_limit_requeues_with_30s` | `LigaRateLimitError` -> card requeued with 30s cooldown |
| `test_run_scan_liga_generic_error_fails_card` | `LigaError` -> card marked failed |
| `test_run_scan_myp_path_unchanged` | provider_name="myp" follows existing MYP path |
| `test_scan_type_liga_full_enum` | `ScanType.LIGA_FULL` exists and has expected value |
| `test_scan_type_liga_partial_enum` | `ScanType.LIGA_PARTIAL` exists and has expected value |
| `test_run_scan_liga_saves_source_liga` | Observation saved with `source="liga"`, `external_id="liga_{card_id}"` |

### T02 — Repo methods + price priority
File: `tests/unit/database/test_repository_liga.py`

| Test function | Verifies |
|---|---|
| `test_get_cards_for_liga_scan_returns_entries_with_card_id` | Returns entries where card_id IS NOT NULL |
| `test_get_cards_for_liga_scan_excludes_null_card_id` | Entries without card_id omitted |
| `test_get_cards_for_liga_scan_no_source_card_required` | Works without MYP source_card linkage |
| `test_get_cards_for_liga_scan_returns_name_en_and_name_pt` | Dict includes name_en, name_pt fields |
| `test_get_cards_for_liga_scan_filter_set_codes` | `set_codes=["DMR"]` filters correctly |
| `test_get_cards_for_liga_scan_filter_limit` | `limit=5` caps results |
| `test_get_cards_for_liga_scan_max_age_days_skips_recent` | Card with liga price 2 days old skipped when max_age_days=7 is... included; card with 1-day-old price skipped when max_age_days=1 |
| `test_get_cards_for_liga_scan_max_age_days_includes_stale` | Card with liga price 10 days old included when max_age_days=7 |
| `test_get_cards_for_liga_scan_max_age_days_includes_no_price` | Card with no liga price at all is included |
| `test_price_priority_liga_beats_jsonld_same_date` | Liga observation wins over jsonld_snapshot on same date |
| `test_price_priority_manual_beats_liga_same_date` | Manual observation wins over liga on same date |
| `test_price_priority_newer_liga_beats_older_manual` | More recent liga date wins over older manual |
| `test_price_priority_source_priority_map` | `SOURCE_PRIORITY` dict has correct ordering (manual=0, liga=1, jsonld_snapshot=2, myp=3) |

### T03 — Clear prices
File: `tests/database/test_clear_prices.py`

| Test function | Verifies |
|---|---|
| `test_clear_prices_dry_run_returns_count` | dry_run=True returns count, no deletion |
| `test_clear_prices_actual_delete_removes_rows` | dry_run=False deletes matching rows |
| `test_clear_prices_refuses_liga_source` | `source="liga"` raises ValueError |
| `test_clear_prices_refuses_manual_source` | `source="manual"` raises ValueError |
| `test_clear_prices_backup_created_before_delete` | Backup function called before DELETE |
| `test_clear_prices_vacuum_after_delete` | VACUUM runs after deletion |
| `test_clear_prices_scan_runs_untouched` | scan_runs table rows unchanged after clear |
| `test_clear_prices_skip_backup_flag` | `skip_backup=True` skips backup call |

File: `tests/cli/test_clear_prices_cli.py`

| Test function | Verifies |
|---|---|
| `test_cli_db_clear_prices_no_confirm_dry_run` | Without --confirm, runs dry-run |
| `test_cli_db_clear_prices_with_confirm_deletes` | With --confirm, calls actual delete |
| `test_cli_db_clear_prices_protected_source_error` | --source liga exits with error message |

### T04 — Liga scan orchestrator
File: `tests/collectors/test_liga_scan.py`

| Test function | Verifies |
|---|---|
| `test_run_liga_scan_mock_provider_saves_observation` | Mock provider returns price -> observation row created |
| `test_run_liga_scan_provider_returns_none_skips` | Provider returns None -> card skipped |
| `test_run_liga_scan_not_found_error_no_requeue` | LigaNotFoundError -> no requeue attempt |
| `test_run_liga_scan_rate_limit_requeues_once` | LigaRateLimitError -> requeued once, then failed |
| `test_run_liga_scan_concurrency_always_1` | Concurrency param ignored, always 1 |
| `test_run_liga_scan_delay_default_5s` | Default delay is 5.0 seconds |
| `test_run_liga_scan_sse_events_emitted` | scan_started, card_scanned, scan_complete events emitted to bus |
| `test_run_liga_scan_creates_scan_run_liga_full` | ScanRun created with type LIGA_FULL |
| `test_run_liga_scan_creates_scan_run_liga_partial` | With filter/limit -> type LIGA_PARTIAL |
| `test_run_liga_scan_max_age_days_passed_to_repo` | max_age_days forwarded to get_cards_for_liga_scan |
| `test_run_liga_scan_browser_closed_on_error` | Provider close() called even on exception (finally block) |

### T05 — Liga sweep
File: `tests/collectors/test_liga_sweep.py`

| Test function | Verifies |
|---|---|
| `test_sweep_batch_splitting_20_cards_1_batch` | 20 cards -> 1 batch |
| `test_sweep_batch_splitting_50_cards_3_batches` | 50 cards with batch_size=20 -> 3 batches |
| `test_sweep_max_age_days_filtering` | Stale cards included, recent excluded |
| `test_sweep_dry_run_no_provider_calls` | dry_run=True returns counts, provider never called |
| `test_sweep_graceful_interruption_partial_results` | KeyboardInterrupt mid-sweep returns partial LigaSweepResult |
| `test_sweep_result_aggregation` | LigaSweepResult fields correctly summed |
| `test_sweep_set_filter_passed_to_repo` | set_filter forwarded in ScanFilter |
| `test_sweep_limit_caps_total_cards` | limit=10 processes at most 10 cards |
| `test_sweep_single_browser_lifecycle` | Provider created once and closed once |

File: `tests/cli/test_liga_sweep_cli.py`

| Test function | Verifies |
|---|---|
| `test_cli_liga_sweep_default_options` | Default batch_size=20, delay=5.0, max_age_days=7 |
| `test_cli_liga_sweep_dry_run` | --dry-run flag triggers dry_run=True |
| `test_cli_liga_sweep_set_filter` | --set DMR passes set_filter="DMR" |
| `test_cli_liga_sweep_limit` | --limit 100 passes limit=100 |

### T06 — API + CLI provider flag
File: `tests/unit/api/test_scan_provider.py`

| Test function | Verifies |
|---|---|
| `test_trigger_scan_provider_liga_creates_liga_full` | POST /scans with provider="liga" -> LIGA_FULL scan type |
| `test_trigger_scan_provider_myp_creates_collection` | POST /scans with provider="myp" -> existing COLLECTION scan type |
| `test_trigger_scan_default_provider_is_liga` | POST /scans without provider field defaults to "liga" |
| `test_scan_request_schema_accepts_provider` | ScanRequest(provider="liga") validates |
| `test_scan_run_response_includes_provider` | Response includes provider field |

File: `tests/cli/test_scan_provider_cli.py`

| Test function | Verifies |
|---|---|
| `test_cli_scan_provider_liga` | `scan --provider liga` calls run_liga_scan |
| `test_cli_scan_provider_myp` | `scan --provider myp` calls run_scan |
| `test_cli_scan_default_provider_liga` | `scan` without --provider uses liga |

### T07 — Admin link monitor
File: `tests/unit/database/test_repository_liga_coverage.py`

| Test function | Verifies |
|---|---|
| `test_get_liga_coverage_stats_all_priced` | All cards have liga price -> coverage_pct=100 |
| `test_get_liga_coverage_stats_none_priced` | No liga prices -> coverage_pct=0, liga_missing=total |
| `test_get_liga_coverage_stats_mixed` | Some priced, some stale, some missing -> correct counts |
| `test_get_liga_coverage_stats_stale_threshold` | stale_days=7 correctly categorizes 8-day-old price |
| `test_get_liga_missing_cards_returns_only_missing` | Cards with recent liga price excluded |
| `test_get_liga_missing_cards_pagination` | limit/offset work correctly |

File: `tests/api/test_collection_liga_status.py`

| Test function | Verifies |
|---|---|
| `test_get_liga_status_returns_coverage` | GET /collection/liga-status returns LigaStatusResponse |
| `test_get_liga_status_requires_auth` | Unauthenticated request returns 401 |
| `test_get_liga_missing_returns_cards` | GET /collection/liga-missing returns list |
| `test_get_liga_missing_pagination` | offset/limit query params respected |
| `test_get_liga_missing_stale_days_param` | stale_days=14 passed to repo |

### T08 — Card detail button priority (no new backend tests)

### T09 — i18n keys (no backend tests)

### T10 — Scheduled Liga scans
File: `tests/unit/scheduler/test_liga_schedule.py`

| Test function | Verifies |
|---|---|
| `test_scheduler_routes_liga_provider` | Job with `"provider": "liga"` in filters_json calls run_liga_scan |
| `test_scheduler_routes_myp_default` | Job without provider field calls run_scan |
| `test_liga_partial_uses_limit_50` | liga_partial scan type passes limit=50 |
| `test_liga_partial_max_age_days_1` | liga_partial uses max_age_days=1 |
| `test_auto_pause_after_3_failures` | 3 consecutive failures -> schedule paused |
| `test_default_schedules_seeded` | `seed_default_liga_schedules()` creates 2 entries |
| `test_default_schedules_idempotent` | Calling seed twice does not duplicate |

## 4. Integration Tests

### Liga scan end-to-end
File: `tests/integration/test_liga_scan_e2e.py`

| Test function | Verifies |
|---|---|
| `test_liga_scan_3_cards_saves_3_observations` | Mock provider, real in-memory DB: 3 cards -> 3 price_observations rows with source="liga" |
| `test_liga_scan_mixed_results` | 1 found + 1 not-found + 1 error -> correct scan_run counts (1 saved, 1 skipped, 1 failed) |
| `test_liga_scan_observations_visible_in_latest_prices` | After liga scan, `get_latest_prices_batch()` returns liga prices |
| `test_liga_price_overrides_old_myp_price` | Liga observation on same date as MYP -> liga wins in `get_latest_prices_batch()` |

### Liga sweep end-to-end
File: `tests/integration/test_liga_sweep_e2e.py`

| Test function | Verifies |
|---|---|
| `test_sweep_5_cards_batch_2_creates_3_batches` | Mock provider, batch_size=2, 5 cards -> 3 batch iterations, 5 observations |
| `test_sweep_resume_skips_recently_scanned` | Run sweep, then run again with max_age_days=7 -> second run processes 0 cards |

### Clear prices + scan interaction
File: `tests/integration/test_clear_and_rescan.py`

| Test function | Verifies |
|---|---|
| `test_clear_myp_then_liga_scan_replaces_prices` | Clear jsonld_snapshot prices, run liga scan -> only liga prices remain |

## 5. Frontend Tests

### AdminLigaStatus page
File: `frontend/tests/pages/AdminLigaStatus.test.tsx`

| Test function | Verifies |
|---|---|
| `renders summary KPI cards` | Total, Liga Priced, Missing, Stale cards displayed |
| `renders coverage progress bar` | Progress bar width matches coverage_pct |
| `renders missing cards table` | Table rows for cards without Liga price |
| `scan all missing button triggers scan` | Click -> calls triggerScanAuth with provider="liga" |
| `shows empty state when no missing cards` | "All cards have Liga prices" message |
| `polls status when scan running` | Auto-refresh behavior during active scan |

### Card detail button hierarchy
File: `frontend/tests/pages/CollectionCardDetail.liga.test.tsx` (extend existing)

| Test function | Verifies |
|---|---|
| `renders Liga as primary refresh button` | Liga button has emerald/primary styling |
| `renders MYP as secondary refresh button` | MYP button has gray/outline styling |
| `Liga button calls refresh-liga endpoint` | Click -> POST /collection/{id}/refresh-liga |
| `MYP button calls refresh endpoint` | Click -> POST /collection/{id}/refresh |

### PriceSourceBadge colors
File: `frontend/tests/components/PriceSourceBadge.test.tsx` (extend existing)

| Test function | Verifies |
|---|---|
| `liga source shows emerald badge` | source="liga" -> green/emerald color class |
| `myp source shows amber badge` | source="jsonld_snapshot" -> amber color class |
| `manual source shows blue badge` | source="manual" -> blue color class |

### CollectionCardTile + DeckCardTile refresh endpoint
File: `frontend/tests/components/CollectionCardTile.liga.test.tsx`

| Test function | Verifies |
|---|---|
| `refresh calls liga endpoint` | Hover refresh icon click -> POST /collection/{id}/refresh-liga |

File: `frontend/tests/components/DeckCardTile.liga.test.tsx`

| Test function | Verifies |
|---|---|
| `refresh calls liga endpoint` | Hover refresh icon click -> POST /collection/{id}/refresh-liga |

### Scan API + hook
File: `frontend/tests/api/scans.liga.test.ts`

| Test function | Verifies |
|---|---|
| `triggerScanAuth sends provider field` | POST body includes provider |
| `triggerScanAuth defaults provider to liga` | No explicit provider -> "liga" sent |

File: `frontend/tests/hooks/useCollectionRefresh.liga.test.ts`

| Test function | Verifies |
|---|---|
| `uses provider liga by default` | Hook trigger call includes provider="liga" |

### i18n keys
File: `frontend/tests/i18n/liga-keys.test.tsx`

| Test function | Verifies |
|---|---|
| `all admin.ligaStatus keys present in en.json` | ~12 keys exist |
| `all admin.ligaStatus keys present in pt-BR.json` | ~12 keys exist |
| `card.refreshLiga key in both locales` | Key exists in both |
| `card.refreshMyp key in both locales` | Key exists in both |
| `scan.provider keys in both locales` | liga + myp keys in both |
| `key count matches between locales` | en.json and pt-BR.json have same key count |

## 6. Regression Tests

The following existing test files/suites MUST continue to pass without modification:

### Backend
- `tests/unit/api/test_scan_endpoints.py` — existing MYP scan trigger/list/detail tests
- `tests/unit/cli/test_scan_commands.py` — existing CLI scan tests (MYP path)
- `tests/unit/database/test_repository_scans.py` — scan_run CRUD
- `tests/unit/database/test_repository_collection.py` — collection queries
- `tests/collectors/test_snapshot_prices.py` — MYP snapshot price collection
- `tests/api/test_collection_refresh_liga.py` — existing F59 Liga refresh endpoint tests
- `tests/providers/test_liga_provider.py` — F57 Liga provider tests
- `tests/unit/database/test_scheduled_scan_repo.py` — scheduled scan repo tests
- `tests/api/test_collection_detail.py` — collection detail endpoint
- `tests/api/test_collection_sorting.py` — collection sorting
- `tests/unit/api/test_app_lifespan.py` — app startup/shutdown

### Frontend
- `frontend/tests/hooks/useCollectionRefresh.test.ts` — existing refresh hook tests
- `frontend/tests/components/ScanProgressBar.test.tsx` — SSE progress bar
- `frontend/tests/hooks/useScanStream.test.ts` — SSE stream hook
- `frontend/tests/pages/CollectionCardDetail.test.tsx` — existing detail page tests
- `frontend/tests/components/DeckCardTile.test.tsx` — existing deck tile tests
- `frontend/tests/components/PriceSourceBadge.test.tsx` — existing badge tests
- `frontend/tests/pages/Schedules.test.tsx` — schedules page
- `frontend/tests/components/ScheduleForm.test.tsx` — schedule form

### Key regression risks
1. **Price priority change** (T02) could break tests that assert MYP prices win. Search for tests using `get_latest_prices_batch` or asserting `source="jsonld_snapshot"` as winner.
2. **ScanType enum additions** (T01) could break tests that exhaustively match enum values.
3. **Default provider change to liga** (T06) could break tests that assume MYP is default for `/scans` or CLI `scan`.
4. **Refresh endpoint change** (T08) in CollectionCardTile/DeckCardTile could break tests asserting the old `/refresh` URL.

## 7. Coverage Targets

### New test counts (estimated)

| Category | New tests | File count |
|---|---|---|
| Backend unit (T01-T03) | ~30 | 4 files |
| Backend unit (T04-T06) | ~28 | 5 files |
| Backend unit (T07) | ~11 | 2 files |
| Backend unit (T10) | ~7 | 1 file |
| Backend integration | ~7 | 3 files |
| Frontend (T07-T09) | ~28 | 8 files |
| **Total** | **~111** | **23 files** |

### Expected post-F60 counts
- Backend: ~1761 + 83 = **~1844 tests**
- Frontend: ~963 + 28 = **~991 tests**

### Coverage impact
- Target: maintain **>90% backend coverage** (currently 90.11%)
- New modules (`liga_scan.py`, `liga_sweep.py`, `clear_prices_by_source`) must have **>95% line coverage**
- Repository methods (`get_cards_for_liga_scan`, `get_liga_coverage_stats`) must have **100% branch coverage** on filter logic
- Frontend: new `AdminLigaStatus.tsx` page must have **>85% coverage**

### Files requiring highest test density
1. `src/database/repository.py` — price priority logic is critical; every SOURCE_PRIORITY path tested
2. `src/collectors/liga_scan.py` — all error paths (not-found, rate-limit, generic) tested
3. `src/collectors/liga_sweep.py` — batch splitting, resume, interruption tested
4. `src/database/cleanup.py` — protected source guard is a safety invariant; must not regress
