# F147-T02: Add PATCH endpoint for updating alert target_price

**Wave:** 0 (sequential — backend must exist before frontend inline edit)
**Estimate:** Small

## User Story

As a user with an existing price alert, I want to update its target price
without deleting and recreating it, so that I can adjust my thresholds
quickly.

## Problem

No PUT or PATCH endpoint exists for alerts. The only mutation endpoints
are POST (create) and DELETE. Users must delete and recreate an alert to
change the target price, losing the creation timestamp.

## Dev Notes

### Changes to `src/api/routers/alerts.py`

1. Add a new Pydantic schema:
   ```python
   class UpdateAlertRequest(BaseModel):
       target_price: float | None = Field(None, gt=0)
       direction: str | None = Field(None, pattern="^(below|above)$")
   ```

2. Add PATCH endpoint:
   ```python
   @router.patch("/{alert_id}", response_model=ApiResponse[AlertResponse])
   def update_alert(
       alert_id: int,
       request: UpdateAlertRequest,
       user: User = Depends(get_current_user),
       repo: Repository = Depends(get_db),
   ):
   ```

3. Logic:
   - Fetch alert by ID, verify it exists (404 if not).
   - Verify `alert.user_id == user.id` (403 if not).
   - Verify `alert.is_active == 1` — cannot edit triggered alerts (409).
   - Update only the fields provided (partial update pattern).
   - Commit and return updated alert with card_name joined.

### Changes to `frontend/src/api/alerts.ts`

1. Add `updateAlert` function:
   ```typescript
   export function updateAlert(
     alertId: number,
     body: { target_price?: number; direction?: string },
   ): Promise<ApiResponse<AlertResponse>> {
     return apiPatch<AlertResponse>(`/api/v1/alerts/${alertId}`, body);
   }
   ```

2. Verify `apiPatch` exists in `api/client.ts` (it does — used by
   `markAllNotificationsRead`).

### Changes to `frontend/src/types/alerts.ts`

1. Add:
   ```typescript
   export interface UpdateAlertRequest {
     target_price?: number;
     direction?: "below" | "above";
   }
   ```

## Testing

### Backend tests (`tests/api/test_alerts_router.py`)
- PATCH with valid target_price returns 200 + updated alert.
- PATCH with valid direction returns 200 + updated alert.
- PATCH on non-existent alert returns 404.
- PATCH on another user's alert returns 403.
- PATCH on triggered (inactive) alert returns 409.
- PATCH with invalid target_price (<=0) returns 422.
- PATCH with empty body returns 200 (no-op, returns unchanged alert).

### Frontend tests
- `updateAlert` calls correct endpoint with correct payload.

## Acceptance Criteria
- [ ] PATCH `/api/v1/alerts/{alert_id}` endpoint works
- [ ] Only owner can update their alerts
- [ ] Only active alerts can be updated
- [ ] Partial updates work (send only target_price or only direction)
- [ ] Frontend `updateAlert` API function exists
- [ ] Backend tests cover happy path and error cases
