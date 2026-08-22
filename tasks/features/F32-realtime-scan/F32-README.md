# F32 -- Real-time Scan Progress (Varredura em Tempo Real)

**Status:** planned
**Created:** 2026-08-21

## Summary

Replace the 3-second polling loop with Server-Sent Events (SSE) so that scan
progress streams to the browser in real time. Each card scanned produces an
event with its name, price result, and running totals. The collection grid
fills in as data arrives instead of waiting for a full re-fetch at the end.

## User Story

As a collector, I want to see each card being scanned in real time -- its name,
whether a price was found, and the running progress -- so I know exactly what is
happening during a bulk refresh instead of watching a static progress bar jump
every 3 seconds.

## Architecture

### Backend

1. **Event bus** -- a lightweight in-memory pub/sub (`asyncio.Queue` per scan)
   stored in a module-level dict keyed by `scan_id`. The scan orchestrator
   publishes `ScanEvent` dataclasses; SSE consumers read from the queue.

2. **SSE endpoint** -- `GET /api/v1/scans/{scan_id}/stream` returns
   `text/event-stream`. It reads from the scan's event queue and yields
   JSON-encoded events. The endpoint is auth-protected (same as existing
   scan endpoints). FastAPI's `StreamingResponse` handles the chunked
   transfer. When the scan finishes, the endpoint sends a `done` event and
   closes.

3. **Scan orchestrator changes** -- after each card is processed (success or
   failure), `run_scan` publishes a `ScanEvent` to the event bus with:
   `card_name`, `external_id`, `price_found` (bool), `price` (Decimal|None),
   `cards_processed`, `cards_total`, `cards_failed`, `observations_saved`.
   A final `scan_complete` event carries the summary. The existing
   `update_scan_run` DB writes remain unchanged (backwards compatible).

4. **Backwards compatibility** -- the polling endpoint `GET /scans/{scan_id}`
   continues to work. The SSE endpoint is additive. Clients that do not
   support SSE (or arrive after the scan started) can still poll.

### Frontend

1. **useScanStream hook** -- wraps `EventSource` with reconnect, auth token
   injection (via query param or custom header depending on SSE limitations),
   automatic fallback to polling if SSE connection fails. Returns a stream of
   `ScanEvent` objects plus aggregate `progress`.

2. **useCollectionRefresh v2** -- refactored to use `useScanStream` instead
   of `setInterval` polling. The public API (`isRefreshing`, `progress`,
   `startRefresh`, `cancelRefresh`) stays identical so consuming components
   need zero changes.

3. **Live card updates** -- as `card_scanned` events arrive, update the
   matching card in the collection grid with its new price (optimistic local
   state update). Cards that just got scanned get a brief highlight animation
   (green border flash for price found, dim for no price).

4. **Enhanced progress bar** -- show card name currently being scanned,
   running price-found ratio, estimated time remaining (based on average
   card processing time).

## Constraints

- SSE chosen over WebSocket: simpler, unidirectional (server to client), no
  extra dependencies, works through most proxies. WebSocket is overkill for
  this use case.
- Auth for SSE: `EventSource` API does not support custom headers. Options:
  (a) pass JWT as query param `?token=...`, (b) use cookie-based auth. We
  will use query param approach with short-lived token. The SSE endpoint
  validates the token the same way as other auth endpoints.
- Event bus is in-memory (not Redis/etc). Suitable for single-process
  deployment. If the server restarts mid-scan, the scan thread dies anyway.
- Queue cleanup: event bus entry is removed when the SSE endpoint closes or
  after a 5-minute TTL (whichever comes first).
- No new pip dependencies required. `asyncio.Queue` and
  `starlette.responses.StreamingResponse` are already available.

## Acceptance Criteria

- [ ] `GET /api/v1/scans/{scan_id}/stream` returns `text/event-stream`
- [ ] Each processed card produces a JSON SSE event within 1 second
- [ ] Progress bar updates per-card (not every 3 seconds)
- [ ] Card name of the currently-scanned card is visible during scan
- [ ] Collection grid updates card prices as scan events arrive
- [ ] Scanned cards get a brief visual highlight (green flash)
- [ ] Fallback to polling if SSE connection fails
- [ ] Existing polling endpoint still works (backwards compatible)
- [ ] Auth required for SSE stream (401 without valid token)
- [ ] Backend tests for event bus, SSE endpoint, scan orchestrator events
- [ ] Frontend tests for useScanStream hook, progress UI, card highlights

## Tasks

| Task | File | Wave | Description |
|------|------|------|-------------|
| T01 | F32-T01.md | 0 | Backend: ScanEvent domain model + in-memory event bus |
| T02 | F32-T02.md | 1 | Backend: scan orchestrator -- publish events to event bus |
| T03 | F32-T03.md | 1 | Backend: SSE endpoint `GET /scans/{scan_id}/stream` |
| T04 | F32-T04.md | 2 | Frontend: useScanStream hook (EventSource + fallback) |
| T05 | F32-T05.md | 2 | Frontend: useCollectionRefresh v2 (swap polling for SSE) |
| T06 | F32-T06.md | 3 | Frontend: live card updates + highlight animation |
| T07 | F32-T07.md | 3 | Frontend: enhanced progress bar (card name, ETA, ratio) |
| T08 | F32-T08.md | 4 | i18n keys + integration tests + diagrams |

## Waves

- **Wave 0** (1 task): T01 -- domain model + event bus (no side effects)
- **Wave 1** (2 tasks, parallel): T02 (orchestrator events), T03 (SSE endpoint)
- **Wave 2** (2 tasks, parallel): T04 (useScanStream hook), T05 (refactor useCollectionRefresh)
- **Wave 3** (2 tasks, parallel): T06 (live card updates), T07 (enhanced progress bar)
- **Wave 4** (1 task): T08 (i18n, integration tests, diagrams, README update)

## File Impacts

### Backend (new files)
- `src/events/scan_bus.py` -- event bus module
- `src/domain/events.py` -- ScanEvent dataclass (or add to models.py)

### Backend (modified files)
- `src/collectors/scan.py` -- publish events after each card
- `src/api/routers/scans.py` -- add SSE stream endpoint
- `src/api/app.py` -- no changes needed (router already included)

### Frontend (new files)
- `frontend/src/hooks/useScanStream.ts` -- EventSource wrapper hook

### Frontend (modified files)
- `frontend/src/hooks/useCollectionRefresh.ts` -- swap polling for SSE
- `frontend/src/pages/MyCollection.tsx` -- live card updates, highlight
- `frontend/src/i18n/locales/en.json` -- new keys
- `frontend/src/i18n/locales/pt-BR.json` -- new keys

## Diagrams

- `docs/diagrams/F32-architecture.mmd`
- `docs/diagrams/F32-journey.mmd`
