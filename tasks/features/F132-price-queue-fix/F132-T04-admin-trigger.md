# F132-T04: Admin Trigger for Price Request Processing

**Wave:** 0
**Status:** pending
**Depends on:** none

## User Story

As an admin, I want a button in the Admin Panel's Price Requests section
to manually trigger processing of pending price requests, so that I can
process the queue on-demand without waiting for the daily batch job or
running the CLI manually.

## Important Constraint

Liga Magic requires Playwright running from a residential IP. The Render
server (production) cannot process price requests because Liga blocks
datacenter IPs. Processing must happen on the user's local machine via
the CLI command.

Therefore, the admin trigger endpoint should NOT attempt to process
requests inline. Instead, it should follow the pattern of
`POST /admin/jobs/liga-scan` which spawns a background thread. However,
since the Render server lacks Liga access, this endpoint will only work
when the API is running locally (where Playwright + residential IP are
available).

The admin UI should make this clear with a tooltip/note.

## Dev Notes

### 1. Backend: Add POST /admin/process-price-requests endpoint

File: `src/api/routers/admin.py`

Follow the existing pattern from `POST /admin/jobs/liga-scan` (lines 315-360):

```python
@router.post("/jobs/process-price-requests")
def trigger_process_price_requests(
    request: Request,
    admin: User = Depends(require_admin),
    repo: Repository = Depends(get_db),
    audit: AuditService = Depends(get_audit_service),
    limit: int = Query(100, ge=1, le=1000),
    delay: float = Query(2.0, ge=0.5, le=10.0),
):
    """Trigger processing of pending price requests (admin only).

    Spawns a background thread that runs the same logic as the
    `process-price-requests` CLI command. Only works when the server
    has access to LigaMagic (residential IP + Playwright).
    """
    # Check if there are any pending requests first
    counts = repo.count_price_requests_by_status()
    pending_count = counts.get("pending", 0)
    if pending_count == 0:
        return success_response(
            data={"status": "no_pending", "message": "No pending requests"}
        )

    scan_id = repo.create_scan_run(
        "process_price_requests",
        json.dumps({
            "triggered_by": admin.id,
            "limit": limit,
            "pending_count": pending_count,
        }),
    )

    def _run():
        # Reuse the same async logic from the CLI command
        asyncio.run(_process_requests(db_url, limit, delay))

    thread = threading.Thread(target=_run, daemon=True)
    thread.start()

    audit.log(
        actor=admin,
        action="job_trigger",
        target_type="scan",
        target_id=str(scan_id),
        details={
            "job_type": "process_price_requests",
            "limit": limit,
            "pending_count": pending_count,
        },
        ip_address=request.client.host if request.client else None,
    )

    return success_response(
        data={
            "scan_id": scan_id,
            "status": "started",
            "pending_count": pending_count,
        }
    )
```

The `_process_requests` helper should be extracted from (or import from)
the CLI's `process_price_requests` command logic. Consider extracting the
core async processing logic from `src/cli/main.py` (lines 1210-1281) into
a reusable function in `src/collectors/price_request_processor.py` that
both the CLI and the API endpoint can call. This avoids code duplication.

### 2. Extract processing logic into reusable module

Create: `src/collectors/price_request_processor.py`

Move the async `_process_all()` function from `src/cli/main.py` into this
module as a standalone async function:

```python
async def process_pending_price_requests(
    db_url: str,
    limit: int = 50,
    delay: float = 2.0,
) -> tuple[int, int]:
    """Process pending price update requests. Returns (completed, failed)."""
    ...
```

Then update both:
- `src/cli/main.py` `process-price-requests` command to call this function
- `src/api/routers/admin.py` new endpoint to call this function in a thread

### 3. Frontend: Add trigger button to AdminPriceRequestsSection

File: `frontend/src/components/admin/AdminPriceRequestsSection.tsx`

Add a "Process Queue" button above the stats bar:

```tsx
<button
  onClick={handleProcessQueue}
  disabled={processing || (stats?.pending ?? 0) === 0}
  className="px-4 py-2 text-sm bg-cyan-700 hover:bg-cyan-600
    disabled:bg-slate-600 disabled:cursor-not-allowed text-white rounded-lg
    flex items-center gap-2"
  data-testid="process-queue-btn"
  title="Requires local server with Liga access"
>
  {processing ? (
    <>
      <SpinnerIcon /> Processing...
    </>
  ) : (
    <>
      <PlayIcon /> Process Queue ({stats?.pending ?? 0} pending)
    </>
  )}
</button>
```

After clicking:
- Call `POST /api/v1/admin/jobs/process-price-requests`
- Show "Processing started" feedback
- Refresh the stats and request list after a short delay (5s)
- Show a note: "Processing runs in background. Refresh to see updates."

### 4. Frontend: Add API function

File: `frontend/src/api/admin.ts`

```typescript
export interface ProcessQueueResult {
  scan_id: number;
  status: string;
  pending_count: number;
}

export function triggerProcessPriceRequests(
  limit?: number,
): Promise<ApiResponse<ProcessQueueResult>> {
  return apiPost<ProcessQueueResult>(
    "/api/v1/admin/jobs/process-price-requests",
    {},
    { timeoutMs: 15_000 },
  );
}
```

Note: Use `apiPost` with an empty body (or pass limit as query param).
The endpoint uses Query params, not body params, so this may need to be
an `apiPost` to the URL with query string, or the endpoint could accept
both. Simplest: use `apiGet` with POST override, or change the endpoint
to accept a JSON body. Follow the existing pattern from `trigger_liga_scan`
which uses Query params -- the frontend should append `?limit=100` to the URL.

Actually, looking at the existing `trigger_liga_scan` endpoint, the frontend
`AdminOperationsSection` likely uses `apiPost` with query params in the URL.
Check the existing pattern and follow it.

## Testing

### Backend

File: `tests/api/test_admin_process_price_requests.py`

- **Trigger returns started**: POST to endpoint with pending requests
  returns `{"status": "started", "pending_count": N}`.
- **No pending returns no_pending**: POST with empty queue returns
  `{"status": "no_pending"}`.
- **Non-admin rejected**: non-admin user gets 403.
- **Audit log created**: verify audit entry after trigger.

File: `tests/collectors/test_price_request_processor.py`

- **Processes pending requests**: mock LigaMagicProvider, verify completed
  count matches pending count.
- **Handles failures**: mock provider to raise LigaError, verify failed
  count and error_message stored.
- **Respects limit**: pass limit=2 with 5 pending, verify only 2 processed.
- **Skips cards without names**: request for card with no name_en/name_pt
  is marked failed with "Card has no name" error.

### Frontend

File: `frontend/src/components/admin/__tests__/AdminPriceRequestsSection.test.tsx`

- **Process button shown**: button renders with pending count.
- **Button disabled when no pending**: when stats.pending=0, button is
  disabled.
- **Click triggers API call**: clicking button calls
  `triggerProcessPriceRequests`.
- **Shows processing state**: after click, button shows spinner and
  "Processing..." text.
- **Refreshes stats after trigger**: after successful trigger, stats and
  request list are reloaded.

## Acceptance Criteria

- [ ] `POST /api/v1/admin/jobs/process-price-requests` endpoint created
- [ ] Processing logic extracted to reusable `src/collectors/price_request_processor.py`
- [ ] CLI `process-price-requests` refactored to use the extracted module
- [ ] Admin UI has "Process Queue" button with pending count
- [ ] Button disabled when no pending requests
- [ ] Processing runs in background thread (non-blocking)
- [ ] Audit log entry created on trigger
- [ ] 4+ backend tests, 5+ frontend tests
