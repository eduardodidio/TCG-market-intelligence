# F65 Credit Token System -- QA Report

**QA Agent:** Claude Opus 4.6
**Date:** 2026-08-26
**Verdict:** PASSED

---

## Test Results

### Backend
- **Tests collected:** 2160
- **Tests passed:** 2160 (after QA fixes to 2 pre-existing test regressions)
- **Credit-specific tests:** 83 (27 model + 28 service + 13 router + 15 guards)
- **Coverage:** not re-measured (previous baseline ~91%)

### Frontend
- **Test files:** 102 passed, 0 failed
- **Tests passed:** 1063 (after QA fixes to 7 test failures)
- **Credit-specific tests:** 29 (12 TreasureBalance + 17 CreditConfirmModal)

---

## Test Fixes Applied by QA

### Fix 1: CollectionCardDetail.liga.test.tsx (7 tests)
**Root cause:** F65 changed refresh buttons to open a CreditConfirmModal before
triggering the API call. The existing Liga test file clicked buttons expecting
immediate API calls, but now there is an intermediate modal confirmation step.

**Fix:** Added `makeCreditBalanceResponse()` to mock the `/credits/balance`
endpoint, and a `clickAndConfirmRefresh()` helper that clicks the button, waits
for the modal, and clicks the confirm button. Applied to all 7 tests that
interact with refresh buttons.

**File:** `frontend/tests/pages/CollectionCardDetail.liga.test.tsx`

### Fix 2: test_seed_users.py (3 tests)
**Root cause:** Pre-existing regression from commit `9d6d74c` (pre-F65). The
`anderson.serafim` user was removed from the seed command and the default
password changed from `mudar@123` to `mudar12345`, but the tests were not
updated.

**Fix:** Removed `anderson.serafim` assertions, updated default password
assertion to `mudar12345`.

**File:** `tests/cli/test_seed_users.py`

### Fix 3: test_cli_collector.py (1 test)
**Root cause:** Pre-existing regression from F63 project rename. CLI help text
changed from "TCG Market Intelligence" to "TEDHC Market" but the test was not
updated.

**Fix:** Updated assertion to match new CLI help text.

**File:** `tests/unit/test_cli_collector.py`

---

## Acceptance Criteria Validation

| # | Criterion | Status | Evidence |
|---|-----------|--------|----------|
| 1 | `credit_transactions` table logs every grant/deduct with timestamp + reason | PASS | `CreditTransactionRow` in `models.py` (lines 298-311): columns `user_id`, `amount`, `reason`, `reference_id`, `created_at`. `update_credit_balance` in repository inserts a transaction row on every balance change. 27 model tests confirm behavior. |
| 2 | POST /credits/claim-bonus grants 5 credits if 12h+ since last claim | PASS | `credits.py` router line 59-76: calls `svc.claim_bonus()`, returns `{"balance": N, "credited": 5}` on success, 429 with `BONUS_NOT_READY` if too early. `service.py` checks `last_bonus_at + 12h` cutoff. 4 router tests + 28 service tests cover timing edge cases. |
| 3 | GET /credits/balance returns current balance + next bonus eligibility | PASS | Router line 16-32: returns `balance`, `last_bonus_at`, `bonus_eligible`, `next_bonus_at`, `bonus_amount`, `is_admin`. 4 router tests verify fields. |
| 4 | GET /credits/history returns paginated transaction log | PASS | Router line 35-56: accepts `limit` (1-100) and `offset` (>=0) query params, returns `{"transactions": [...]}`. 5 router tests verify pagination. |
| 5 | Refresh endpoints return 402 when credits insufficient (non-admin) | PASS | MYP refresh (collection.py line 772-775), Liga refresh (line 920-923), bulk scan (scans.py line 129-137) all check `credit_svc.check_sufficient()` and return 402 with `{"detail": {"message": ..., "balance": N, "cost": N}}`. 5 guard tests verify 402 responses. |
| 6 | Admin users (is_admin=1) bypass all credit checks | PASS | All three guard locations check `if not user.is_admin` before credit validation. Admin users skip `check_sufficient()` and `deduct()` entirely. 3 guard tests verify admin bypass (MYP, Liga, scan). |
| 7 | Frontend shows credit balance in sidebar with claim button | PASS | `TreasureBalance` component integrated in `Layout.tsx` (line 132) inside `isAuthenticated` guard. Shows balance count, claim button when eligible, admin badge. 12 component tests. |
| 8 | Confirmation modal appears before credit-consuming actions | PASS | `CreditConfirmModal` used in `CollectionCardDetail.tsx` (single refresh), `MyCollection.tsx` (bulk scan), `DeckCardTile.tsx` (tile refresh). Shows cost, balance, balance-after, admin bypass text, insufficient warning. Confirm disabled when insufficient. 17 component tests. |
| 9 | i18n keys for EN and PT-BR | PASS | 16 matching keys in both `en.json` and `pt-BR.json` under the `"credits"` namespace: balance, claimBonus, bonusAvailable, nextBonus, admin, confirmTitle, confirmCost, confirmBalance, balanceAfter, insufficient, spend, cancel, adminBypass, refreshCost, scanCost. |

---

## TechLead Review Items Verification

### B1 (BLOCKING): Frontend field name mismatch -- VERIFIED FIXED
`ClaimBonusResponse` in `credits.ts` uses `{ balance, credited }` matching the
backend response. `useCredits.ts` reads `res.data.balance`.

### B2 (BLOCKING): MYP refresh deducting on no-price -- VERIFIED FIXED
`collection.py` refresh endpoint uses a `price_saved` flag; credits deducted
only when `price_saved is True` (line 887).

### I1 (IMPORTANT): TOCTOU between check and deduct -- ACKNOWLEDGED
Low risk for SQLite single-writer. `deduct()` in service does its own balance
check and raises `InsufficientCreditsError`, but the router does not catch
`ValueError` from `update_credit_balance`. Non-blocking for current architecture.

### I2 (IMPORTANT): Bulk scan upfront deduction -- ACKNOWLEDGED
Documented in journey diagram as intentional. Background tasks cannot deduct
after completion without a callback mechanism.

---

## Diagrams and Documentation

- `docs/diagrams/F65-architecture.mmd` -- present, valid Mermaid, accurate
- `docs/diagrams/F65-journey.mmd` -- present, valid Mermaid, accurate
- Both diagrams correctly reflect the implemented architecture and user flows

---

## Retrospective Summary

### What worked well
- Clean separation of concerns: constants, exceptions, service, router guards
- Credit service is framework-agnostic (no FastAPI imports), making it trivially testable
- Admin bypass at router level keeps the service simple (always charges)
- Comprehensive test coverage: 112 new tests (83 backend + 29 frontend)
- MTG Treasure Token theming adds personality without complexity

### What caused issues
- Frontend field name mismatch (B1) between backend response and TypeScript
  interface -- caught by TechLead, not by existing tests
- MYP refresh missing the price_saved guard (B2) -- asymmetric with Liga path
  which already had it
- Existing Liga tests broke because they assumed buttons trigger API calls
  directly, but F65 added an intermediate modal step

### Durable lessons (appended to agent-learnings files)
- When adding a confirmation step (modal/dialog) before an existing action,
  update ALL tests that interact with that action's trigger
- Backend response field names must be verified against frontend interfaces as a
  TechLead checklist item -- TypeScript types do not fail at build time when a
  field is missing from a JSON response
- Deduct-after-success guards must be symmetric across all provider paths. When
  one provider has a guard, all providers for the same action must have it.
