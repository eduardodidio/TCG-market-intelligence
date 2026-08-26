# F65 Credit Token System -- Tech Lead Review Report

**Reviewer:** Tech Lead agent
**Date:** 2026-08-26
**Verdict:** APPROVED (after fixing 2 BLOCKING issues inline)

---

## BLOCKING Issues (Fixed)

### B1. Frontend ClaimBonusResponse field name mismatch

**Files:** `frontend/src/api/credits.ts`, `frontend/src/hooks/useCredits.ts`

The backend `POST /credits/claim-bonus` returns `{"balance": N, "credited": 5}`,
but the frontend `ClaimBonusResponse` interface declared `new_balance` and
`amount_claimed`, and `useCredits.ts` read `res.data.new_balance`. This meant
clicking "Claim Bonus" would silently fail to update the displayed balance
(set `null` into state).

**Fix applied:** Changed `ClaimBonusResponse` to `{ balance, credited }` and
updated `useCredits.ts` to read `res.data.balance`.

### B2. MYP refresh deducted credits even when no price was returned

**File:** `src/api/routers/collection.py` (refresh_card_price endpoint)

The credit deduction at line 884 ran unconditionally after the price fetch,
regardless of whether `jsonld.price` was null/zero. The spec says "Credits
are deducted only after the provider returns price data. Failed refreshes
do not cost credits." The Liga refresh correctly guarded this (returns early
on no-price/error paths before the deduction), but the MYP path did not.

**Fix applied:** Added a `price_saved` flag; credits are only deducted when
`price_saved is True`.

---

## IMPORTANT Findings (Non-blocking)

### I1. TOCTOU between check_sufficient and deduct

**Files:** `src/api/routers/collection.py`, `src/api/routers/scans.py`

The router calls `check_sufficient()` (read-only), then later calls `deduct()`
separately. Between those two calls, a concurrent request could drain the
balance. The `deduct()` method does check balance again inside
`update_credit_balance` and raises `ValueError` if negative, so credits cannot
go below zero. However, the `ValueError` is not caught by the router, meaning
it would bubble up as a 500 Internal Server Error rather than a clean 402.

**Recommendation:** Wrap the `deduct()` call in a try/except for `ValueError`
(or `InsufficientCreditsError`) and return 402 on that path. Alternatively,
merge check+deduct into a single atomic `deduct_if_sufficient()` method.

**Risk:** Low for SQLite single-writer, but would become a real issue with
PostgreSQL or concurrent API servers.

### I2. Bulk scan deducts credits upfront (before knowing success)

**File:** `src/api/routers/scans.py` line 140

For bulk scans, credits are deducted before the background thread even starts.
If the scan thread crashes immediately, credits are lost. This is documented
as intentional in the journey diagram ("5 credits upfront") and is a reasonable
design choice for async operations, but differs from the spec line "Credits
are deducted only after the provider returns price data."

**Recommendation:** Document this explicitly in the README as an intentional
design difference. Background scans cannot deduct after completion without a
callback mechanism.

### I3. CreditHistoryResponse `total` field never returned by backend

**File:** `frontend/src/api/credits.ts` line 20, `src/api/routers/credits.py` line 45

The frontend `CreditHistoryResponse` type declares a `total` field, but the
backend `GET /credits/history` endpoint only returns `{"transactions": [...]}`
with no `total` key. The field is unused in the current frontend code, so this
is not breaking, but it will become an issue if pagination UI is added later.

**Recommendation:** Either add `total` to the backend response or remove it
from the frontend type.

### I4. No input validation on grant/deduct amounts

**File:** `src/credits/service.py`

Neither `grant()` nor `deduct()` validates that `amount`/`cost` is positive.
Calling `service.grant(user_id, -10, "exploit")` would effectively deduct
credits without the balance check. This is not exploitable via the current
API (no public endpoint exposes `grant()` with user-controlled amounts), but
is a latent risk if an admin grant endpoint is added later.

**Recommendation:** Add `if amount <= 0: raise ValueError(...)` to `grant()`
and `if cost <= 0: raise ValueError(...)` to `deduct()`.

---

## MINOR Findings

### M1. Credits router does not use Pydantic response models

**File:** `src/api/routers/credits.py`

The schemas `CreditBalanceResponse`, `CreditTransactionSchema`, and
`ClaimBonusResponse` are defined in `src/api/schemas/credits.py` but the
router returns plain dicts instead of using `response_model=`. This works
but loses automatic validation and OpenAPI documentation.

### M2. `CreditBalanceResponse` missing `last_bonus_at` and `bonus_amount` fields

**File:** `frontend/src/api/credits.ts`

The backend returns `last_bonus_at` and `bonus_amount` in the balance
response, but the frontend `CreditBalanceResponse` interface omits them.
Not currently used in the UI, but makes the type incomplete.

### M3. TreasureTokenCard uses unicode coin emoji

**File:** `frontend/src/components/TreasureTokenCard.tsx` line 26

The `&#x1FA99;` (coin emoji) may not render on all platforms/browsers. The
TreasureBalance component uses a simpler "T" letter approach which is more
robust. Consider a fallback or SVG icon.

### M4. i18n key consistency

The PT-BR translations lack diacritical marks in some credit keys (e.g.,
"Bonus disponivel" should be "Bonus disponivel" or "disponivel"). This is
consistent with the existing pattern in the codebase (ASCII-only PT-BR
translations) but may be worth noting for a future polish pass.

### M5. Each TreasureBalance/DeckCardTile/CollectionCardTile creates its own useCredits instance

Multiple components on the same page each instantiate `useCredits()`,
causing redundant `/credits/balance` API calls. For a future optimization,
consider lifting credits state to a React context.

---

## Security Review

| Check | Status |
|-------|--------|
| Cannot deduct negative amounts (exploit via grant) | Latent risk (see I4), not exploitable via API |
| Balance cannot go below zero | OK -- repo.update_credit_balance checks |
| Admin bypass at router level only | OK -- service always charges |
| All credit endpoints require auth | OK -- Depends(get_current_user) |
| 402 responses are consistent | OK -- same structure across all guarded endpoints |
| Provider errors do not deduct credits | OK (Liga: early return; MYP: fixed in B2) |
| is_admin cannot be self-assigned via API | OK -- no public endpoint to set is_admin |
| Transaction log is immutable (append-only) | OK -- no delete/update endpoints |

## Test Coverage

| Test File | Tests | Coverage Assessment |
|-----------|-------|-------------------|
| test_credit_models.py | 27 | Thorough -- models, repo methods, migration, seed simulation |
| test_service.py | 28 | Thorough -- all service methods, edge cases, bonus timing |
| test_credits_router.py | 13 | Good -- balance, history, claim-bonus, auth required |
| test_credit_guards.py | 15 | Excellent -- 402/admin bypass/deduct-after-success/provider errors |
| TreasureBalance.test.tsx | 12 | Good -- states, loading, admin badge, layout integration |
| CreditConfirmModal.test.tsx | 17 | Thorough -- open/close, cost/balance, admin, buttons, backdrop |

**Total new tests:** 112 (83 backend + 29 frontend)

## i18n Review

Both `en.json` and `pt-BR.json` have matching credit key sets (16 keys each).
All frontend components use `t()` calls with the correct keys.

## Diagram Review

Both `F65-architecture.mmd` and `F65-journey.mmd` are present, syntactically
valid Mermaid, and accurately reflect the implemented architecture and user
flows.

---

## Summary

The feature is well-structured with clean separation of concerns (constants,
exceptions, service, router guards). The MTG Treasure Token theming is a nice
touch. Two blocking issues were found and fixed during this review:

1. Frontend/backend field name mismatch on claim-bonus response
2. MYP refresh deducting credits even when no price data was returned

With these fixes applied and all 112 tests passing, the feature is **APPROVED**.
