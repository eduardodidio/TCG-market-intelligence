# F132-T03: Frontend Polling for Price Request Status

**Wave:** 0
**Status:** pending
**Depends on:** none

## User Story

As a user, after I click "refresh price" on a card, I want to see a
spinning indicator that automatically updates when the price request is
processed, showing me the new price or an error message, instead of a
static clock icon that disappears after 5 seconds.

## Current Behavior

In `CardTile.tsx` (lines 51-68), `handleRefresh`:
1. Calls `refreshCardPrice(card.id)` (POST to queue the request)
2. If response is `"queued"`, sets `queued = true`
3. After 5 seconds, `setTimeout(() => setQueued(false), 5000)` clears it
4. Never polls `GET /cards/{card_id}/price-request-status`

The status endpoint already exists (cards.py lines 305-326) and returns:
```json
{
  "status": "pending|processing|completed|failed",
  "requested_at": "...",
  "processed_at": "...",
  "result_price": 12.50
}
```

## Dev Notes

### 1. Add fetchPriceRequestStatus to frontend API

File: `frontend/src/api/cards.ts`

```typescript
export interface PriceRequestStatus {
  status: "none" | "pending" | "processing" | "completed" | "failed";
  requested_at?: string;
  processed_at?: string;
  result_price?: number | null;
}

export function fetchPriceRequestStatus(
  cardId: number,
): Promise<ApiResponse<PriceRequestStatus>> {
  return apiGet<PriceRequestStatus>(
    `/api/v1/cards/${cardId}/price-request-status`,
  );
}
```

### 2. Add usePriceRequestPolling hook

Create: `frontend/src/hooks/usePriceRequestPolling.ts`

This hook encapsulates the polling logic, keeping CardTile clean:

```typescript
interface UsePriceRequestPollingOptions {
  cardId: number;
  enabled: boolean;  // start polling when true (after queue response)
  onCompleted?: (price: number | null) => void;
  onFailed?: (error?: string) => void;
  intervalMs?: number;   // default 5000
  maxDurationMs?: number; // default 60000 (stop after 60s)
}

interface UsePriceRequestPollingResult {
  status: PriceRequestStatus["status"];
  isPolling: boolean;
  resultPrice: number | null;
}
```

Behavior:
- When `enabled` becomes true, start polling every `intervalMs` (5s).
- On each poll, call `fetchPriceRequestStatus(cardId)`.
- If status is `"completed"`: stop polling, call `onCompleted(result_price)`.
- If status is `"failed"`: stop polling, call `onFailed()`.
- If `maxDurationMs` (60s) elapsed: stop polling (request may still be
  pending but we stop to avoid infinite polling).
- Cleanup: clear interval on unmount or when `enabled` becomes false.
- Use `useRef` for the interval ID to avoid stale closure issues.

### 3. Update CardTile to use the polling hook

File: `frontend/src/components/CardTile.tsx`

Replace the current `queued` state + `setTimeout` with the polling hook:

```typescript
const {
  status: requestStatus,
  isPolling,
  resultPrice,
} = usePriceRequestPolling({
  cardId: card.id,
  enabled: queued,
  onCompleted: (price) => {
    setQueued(false);
    // Optionally update the displayed price locally or trigger a refetch
    if (price !== null && onPriceRefreshed) {
      onPriceRefreshed(card.id, price);
    }
  },
  onFailed: () => {
    setQueued(false);
  },
});
```

Visual states:
- **Not queued**: show refresh icon on hover (current behavior)
- **Pending/Processing (isPolling=true)**: show animated spinner icon
  (replacing the static clock). Use CSS `animate-spin` on the SVG.
- **Completed**: briefly show a green checkmark (1.5s) then revert to
  default. Update the displayed price if `onPriceRefreshed` is provided.
- **Failed**: briefly show a red X (3s) then revert to default.
- **Timeout (polling stopped, still pending)**: show yellow clock icon
  with tooltip "Processing may take a while. Check back later."

### 4. Wire up onPriceRefreshed callback

The `CardTileProps` already has `onPriceRefreshed?: (cardId, newPrice) => void`
but it is not used in the current `CardTile` export (the prop is destructured
but unused in the component signature on line 27). Wire it up so that when
polling returns a completed status with a price, the parent component can
update its local card data without a full page refresh.

### 5. Handle the "none" status edge case

If the status endpoint returns `"none"` (no request found for this card),
stop polling immediately. This can happen if the request was already cleaned
up or if there is a user_id mismatch.

## Testing

### Frontend unit tests

File: `frontend/src/hooks/__tests__/usePriceRequestPolling.test.ts`

- **Polls on enable**: when `enabled=true`, starts calling
  `fetchPriceRequestStatus` every 5s.
- **Stops on completed**: when status returns `"completed"`, stops polling
  and calls `onCompleted` with the price.
- **Stops on failed**: when status returns `"failed"`, stops polling
  and calls `onFailed`.
- **Stops on timeout**: after 60s (use fake timers), stops polling even
  if status is still `"pending"`.
- **Stops on none**: if status is `"none"`, stops immediately.
- **Cleanup on unmount**: clears interval when component unmounts.
- **Does not poll when disabled**: when `enabled=false`, no API calls.

File: `frontend/src/components/__tests__/CardTile.test.tsx` (extend existing)

- **Shows spinner while polling**: when `queued=true` and polling is active,
  the refresh button shows an animated spinner (not a static clock).
- **Shows checkmark on completion**: when polling returns completed, shows
  green checkmark briefly.
- **Shows error on failure**: when polling returns failed, shows red X.
- **Calls onPriceRefreshed**: when polling completes with a price, the
  callback is invoked with `(cardId, price)`.

### Backend
- No backend changes needed. The status endpoint already exists and is tested.

## Acceptance Criteria

- [ ] `fetchPriceRequestStatus` function added to `frontend/src/api/cards.ts`
- [ ] `usePriceRequestPolling` hook created with start/stop/timeout logic
- [ ] CardTile uses polling hook instead of static 5s setTimeout
- [ ] Animated spinner shown while polling (pending/processing)
- [ ] Green checkmark flash on completion, red X on failure
- [ ] `onPriceRefreshed` callback invoked with result price on completion
- [ ] Polling stops after 60s max duration
- [ ] Hook unit tests cover all states (enabled, completed, failed, timeout, none, unmount)
- [ ] CardTile integration tests verify visual states
