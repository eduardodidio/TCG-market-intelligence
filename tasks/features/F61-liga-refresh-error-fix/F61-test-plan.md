# F61 Test Plan

**Status:** drafted
**Generator:** TEA
**Generated at:** 2026-08-25
**Source brief:** F61-README.md (Liga Refresh Error Fix)

## 1. Fixtures

| Fixture | Path | Domain | Owner |
|---------|------|--------|-------|
| mock_playwright_error | tests/providers/liga/ (inline) | provider | F61-T01 |
| mock_provider_registry | tests/api/routers/ (inline) | api | F61-T02 |

_Both fixtures are inline mocks (pytest monkeypatch/Mock). No file-based fixtures needed — this is a pure error-handling bug fix._

## 2. Harnesses por fronteira

### Unit
- **Framework:** pytest (backend), Vitest + React Testing Library (frontend)
- **Command:** `pytest tests/` / `cd frontend && npx vitest run`
- **Default path:** `tests/providers/liga/`, `tests/api/routers/`, `frontend/src/pages/__tests__/`

### Integration
- **N/A** — no cross-service integration needed. The bug is in error propagation within a single request path.

### E2E
- **N/A** — Liga refresh requires a live Playwright browser + external site. E2E would be flaky and expensive. Manual smoke test covers this.

## 3. Perf budgets

_Sem perf budgets aplicaveis — this is an error-handling fix, not a performance feature._

## 4. Mocks vs hits real

| Componente | Decisao | Justificativa |
|------------|---------|---------------|
| Playwright browser | mock | External dependency, slow (~5s startup), flaky. Mock playwright errors directly. |
| LigaMagicProvider.search_card | mock | T02 tests the endpoint, not the provider. Provider tested in T01. |
| ProviderRegistry | mock | Inject mock registry with/without Liga provider to test 503 path. |
| i18n translations | real | Already loaded in test setup, no cost to use real. |

## 5. Test scenarios resumo

1. `search_card` wraps `playwright.Error("")` into `LigaError` with non-empty message (F61-T01)
2. `search_card` wraps `RuntimeError("msg")` into `LigaError` preserving message (F61-T01)
3. `_fetch_page` catches `PlaywrightError` and converts to `LigaError` (F61-T01)
4. Existing `_fetch_page` timeout/OSError tests still pass (F61-T01)
5. `search_card` returns parsed prices on success — no regression (F61-T01)
6. Endpoint uses singleton provider from registry (F61-T02)
7. Endpoint returns 503 when Liga provider not in registry (F61-T02)
8. Catch-all error includes exception type name in message (F61-T02)
9. `LigaError` with empty message produces readable error (F61-T02)
10. Successful Liga fetch saves price observation (F61-T02)
11. No `provider.close()` called per request (F61-T02)
12. Liga refresh error shows warning with `ligaErrorHint` text (F61-T03)
13. Liga refresh error toast stays for 5 seconds (F61-T03)
14. Successful Liga refresh shows success message — no regression (F61-T03)
15. Liga warning with empty backend message still shows hint text (F61-T03)

## 6. Anotacoes para tasks

- (F61-T01, mock_playwright_error)
- (F61-T02, mock_provider_registry)
- (F61-T03, _none — uses existing test setup_)
