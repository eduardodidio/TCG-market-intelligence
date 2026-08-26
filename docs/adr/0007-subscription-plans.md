# 0007 — Subscription Plans & Premium Credit Tiers

**Date:** 2026-08-26
**Status:** PROPOSED
**Deciders:** Eduardo Didio

## Context

The TCG Market Intelligence platform needs a monetization strategy. Currently
all features are available to all authenticated users with no usage limits
beyond rate limiting. As the platform grows and compute costs increase
(especially LigaMagic Playwright scraping at ~5.5s/card), a tiered subscription
model would allow sustainable operation while keeping a generous free tier.

Key forces:

- **Cost pressure**: Playwright-based scraping is resource-intensive; unlimited
  free usage is not sustainable long-term.
- **Credit system (F65)**: The credit/token system provides the metering
  foundation that subscriptions build upon.
- **User retention**: A free tier must remain useful enough to retain casual
  users while incentivizing upgrades.

## Decision

Document the subscription concept for future sprint planning. No implementation
in this ADR — this is a design sketch.

### Proposed Tiers

| Tier       | Monthly Credits | Bonus Multiplier | Price (BRL) | Notes                        |
|------------|-----------------|-------------------|-------------|------------------------------|
| Free       | —               | 1.0x              | R$ 0        | 10 credits/day via hourly bonus |
| Basic      | 500             | 1.5x              | R$ 9.90     | Monthly grant + enhanced bonus |
| Pro        | 2000            | 2.0x              | R$ 29.90    | Priority scans, bulk operations |
| Enterprise | 10000           | 3.0x              | R$ 99.90    | API access, custom integrations |

### Data Model Sketch

```sql
CREATE TABLE subscription_plans (
    id            INTEGER PRIMARY KEY,
    name          TEXT NOT NULL UNIQUE,
    monthly_credits INTEGER NOT NULL DEFAULT 0,
    bonus_multiplier REAL NOT NULL DEFAULT 1.0,
    price_brl     REAL NOT NULL DEFAULT 0.0,
    active        BOOLEAN NOT NULL DEFAULT TRUE,
    created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE user_subscriptions (
    id          INTEGER PRIMARY KEY,
    user_id     INTEGER NOT NULL REFERENCES users(id),
    plan_id     INTEGER NOT NULL REFERENCES subscription_plans(id),
    started_at  TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    expires_at  TIMESTAMP,
    status      TEXT NOT NULL DEFAULT 'active',  -- active, cancelled, expired
    UNIQUE(user_id)  -- one active subscription per user
);
```

### Credit Integration

- Free tier: 10 credits/day granted via hourly bonus claims (F65 mechanism).
- Paid tiers: monthly fixed credit grant on subscription start/renewal, plus
  bonus multiplier applied to hourly claims.
- Credits do not roll over between months for paid tiers.

### Payment

No payment gateway integration is planned yet. This ADR documents the
conceptual model only. Future options include Stripe, MercadoPago, or PIX
integration for Brazilian users.

## Consequences

- **Easier**: Revenue generation, cost allocation per user tier, feature gating.
- **Harder**: User management complexity, billing edge cases (upgrades,
  downgrades, refunds), support burden.
- **Trade-offs**: Free tier must remain genuinely useful or users churn before
  converting. Credit costs must be calibrated against actual compute costs.

## Alternatives Considered

- **Pay-per-use only** — rejected because subscription models have better
  retention and more predictable revenue.
- **Ads-based monetization** — rejected because ad integration conflicts with
  the clean dark-theme UI and TCG community expectations.
- **Donation/tip jar** — rejected as primary model because it does not scale,
  but could supplement subscriptions.
