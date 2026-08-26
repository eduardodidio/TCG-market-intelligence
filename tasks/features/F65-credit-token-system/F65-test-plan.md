# F65 — Credit Token System: Test Plan

## 1. Test Strategy

**Backend:** pytest with SQLAlchemy in-memory SQLite, pytest fixtures for user/credit seeding. Async tests where endpoints are async. Coverage target via pytest-cov.

**Frontend:** Vitest + React Testing Library (RTL). Mock `apiGet`/`apiPost` via vi.fn(). Test hooks with `renderHook`. Modal interactions via `@testing-library/user-event`.

**Approach:** Each task's unit tests validate isolated behavior. Integration tests verify cross-layer round trips. Edge case tests focus on concurrency, boundary values, and race conditions between frontend pre-check and backend deduction.

---

## 2. Unit Tests

### T01 — Database Models + Repository (9 tests)

- CreditBalanceRow and CreditTransactionRow created via SQLAlchemy session
- `ensure_credit_balance` creates row with balance=0 for new user
- `ensure_credit_balance` returns existing row for known user (idempotent)
- `update_credit_balance` with positive delta increases balance, inserts transaction
- `update_credit_balance` with negative delta decreases balance, inserts transaction
- `update_credit_balance` with negative delta exceeding balance raises ValueError
- `get_credit_transactions` returns desc order, respects limit/offset
- Seed user gets is_admin=1, balance=50, transaction reason="initial_credits"
- User domain model has is_admin field defaulting to False

### T02 — CreditService (12 tests)

- `get_balance` returns balance=0 for new user (auto-creates row)
- `deduct(cost=1)` with balance=5 returns balance=4, transaction logged
- `deduct(cost=1)` with balance=0 raises InsufficientCreditsError(balance=0, cost=1)
- `grant(amount=100, reason="admin_grant")` increases balance, transaction logged
- `claim_bonus` with no prior claim grants 5, sets last_bonus_at
- `claim_bonus` called twice within 12h — second returns (balance, False)
- `claim_bonus` after 12h+ grants 5 more credits
- `get_bonus_eligibility` with no prior claim returns eligible=True
- `get_bonus_eligibility` returns next_eligible_at = last_bonus_at + 12h
- `get_transactions` returns most recent first, respects limit/offset
- `check_sufficient(cost=3)` with balance=5 returns True
- `check_sufficient(cost=3)` with balance=2 returns False

### T03 — Credits API Router (8 tests)

- GET /credits/balance returns balance=0 for new user
- GET /credits/balance returns is_admin=true for admin user
- GET /credits/balance includes bonus eligibility fields
- GET /credits/history returns paginated transactions desc
- GET /credits/history respects limit and offset query params
- POST /credits/claim-bonus grants 5 credits, returns new balance
- POST /credits/claim-bonus within 12h returns 429 BONUS_NOT_READY
- All three endpoints return 401 without auth token

### T04 — Credit Guards on Refresh/Scan (12 tests)

- POST /collection/{id}/refresh: non-admin, balance=5 -> succeeds, balance=4, reason="card_refresh"
- POST /collection/{id}/refresh: non-admin, balance=0 -> 402 INSUFFICIENT_CREDITS
- POST /collection/{id}/refresh: provider error -> balance unchanged (no deduction)
- POST /collection/{id}/refresh-liga: non-admin, balance=1 -> succeeds, balance=0
- POST /collection/{id}/refresh-liga: non-admin, balance=0 -> 402
- POST /collection/{id}/refresh: admin -> succeeds regardless of balance, no deduction
- POST /collection/{id}/refresh-liga: admin -> succeeds regardless of balance, no deduction
- POST /scans: non-admin, balance=10 -> succeeds, balance=5
- POST /scans: non-admin, balance=3 -> 402 (cost=5)
- POST /scans: admin -> succeeds regardless of balance, no deduction
- Transaction log records correct reason ("card_refresh" vs "bulk_scan") and reference_id
- Existing refresh tests still pass with seeded credits (regression guard)

### T05 — Frontend Sidebar Balance (8 tests)

- TreasureBalance renders balance number and gold token icon
- TreasureBalance shows claim button when bonusEligible=true
- TreasureBalance hides claim button when bonusEligible=false
- TreasureBalance shows admin badge when isAdmin=true
- useCredits fetches GET /credits/balance on mount
- claimBonus triggers POST /credits/claim-bonus and refetches balance
- Layout renders TreasureBalance when authenticated
- Layout hides TreasureBalance when not authenticated

### T06 — Frontend Confirmation Modal (10 tests)

- TreasureTokenCard renders with count overlay
- CreditConfirmModal shows cost and balance text
- CreditConfirmModal disables confirm button when balance < cost (non-admin)
- CreditConfirmModal enables confirm button for admin regardless of balance
- CreditConfirmModal shows "Admin -- no cost" text for admin users
- CreditConfirmModal calls onConfirm callback on confirm click
- CreditConfirmModal calls onCancel callback on cancel click
- CollectionCardDetail opens modal on refresh click (no immediate API call)
- After modal confirm, refresh API is called
- 402 response triggers balance refetch and shows insufficient state

---

## 3. Integration Tests

### API -> Service -> Repository Round Trips (7 tests)

- POST /credits/claim-bonus -> CreditService.claim_bonus -> repo.update_credit_balance -> verify balance row + transaction row in DB
- GET /credits/balance for seed user -> returns balance=50, is_admin=true
- POST /collection/{id}/refresh (non-admin, seeded balance) -> provider mock returns price -> balance decremented -> transaction with reason="card_refresh" and reference_id=entry_id in DB
- POST /scans (non-admin, balance=5) -> scan triggered -> balance=0 -> transaction reason="bulk_scan"
- POST /collection/{id}/refresh (non-admin, balance=0) -> 402 -> no transaction row created
- Claim bonus -> refresh card -> GET /credits/history shows both transactions in order
- Register new user -> GET /credits/balance returns 0 -> claim bonus -> balance=5

---

## 4. E2E Scenarios

### Scenario 1: New User Claim-and-Spend Flow
1. User logs in (balance=0)
2. Sidebar shows "0" with claim button visible
3. User clicks "Claim Bonus" -> balance becomes 5, claim button disappears
4. User navigates to collection card detail
5. User clicks refresh -> confirmation modal appears (cost=1, balance=5)
6. User confirms -> price refreshes, sidebar updates to 4
7. Repeat until balance=0 -> next refresh shows modal with disabled confirm + "Insufficient tokens!" warning

### Scenario 2: Admin Bypass
1. Admin logs in (balance=50, admin badge visible)
2. Admin clicks refresh -> modal shows "Admin -- no cost"
3. Admin confirms -> refresh succeeds, balance unchanged (still 50)
4. Admin triggers bulk scan -> modal shows "Admin -- no cost", scan runs, balance unchanged

### Scenario 3: Bonus Cooldown
1. User claims bonus (balance goes 0->5)
2. User immediately tries to claim again -> 429, UI shows next eligible time
3. After 12h, claim button reappears -> user claims, balance increases by 5

### Scenario 4: Bulk Scan Credit Check
1. User has balance=3, clicks "Refresh All"
2. Modal shows cost=5, balance=3, confirm button disabled
3. User claims bonus (balance=8), tries again -> modal shows cost=5, balance=8, confirm enabled
4. User confirms -> scan runs, balance=3

---

## 5. Edge Cases

### Boundary Conditions
- Balance exactly equals cost (balance=1, cost=1 for refresh; balance=5, cost=5 for scan) -> should succeed, balance=0
- Balance=0, cost=0 (canonize-all) -> should succeed without any credit check
- Claim bonus at exactly 12h boundary (last_bonus_at + 12h == now) -> should grant
- Very large balance (MAX_INT-adjacent) -> grant should not overflow
- Negative amount passed to grant -> should reject or be validated

### Race Conditions
- Two concurrent refresh requests with balance=1 -> only one should succeed; the other gets 402 or ValueError
- Frontend shows balance=1 in modal, but another tab spends the credit before confirm -> backend returns 402, frontend refetches and shows insufficient
- Claim bonus requested twice concurrently -> only one should grant (last_bonus_at atomicity)
- Bulk scan deduction (pre-deduct) followed by immediate single refresh -> balance must reflect both

### Concurrency
- SQLAlchemy session-level locking on `update_credit_balance` must prevent double-spend
- `ensure_credit_balance` called concurrently for same user -> must not create duplicate rows (unique constraint on user_id)

---

## 6. Regression Risk

### Backend Tests Likely to Break
- **Refresh endpoint tests** (`tests/` for collection router): All tests calling POST /collection/{id}/refresh or /refresh-liga will get 402 unless the test user has credits seeded. Fix: add a pytest fixture that grants 100 credits to the test user before each refresh test.
- **Scan trigger tests** (`tests/` for scans router): POST /scans will return 402 for non-admin test users. Fix: same credit-seeding fixture.
- **Seed user tests**: Any test asserting on the seed-users CLI command output or DB state needs to expect is_admin=1 and credit balance/transaction rows.
- **Auth/deps tests**: Tests that mock or assert on `get_current_user` return value must include `is_admin` field.
- **User domain model tests**: Any test constructing User dataclass must handle new `is_admin` field (has default=False, so low risk).

### Frontend Tests Likely to Break
- **Layout.test.tsx**: Layout now renders TreasureBalance; mocks for the credits API or useCredits hook needed.
- **CollectionCardDetail tests**: Refresh button now opens modal instead of calling API directly; test flow changes.
- **CollectionCardTile / DeckCardTile tests**: Same modal wrapping change.
- **useCollectionRefresh tests**: Bulk scan flow now includes modal step.

### Mitigation
- Create a shared `seed_credits` pytest fixture (backend) that grants 100 credits + sets is_admin=False for the standard test user.
- Create a separate `admin_user` fixture with is_admin=True for admin-bypass tests.
- Create a `mockUseCredits` helper (frontend) returning default values for non-credit-related tests.

---

## 7. Coverage Targets

### Expected New Tests

| Task | Backend | Frontend | Total |
|------|---------|----------|-------|
| T01  | 9       | 0        | 9     |
| T02  | 12      | 0        | 12    |
| T03  | 8       | 0        | 8     |
| T04  | 12      | 0        | 12    |
| T05  | 0       | 8        | 8     |
| T06  | 0       | 10       | 10    |
| Integration | 7 | 0     | 7     |
| **Total** | **48** | **18** | **66** |

### Coverage Goals

- **Backend:** Maintain >=91% overall coverage. New modules (`src/credits/`) target 95%+.
- **Frontend:** New components (TreasureBalance, CreditConfirmModal, TreasureTokenCard) target 100% line coverage. useCredits hook target 90%+.
- **Regression:** Zero existing test failures after credit-seeding fixtures are applied.

### Post-Feature Test Counts (estimated)

- Backend: ~1810 tests (current 1761 + 48 new + ~1 fixture adjustment)
- Frontend: ~981 tests (current 963 + 18 new)
