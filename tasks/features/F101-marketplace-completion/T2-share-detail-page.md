# T2 — Share Code Detail Page

**Wave:** 1
**Type:** Frontend
**Depends on:** T1
**Estimate:** Medium

## User Story

As a user who receives a share code (via chat, forum, etc.), I want to open
`/marketplace/share/<code>` in my browser and see that seller's shared
collection with card images, names, prices, and the ability to express interest.

## Desired Behavior

### Route: `/marketplace/share/:code`
- **Public page** — no authentication required to view.
- Shows a header with the share code and collection stats (total cards, sets,
  shared_at) from the enhanced T1 endpoint.
- Lists cards in a responsive grid (reuse `MarketplaceCardTile` from
  `Marketplace.tsx`).
- Search bar to filter within the collection.
- Pagination (load more or infinite scroll matching existing patterns).
- "Express Interest" button on each card (requires auth — redirect to login
  if not authenticated).
- Breadcrumb: Dashboard > Marketplace > Collection `<code>`.

### Empty / error states:
- Invalid share code -> show `EmptyState` with "Collection not found" message.
- Empty collection -> show `EmptyState` with "This collection has no cards".
- Network error -> show `ErrorBanner` with retry.

## Dev Notes

### New files:
- `frontend/src/pages/SharedCollectionPage.tsx` — the page component.

### Files to modify:
- `frontend/src/App.tsx` — add lazy import + route `/marketplace/share/:code`
  (public, inside Layout, NOT wrapped in ProtectedRoute).
- `frontend/src/api/marketplace.ts` — add `fetchSharedCollection(code, params)`
  function calling `GET /api/v1/marketplace/listings/{code}`.
- `frontend/src/i18n/locales/en.json` — add keys under `marketplace`:
  `sharedCollection`, `collectionNotFound`, `emptyCollection`, `totalCards`,
  `sharedSince`, `copyCode`.
- `frontend/src/i18n/locales/pt-BR.json` — corresponding Portuguese keys.

### Implementation pattern:
- Follow `Marketplace.tsx` structure (useState + useEffect + useCallback).
- Extract `MarketplaceCardTile` into its own file if not already, or import
  from Marketplace. If extracting is complex, just duplicate the component
  in the new page (small, self-contained).
- Use `useParams()` to get the share code from the URL.
- The route must be placed BEFORE the `/marketplace` catch-all route in
  App.tsx to avoid conflicts.

### Key constraint:
- The page MUST work without authentication. The "Express Interest" button
  should check auth state and redirect to `/login?redirect=/marketplace/share/<code>`
  if the user is not logged in.

## Testing

### Vitest + React Testing Library:
- `test_renders_shared_collection_page` — mock API, verify cards render.
- `test_shows_empty_state_for_invalid_code` — mock 404, verify EmptyState.
- `test_shows_collection_stats` — verify total_cards, sets, shared_at display.
- `test_interest_button_redirects_when_unauthenticated` — verify redirect.
- `test_search_filters_listings` — type in search, verify API called with param.
- `test_breadcrumb_shows_share_code` — verify breadcrumb structure.
