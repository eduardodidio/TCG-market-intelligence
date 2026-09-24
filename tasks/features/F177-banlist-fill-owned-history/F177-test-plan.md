# F177-test-plan — Ban list: populate + "Somente minha coleção" + history modal

- **Status:** drafted
- **Generator:** TEA
- **Generated-at:** 2026-09-24
- **Source-brief:** `tasks/features/F177-banlist-fill-owned-history/_brief/00-overview.md` (+ `01-sync-fix.md`, `02-backend-api.md`, `03-frontend.md`, `04-routing-docs-ops.md`)

## 1. Fixtures

| Fixture | Path | Domain | Owner |
|---|---|---|---|
| `sqlite-fixture` | `tests/banlist/test_repository.py` pattern (temp `Repository(f"sqlite:///{tmp_path}/t.db")`, no new file — each test module builds its own via this pattern) | db | F177-T03 |
| `bulk-jsonl-sample` | `tests/banlist/fixtures/bulk_sample.jsonl` (3 cards: 1 commander-banned, 1 vintage-restricted, 1 all-legal; includes a Liga-style set code + zero-padded/non-padded collector-number pair) | sync | F177-T06 |
| `bulk-jsonl-gz-sample` | `tests/banlist/fixtures/bulk_sample.jsonl.gz` (gzip of the same 3 records, byte-identical content to `bulk-jsonl-sample`) | sync | F177-T06 |
| `bulk-json-array-sample` | `tests/banlist/fixtures/bulk_sample_array.json` (legacy `[`, `{...},` × N, `]` shape, with a CRLF line and a blank line injected) | sync | F177-T06 |
| `mock-transport` | inline `httpx.MockTransport` handlers in `tests/banlist/test_sync_f177.py` (302→200 redirect case, chunked-body case with 7-byte chunks, malformed-line case) | sync | F177-T06 |
| `api-test-client` | reuse of `tests/banlist/test_api.py` app/db fixtures + dependency override for `get_optional_user` (fake `User(id="u1")`) | api | F177-T07 |
| `frontend-modal-mock` | `vi.mock("../../src/api/banlist")` block in `frontend/tests/components/BanCardDetailModal.test.tsx` (legalities + history payloads, incl. a `scryfall_baseline` event) | frontend | F177-T05 |
| `frontend-banlist-mock` | `vi.mock("../../src/api/banlist")` + `vi.mock("../../src/hooks/useAuth")` blocks in `frontend/tests/pages/BanList.test.tsx` (grouped entries incl. `printings`/`owned`/`owned_quantity`, status payload) | frontend | F177-T08 |
| `i18n-locale-json` | `frontend/src/i18n/locales/en.json`, `frontend/src/i18n/locales/pt-BR.json` (existing files, new `banlist.*` keys added in place) | frontend/i18n | F177-T02 |
| `bat-static-check` | `bats/banlist-sync.bat` itself, read as text by its own regression test | infra | F177-T10 |

## 2. Harnesses por fronteira

### Unit
- Framework: pytest (backend), Vitest + React Testing Library (frontend)
- Command: `pytest tests/banlist/ -v` (backend); `cd frontend && npx vitest run tests/components/BanCardDetailModal.test.tsx` (frontend component)
- Default test path: `tests/banlist/` (backend pure helpers, writer, queries); `frontend/tests/components/`, `frontend/tests/i18n/`

### Integration
- Framework: pytest + FastAPI `TestClient` (backend API against a real temp-SQLite DB); Vitest + RTL with mocked API client (frontend pages)
- Command: `pytest tests/banlist/test_api_f177.py tests/banlist/test_api.py -v` (backend); `cd frontend && npx vitest run tests/pages/BanList.test.tsx tests/api/banlist.test.ts tests/routes/banlistRedirect.test.tsx` (frontend)
- Default test path: `tests/banlist/test_api_f177.py`; `frontend/tests/pages/`, `frontend/tests/routes/`

### E2E
**N/A** — the project has no browser-driven E2E harness (no Playwright/Cypress runner configured for the app), and the sandbox cannot reach Scryfall (proxy CONNECT 403) to exercise a real sync end-to-end. Post-merge manual verification is the user's own responsibility per the feature's "Operational note" (run `bats\banlist-sync.bat` once locally, then check `/banlist` in a browser) — this is out of scope for automated CI.

## 3. Perf budgets

| Métrica | Limite | Como medir | Aplicável a |
|---|---|---|---|
| Legality writer batching | 1201 rows → ≤ 3 `Session.execute` calls (CHUNK_SIZE=500) | spy/patch `Session.execute`, assert call count, in `test_legality_writer.py` | F177-T03 |
| Diff-only re-sync | Second sync run on unchanged data → 0 upserts, 0 history rows written | assert row counts before/after second `run_banlist_sync` call, in `test_sync_f177.py` | F177-T06 |
| Grouped list query | No N+1: `list_banlist_grouped` must not issue one query per group | count `Session.execute`/`Session.exec` calls stay O(1) relative to group count (e.g. ≤ 3 queries for any page size), in `test_banlist_queries.py` | F177-T04 |

_No latency/SLA budgets apply — Scryfall network calls aren't reachable in CI, so wall-clock timing there is not testable; the only enforceable perf property is "batched, not per-row," which the row-count/call-count assertions above already cover per `feedback_no_ceremony_specs.md` (no ceremony budgets without a concrete regression they catch)._

## 4. Mocks vs hits real

| Componente | Decisão | Justificativa |
|---|---|---|
| Scryfall bulk download (httpx) | mock (`httpx.MockTransport`) | Sandbox proxy returns CONNECT 403 for Scryfall — real calls are impossible here, not just undesirable. Deterministic fixtures also let redirect/gzip/malformed-line paths be tested without depending on Scryfall's actual catalog shape. |
| SQLite/Postgres DB (writer, queries, sync, API tests) | real (temp SQLite via `Repository`) | Cheap (in-memory-speed temp file), deterministic, and the whole point of these modules is SQL/ORM/dialect correctness (`dialect_insert`, `on_conflict_do_update`, `func.coalesce`) — mocking the DB would test nothing real. Matches `feedback_no_ceremony_specs.md`: don't mock what's free and load-bearing. |
| `get_optional_user` (FastAPI dependency) | mock (dependency override) | Auth flow (token issuing/verification) is exercised elsewhere; overriding to a fake `User(id="u1")` isolates the `owned_only` authorization branch without re-testing login. |
| `frontend/src/api/banlist.ts` in page/component tests | mock (`vi.mock`) | No backend process runs in the Vitest environment; mocking the API client is the only way to unit-test `BanList.tsx`/`BanCardDetailModal.tsx` in isolation. The client itself (`banlist.test.ts`) is tested separately against a mocked `fetch`, verifying URL/query-param construction (e.g. `owned_only=true` only when set). |
| `useAuth` hook in `BanList.test.tsx` | mock (`vi.mock`) | Lets the toggle's logged-in/logged-out branches be tested directly without standing up the full auth provider/token lifecycle. |

## 5. Test scenarios resumo

1. `legality_writer` batched upsert of legalities and history, dedupe on duplicate keys, `effective_date` coalesce-on-update, FK-violation rollback — **F177-T03**
2. `banlist_queries.list_banlist_grouped` grouping/sorting/pagination/owned-matching correctness, `owned_only` without `user_id`, `get_banlist_status` on empty DB — **F177-T04**
3. `BanCardDetailModal` rendering (legalities sorted by severity, history grouped by format, baseline label, empty/error states), a11y (`role="dialog"`, Esc/backdrop/close) — **F177-T05**
4. `banlist_sync` bulk parsing across JSONL/JSONL.gz/JSON-array, redirect-following, set-code/collector-number mapping, compact storage policy, baseline-vs-diff history, fail-loud on 0 matches — **F177-T06**
5. `GET /banlist` grouped response with `printings`/`owned`/`owned_quantity`, `owned_only` 401-without-auth, `status`/`limit` validation (422), `GET /banlist/status` — **F177-T07**
6. `BanList.tsx` toggle (enabled/disabled by auth), modal open/close wiring, owned badge + printings hint, not-synced/owned-empty states, load-more pagination — **F177-T08**
7. Menu no longer shows "Histórico de banimentos"; `/banlist/history` redirects to `/banlist`; no dangling `BanHistory` imports — **F177-T09**
8. `bats/banlist-sync.bat` exists, calls the CLI, exits 1 on failure; README documents F177 — **F177-T10**
9. i18n key parity (`banlist.*`, `banlist.detail.*`) present and non-empty in `en.json` + `pt-BR.json`, interpolation placeholders intact — **F177-T02**
10. PRD/ADR 0018/diagrams exist with correct filenames and reserved numbering; branch confirmed not `main` — **F177-T01**

## 6. Anotações para tasks

- `F177-T01` — fixtures: _none (docs-only task; no test fixtures apply)_
- `F177-T02` — fixtures: `i18n-locale-json`
- `F177-T03` — fixtures: `sqlite-fixture`
- `F177-T04` — fixtures: `sqlite-fixture`
- `F177-T05` — fixtures: `frontend-modal-mock`
- `F177-T06` — fixtures: `bulk-jsonl-sample`, `bulk-jsonl-gz-sample`, `bulk-json-array-sample`, `mock-transport`, `sqlite-fixture`
- `F177-T07` — fixtures: `api-test-client`, `sqlite-fixture`
- `F177-T08` — fixtures: `frontend-banlist-mock`
- `F177-T09` — fixtures: `frontend-banlist-mock` (reused for the redirect/Layout regression tests)
- `F177-T10` — fixtures: `bat-static-check`
