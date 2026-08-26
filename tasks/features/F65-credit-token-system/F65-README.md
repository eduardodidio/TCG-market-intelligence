# F65 — Credit Token System (Treasure Tokens)

**Status:** planned
**Created:** 2026-08-26
**Priority:** P0 (core system — F66, F67, F69 depend on this)

## Summary

Introduce a credit economy based on "Treasure Tokens" (MTG flavor). Every
price-costing action costs credits: single card refresh = 1 credit, bulk
scan = 5 credits. Users earn 5 credits every 12 hours via explicit claim.
Admin users (`is_admin=1`) bypass all credit checks. The frontend displays
credits as treasure tokens in the sidebar with a confirmation modal before
credit-consuming actions.

## Business Rules

- **Costs**: Single refresh (MYP or Liga) = 1 credit. Bulk scan (POST /scans) = 5 credits.
- **Free actions**: POST /collection/canonize-all costs 0 credits.
- **No maximum**: Credits accumulate without limit.
- **Seed user**: Gets `is_admin=1` and 50 initial credits.
- **Bonus**: 5 credits every 12 hours, explicitly claimed via endpoint.
  NOT cumulative (missing a window does not stack).
- **Admin bypass**: `is_admin=1` users skip ALL credit checks (balance is
  never deducted for guarded endpoints).
- **Insufficient credits**: HTTP 402 (Payment Required) with structured error body.
- **Deduct after success**: Credits are deducted only after the provider
  returns price data. Failed refreshes do not cost credits.

## Acceptance Criteria

1. `credit_transactions` table logs every grant/deduct with timestamp + reason.
2. `POST /credits/claim-bonus` grants 5 credits if 12h+ since last claim.
3. `GET /credits/balance` returns current balance + next bonus eligibility.
4. `GET /credits/history` returns paginated transaction log.
5. Refresh endpoints return 402 when credits insufficient (non-admin).
6. Admin users (`is_admin=1`) bypass all credit checks.
7. Frontend shows credit balance in sidebar with claim button.
8. Confirmation modal appears before credit-consuming actions.
9. i18n keys for EN and PT-BR.

## Architecture Decisions

- **Separate balance table** (not a field on users): Allows atomic updates,
  cleaner audit trail, no contention with user profile updates.
- **Transaction log**: Immutable — every credit change is logged. Enables
  debugging, analytics, future refund capability.
- **is_admin on UserRow**: Simple boolean flag, no RBAC overhead for current needs.
- **402 status code**: Semantically correct for "you need credits to do this."
- **Credit service layer**: `src/credits/service.py` encapsulates all credit
  logic (check, deduct, grant, claim_bonus) — keeps routers thin.
- **Admin check at router level**: CreditService always charges; router-level
  guard skips the service call entirely for admin users.

## Waves

| Wave | Tasks | Description |
|------|-------|-------------|
| 0    | T01, T02 | DB models + migration + CreditService |
| 1    | T03, T04 | Credits API router + credit guards on refresh/scan endpoints |
| 2    | T05, T06 | Frontend: sidebar balance + confirmation modal |

## Tasks

- **T01** (Wave 0): DB models — CreditBalanceRow, CreditTransactionRow, is_admin on UserRow
- **T02** (Wave 0): Credit service — CreditService class with check/deduct/grant/claim_bonus
- **T03** (Wave 1): Credits API router — /credits/balance, /credits/history, /credits/claim-bonus
- **T04** (Wave 1): Credit guard on refresh + scan endpoints — deduct on success, 402 if insufficient, admin bypass
- **T05** (Wave 2): Frontend sidebar credit balance + treasure token icon
- **T06** (Wave 2): Frontend credit confirmation modal with treasure token card art

## Diagrams

- `docs/diagrams/F65-architecture.mmd` — credit flow: service, repo, tables, API
- `docs/diagrams/F65-journey.mmd` — user journey: claim bonus, refresh card, insufficient credits
