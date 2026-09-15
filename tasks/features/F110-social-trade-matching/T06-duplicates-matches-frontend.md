# T06 -- Duplicates View & Trade Matches Page

**Wave:** 2 (Frontend)
**Depends on:** T03, T04
**Blocks:** nothing

## User Story

As a user, I want to see my duplicate cards and find other users who want
them (or who have cards I want) so I can arrange trades.

## Dev Notes

### API client: `frontend/src/api/tradeMatch.ts`

```typescript
export async function fetchDuplicates(params?: {
  limit?: number;
  offset?: number;
}): Promise<{ duplicates: DuplicateCard[]; count: number }>;

export async function fetchTradeMatches(
  limit?: number,
): Promise<{ matches: TradeMatch[] }>;

export async function fetchReverseMatches(
  limit?: number,
): Promise<{ matches: TradeMatch[] }>;
```

### Types: `frontend/src/types/tradeMatch.ts`

```typescript
export interface DuplicateCard {
  card_id: number;
  name_en: string;
  name_pt: string | null;
  set_code: string | null;
  collector_number: string | null;
  quantity: number;
  surplus: number;
  quality: string | null;
  image_uri: string | null;
  current_price: number | null;
}

export interface MatchedCard {
  card_id: number;
  name_en: string;
  set_code: string | null;
  image_uri: string | null;
  partner_quantity: number;
  your_max_price: number | null;
}

export interface TradeMatch {
  partner_name: string;
  share_code: string;
  matching_card_count: number;
  matched_cards: MatchedCard[];
}
```

### TradeMatchesPage (`frontend/src/pages/TradeMatchesPage.tsx`)

- Route: `/trade-matches` (protected)
- Breadcrumb: Home > Trade Matches

- **Three sections** (tabs or accordion):

  1. **My Duplicates** -- grid of duplicate cards showing surplus count,
     image, name, price. Links to card detail. Badge showing "x2", "x3" etc.
     Empty state: "No duplicates found. Cards with quantity > 1 appear here."

  2. **They Have What I Want** -- list of trade partners ranked by match
     count. Each partner card shows: display_name (or "Anonymous"),
     share_code link, matching card count, expandable list of matched cards
     with thumbnails.
     Empty state: "Add cards to your wishlist to find trade partners."
     CTA: "Go to Wishlist"

  3. **They Want What I Have** (reverse matches) -- same layout as above
     but reversed. Shows users whose wishlists match my duplicates.
     Empty state: "Share your collection and have duplicates to appear here."

### DuplicatesList (`frontend/src/components/DuplicatesList.tsx`)

- Reusable component for the duplicates grid
- Props: `duplicates: DuplicateCard[]`
- Each card: image, name, set badge, surplus badge (green "x2"),
  current price if available
- Compact mode for embedding in other pages

### Integration points

- Add `/trade-matches` route to `App.tsx` (protected, lazy loaded)
- Add nav link in `Layout.tsx` sidebar (under Marketplace section,
  next to "My Trades")
- Link from MyTrades page to TradeMatchesPage ("Find trade partners")
- i18n keys for both locales:
  - `tradeMatch.title`, `tradeMatch.duplicates`, `tradeMatch.theyHave`,
    `tradeMatch.theyWant`, `tradeMatch.matchingCards`, `tradeMatch.surplus`,
    `tradeMatch.noMatches`, `tradeMatch.noDuplicates`, `tradeMatch.anonymous`,
    `tradeMatch.viewCollection`, `tradeMatch.goToWishlist`,
    `tradeMatch.shareToMatch`

## Testing

- Test TradeMatchesPage renders all three tabs
- Test empty states for each section
- Test duplicates list renders cards with surplus badge
- Test trade matches display partner info
- Test reverse matches section
- Test link to partner's shared collection (via share_code)
- Test responsive layout (mobile: single column)
- Test i18n keys exist in both locales
