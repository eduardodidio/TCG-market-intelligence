# F09 Test Plan

**Status:** drafted
**Generator:** TEA
**Generated at:** 2026-08-19
**Source brief:** F09 — Scheduled Price Collection (health endpoint, API key guard, cron script, frontend freshness indicator)

---

## 1. Fixtures

| Fixture | Path | Domain | Owner |
|---------|------|--------|-------|
| `db_with_observations` | `tests/conftest.py` (existing) | db | F09-T01 |
| `db_with_stale_cards` | `tests/conftest.py` or `tests/api/test_collect_health.py` | db | F09-T01 |
| `db_with_errors` | `tests/api/test_collect_health.py` | db | F09-T01 |
| `monkeypatch_api_key` | `tests/api/test_collect_auth.py` | api/auth | F09-T02 |

All fixtures are lightweight (in-memory SQLite, env var patching). No external files, no audio/media, no heavy setup. Each justified by reuse across 2+ test cases within the same file.

## 2. Harnesses por fronteira

### Unit

- **Framework:** pytest
- **Command:** `python -m pytest tests/ -x -q`
- **Default path:** `tests/database/test_repository.py`, `tests/api/test_collect_health.py`, `tests/api/test_collect_auth.py`

### Integration

- **Framework:** pytest + FastAPI TestClient
- **Command:** `python -m pytest tests/api/ -x -q`
- **Default path:** `tests/api/`

### E2E

- **Framework:** Vitest + React Testing Library (frontend only)
- **Command:** `cd frontend && npx vitest run`
- **Default path:** `frontend/tests/`

Full E2E (backend + frontend together) is **N/A** — the project runs locally without a deployment target. Frontend tests mock the API layer. Backend integration tests use TestClient. This is sufficient for the current scope.

## 3. Perf budgets

| Metrica | Limite | Como medir | Aplicavel a |
|---------|--------|-----------|-------------|
| Health endpoint latency | < 500ms | pytest benchmark or manual `time curl` | F09-T01 |

_Single perf budget from NFR-01. Other tasks have no perf-sensitive paths._

## 4. Mocks vs hits real

| Componente | Decisao | Justificativa |
|-----------|---------|---------------|
| SQLite database (repository methods) | real | In-memory SQLite is fast and deterministic. Mocking the repo would hide SQL bugs. |
| FastAPI TestClient | real | TestClient runs the full ASGI stack in-process — no external dependency. |
| `os.environ` (API key) | mock | `monkeypatch.setenv` is standard pytest practice. Cannot use real env vars without side effects. |
| Health endpoint (frontend) | mock | Frontend tests mock `fetch` via MSW or vi.mock. Cannot call real backend from Vitest. |
| `Date.now()` (frontend relative time) | mock | Required for deterministic "X hours ago" assertions. |

## 5. Test scenarios resumo

### Backend (F09-T01: Health endpoint)

1. `test_get_latest_observation_date_empty_db` — repo returns None when no observations exist (F09-T01)
2. `test_get_latest_observation_date_with_data` — repo returns correct date (F09-T01)
3. `test_get_stale_cards_count_no_stale` — returns 0 when all cards have recent observations (F09-T01)
4. `test_get_stale_cards_count_with_stale` — returns correct count for cards with old/no observations (F09-T01)
5. `test_get_recent_errors_count` — counts only unresolved errors within 7-day window (F09-T01)
6. `test_health_endpoint_returns_200` — GET /collect/health returns 200 with correct schema (F09-T01)
7. `test_health_status_healthy` — status="healthy" when data is fresh and no errors (F09-T01)
8. `test_health_status_stale` — status="stale" when >50% cards are stale (F09-T01)
9. `test_health_status_error` — status="error" when recent_errors_count > 0 (F09-T01)

### Backend (F09-T02: API key guard)

10. `test_verify_api_key_no_env_var_allows_all` — no exception when TCG_API_KEY unset (F09-T02)
11. `test_verify_api_key_valid_key` — no exception when header matches (F09-T02)
12. `test_verify_api_key_missing_header` — HTTPException 401 (F09-T02)
13. `test_verify_api_key_wrong_key` — HTTPException 401 (F09-T02)
14. `test_collect_update_requires_key_when_configured` — POST /collect/update returns 401 without key (F09-T02)
15. `test_collect_backfill_requires_key_when_configured` — POST /collect/backfill returns 401 without key (F09-T02)
16. `test_collect_update_works_without_key_in_dev_mode` — POST works when TCG_API_KEY unset (F09-T02)
17. `test_health_no_key_required` — GET /collect/health returns 200 even when TCG_API_KEY is set (F09-T02)

### Frontend (F09-T04: Freshness indicator)

18. `test_freshness_indicator_renders_relative_time` — shows "2 hours ago" (F09-T04)
19. `test_freshness_indicator_renders_unknown_when_null` — shows "Unknown" when null (F09-T04)
20. `test_freshness_indicator_status_dot_colors` — green/yellow/red based on status (F09-T04)
21. `test_dashboard_renders_freshness_indicator` — Dashboard shows freshness with mocked health (F09-T04)
22. `test_dashboard_renders_without_freshness_on_error` — Dashboard loads when health endpoint fails (F09-T04)

### Shell script (F09-T03)

_Manual testing only — shell scripts are not unit-testable in pytest. See T03 acceptance criteria for manual verification steps._

### Documentation (F09-T05)

_No automated tests — Mermaid syntax validation only._

## 6. Anotacoes para tasks

| Task | Fixtures |
|------|----------|
| F09-T01 | `db_with_observations`, `db_with_stale_cards`, `db_with_errors` |
| F09-T02 | `monkeypatch_api_key` |
| F09-T04 | (none — frontend mocks are inline vi.mock) |
