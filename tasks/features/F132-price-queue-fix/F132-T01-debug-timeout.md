# F132-T01: Debug and Fix Timeout on Refresh-Price

**Wave:** 0
**Status:** pending
**Depends on:** none

## User Story

As a user, when I click the refresh-price button on a card tile, the request
should succeed quickly (queue the request) instead of timing out, so that I
get immediate feedback that my price update was queued.

## Problem Analysis

The `POST /api/v1/cards/{card_id}/refresh-price` endpoint performs only:
1. Credit check (DB read)
2. Card lookup (DB read)
3. Credit deduction (DB write)
4. Queue row insert with 24h dedup (DB read + write)

This should complete in <200ms even on a cold Neon connection. However the
frontend `refreshCardPrice` in `frontend/src/api/cards.ts` calls `apiPost`
without a custom `timeoutMs`, so it inherits `DEFAULT_TIMEOUT_MS = 10_000`.

Potential causes of timeout:
- **Neon cold start**: first request after idle can take 1-2s (pool_pre_ping
  handles this, but only on the server side).
- **Render cold start**: free-tier Render spins down after inactivity; first
  request can take 10-30s to wake up the container.
- **Network latency**: user's browser to Render (US East) could be slow.

The fix is NOT to increase `DEFAULT_TIMEOUT_MS` globally (that would mask
real issues), but to pass a per-call `timeoutMs` to `refreshCardPrice`,
similar to how `searchCardsWeb` already passes `35_000`.

## Dev Notes

### 1. Frontend: Add timeout override to refreshCardPrice

File: `frontend/src/api/cards.ts`

```typescript
export function refreshCardPrice(
  cardId: number,
): Promise<ApiResponse<PriceRefreshResponse>> {
  return apiPost<PriceRefreshResponse>(
    `/api/v1/cards/${cardId}/refresh-price`,
    {},
    { timeoutMs: 30_000 },  // Allow for Render cold start
  );
}
```

Rationale: 30s covers Render spin-up (worst case). The endpoint itself is
fast once the server is warm. This matches the pattern used by
`searchCardsWeb` which already has `timeoutMs: 35_000`.

### 2. Frontend: Better error handling in CardTile

File: `frontend/src/components/CardTile.tsx` (handleRefresh)

Currently the catch block silently swallows errors. Add user-visible feedback:
- If the response has errors (including TIMEOUT), show a brief toast or
  change the icon to a red X for 3 seconds.
- Check `res.errors` array for TIMEOUT code and show a specific message.

### 3. Backend: Verify endpoint performance (optional)

Add a quick log timing to the refresh-price endpoint to confirm it runs
in <200ms. This is informational, not a code change to ship.

## Testing

### Backend
- Existing tests for `POST /cards/{card_id}/refresh-price` should still pass.
- No new backend tests needed (the fix is frontend-only).

### Frontend
- **Unit test**: `refreshCardPrice` passes `timeoutMs: 30_000` to `apiPost`.
  Mock `apiPost` and assert the options argument.
- **Unit test**: CardTile `handleRefresh` -- when `refreshCardPrice` returns
  an error response, the component shows error state (not just silent fail).
- **Unit test**: CardTile `handleRefresh` -- when response has TIMEOUT error
  code, component shows timeout-specific feedback.

## Acceptance Criteria

- [ ] `refreshCardPrice` calls `apiPost` with `{ timeoutMs: 30_000 }`
- [ ] CardTile shows visual feedback on refresh error (not silent fail)
- [ ] Existing card refresh tests pass
- [ ] No changes to `DEFAULT_TIMEOUT_MS` global constant
