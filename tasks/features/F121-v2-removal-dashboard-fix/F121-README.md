# F121 — V2 Removal + Classic Dashboard Fix

**Status:** done
**Priority:** P0 (blocking production)
**Estimated tasks:** 4
**Waves:** 2

## Summary

Remove all V2 UI code (LayoutV2, DashboardV2, CollectionV2, RoutePrefixContext,
`/v2` routes) and revert classic layout pages to stop using `useRoutePrefix`.
Fix the "An internal error occurred" on the classic Dashboard page (500 from
a backend endpoint when running against Neon PostgreSQL). Ensure the classic
layout is fully functional with Neon PostgreSQL.

## Context

- V2 UI was introduced in F117/F118 but the user decided the classic layout
  is better. V2 code should be removed entirely, with design notes saved in
  memory for potential future reference.
- After migrating from SQLite to Neon PostgreSQL (us-east-1), the Dashboard
  page returns "An internal error occurred". The collection page works fine.
- The Dashboard calls 3 API endpoints: `/market/stats`, `/collect/health`,
  `/collection/summary`. All use SQLAlchemy ORM (PG-compatible). The exact
  failing endpoint needs runtime debugging.
- 21 page files were modified to use `useRoutePrefix()` — all need to be
  reverted to hardcoded paths.

## Wave Manifest

### Wave 0 (foundation — no file overlap)
- **F121-T01**: Delete V2 files and remove `/v2` routes from App.tsx
- **F121-T02**: Diagnose and fix Dashboard 500 error on PostgreSQL

### Wave 1 (depends on T01)
- **F121-T03**: Revert `useRoutePrefix` from all classic page files
- **F121-T04**: Frontend tests — verify classic layout works, V2 references gone

## Files to delete (8)
- `frontend/src/components/LayoutV2.tsx`
- `frontend/src/components/__tests__/LayoutV2.test.tsx`
- `frontend/src/pages/DashboardV2.tsx`
- `frontend/src/pages/CollectionV2.tsx`
- `frontend/src/pages/__tests__/V2Routes.test.tsx`
- `frontend/src/contexts/RoutePrefixContext.tsx`
- `frontend/tests/pages/CollectionV2.test.tsx`
- `frontend/tests/pages/DashboardV2.test.tsx`

## Files to modify (useRoutePrefix removal — 21 files + 2 structural)
- AchievementsPage, AdminPanel, AlertsPage, BanHistory, BanList,
  CardDetail, CatalogPage, CollectionCardDetail, Dashboard, DeckList,
  DeckView, Evaluations, MarketPage, Marketplace, MyCollection, Settings,
  TopDecksPage, TradeMatchesPage, Trending, WishlistPage
- `frontend/src/App.tsx` (remove V2 routes + RoutePrefixProvider wrapper)
- `frontend/src/components/Layout.tsx` (remove "Try New UI" floating button)

## Acceptance Criteria
1. No V2 files remain in the codebase
2. No imports of `useRoutePrefix` or `RoutePrefixContext` anywhere
3. Classic Dashboard loads without errors on Neon PostgreSQL
4. All classic pages navigate correctly with hardcoded paths
5. Frontend builds without errors
6. Existing tests pass (minus deleted V2 tests)
