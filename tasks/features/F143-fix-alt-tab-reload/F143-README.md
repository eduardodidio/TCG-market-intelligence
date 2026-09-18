# F143 — Fix Alt-Tab Page Reload

**Status:** planned
**Created:** 2026-09-18
**Priority:** P1

## Summary

Quick alt-tab causes visible page reload. Root cause: multiple independent
`visibilitychange` handlers fire simultaneously on tab focus, each triggering
API calls that cascade into full re-renders. The 30-second debounce is too
aggressive for normal alt-tab workflows.

## Root Cause Analysis

Four independent `visibilitychange` listeners exist:

| Location | Debounce | What it does |
|----------|----------|--------------|
| `useApi.ts` (L82-95) | 30s (`REFETCH_DEBOUNCE_MS`) | Generic refetch for any `useApi` caller with `refetchOnFocus: true` |
| `DeckList.tsx` (L38-47) | 30s (hardcoded) | Re-fetches deck list — **duplicates** what `useApi` would do |
| `MyCollection.tsx` (L408-418) | 30s (hardcoded) | Increments `refreshKey` to trigger re-fetch — **duplicates** what `useApi` would do |
| `useOwnedCardIds.ts` (L43-52) | **NONE** | Re-fetches entire collection (`limit=9999`) on every single tab focus |

Problems:
1. **`useOwnedCardIds` has zero debounce** — fetches 9999 cards on every alt-tab.
2. **30s debounce is too short** — a quick alt-tab to check Discord/docs triggers reload.
3. **DeckList and MyCollection** have hand-rolled handlers that duplicate `useApi`'s built-in `refetchOnFocus` capability.
4. On pages like Dashboard, `refetchOnFocus: true` is used by multiple `useApi` calls (health + summary), plus `useOwnedCardIds` fires from MarketPage/Trending — all at once.

## Fix Strategy

1. Increase `REFETCH_DEBOUNCE_MS` from 30s to **120s** (2 minutes) in `useApi.ts`.
2. Remove the custom `visibilitychange` handler from `DeckList.tsx` and refactor to use `useApi` with `refetchOnFocus: true`.
3. Remove the custom `visibilitychange` handler from `MyCollection.tsx` and wire the stale-check through the existing data flow (or use `useApi`'s refetchOnFocus).
4. Add a debounce to `useOwnedCardIds.ts` — add a `lastFetchedAtRef` with the same 120s threshold.

## Scope

| In scope | Out of scope |
|----------|--------------|
| `useApi.ts` debounce increase (30s -> 120s) | Service Worker / PWA update prompts |
| `DeckList.tsx` visibilitychange removal | New caching layer |
| `MyCollection.tsx` visibilitychange removal | React Query migration |
| `useOwnedCardIds.ts` debounce addition | Backend API changes |

## Consumers of refetchOnFocus (unchanged, just get longer debounce)

- `Dashboard.tsx` — `fetchCollectionHealth()`, `fetchCollectionSummary()` (both `refetchOnFocus: true`)
- `CollectionCardDetail.tsx` — card detail fetch (`refetchOnFocus: true`)

## Tasks

| ID | Title | Wave | Depends on |
|----|-------|------|------------|
| T01 | Increase useApi debounce + add debounce to useOwnedCardIds | 0 | -- |
| T02 | Remove redundant visibilitychange handlers from DeckList + MyCollection | 0 | -- |

## Waves

- **Wave 0**: T01 + T02 (parallel — T01 touches hooks, T02 touches pages)

## Risks

- Increasing debounce to 120s means users returning after 1-2 minutes see stale data until next manual action. Acceptable tradeoff: the manual refresh button still works, and 2 minutes is a reasonable staleness window for price data that updates daily.
- DeckList currently does NOT use `useApi` — it has manual fetch logic. T02 can either refactor to `useApi` or simply remove the visibilitychange handler and keep the manual fetch (simpler, less risky).
