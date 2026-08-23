# F52 — Fix Dashboard Trending (Gainers/Losers)

**Status:** done
**Priority:** high (regression bug)
**Dependencies:** none

## Summary

The dashboard trending section (gainers/losers) stopped showing data after
recent refactors (F38 landing trending, F44 shared data arch). Backend
investigation confirms the API IS returning data correctly (3 gainers,
1 loser found in database). The issue is on the frontend side.

## Root Cause Analysis

Backend API at `/market/trending/gainers` and `/losers` returns valid data.
Possible frontend causes:

1. **API response envelope mismatch**: `TrendingSection` expects
   `TrendingResponse` but the API may wrap it in `ApiResponse<T>` envelope
   (`{ data, errors, meta }`). If `useApi` doesn't unwrap correctly, the
   component receives `undefined` cards.
2. **Cache initialization**: `TrendingService` has a 30-min cache. If the
   service was created before price data existed, the cache holds empty
   results until TTL expires. No cache invalidation on price scans.
3. **Signal/abort issue**: `TrendingSection.tsx:35` receives `signal` from
   `useApi` but doesn't pass it to `fetchTrending()` — requests may be
   silently aborted.
4. **Rendering condition**: The component shows empty state when
   `data.cards.length === 0` — if `data` is the raw API envelope, then
   `data.cards` would be `undefined`.

## Waves

### Wave 0 (all parallel)
- **F52-T01** — Debug and fix trending data flow (frontend) -- **done**
- **F52-T02** — Add cache invalidation on scan completion -- **done**
