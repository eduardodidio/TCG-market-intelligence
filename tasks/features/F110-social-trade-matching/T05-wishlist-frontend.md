# T05 -- Wishlist Page & "Add to Wishlist" Button

**Wave:** 2 (Frontend)
**Depends on:** T02
**Blocks:** nothing

## User Story

As a user, I want a dedicated Wishlist page to manage my wanted cards,
and I want an "Add to Wishlist" button on card detail pages so I can
quickly add cards I want.

## Dev Notes

### API client: `frontend/src/api/wishlist.ts`

```typescript
export async function fetchWishlist(params?: {
  search?: string;
  acquired?: boolean;
  limit?: number;
  offset?: number;
}): Promise<{ items: WishlistItem[]; count: number }>;

export async function addToWishlist(
  cardId: number,
  notes?: string,
  maxPrice?: number,
): Promise<void>;

export async function removeFromWishlist(cardId: number): Promise<void>;

export async function markAcquired(cardId: number): Promise<void>;

export async function checkWishlist(
  cardIds: number[],
): Promise<{ wishlisted: number[] }>;
```

### Types: `frontend/src/types/wishlist.ts`

```typescript
export interface WishlistItem {
  id: number;
  card_id: number;
  name_en: string;
  name_pt: string | null;
  set_code: string | null;
  collector_number: string | null;
  notes: string | null;
  max_price: number | null;
  is_acquired: boolean;
  acquired_at: string | null;
  created_at: string;
  image_uri: string | null;
  current_price: number | null;
}
```

### WishlistPage (`frontend/src/pages/WishlistPage.tsx`)

- Route: `/wishlist` (protected)
- Breadcrumb: Home > Wishlist
- Tabs: "Wanted" (is_acquired=false) | "Acquired" (is_acquired=true)
- Card grid with: image thumbnail, name, set, price, notes, actions
- Actions per card: Remove (trash icon), Mark Acquired (check icon)
- Search bar (filters by name)
- Empty state when no items (use EmptyState component)
- "Browse Catalog" CTA in empty state

### AddToWishlistButton (`frontend/src/components/AddToWishlistButton.tsx`)

- Heart icon button (outline when not wishlisted, filled when wishlisted)
- Props: `cardId: number`
- Uses `checkWishlist` on mount (batch check via context or per-card)
- On click: toggle add/remove with optimistic UI
- Place on: CardDetail page, CatalogPage card items, collection card detail

### Integration points

- Add `/wishlist` route to `App.tsx` (protected, lazy loaded)
- Add nav link in `Layout.tsx` sidebar (under Collection section)
- Add `AddToWishlistButton` to `CardDetail.tsx` header area
- i18n keys for both `en.json` and `pt-BR.json`:
  - `wishlist.title`, `wishlist.empty`, `wishlist.addSuccess`,
    `wishlist.removeSuccess`, `wishlist.markAcquired`, `wishlist.tabs.wanted`,
    `wishlist.tabs.acquired`, `wishlist.browseCatalog`, `wishlist.maxPrice`,
    `wishlist.notes`

## Testing

- Test WishlistPage renders empty state
- Test WishlistPage renders items
- Test tab switching (wanted vs acquired)
- Test remove item (optimistic + API call)
- Test mark acquired
- Test AddToWishlistButton toggle state
- Test search filter
- Test i18n keys exist in both locales
