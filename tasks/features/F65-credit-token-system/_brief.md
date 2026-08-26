# F65 — Credit Token System (Treasure Tokens)

## Problem
All authenticated operations (price scans, Liga refreshes, bulk canonize) are
currently unlimited. As compute costs grow (Playwright ~5.5s/card), a metering
layer is needed before subscription tiers (ADR-0007) can be built.

## Scope
- **Backend**: `credit_balances` + `credit_transactions` SQLite tables,
  `is_admin` field on users, `CreditService` (check/deduct/grant/claim_bonus
  5 credits every 12h), `/credits/*` API endpoints, 402 guard on refresh
  endpoints.
- **Frontend**: sidebar `TreasureBalance` widget, `CreditConfirmModal` with
  MTG card art theme, i18n (EN + PT-BR).

## Constraints
- No payment gateway — credits are earned via hourly bonus only (for now).
- Admin users bypass credit checks entirely.
- ADR-0009 (auto-claim middleware) is DEFERRED — use explicit endpoint.
- Credit costs: single refresh = 1 credit, bulk scan = 5 credits.
- New seed user gets 50 initial credits.

## Acceptance Criteria
1. `credit_transactions` table logs every grant/deduct with timestamp + reason.
2. `POST /credits/claim-bonus` grants 5 credits if 12h+ since last claim.
3. `GET /credits/balance` returns current balance + next bonus eligibility.
4. `GET /credits/history` returns paginated transaction log.
5. Refresh endpoints return 402 when credits insufficient (non-admin).
6. Admin users (is_admin=true) bypass all credit checks.
7. Frontend shows credit balance in sidebar with claim button.
8. Confirmation modal appears before credit-consuming actions.
9. i18n keys for EN and PT-BR.
