# F189-T02 — Remove BetaRoute from decks, move to primary nav

**Feature:** F190
**Wave:** 0
**Status:** planned
**Parallel:** no (runs after T01 in Wave 0; depends on T01 completing to avoid merge conflicts on App.tsx and Layout.tsx)

## User Story

As a user, I want deck pages to appear in the main navigation instead of under a Beta section, so I can find and use my decks without toggling the Beta menu.

## Dev Notes

### Files to MODIFY

**`frontend/src/App.tsx`**
- Remove `<BetaRoute>` wrapper from the `/decks` route (lines 322-324 become just `<DeckList />`)
- Remove `<BetaRoute>` wrapper from the `/decks/ranking` route (lines 334-336 become just `<TopDecksPage />`)
- Remove `<BetaRoute>` wrapper from the `/decks/:id` route (lines 362-364 become just `<DeckView />`)
- Note: after T01 runs, the `/decks/build` route is already gone, so only 3 routes need unwrapping
- Check if BetaRoute import can be removed entirely; likely NOT, since other routes (marketplace, trade-matches, etc.) still use it

**`frontend/src/components/Layout.tsx`**
- Remove from BETA_NAV_ITEMS:
  - `{ to: "/decks", labelKey: "nav.myDecks", requiresAuth: true, icon: ICONS.rectStack }` (line 77)
  - `{ to: "/decks/ranking", labelKey: "nav.topDecks", requiresAuth: true, icon: ICONS.star }` (line 78)
  - (buildDeck and deckEvaluator already removed by T01)
- Add to PRIMARY_NAV_ITEMS (insert after the alerts entry, before settings):
  - `{ to: "/decks", labelKey: "nav.myDecks", requiresAuth: true, icon: ICONS.rectStack }`
  - `{ to: "/decks/ranking", labelKey: "nav.topDecks", requiresAuth: true, icon: ICONS.star }`
- Current PRIMARY_NAV_ITEMS order (line 62-71): dashboard, myCollection, importPurchases, wishlist, exploreCards, alerts, settings, admin
- New order: dashboard, myCollection, importPurchases, wishlist, exploreCards, alerts, **myDecks, topDecks**, settings, admin

### Key constraints
- BetaRoute.tsx component file is NOT deleted (still used by marketplace, trade-matches, achievements, evaluations, market, trending, banlist, news)
- The BetaRoute import in App.tsx stays (other routes still use it)
- No backend changes needed

### Edge cases
- Verify that the deck pages remain accessible only to authenticated users (requiresAuth: true on nav items, and the ProtectedRoute wrapper or equivalent guards in the route tree)
- If ProtectedRoute wraps the deck routes at a higher level in the Route tree, the requiresAuth on nav items is sufficient for hiding the nav link from guests

## Testing

- [ ] `npm run build` succeeds
- [ ] `npm test` passes — update any tests that assert BetaRoute wrapping on deck pages
- [ ] Manual: /decks appears in primary sidebar nav (not under Beta section)
- [ ] Manual: /decks/ranking appears in primary sidebar nav
- [ ] Manual: clicking deck nav items navigates correctly
- [ ] Manual: deck pages are accessible without toggling Beta nav
- [ ] Manual: other Beta nav items (market, trending, marketplace, etc.) remain under Beta section
- [ ] Manual: unauthenticated users do NOT see deck nav items
