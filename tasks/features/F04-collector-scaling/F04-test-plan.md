# F04 Test Plan -- Collector Scaling: Batch Upsert, Concurrency, Integration Tests

**Status:** drafted
**Generator:** TEA (Test Architect)
**Generated at:** 2026-08-18
**Source brief:** F04 prepares the collector pipeline to scale from 30 cards to the full MYP catalog (~10k+ cards) via batch upsert (T01), concurrent card processing with resume (T02), and integration tests for the full collector pipeline (T03). Identified as ACT-06/07/08 in Gandalf review D-20260818-001.

---

## 1. Fixtures

| Fixture | Path | Domain | Owner |
|---------|------|--------|-------|
| `batch_prices` | `tests/unit/test_repository.py` | List of 10 `HistoricalPrice` objects with distinct `(source, external_id, observed_at)` | F04-T01 |
| `large_batch_prices` | `tests/unit/test_repository.py` | List of 600 `HistoricalPrice` objects (exceeds 500 chunk size) | F04-T01 |
| `duplicate_prices` | `tests/unit/test_repository.py` | Subset of `batch_prices` for duplicate insertion tests | F04-T01 |
| `mock_provider` | `tests/unit/test_backfill.py` | `AsyncMock` of `MypCardsProvider` with configurable `discover_sets`, `discover_cards`, `get_card_details`, `get_price_history` | F04-T02 |
| `mock_repo` | `tests/unit/test_backfill.py` | `MagicMock` of `Repository` with `get_cards_with_observations` returning configurable collected IDs | F04-T02 |
| `editions_html` | `tests/fixtures/editions_page.html` | Minimal HTML with 2 set links parseable by `parse_set_links` | F04-T03 |
| `set_page_html` | `tests/fixtures/set_page.html` | Minimal HTML with 3 card links parseable by `parse_card_links` | F04-T03 |
| `card_page_html` | `tests/fixtures/card_page.html` | Minimal HTML with JSON-LD `@type: Product` schema parseable by `parse_card_page` | F04-T03 |
| `history_page_html` | `tests/fixtures/history_page.html` | Minimal HTML with `window.precoChartConfig` JS var parseable by `parse_price_history` | F04-T03 |
| `db_url` | `tests/integration/test_collector_pipeline.py` | `"sqlite:///:memory:"` for in-memory SQLite | F04-T03 |
| `mock_fetch` | `tests/integration/test_collector_pipeline.py` | Patched `MypCardsProvider._fetch` that maps URL patterns to HTML fixture strings | F04-T03 |

**Justification:** HTML fixtures are critical for T03 integration tests -- they must be minimal but structurally valid so the real parsers can extract data. Reuse patterns from `tests/unit/test_parsers.py` where possible. The `_fetch` mock is the single HTTP seam: everything downstream (parsers, repository, SQLite) runs real code.

---

## 2. Harnesses por fronteira

### Unit

- **Framework:** pytest, pytest-asyncio
- **Command:** `python -m pytest tests/unit/ -v`
- **Test files:**
  - `tests/unit/test_repository.py` -- existing file, add batch upsert test cases (F04-T01)
  - `tests/unit/test_backfill.py` -- new file, tests for concurrency and resume logic (F04-T02)

### Integration

- **Framework:** pytest, pytest-asyncio, in-memory SQLite
- **Command:** `python -m pytest tests/integration/ -v`
- **Test files:**
  - `tests/integration/test_collector_pipeline.py` -- new file, full pipeline tests with mocked HTTP (F04-T03)
- **Database:** `sqlite:///:memory:` -- no file I/O, no cleanup needed, fast execution
- **Mock boundary:** only `MypCardsProvider._fetch` is mocked; parsers, repository, and SQLite run real code

### E2E

**N/A** -- The collector is a CLI tool operating against a local SQLite database and a single external website (MYP Cards). True E2E would require hitting the real MYP site, which is Cloudflare-protected and rate-limited. The integration tests with mocked HTTP provide equivalent coverage of the full pipeline (CLI args -> backfill orchestration -> provider -> parser -> repository -> SQLite). Manual E2E validation against the real site is documented in QA procedures but is not automatable without flakiness risk.

---

## 3. Perf budgets

| Metrica | Limite | Como medir | Aplicavel a |
|---------|--------|------------|-------------|
| Batch upsert 600 rows | < 500ms | `pytest --durations=5` on `test_large_batch` | F04-T01 |
| Integration suite total | < 5s | `python -m pytest tests/integration/ --durations=10` | F04-T03 |
| Full test suite (unit + integration) | < 10s | `python -m pytest tests/ --durations=10` | All |
| No individual test > 2s | < 2s per test | `pytest --durations=0` | All F04 tests |

**Note:** Concurrency tests (F04-T02) must NOT rely on wall-clock timing to verify semaphore limits -- use semaphore tracking or mock instrumentation instead. Timing-based assertions are inherently flaky in CI.

---

## 4. Mocks vs hits real

| Componente | Decisao | Justificativa |
|------------|---------|---------------|
| `curl_cffi` HTTP requests | **mock** | No real network calls. Mock `MypCardsProvider._fetch` to return pre-built HTML strings. Integration tests must be deterministic and offline. |
| SQLite database (unit tests) | **real** | `tests/unit/test_repository.py` already uses real SQLite via `tmp_path`. Batch upsert tests must exercise real `INSERT ON CONFLICT DO NOTHING` behavior. |
| SQLite database (integration tests) | **real** | `sqlite:///:memory:` -- exercises real SQLAlchemy ORM, real schema creation, real upsert logic. |
| `src/parsers/myp.py` | **real** | Parsers are pure functions (HTML in, data out). Integration tests feed them realistic HTML fixtures -- mocking parsers would defeat the purpose. |
| `src/database/repository.py` (in unit backfill tests) | **mock** | F04-T02 unit tests mock Repository to isolate concurrency/resume logic from DB concerns. |
| `src/database/repository.py` (in integration tests) | **real** | Integration tests exercise the full stack including real Repository against in-memory SQLite. |
| `MypCardsProvider` (in unit backfill tests) | **mock** | F04-T02 unit tests mock the provider to control discovery and card detail responses without HTTP. |
| `asyncio.Semaphore` | **real** | Do not mock the semaphore -- verify concurrency behavior via instrumentation (e.g., track max concurrent invocations with a counter). |

---

## 5. Test scenarios resumo

### F04-T01 (Batch Upsert) -- 6 tests

1. **Happy path:** Insert 10 new observations, verify returned count == 10 and all rows in DB (F04-T01)
2. **Duplicates:** Insert 10, then insert same 10 again, verify second call returns 0 (F04-T01)
3. **Mixed new + duplicate:** Insert 10, then insert 15 where 10 overlap, verify count == 5 (F04-T01)
4. **Empty list:** Insert empty list, verify returns 0, no DB error (F04-T01)
5. **Large batch (chunk boundary):** Insert 600 observations (exceeds 500 chunk size), verify all 600 inserted correctly (F04-T01)
6. **Single observation:** Insert 1 observation, verify count == 1 (F04-T01)

### F04-T02 (Concurrency + Resume) -- 6 tests

7. **Resume skip:** Mock repo with 5 collected IDs, discover 10 cards, verify only 5 are processed (F04-T02)
8. **No resume:** Same setup with resume=False, verify all 10 are processed (F04-T02)
9. **Concurrency limit:** Mock provider with tracking, run with concurrency=2, verify max 2 concurrent via counter (not timing) (F04-T02)
10. **Error isolation:** One card raises Exception, verify others complete successfully and summary.cards_failed == 1 (F04-T02)
11. **Empty discovery:** Discover 0 cards, verify clean exit with summary.cards_discovered == 0 (F04-T02)
12. **Dry run + resume:** Verify resume filtering is skipped when dry_run=True (F04-T02)

### F04-T03 (Integration Tests) -- 10 tests

13. **Full backfill pipeline:** Discover sets -> discover cards -> get details -> get history -> verify data in DB (F04-T03)
14. **Backfill with set_filter:** Only cards from filtered set are processed (F04-T03)
15. **Backfill dry_run:** No rows written to DB (F04-T03)
16. **Backfill resume skips collected:** Pre-populate DB with card observations, run backfill, verify those cards are skipped (F04-T03)
17. **Backfill card error continues:** One card's detail page returns invalid HTML, verify other cards succeed (F04-T03)
18. **Update existing cards:** `run_update` fetches recent history for cards already in DB (F04-T03)
19. **Retry failed cards:** `run_retry_failed` retries cards with unresolved errors in DB (F04-T03)
20. **Retry no errors:** `run_retry_failed` with no errors in DB returns clean summary (F04-T03)
21. **Backfill concurrent:** Verify concurrency parameter is passed through and functional (F04-T03)
22. **Summary counts accurate:** Verify `CollectionSummary` fields (discovered, processed, failed, skipped) match expected values (F04-T03)

### Regression

23. **All 105 existing tests pass:** Run full suite `python -m pytest tests/ -v` -- no regressions from batch upsert or concurrency changes (AC5)

---

## 6. Anotacoes para tasks

| Task | Fixtures needed |
|------|----------------|
| F04-T01 | `batch_prices`, `large_batch_prices`, `duplicate_prices` |
| F04-T02 | `mock_provider`, `mock_repo` |
| F04-T03 | `editions_html`, `set_page_html`, `card_page_html`, `history_page_html`, `db_url`, `mock_fetch` |

---

## Risks for QA

1. **SQLite `rowcount` reliability with ON CONFLICT DO NOTHING.** The task assumes `result.rowcount` returns only actually-inserted rows. This is documented SQLite behavior but should be verified in the batch upsert tests. If unreliable, fallback to count-before/count-after approach as noted in F04-T01 dev notes.

2. **Concurrency test flakiness.** Tests verifying semaphore limits must NOT use wall-clock timing. Use an atomic counter (`asyncio.Lock` + max-concurrent tracker) to verify the concurrency limit is respected. Any timing-based assertion will be flaky in CI environments with variable CPU load.

3. **HTML fixture drift.** The integration test HTML fixtures must match the parser expectations exactly. If parsers are updated (e.g., new CSS selectors), the fixtures must be updated in sync. Consider a comment in each fixture file referencing the parser function it feeds.

4. **`asyncio_mode = "auto"` dependency.** Both T02 and T03 tests use `pytest-asyncio`. Verify `pyproject.toml` has `asyncio_mode = "auto"` configured. If not, all async test functions need explicit `@pytest.mark.asyncio` decorators.

5. **Provider `_fetch` mock seam.** The integration tests mock at `MypCardsProvider._fetch`. If the provider's internal structure changes (e.g., renaming `_fetch` to `_request`), all integration tests break. This is an acceptable coupling for integration tests but should be noted.
