# F69 — Share Collection & Trading System

**Status:** planned
**Created:** 2026-08-26
**Priority:** P2 (marketplace feature)
**Wave Group:** 3 (depends on F65 credit system + F66 admin panel)

## Summary

Enable users to share their collections publicly (anonymized) and express
interest in trading cards. The platform acts as a privacy-first intermediary:
user identities are hidden until both parties agree to a trade. On agreement,
the platform reveals contact info and charges a credit fee based on card value
(Fibonacci-inspired tiers). Fees are charged to BOTH buyer and seller.

## Credit Fee Tiers (per card)

| Card Value (BRL) | Fee (credits) |
|-------------------|---------------|
| <= R$10           | 2             |
| <= R$50           | 3             |
| <= R$100          | 5             |
| <= R$150          | 8             |
| <= R$200          | 13            |
| <= R$500          | 21            |
| > R$500           | 50            |

## Acceptance Criteria

1. Toggle sharing on/off for user's collection
2. Shared collections browsable at /marketplace (anonymized — no user names)
3. Users can express interest in specific cards from shared collections
4. Card owners see interest notifications
5. Both parties can accept/reject trade interest
6. On mutual agreement: platform reveals emails, deducts credits from both
7. Credit fee based on card's latest price (tier table above)
8. Insufficient credits prevents trade completion (preview fee first)
9. Trade history visible at /marketplace/my-trades
10. Privacy: No user data leaked before agreement

## Architecture Decisions

- **Anonymized listings**: Shared collection shows card data but not user info.
  Each listing has a random reference code (not user ID).
- **Interest model**: Buyer expresses interest → seller reviews → both confirm → reveal
- **Fee charged on reveal**: Credits deducted only when both parties confirm.
  Interest expression is free.
- **Price for fee calculation**: Use latest `price_observations` median_price.
  If no price, use R$10 tier (minimum fee of 2 credits).
- **No real-time chat**: Trade communication via structured messages in
  trade_interests table. Future: websocket chat.

## Waves

| Wave | Tasks | Description |
|------|-------|-------------|
| 0    | T01   | Database models (sharing, interests, agreements) |
| 0    | T02   | Trade fee calculator (price tier logic) |
| 1    | T03   | Marketplace API router (listings, interest, agree) |
| 2    | T04   | Frontend: share toggle + marketplace browse page |
| 3    | T05   | Frontend: trade flow (interest, negotiation, agreement) |

## Tasks

- **T01** (Wave 0): DB models — SharedCollectionRow, TradeInterestRow, TradeAgreementRow
- **T02** (Wave 0): Trade fee calculator — pure function mapping price to credit tier
- **T03** (Wave 1): Marketplace API — /marketplace/listings, /interest, /agree, /my-trades
- **T04** (Wave 2): Frontend marketplace browse page + share toggle
- **T05** (Wave 3): Frontend trade flow — interest form, negotiation, agreement reveal
