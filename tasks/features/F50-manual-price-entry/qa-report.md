# QA Report -- F50 Manual Price Entry

**QA Agent** | **Date:** 2026-08-23
**Feature:** F50 Manual Price Entry
**Verdict:** PASSED

---

## 1. Acceptance Criteria Validation

| AC | Description | Status | Evidence |
|----|-------------|--------|----------|
| AC1 | User can set manual price via PATCH /collection/{id}/price (stored as source="manual") | PASS | Endpoint at `collection.py:517`, stores via `upsert_manual_price` with `source="manual"`. 13 API integration tests + 5 repository unit tests + 9 schema validation tests cover auth, IDOR, validation, happy path, USD/PILA conversion, auto-card-creation, and exchange rate failure. |
| AC2 | Collection responses include price_source field | PASS | `CollectionCard.price_source: str | None` in schema (`collection.py:23`). Populated in both list (`collection.py:114`) and detail (`collection.py:779`) responses. 7 price source priority tests (repo level) + 7 API integration tests verify manual/myp/jsonld/null sources in list and detail. |
| AC3 | Frontend shows manual price input + "Manual Price" badge | PASS | `ManualPriceInput` component with validation (>0, <=99999.99), success/error states, i18n. `PriceSourceBadge` renders amber badge for `source="manual"`, null for others. Pencil icon on `MyCollection` tiles. 8 badge tests + 12 input tests. |
| AC4 | All manual price UI strings translated in EN and PT-BR | PASS | 10 keys under `price.*` namespace in both `en.json` and `pt-BR.json`. 22 i18n tests verify key existence, non-empty values, parity, and differentiation. |

---

## 2. B1 Bug Fix Verification (CRITICAL)

The TechLead identified a CRITICAL bug: `upsert_manual_price` used `entry_id` in `external_id` but `get_latest_prices_batch` queried using `card_id`. This would make manual prices invisible in collection responses.

**Fix verified:**
- `repository.py:195` -- `upsert_manual_price(self, card_id: int, ...)` accepts `card_id`
- `repository.py:204` -- `external_id = f"manual_{card_id}"`
- `repository.py:460` -- `manual_external_id = f"manual_{card_id}"`
- `collection.py:558` -- endpoint passes `entry.card_id` to `upsert_manual_price`
- Both sides now consistently use `card_id`. Fix confirmed.

**QA-added test:** `test_round_trip_upsert_then_read_via_get_latest_prices_batch` in `tests/unit/database/test_repository_manual_price.py` -- writes via `upsert_manual_price`, reads back via `get_latest_prices_batch`, asserts source/price/external_id match. This is the exact regression test the TechLead noted was missing.

---

## 3. Security Review

| Check | Status | Notes |
|-------|--------|-------|
| Auth enforcement | PASS | `require_auth_or_api_key` dependency on PATCH endpoint. Test `test_auth_required` verifies 401. |
| IDOR protection | PASS | Separate 404 (not found) and 403 (wrong user) at `collection.py:528-531`. Test `test_idor_check` verifies 403. |
| Input validation | PASS | `ManualPriceRequest` validates: price > 0, price <= 99999.99, currency in {BRL, USD, PILA}. 4 validation tests cover negative, zero, over-max, invalid currency. |
| SQL injection | PASS | Parameterized queries via SQLAlchemy throughout. |

---

## 4. Test Results

### Backend (47 F50-specific + 1 QA-added = 48 tests)

| File | Tests | Status |
|------|-------|--------|
| `tests/unit/database/test_repository_manual_price.py` | 6 (5 original + 1 QA round-trip) | ALL PASS |
| `tests/unit/database/test_repository_price_source.py` | 7 | ALL PASS |
| `tests/api/test_manual_price.py` | 13 | ALL PASS |
| `tests/api/test_price_source.py` | 7 | ALL PASS |
| `tests/unit/api/test_manual_price_schema.py` | 9 | ALL PASS |
| `tests/unit/api/test_price_source_schema.py` | 6 | ALL PASS |

**Full backend suite:** 1139 passed, 0 failed (72.96% coverage, above 70% floor)

### Frontend (42 F50-specific tests)

| File | Tests | Status |
|------|-------|--------|
| `frontend/tests/components/PriceSourceBadge.test.tsx` | 8 | ALL PASS |
| `frontend/tests/components/ManualPriceInput.test.tsx` | 12 | ALL PASS |
| `frontend/tests/i18n/manual-price-keys.test.tsx` | 22 | ALL PASS |

**Full frontend suite:** 905 passed, 0 failed (88 test files)

**Total F50 tests:** 90 (48 backend + 42 frontend)

---

## 5. Tests Added by QA

1. `test_round_trip_upsert_then_read_via_get_latest_prices_batch` in `tests/unit/database/test_repository_manual_price.py` -- Regression test for B1 fix. Writes a manual price via `upsert_manual_price`, then reads it back via `get_latest_prices_batch`, asserting that the observation is found with correct source, price, and external_id.

---

## 6. Documentation Verification

| Item | Status | Notes |
|------|--------|-------|
| Architecture diagram | PASS | `docs/diagrams/F50-architecture.mmd` -- accurately shows Frontend -> API -> Repository -> Database flow, currency converter, auto-card-creation, and price source priority logic. |
| User journey diagram | PASS | `docs/diagrams/F50-journey.mmd` -- covers detail view, validation, currency conversion, auto-card-creation, upsert, refresh, and collection list pencil icon. |
| README update | PASS | F50 section present with backend, query logic, frontend, and i18n subsections. |

---

## 7. TechLead Review Items Status

| Item | Severity | Status | Notes |
|------|----------|--------|-------|
| B1 | BLOCKING | FIXED | external_id mismatch resolved. Round-trip test added by QA. |
| I1 | IMPORTANT | DEFERRED (acceptable) | Display currency not forwarded as query param in `setManualPrice`. The `onSaved` callback triggers `refetch` which uses the correct currency, so the page updates correctly. The brief moment of BRL-denominated response is masked by the immediate refetch. Low user impact. |
| B2 | IMPORTANT | DEFERRED (existing issue) | N+1 query pattern in `get_latest_prices_batch` pre-dates F50. F50 added +1 query per card_id for manual price lookup, incrementally worsening the existing pattern. Acceptable as follow-up optimization. |
| D1 | IMPORTANT | FIXED | Diagrams created. |
| D2 | IMPORTANT | FIXED | README updated. |
| M1 | MINOR | DEFERRED | Scientific notation in number input. Frontend validation catches values > 99999.99. Low priority UX issue. |

---

## 8. Observations

- **act() warnings** in ManualPriceInput tests are cosmetic (known React 19 testing pattern, per F07 learnings). All assertions pass correctly.
- **Test plan coverage:** The test plan specified 38 scenarios. The implementation delivered 89 tests (47 backend + 42 frontend), exceeding the plan significantly with additional edge cases (null card_id in list, detail schema inheritance, input disabled states, error clearing, i18n differentiation check).
- **Price source priority logic** is well-tested at both repository level (real SQLite) and API level (mocked repo), covering: manual wins same-day, latest date wins cross-day, manual-only, myp-only, jsonld-only, no observations, and manual vs jsonld same-day.

---

## 9. Final Verdict

**PASSED**

All 4 acceptance criteria are met. The critical B1 bug is fixed and covered by a new round-trip regression test. Security checks (auth, IDOR, input validation) are solid. Documentation deliverables are complete. Full test suites pass (1139 backend, 905 frontend). No blockers remain.
