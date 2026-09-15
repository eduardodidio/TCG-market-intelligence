# F118 — V2 Self-Contained Navigation

**Status:** planned
**Created:** 2026-09-10
**Branch:** homol

## Summary

Make the V2 layout fully self-contained: once a user enters `/v2`, all
navigation stays within the V2 layout. No page click should redirect to
the classic layout. The user only leaves V2 via the explicit "Back to
Classic" button.

**Approach:** Create a `RoutePrefixContext` + `useRoutePrefix()` hook.
Pages use the hook to prefix their internal links. The V2 layout provides
`prefix="/v2"`, the classic layout provides `prefix=""`. All existing page
components are reused — no business logic rewrite. Routes for `/v2/*` are
registered in App.tsx pointing to existing page components.

## Problem

LayoutV2 (F117) only has 2 pages: Dashboard and Collection. Its nav links
point to `/cards`, `/catalog`, `/alerts` — which are classic Layout routes.
Clicking them kicks the user back to the old UI. Internal links within
pages (e.g., CollectionV2 → `/collection/${id}`) also break out of V2.

## Wave Plan

| Wave | Tasks | Parallelism | Notes |
|------|-------|-------------|-------|
| 0 | T01 | 1 | RoutePrefixContext (new file, zero conflicts) |
| 1 | T02, T03 | 2 parallel | Routes + layouts (T02) vs page links (T03) |
| 2 | T04 | 1 | Tests |

## Task List

| Task | Summary | Wave | Files |
|------|---------|------|-------|
| T01 | RoutePrefixContext + useRoutePrefix hook | 0 | contexts/RoutePrefixContext.tsx (new) |
| T02 | Register all /v2/* routes + wire provider + expand LayoutV2 nav | 1 | App.tsx, Layout.tsx, LayoutV2.tsx |
| T03 | Migrate page internal links to use useRoutePrefix | 1 | ~12 page files |
| T04 | Tests for V2 routing + prefix context + nav self-containment | 2 | __tests__/*.test.tsx |

## File Conflict Map

- **RoutePrefixContext.tsx** — T01 creates (new file)
- **App.tsx** — T02 only
- **Layout.tsx** — T02 only (wrap with RoutePrefixProvider prefix="")
- **LayoutV2.tsx** — T02 only (wrap with RoutePrefixProvider prefix="/v2", expand NAV_ITEMS)
- **Page files** — T03 only (CollectionV2, CardDetail, CollectionCardDetail, CatalogPage, Dashboard, DeckList, MarketPage, Marketplace, MyCollection, TopDecksPage, TradeMatchesPage, Trending)
- **Test files** — T04 only

## Design Decisions

1. **RoutePrefixContext** — lightweight context (single string value), no re-render cost
2. **Reuse existing pages** — no V2-specific page rewrites needed (except CollectionV2/DashboardV2 which already exist)
3. **useRoutePrefix()** — pages call this to get "" or "/v2" and prepend to `to=` props
4. **Full nav in LayoutV2** — all primary + beta sections, admin route (same structure as classic)
5. **SharedCollectionPage stays classic** — public route, not inside V2 auth flow
