# F90 Multi-Feature Batch -- QA Report

**QA Agent:** QA
**Date:** 2026-08-29
**Branch:** homol

---

## Test Suite Results

### Backend
- **Total:** 2780 tests (2779 passed, 1 failed)
- **Failed:** `tests/cli/test_seed_users.py::TestSeedUsers::test_uses_default_password_when_no_env`
  - **Pre-existing failure** from F88 seed password change (not related to F90)
- **Coverage:** 91.40% (well above the 70% threshold)

### Frontend
- **Total:** 1468 tests, 133 test files -- all passed

---

## Per-Task Coverage

| File | Coverage | Uncovered Lines |
|------|----------|-----------------|
| `src/api/routers/evaluations.py` | 93% | L72 (create internal error), L136-138 (batch_add rollback), L141 (0 added) |
| `src/api/routers/card_search.py` | 97% | L87-88 (timeout path) |
| `src/api/schemas/evaluations.py` | 100% | -- |
| `src/api/schemas/card_search.py` | 100% | -- |
| `src/services/trending.py` | 86% | L128-130 (USD fallback), L135-144 (currency conversion) |
| `src/scheduler/service.py` | 90% | L161-162, L214, L224-225 (scan execution internals) |
| `src/database/models.py` (EvaluationEntryRow) | 100% | -- |
| `src/database/repository.py` (eval methods) | 92% | Uncovered lines are pre-existing, not F90-specific |

---

## Test Gaps Found and Filled

12 new tests added in `tests/unit/api/test_f90_gap_tests.py`:

### T03: Trending Collection-Only
| # | Test | Result |
|---|------|--------|
| 1 | User with 0 collection cards returns empty trending (up) | PASS |
| 2 | User with 0 collection cards returns empty trending (down) | PASS |

**Finding:** When `get_trending_price_data_for_user` returns an empty dict, the service correctly returns a `TrendingResponse` with an empty cards list. No crash or error.

### T04: Schedule Token Cost
| # | Test | Result |
|---|------|--------|
| 3 | Scheduler skips CreditService when card_count == 0 | PASS |

**Finding:** The `if card_count > 0` guard at line 182 of `scheduler/service.py` correctly skips token check/deduction when the user has zero collection cards. CreditService is never instantiated.

### T05: Explore Cards Web Search
| # | Test | Result |
|---|------|--------|
| 4 | Liga returns dict without `normal`/`foil` keys -> empty result | PASS |
| 5 | Liga returns all None prices -> empty result | PASS |
| 6 | Liga returns only foil price (no normal) -> result with foil_price only | PASS |
| 7 | Liga search timeout -> 504 | PASS |

**Finding:** The `.get("normal", {})` pattern handles missing keys gracefully. The `any(v is not None for v in normal.values())` check correctly identifies all-None dicts. Timeout is handled via `asyncio.wait_for`.

### T06: Evaluation List
| # | Test | Result |
|---|------|--------|
| 8 | Duplicate card name allowed (no unique constraint) | PASS |
| 9 | Same card from different sets coexists | PASS |
| 10 | Promote returns 400 when batch_add adds 0 cards | PASS |

**Finding:** Duplicate card names are permitted (no DB constraint). This is acceptable for tracking different printings/prices. The promote endpoint returns HTTP 400 with "Failed to add card to collection" when `batch_add_entries` returns `added=0`, and the evaluation entry is NOT deleted (preserving user data).

### T05 to T06 Integration
| # | Test | Result |
|---|------|--------|
| 11 | WebSearchResult fields map correctly to EvalCreateRequest | PASS |
| 12 | WebSearchResult without local card -> card_id is None | PASS |

---

## Integration Verification

### T05 "Add to Evaluation" wires to T06 API endpoint
- **VERIFIED.** `frontend/src/pages/Cards.tsx` imports `createEvaluation` from `api/evaluations.ts`.
- The create payload maps `result.card_name`, `result.liga_url`, `result.normal_price`, and `result.local_card_id` from the web search result to the evaluation create body.
- `POST /api/v1/evaluations` is correctly registered in `src/api/app.py`.

### T06 nav item appears in T02 Beta Test group
- **VERIFIED.** `Layout.tsx` includes `{ to: "/evaluations", labelKey: "nav.evaluations", requiresAuth: true }` in `BETA_NAV_ITEMS`.
- Route is registered in `App.tsx` under `ProtectedRoute`.
- i18n keys present in both `en.json` and `pt-BR.json`.

### T04 token check works with T03 collection-scoped data
- **VERIFIED.** Both features use `repo.count_collection(user_id)` for the user's card count. T04 uses it for cost estimation; T03 uses a separate JOIN query (`get_trending_price_data_for_user`) scoped by user_id via `UserCollectionRow`. No conflict between these features.

### T01 Schedule Save Fix
- **VERIFIED.** All schedule endpoints now return `ApiResponse` envelope via `success_response()`. Frontend can parse `resp.data` consistently. 15 endpoint tests + 2 round-trip tests confirm the envelope shape with `data`, `meta`, and `errors` fields.

---

## Non-Blocking Observations (from Tech Lead review, confirmed by QA)

| # | Task | Observation | QA Verdict |
|---|------|-------------|------------|
| 1 | T04 | No token refund on scan failure | Consistent with manual scan behavior. Future improvement. |
| 2 | T05 | Price display hardcoded as `R$` in web results | Technically correct (Liga prices are BRL) but inconsistent with CurrencyIndicator pattern. Minor. |
| 3 | T06 | No unique constraint on `(user_id, card_name)` | Tested and confirmed: duplicates allowed. Acceptable for different printings. |
| 4 | T06 | Image column header uses `common.noImage` key | Cosmetic. Non-blocking. |
| 5 | T06 | `_image_url` does not use `map_to_scryfall_set_code()` | May cause incorrect image URLs for variant set codes. Non-blocking for now. |

---

## Summary

| Metric | Value |
|--------|-------|
| Backend tests | 2779 passed, 1 failed (pre-existing) |
| Frontend tests | 1468 passed |
| Backend coverage | 91.40% |
| New gap tests added | 12 |
| Integration checks | 3/3 verified |
| Blocking issues | 0 |

---

## Overall Verdict: PASSED

All six tasks (T01-T06) are correctly implemented, well-tested, and properly integrated. The single test failure is pre-existing (F88 seed password) and unrelated to F90. Coverage remains well above threshold. No blocking issues found.
