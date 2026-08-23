# F50 Manual Price Entry — Test Plan

**Status:** drafted
**Generator:** TEA
**Generated at:** 2026-08-22
**Source brief:** F50-README.md (AC1–AC4: manual price endpoint, price_source indicator, frontend input+badge, i18n)

---

## 1. Test Strategy Overview

F50 adds manual price entry across four boundaries: a new PATCH endpoint with currency conversion and upsert logic (T01), a price_source field in schemas and query priority logic (T02), frontend components for price input and source badge (T03), and i18n keys (T04).

The feature reuses the existing `PriceObservationRow` table with `source="manual"` — no new tables. The core complexity lies in the upsert-same-day logic, currency conversion, IDOR checks, and the price source priority query (manual wins same day, latest date wins cross-day).

**Key risks:**
- Same-day upsert vs duplicate creation (unique constraint on source+external_id+observed_at)
- Currency conversion correctness (USD/PILA to BRL before storage)
- Price source priority when manual and MYP prices coexist
- Auto-creation of CardRow for unlinked entries (edge case)

**Frameworks:**
- Backend: pytest + pytest-cov (target >=70%, project currently at ~91%)
- Frontend: Vitest + React Testing Library
- E2E: **N/A** — no E2E framework in project; coverage handled by integration + frontend unit tests

---

## 2. Fixtures

| Fixture | Path | Domain | Owner |
|---------|------|--------|-------|
| `_make_collection_row` | `tests/api/test_collection_detail.py` (reuse) | db/domain | existing |
| `_make_price_obs` | `tests/api/test_collection_detail.py` (reuse) | db/domain | existing |
| `_make_source_card` | `tests/api/test_collection_detail.py` (reuse) | db/domain | existing |
| `_make_app` | `tests/api/test_collection_detail.py` (reuse) | api | existing |
| `make_manual_price_obs` | `tests/api/test_manual_price.py` (inline) | db | F50-T01 |
| `makeLinkedEntryWithSource` | `frontend/tests/pages/CollectionCardDetail.test.tsx` (inline) | api | F50-T03 |

Fixtures follow the project pattern of inline helpers per test module (see `_make_collection_row` in `test_collection_detail.py`). `make_manual_price_obs` is a thin wrapper around `_make_price_obs` with `source="manual"` and `external_id="manual_{id}"` defaults. No shared fixture file needed — rework prevented is minimal for 4 tasks.

---

## 3. Harnesses por fronteira

### Unit

- **Framework:** pytest
- **Command:** `pytest tests/unit/database/test_repository_manual_price.py tests/unit/api/test_manual_price_schema.py -v`
- **Default test path:** `tests/unit/`

### Integration

- **Framework:** pytest + FastAPI TestClient
- **Command:** `pytest tests/api/test_manual_price.py tests/api/test_price_source.py -v`
- **Default test path:** `tests/api/`

### Frontend Unit

- **Framework:** Vitest + React Testing Library
- **Command:** `cd frontend && npx vitest run tests/components/PriceSourceBadge.test.tsx tests/pages/CollectionCardDetail.test.tsx tests/i18n/manual-price-keys.test.tsx`
- **Default test path:** `frontend/tests/`

### E2E

**N/A** — Project has no E2E framework (Cypress/Playwright). Frontend integration is covered by React Testing Library render tests with mocked fetch.

---

## 4. Perf budgets

| Metrica | Limite | Como medir | Aplicavel a |
|---------|--------|------------|-------------|
| PATCH /collection/{id}/price response | <500ms | TestClient wall time | F50-T01 |

_Single-card manual price entry is a simple upsert. No batch operations, no external provider calls (unless currency conversion hits BCB, which is cached). Perf risk is low._

---

## 5. Mocks vs hits real

| Componente | Decisao | Justificativa |
|------------|---------|---------------|
| SQLAlchemy repository | mock | Unit tests mock repo; integration tests use FastAPI TestClient with dependency overrides. Matches `test_collection_detail.py` pattern. |
| CurrencyConverter | mock | Avoids BCB API call in tests. Deterministic conversion rate needed for assertions (e.g., mock 1 USD = 5.00 BRL). |
| `require_auth_or_api_key` | mock | Override via FastAPI dependency injection. Matches existing auth test pattern. |
| PriceObservationRow upsert | real (integration) | The INSERT OR REPLACE logic is the core of T01. Integration tests should exercise actual SQLite to verify unique constraint behavior. |
| i18n JSON files | real | Static files, read directly in tests. Matches `canonize-keys.test.tsx` pattern. |
| fetch (frontend) | mock | `vi.fn()` mock as per all existing frontend tests. |

---

## 6. Test scenarios resumo

### F50-T01 — Manual Price Backend (Endpoint + source="manual")

1. `test_manual_price_creates_observation` — PriceObservationRow created with source="manual", external_id="manual_{entry_id}" [F50-T01]
2. `test_manual_price_converts_currency_usd` — USD input converted to BRL via CurrencyConverter before storage [F50-T01]
3. `test_manual_price_converts_currency_pila` — PILA input stored as-is (1:1 with BRL) [F50-T01]
4. `test_manual_price_upserts_same_day` — second call on same day updates existing row, not creates duplicate [F50-T01]
5. `test_manual_price_creates_new_day` — call on different day creates new observation row [F50-T01]
6. `test_manual_price_auto_creates_card` — unlinked entry (card_id=NULL) gets minimal CardRow created and linked [F50-T01]
7. `test_manual_price_external_id_format` — external_id follows "manual_{entry_id}" format [F50-T01]
8. `test_manual_price_endpoint_auth_required` — PATCH /collection/{id}/price returns 401 without token [F50-T01]
9. `test_manual_price_endpoint_idor_check` — returns 403 when entry belongs to different user [F50-T01]
10. `test_manual_price_endpoint_returns_detail` — response includes updated price and price_source="manual" [F50-T01]
11. `test_manual_price_endpoint_validates_negative` — returns 422 for negative price [F50-T01]
12. `test_manual_price_endpoint_validates_zero` — returns 422 for price=0 [F50-T01]
13. `test_manual_price_endpoint_404_nonexistent` — returns 404 for nonexistent entry_id [F50-T01]

### F50-T02 — Price Source Indicator in Schemas

14. `test_price_source_manual_in_response` — CollectionCard includes price_source="manual" when latest obs is manual [F50-T02]
15. `test_price_source_myp_in_response` — price_source="myp" when latest is MYP [F50-T02]
16. `test_price_source_jsonld_in_response` — price_source="jsonld_snapshot" when latest is jsonld [F50-T02]
17. `test_price_source_null_no_observations` — price_source=None when card has no price observations [F50-T02]
18. `test_price_source_manual_wins_same_day` — manual beats MYP when both have same observed_at date [F50-T02]
19. `test_price_source_latest_date_wins` — newer MYP observation beats older manual observation [F50-T02]
20. `test_price_source_in_collection_list` — GET /collection response includes price_source per card [F50-T02]
21. `test_collection_card_schema_has_price_source` — CollectionCard Pydantic schema includes price_source field [F50-T02]

### F50-T03 — Frontend Manual Price Input + Badge

22. `test_price_source_badge_renders_manual` — PriceSourceBadge renders amber badge with "Manual Price" text for source="manual" [F50-T03]
23. `test_price_source_badge_hidden_for_auto` — no badge rendered for source="myp" or "jsonld_snapshot" [F50-T03]
24. `test_price_source_badge_hidden_for_null` — no badge when price_source is null/undefined [F50-T03]
25. `test_manual_price_input_renders_on_detail` — CollectionCardDetail shows price input field and save button [F50-T03]
26. `test_manual_price_input_rejects_negative` — validation prevents negative values [F50-T03]
27. `test_manual_price_input_rejects_zero` — validation prevents zero [F50-T03]
28. `test_manual_price_input_calls_patch` — save button fires PATCH /collection/{id}/price with correct body [F50-T03]
29. `test_manual_price_input_refreshes_on_success` — card detail re-fetched after successful save [F50-T03]
30. `test_manual_price_input_shows_error` — error toast/message on API failure [F50-T03]
31. `test_card_tile_manual_indicator` — pencil/M icon shown on tile when price_source="manual" [F50-T03]
32. `test_card_tile_no_indicator_auto` — no manual indicator for auto-sourced prices [F50-T03]
33. `test_set_manual_price_api_client` — `setManualPrice()` sends correct PATCH request [F50-T03]

### F50-T04 — i18n Keys for Manual Price UI

34. `test_i18n_manual_price_keys_exist_en` — all ~9 price.* keys present in en.json [F50-T04]
35. `test_i18n_manual_price_keys_exist_pt` — all ~9 price.* keys present in pt-BR.json [F50-T04]
36. `test_i18n_keys_no_missing_translations` — every key in en.json has corresponding key in pt-BR.json [F50-T04]
37. `test_price_source_badge_uses_i18n` — PriceSourceBadge renders translated text via t() [F50-T04]
38. `test_manual_price_input_uses_i18n` — input labels and buttons use t() for all user-visible strings [F50-T04]

---

## 7. Test file paths and coverage targets

### Backend test files

| File | Scenarios | Task |
|------|-----------|------|
| `tests/unit/database/test_repository_manual_price.py` | #1, #4, #5, #6, #7 | F50-T01 |
| `tests/api/test_manual_price.py` | #2, #3, #8, #9, #10, #11, #12, #13 | F50-T01 |
| `tests/api/test_price_source.py` | #14–#21 | F50-T02 |
| `tests/unit/api/test_manual_price_schema.py` | #21 (schema validation) | F50-T02 |

### Frontend test files

| File | Scenarios | Task |
|------|-----------|------|
| `frontend/tests/components/PriceSourceBadge.test.tsx` | #22, #23, #24 | F50-T03 |
| `frontend/tests/pages/CollectionCardDetail.test.tsx` (extend) | #25–#30 | F50-T03 |
| `frontend/tests/components/CardTile.test.tsx` (new or extend) | #31, #32 | F50-T03 |
| `frontend/tests/api/collection.test.ts` (new or extend) | #33 | F50-T03 |
| `frontend/tests/i18n/manual-price-keys.test.tsx` | #34–#38 | F50-T04 |

### Coverage targets

| Scope | Target | Current |
|-------|--------|---------|
| Backend overall (`--cov=src`) | >=70% (CI gate) | 91.61% |
| `src/database/repository.py` (upsert_manual_price) | >=90% | existing |
| `src/api/routers/collection.py` (PATCH price additions) | >=85% | existing |
| Frontend: PriceSourceBadge | >=95% | new |
| Frontend: ManualPriceInput section | >=85% | new (in CollectionCardDetail) |
| Frontend: i18n manual price keys | 100% | new |

**Estimated new tests:** ~21 backend + ~17 frontend = ~38 tests total.

---

## 8. Anotacoes para tasks

| Task | Fixtures |
|------|----------|
| F50-T01 | `make_manual_price_obs`, reuse `_make_collection_row`, reuse `_make_app`, reuse `_make_price_obs` |
| F50-T02 | reuse `_make_collection_row`, reuse `_make_price_obs`, reuse `_make_app` |
| F50-T03 | `makeLinkedEntryWithSource`, reuse `makeLinkedEntry` |
| F50-T04 | (none — reads static JSON) |
