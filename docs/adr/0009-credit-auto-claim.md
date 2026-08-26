# 0009 — Credit Auto-Claim via Request Middleware

**Date:** 2026-08-26
**Status:** DEFERRED
**Deciders:** Eduardo Didio

## Context

The credit/token system (F65) includes an hourly bonus mechanism where users
can claim free credits periodically. The baseline design uses an explicit
`POST /credits/claim-bonus` endpoint that the frontend calls on a timer or
when the user clicks a "claim" button.

An alternative approach is to auto-grant credits transparently on any
authenticated API request, removing the need for explicit claims. This ADR
evaluates that alternative.

### Forces

- **User convenience**: Auto-claim means users never forget to claim or miss
  bonus windows.
- **Engagement incentive**: Explicit claims encourage users to return to the
  app (gamification).
- **Performance**: Auto-claim adds database overhead to every authenticated
  request.
- **Transparency**: Users may prefer seeing their credits grow explicitly
  rather than silently.

## Decision

**Start with the explicit endpoint** as implemented in F65. Revisit auto-claim
middleware based on user engagement data after the platform has active users.

### Deferred Design (for future reference)

```python
# Sketch — NOT implemented

class CreditAutoClaimMiddleware:
    """
    FastAPI middleware that auto-grants hourly bonus credits
    on authenticated requests when eligible.
    """

    async def __call__(self, request: Request, call_next):
        response = await call_next(request)

        user = getattr(request.state, "user", None)
        if user is None:
            return response

        # Check eligibility: 12h+ since last bonus
        now = datetime.utcnow()
        if user.last_bonus_at and (now - user.last_bonus_at).total_seconds() < 43200:
            return response

        # Auto-grant in background (non-blocking)
        background = BackgroundTasks()
        background.add_task(grant_bonus, user.id, amount=5)
        response.background = background

        return response
```

### Key Design Points

- **Cooldown**: 12 hours between auto-claims (same as explicit endpoint).
- **Grant amount**: 5 credits per auto-claim (configurable via env var).
- **Non-blocking**: Uses FastAPI `BackgroundTasks` so the response is not
  delayed by the credit grant.
- **DB overhead**: One read query per authenticated request to check
  `last_bonus_at`. Write only when granting (every 12h per user).
- **Subscription multiplier**: If ADR-0007 tiers are active, the auto-claim
  amount is multiplied by the user's `bonus_multiplier`.

### Trigger for Revisiting

Consider implementing auto-claim if:
- User engagement data shows < 30% of eligible users claim their bonus manually.
- The explicit claim button has low click-through rates.
- User feedback requests passive credit accumulation.

## Consequences

- **Easier** (if implemented): Zero-friction credit accumulation, no missed
  bonuses, simpler frontend (no claim button/timer).
- **Harder** (if implemented): +1 DB query per authenticated request, harder to
  debug credit grants, less gamification incentive to return.
- **Trade-offs**: Convenience vs. engagement. Auto-claim removes a reason for
  users to actively check the app, but also removes a friction point.

## Alternatives Considered

- **Explicit endpoint only (current)** — chosen as the starting approach.
  Simple, transparent, gamified. Users see a button, click it, get credits.
- **Cron job grant** — grant credits to all users on a schedule regardless of
  activity. Rejected because it rewards inactive users equally and does not
  incentivize engagement.
- **Login-only grant** — grant credits only on login. Rejected because it
  penalizes users who stay logged in with long-lived sessions.
