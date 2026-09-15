# F101 — Marketplace Completion

**Status:** planned
**Priority:** P2
**Branch:** homol

## Summary

Complete the marketplace experience by adding a public share code detail page,
a copy-to-clipboard button for share codes, and promoting the Marketplace link
from the Beta nav section to the primary navigation.

## Current State

The marketplace system already has:
- **Backend:** Full router at `src/api/routers/marketplace.py` with 7 endpoints
  (sharing toggle, browse listings, view shared collection by code, express
  interest, my trades, respond, confirm agreement).
- **Frontend:** `Marketplace.tsx` page (browse + interest modal), `MyTrades.tsx`
  page, `marketplace.ts` API client with all fetch functions.
- **Models:** `SharedCollectionRow` (share_code, is_shared), `TradeInterestRow`,
  `TradeAgreementRow`.
- **Nav:** Marketplace link exists but is buried in the "Beta Test" collapsible
  section of `Layout.tsx`.

## What Is Missing

1. **No share code detail page** — `GET /marketplace/listings/:share_code`
   exists on the backend but there is no frontend route `/marketplace/share/:code`
   to display a specific seller's shared collection. The API also returns only
   `share_code` without the seller's display name or collection stats.
2. **No copy-code UX** — Share codes are shown truncated (`slice(0,8)...`) on
   marketplace tiles with no way to copy them.
3. **Nav buried** — The Marketplace link requires expanding the Beta section;
   it should be in the primary nav for authenticated users.

## Wave Plan

### Wave 0 — Backend (1 task)
| Task | File | Description |
|------|------|-------------|
| T1 | `T1-share-collection-endpoint.md` | Enhance `GET /marketplace/listings/:share_code` to return collection metadata (card count, set breakdown, shared_at) |

### Wave 1 — Frontend (3 tasks, parallelizable)
| Task | File | Description |
|------|------|-------------|
| T2 | `T2-share-detail-page.md` | New `SharedCollectionPage` at `/marketplace/share/:code` (public) |
| T3 | `T3-copy-code-button.md` | `CopyCodeButton` component + integration in Marketplace tiles |
| T4 | `T4-nav-link-promotion.md` | Move Marketplace from BETA_NAV to PRIMARY_NAV in Layout.tsx |

## Dependencies

- T2 depends on T1 (needs enhanced endpoint response).
- T3 and T4 are independent of each other and of T2.

## Risk Assessment

Low risk. No new database tables. One endpoint enhancement, one new page, two
small component changes. All patterns well-established in the codebase.
