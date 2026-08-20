# F10 Test Plan -- Collection-Centric Pivot
**Status:** drafted
**Generator:** TEA
**Generated at:** 2026-08-19T16:30:00Z
**Source brief:** tasks/features/F10-collection-pivot/F10-README.md

---

## 1. Fixtures

| Fixture | Path | Domain | Owner (task) |
|---------|------|--------|--------------|
| `myp_search_response_bolt` | `tests/fixtures/myp_search_bolt.json` | MYP search API JSON response for "Lightning Bolt" (multiple results across sets) | F10-T01 |
| `myp_search_response_empty` | `tests/fixtures/myp_search_empty.json` | MYP search API JSON response with empty array `[]` | F10-T01 |
| `myp_search_response_single` | `tests/fixtures/myp_search_single.json` | MYP search API JSON response with exactly one result (for unambiguous name match testing) | F10-T01 |
| `collection_entries_fixture` | `tests/fixtures/collection_entries.py` | Python factory: creates 5 `UserCollectionRow` objects with known set_code, collector_number, name_en (covers matched, ambiguous, unmatched scenarios) | F10-T02 |
| `match_search_results_fixture` | `tests/fixtures/match_search_results.py` | Python factory: creates lists of `MypSearchResult` objects for SKU-exact, name+set, ambiguous, and no-match scenarios | F10-T02 |
| `seeded_collection_repo` | `tests/database/conftest.py` or inline | pytest fixture: Repository with `UserCollectionRow` entries + some pre-existing `CardRow`/`SourceCardRow` data, using `tmp_path` SQLite | F10-T04 |
| `sync_provider_mock` | `tests/collectors/conftest.py` or inline | pytest fixture: `MagicMock`/`AsyncMock` of `MypCardsProvider` with `search_card`, `get_card_details`, `get_price_history` returning realistic data | F10-T06 |
| `mockCollectionSummary` | `frontend/tests/fixtures/api-responses.ts` | TypeScript factory: returns `ApiResponse<CollectionSummary>` with total_unique, total_cards, total_value, linked_count fields | F10-T09 |
| `mockEmptyMarketStats` | `frontend/tests/fixtures/api-responses.ts` | TypeScript factory: returns `ApiResponse<MarketStats>` with all-zero values for empty state testing | F10-T09 |

---

## 2. Harnesses por fronteira

### Unit
- **Framework:** pytest (backend), Vitest + React Testing Library (frontend)
- **Command (backend):** `python -m pytest tests/ -v --tb=short`
- **Command (frontend):** `cd frontend && npx vitest run`
- **Default test paths:** `tests/parsers/`, `tests/collection/`, `tests/database/`, `tests/collectors/`, `tests/cli/`, `tests/api/` (backend); `frontend/tests/` (frontend)

### Integration
- **Framework:** pytest + `sqlite:///:memory:` (or `tmp_path` SQLite) for DB-backed tests; FastAPI `TestClient` for API tests
- **Command:** `python -m pytest tests/ -v --tb=short -k integration` (or run specific files: `tests/collectors/test_sync_integration.py`, `tests/api/test_collection_sync_api.py`)
- **Default test paths:** `tests/collectors/test_sync_integration.py`, `tests/api/test_collection_sync_api.py`
- **Note:** Integration tests mock the MYP provider but use a real SQLite engine. This validates the full pipeline from orchestrator through repository to actual DB state.

### E2E
**N/A** -- The sync pipeline involves external HTTP calls to MYP Cards (rate-limited, Cloudflare-protected). E2E testing against the live MYP API is impractical: it takes ~35-55 minutes for 548 cards, is rate-limited, and would be flaky due to external dependency. The integration tests with mocked provider + real DB provide sufficient confidence. Manual verification is documented in individual task files for the scenarios that require real MYP interaction.

---

## 3. Perf budgets

| Metrica | Limite | Como medir | Aplicavel a |
|---------|--------|------------|-------------|
| Unit test suite (backend, all F10 tests) | < 10s | `time python -m pytest tests/parsers/test_myp_search.py tests/collection/ tests/database/test_backup.py tests/database/test_cleanup.py tests/collectors/test_match_report.py tests/collectors/test_sync_collection.py tests/cli/test_sync_collection.py tests/api/test_collection_sync.py -v` | F10-T01 through F10-T08, F10-T12 |
| Integration test suite (F10-T12) | < 10s | `time python -m pytest tests/collectors/test_sync_integration.py tests/api/test_collection_sync_api.py -v` | F10-T12 |
| Frontend test suite (F10 tests) | < 15s | `cd frontend && time npx vitest run tests/components/Dashboard.test.tsx tests/pages/CardDetail.test.tsx` | F10-T09, F10-T10 |
| Overall coverage (backend) | >= 70% | `python -m pytest --cov=src --cov-report=term-missing --cov-fail-under=70` | All tasks |
| Sync orchestrator coverage | >= 85% | `python -m pytest --cov=src/collectors/sync_collection.py --cov-report=term-missing` | F10-T06, F10-T12 |

---

## 4. Mocks vs hits real

| Componente | Decisao | Justificativa |
|------------|---------|---------------|
| MYP search API (`/produto/search`) | **mock** | External rate-limited service behind Cloudflare. Must be mocked in all automated tests. Use realistic JSON fixtures from actual API responses. |
| MYP card page / history page fetch | **mock** | Same rationale: external HTTP calls. Mock `provider.get_card_details()` and `provider.get_price_history()` at the method level. |
| SQLite DB (unit tests for backup/cleanup) | **real** | Use `tmp_path` SQLite files for backup tests (need real file I/O to test `sqlite3.backup()`). Use `sqlite:///:memory:` for cleanup logic tests. |
| SQLite DB (integration tests) | **real** | Use `tmp_path` SQLite (not `:memory:`) for sync integration tests -- needed to verify full pipeline writes and reads. Matches existing pattern in `test_repository_api.py`. |
| FastAPI TestClient | **real** | Use real `TestClient` from `fastapi.testclient` -- no mocking needed. This is the established project pattern. |
| `verify_api_key` dependency | **real** | Test with `monkeypatch.setenv("TCG_API_KEY", ...)` -- real dependency, controlled via env vars. Matches existing `test_collect_auth.py` pattern. |
| `run_sync_collection` (in CLI tests) | **mock** | CLI tests verify argument passing, not pipeline logic. Mock the orchestrator function, assert it receives correct kwargs. |
| `run_sync_collection` (in API tests) | **mock** | API endpoint tests verify HTTP contract (status, schema, auth). Mock the orchestrator via `asyncio.create_task` or patch. |
| Collection matcher (pure functions) | **real** | Pure functions with no side effects. Test directly with constructed inputs. No mocking needed. |
| `parse_search_results` parser | **real** | Pure function. Feed it JSON fixture strings, assert output. No mocking. |
| Frontend `fetch` calls | **mock** | Use `vi.stubGlobal("fetch", vi.fn())` pattern already established in `Dashboard.test.tsx`. Mock responses with fixture factories from `api-responses.ts`. |
| `Date.now()` (frontend freshness) | **mock** | Use `vi.spyOn(Date, "now")` when testing time-dependent display. Matches existing pattern. |

---

## 5. Test scenarios resumo

### Wave 0 -- Dry-run Match Report

1. **(F10-T01)** `parse_search_results` correctly parses a valid MYP search JSON response into a list of `MypSearchResult` objects.
2. **(F10-T01)** `parse_search_results` returns empty list for an empty JSON array `[]`.
3. **(F10-T01)** `parse_search_results` returns empty list (no crash) for malformed JSON input.
4. **(F10-T01)** `parse_search_results` handles a response with missing optional fields gracefully (partial `MypSearchResult`).
5. **(F10-T01)** `MypCardsProvider.search_card` calls `_fetch` with correctly encoded URL for special characters (accents, apostrophes).
6. **(F10-T01)** `MypCardsProvider.search_card("")` returns empty list without calling the API.
7. **(F10-T01)** `MypCardsProvider.search_card` returns parsed results from mocked `_fetch` response.
8. **(F10-T02)** Matcher returns `status="matched"`, `confidence="sku_exact"` when search result SKU matches collection entry's `set_code + collector_number`.
9. **(F10-T02)** Matcher returns `status="matched"`, `confidence="name_set"` when name matches and set can be confirmed but SKU is absent.
10. **(F10-T02)** Matcher returns `status="ambiguous"` when multiple candidates match by name but none by SKU.
11. **(F10-T02)** Matcher returns `status="unmatched"` when search results list is empty.
12. **(F10-T02)** Set code comparison is case-insensitive (`DMR` vs `dmr` both match).
13. **(F10-T02)** Collector numbers with letters (`"123a"`) match correctly via string comparison.
14. **(F10-T02)** When no search result has a SKU, matcher falls back to name-based matching.
15. **(F10-T03)** Match report orchestrator produces correct summary counts (matched, ambiguous, unmatched) from mocked provider + matcher.
16. **(F10-T03)** `--limit` flag restricts processing to N cards.
17. **(F10-T03)** Match report makes zero DB write calls (read-only operation).

### Wave 1 -- DB Backup + Cleanup + Normalization

18. **(F10-T04)** `backup_database` creates a valid SQLite file with timestamp in filename.
19. **(F10-T04)** `backup_database` backup file contains the same data as the source DB.
20. **(F10-T04)** Cleanup dry-run reports correct counts of rows that would be deleted, without mutating the DB.
21. **(F10-T04)** Cleanup deletes `cards`, `source_cards`, and `price_observations` rows not linked to any `user_collection` entry.
22. **(F10-T04)** Cleanup preserves all cards that ARE linked to `user_collection` entries (and their associated source_cards/price_observations).
23. **(F10-T04)** Cleanup refuses to run when `user_collection` table is empty (safety check).
24. **(F10-T04)** Cleanup calls backup before deleting (unless `--no-backup` is passed).
25. **(F10-T05)** `parse_sku("magic_LTR_748")` returns `("ltr", "748")` -- lowercase set code.
26. **(F10-T05)** Existing tests that assert uppercase set codes from `parse_sku` are updated to expect lowercase.

### Wave 2 -- Core Sync Pipeline

27. **(F10-T06)** Sync pipeline for a matched card: creates `CardRow`, `SourceCardRow`, inserts `PriceObservationRow`s, sets `card_id` on `UserCollectionRow`.
28. **(F10-T06)** Unmatched cards are logged but not stored; `card_id` remains `NULL`.
29. **(F10-T06)** `skip_matched=True` skips entries where `card_id IS NOT NULL`.
30. **(F10-T06)** `dry_run=True` does not call any repository write methods.
31. **(F10-T06)** Provider exception on one card does not abort the entire sync (graceful degradation).
32. **(F10-T06)** `SyncSummary` counts (matched, ambiguous, unmatched, errors, cards_created, observations_saved) are accurate.
33. **(F10-T06)** Collection entries without `name_en` are skipped and counted separately.

### Wave 3 -- CLI + API

34. **(F10-T07)** CLI `sync-collection` passes `--dry-run`, `--limit`, `--delay`, `--history-days`, `--concurrency` to `run_sync_collection` correctly.
35. **(F10-T07)** CLI `--force` flag maps to `skip_matched=False`.
36. **(F10-T07)** CLI prints a formatted summary after sync completes.
37. **(F10-T08)** `POST /api/v1/collection/sync` returns 200 with `job_id` and `status="started"`.
38. **(F10-T08)** `POST /api/v1/collection/sync` without API key returns 401 when `TCG_API_KEY` is set.
39. **(F10-T08)** Request body validation rejects invalid types (e.g., `limit="abc"`).

### Wave 4 -- Frontend Adjustments

40. **(F10-T09)** Dashboard renders collection KPIs (cards, copies, value, coverage) when collection summary API returns data.
41. **(F10-T09)** Dashboard renders gracefully (no crash, shows empty state) when collection summary returns zero values.
42. **(F10-T09)** Dashboard renders gracefully when market stats returns zero values.
43. **(F10-T09)** Cards page shows updated empty state message post-cleanup.
44. **(F10-T10)** CardDetail renders a Scryfall image `<img>` when `set_code` and `collector_number` are present.
45. **(F10-T10)** CardDetail does NOT render an image when `set_code` is null.
46. **(F10-T10)** Image `onError` handler hides the element (sets `display: none`).
47. **(F10-T10)** MarketMovers page shows updated empty state message when no movers data.

### Wave 5 -- Documentation + Integration Tests

48. **(F10-T11)** Documentation verification only (no automated tests): PRD, diagrams, ADR, README files exist and are valid. Manual check.
49. **(F10-T12)** Integration: full sync happy path -- 3-5 collection entries, mocked provider, real DB. Assert cards/source_cards/observations created, user_collection.card_id set.
50. **(F10-T12)** Integration: partial match -- 5 entries, 3 matched, 2 unmatched. Assert SyncSummary counts and DB state.
51. **(F10-T12)** Integration: resume after partial sync -- run with limit, then again with skip_matched=True. Assert no duplicates.
52. **(F10-T12)** Integration: error recovery -- provider raises on 1 card. Assert sync completes, error counted, other cards synced.
53. **(F10-T12)** Integration: cleanup + sync -- pre-populate non-collection cards, run cleanup, run sync. Assert only collection cards remain with price data.
54. **(F10-T12)** Integration: API endpoint -- TestClient POST to `/api/v1/collection/sync`, assert 200 + job_id; POST without auth, assert 401.

---

## 6. Anotacoes para tasks

| Task | Fixture slugs |
|------|---------------|
| F10-T01 | `myp_search_response_bolt`, `myp_search_response_empty`, `myp_search_response_single` |
| F10-T02 | `collection_entries_fixture`, `match_search_results_fixture` |
| F10-T03 | `collection_entries_fixture`, `sync_provider_mock` |
| F10-T04 | `seeded_collection_repo` |
| F10-T05 | (no shared fixtures -- updates existing `test_myp.py` assertions) |
| F10-T06 | `sync_provider_mock`, `collection_entries_fixture`, `seeded_collection_repo` |
| F10-T07 | (no shared fixtures -- mocks `run_sync_collection` directly) |
| F10-T08 | (no shared fixtures -- uses TestClient + mocks orchestrator) |
| F10-T09 | `mockCollectionSummary`, `mockEmptyMarketStats` |
| F10-T10 | (no new shared fixtures -- extends existing `mockCardDetail` in `api-responses.ts`) |
| F10-T11 | (no automated tests -- documentation verification only) |
| F10-T12 | `sync_provider_mock`, `collection_entries_fixture`, `seeded_collection_repo`, `myp_search_response_bolt` |
