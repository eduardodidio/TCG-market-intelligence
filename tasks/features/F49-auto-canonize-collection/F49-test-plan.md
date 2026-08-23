# F49 Auto-Canonize Collection — Test Plan

**Status:** drafted
**Generator:** TEA
**Generated at:** 2026-08-22
**Source brief:** F49-README.md (AC1–AC5: bulk canonize endpoint, auto-canonize on CSV import, CLI command, frontend UI, i18n)

---

## 1. Test Strategy Overview

F49 adds bulk canonization across four boundaries: a new async service (`bulk_canonize`), an API endpoint, a CLI command, a CSV import hook, and frontend UI with i18n. The existing single-card canonize logic (`tests/api/test_collection_canonize.py`) already validates MYP provider interaction patterns (mock provider, mock matcher, mock converter). F49 tests reuse those patterns and extend them to batch/loop scenarios.

**Key risks:**
- Concurrency control (semaphore) under rate limiting
- Background task lifecycle (import triggers canonize without blocking response)
- Orphan detection (card_id present but no SourceCardRow)

**Frameworks:**
- Backend: pytest + pytest-cov (target >=70%, project currently at ~91%)
- Frontend: Vitest + React Testing Library
- E2E: **N/A** — no E2E framework in project; coverage handled by integration + frontend unit tests

---

## 2. Fixtures

| Fixture | Path | Domain | Owner |
|---------|------|--------|-------|
| `make_unlinked_collection_rows` | `tests/collectors/test_bulk_canonize.py` (inline) | db/domain | F49-T01 |
| `make_orphan_collection_rows` | `tests/collectors/test_bulk_canonize.py` (inline) | db/domain | F49-T01 |
| `mockBulkCanonizeResult` | `frontend/tests/fixtures/api-responses.ts` | api | F49-T04 |
| Reuse: `_make_collection_row` | `tests/api/test_collection_canonize.py` | db | existing |
| Reuse: `myp_search_responses` | `tests/fixtures/myp_search_responses.py` | provider | existing |

Fixtures are inline helpers following the project pattern (see `_make_scan_run` in `tests/unit/cli/test_scan_commands.py`). No shared fixture file needed — each test module defines its own minimal helpers. Justified by: the bulk canonize service is the only consumer of these builders; extracting to a shared module would add indirection with no reuse benefit.

---

## 3. Harnesses por fronteira

### Unit

- **Framework:** pytest
- **Command:** `pytest tests/collectors/test_bulk_canonize.py tests/unit/cli/test_canonize_all.py tests/unit/api/test_canonize_all_schema.py -v`
- **Default test path:** `tests/collectors/`, `tests/unit/cli/`, `tests/unit/api/`

### Integration

- **Framework:** pytest + FastAPI TestClient
- **Command:** `pytest tests/api/test_collection_canonize_all.py tests/api/test_collection_import_canonize.py -v`
- **Default test path:** `tests/api/`

### Frontend Unit

- **Framework:** Vitest + React Testing Library
- **Command:** `cd frontend && npx vitest run tests/components/BulkCanonizeButton.test.tsx tests/pages/MyCollection.test.tsx tests/i18n/canonize-keys.test.tsx`
- **Default test path:** `frontend/tests/`

### E2E

**N/A** — Project has no E2E framework (Cypress/Playwright). Frontend integration is covered by React Testing Library render tests with mocked fetch.

---

## 4. Perf budgets

| Metrica | Limite | Como medir | Aplicavel a |
|---------|--------|------------|-------------|
| Bulk canonize throughput | <=2s per card (including MYP round-trip) | structlog timing in `bulk_canonize` | F49-T01 |
| API response time (202) | <500ms (non-blocking) | TestClient wall time | F49-T01 |

_Perf budgets are soft guidelines, not CI gates. The MYP provider already has rate limiting and backoff; bulk canonize inherits those constraints._

---

## 5. Mocks vs hits real

| Componente | Decisao | Justificativa |
|------------|---------|---------------|
| MypCardsProvider | mock | External service, rate-limited, Cloudflare-protected. Mocking prevents flaky tests and respects MYP TOS. Matches existing pattern in `test_collection_canonize.py`. |
| SQLAlchemy repository | mock | Unit tests mock repo; integration tests use FastAPI TestClient with dependency overrides (existing pattern). |
| `match_collection_card` | mock | Pure function tested separately in `tests/collection/`. Mock in service tests to isolate bulk loop logic. |
| `asyncio.Semaphore` | real | Concurrency primitive is deterministic and fast. No reason to mock. |
| FastAPI BackgroundTasks | mock | Verify task is scheduled without actually running async canonize. Matches `test_collection_sync.py` pattern (`patch asyncio.create_task`). |
| i18n JSON files | real | Static files, read directly in tests. Matches `banHistory-keys.test.tsx` pattern. |
| fetch (frontend) | mock | `vi.fn()` mock as per all existing frontend tests. |

---

## 6. Test scenarios resumo

### F49-T01 — Bulk Canonize Service + Endpoint

1. `test_bulk_canonize_skips_already_linked` — entries with card_id + source_cards are skipped (count in `skipped`) [F49-T01]
2. `test_bulk_canonize_processes_unlinked` — entries with card_id=NULL are processed, canonize called [F49-T01]
3. `test_bulk_canonize_handles_orphans` — entries with card_id but no SourceCardRow are re-processed [F49-T01]
4. `test_bulk_canonize_respects_limit` — when limit=N, only first N entries processed [F49-T01]
5. `test_bulk_canonize_rate_limit_handling` — 429 from MYP counted in `rate_limited`, does not abort batch [F49-T01]
6. `test_bulk_canonize_concurrency_semaphore` — verify semaphore(concurrency) limits parallel calls [F49-T01]
7. `test_bulk_canonize_summary_counts` — returned summary has correct total/canonized/failed/skipped/rate_limited [F49-T01]
8. `test_bulk_canonize_empty_collection` — no unlinked entries returns summary with all zeros [F49-T01]
9. `test_canonize_all_endpoint_auth_required` — POST /collection/canonize-all returns 401 without token [F49-T01]
10. `test_canonize_all_endpoint_returns_202` — returns 202 Accepted with BulkCanonizeResult schema [F49-T01]
11. `test_canonize_all_endpoint_accepts_limit_param` — query param limit forwarded to service [F49-T01]
12. `test_canonize_all_schema_validation` — BulkCanonizeResult has all required fields [F49-T01]

### F49-T02 — Auto-Canonize Hook on CSV Import

13. `test_import_returns_new_entry_ids` — ImportResult includes list of newly created entry IDs [F49-T02]
14. `test_import_skips_existing_entries` — duplicate rows not in new_entry_ids [F49-T02]
15. `test_import_result_has_canonize_scheduled` — schema field canonize_scheduled present and defaults False [F49-T02]
16. `test_import_triggers_background_canonize` — background task scheduled after import with new_entry_ids [F49-T02]
17. `test_import_canonize_does_not_block_response` — import returns 200 before canonize completes [F49-T02]
18. `test_import_no_new_entries_skips_canonize` — when all entries are duplicates, no background task scheduled [F49-T02]

### F49-T03 — Bulk Canonize CLI Command

19. `test_canonize_all_cli_dry_run` — prints unlinked count, no MYP calls made [F49-T03]
20. `test_canonize_all_cli_with_limit` — passes limit to bulk_canonize service [F49-T03]
21. `test_canonize_all_cli_prints_summary` — output contains total/canonized/failed/rate_limited [F49-T03]
22. `test_canonize_all_cli_requires_user_id` — exits with error if --user-id not provided [F49-T03]
23. `test_canonize_all_cli_default_concurrency` — defaults to concurrency=3 [F49-T03]

### F49-T04 — Frontend Bulk Canonize UI

24. `test_canonize_all_button_hidden_when_all_linked` — BulkCanonizeButton not rendered when linked_count == total_unique [F49-T04]
25. `test_canonize_all_button_visible_when_unlinked` — rendered with unlinked count when linked_count < total_unique [F49-T04]
26. `test_canonize_all_button_calls_api` — fires POST /collection/canonize-all on click [F49-T04]
27. `test_canonize_all_shows_loading` — shows spinner/loading state while request in-flight [F49-T04]
28. `test_canonize_all_shows_result` — displays summary toast/banner after completion [F49-T04]
29. `test_canonize_all_refreshes_collection` — triggers collection data re-fetch on completion [F49-T04]
30. `test_canonize_all_button_disabled_during_loading` — button not clickable while canonizing [F49-T04]

### F49-T05 — i18n Keys

31. `test_i18n_canonize_keys_exist_en` — all ~7 canonize keys present in en.json [F49-T05]
32. `test_i18n_canonize_keys_exist_pt` — all ~7 canonize keys present in pt-BR.json [F49-T05]
33. `test_canonize_button_uses_i18n` — BulkCanonizeButton renders translated text via t() [F49-T05]

---

## 7. Test file paths and coverage targets

### Backend test files

| File | Scenarios | Task |
|------|-----------|------|
| `tests/collectors/test_bulk_canonize.py` | #1–#8 | F49-T01 |
| `tests/unit/api/test_canonize_all_schema.py` | #12 | F49-T01 |
| `tests/api/test_collection_canonize_all.py` | #9–#11 | F49-T01 |
| `tests/collection/test_importer_canonize.py` | #13–#15, #18 | F49-T02 |
| `tests/api/test_collection_import_canonize.py` | #16–#17 | F49-T02 |
| `tests/unit/cli/test_canonize_all.py` | #19–#23 | F49-T03 |

### Frontend test files

| File | Scenarios | Task |
|------|-----------|------|
| `frontend/tests/components/BulkCanonizeButton.test.tsx` | #24–#27, #30 | F49-T04 |
| `frontend/tests/pages/MyCollection.test.tsx` (extend) | #28–#29 | F49-T04 |
| `frontend/tests/i18n/canonize-keys.test.tsx` | #31–#33 | F49-T05 |

### Coverage targets

| Scope | Target | Current |
|-------|--------|---------|
| Backend overall (`--cov=src`) | >=70% (CI gate) | 91.61% |
| `src/collectors/bulk_canonize.py` | >=90% | new |
| `src/api/routers/collection.py` (canonize-all additions) | >=85% | existing |
| `src/collection/importer.py` (new_entry_ids + hook) | >=85% | existing |
| `src/cli/main.py` (canonize-all command) | >=80% | existing |
| Frontend: BulkCanonizeButton | >=90% | new |
| Frontend: i18n canonize keys | 100% | new |

**Estimated new tests:** ~18 backend + ~10 frontend = ~28 tests total.

---

## 8. Anotacoes para tasks

| Task | Fixtures |
|------|----------|
| F49-T01 | `make_unlinked_collection_rows`, `make_orphan_collection_rows`, reuse `_make_collection_row`, reuse `myp_search_responses` |
| F49-T02 | reuse `_make_collection_row` |
| F49-T03 | reuse `_make_collection_row` |
| F49-T04 | `mockBulkCanonizeResult` |
| F49-T05 | (none — reads static JSON) |
