"""Scan runs router — trigger, list, inspect, and stream collection price scans."""

from __future__ import annotations

import asyncio
import os
import threading
from collections.abc import AsyncGenerator
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Request
from jose import JWTError
from starlette.responses import StreamingResponse

from src.api.deps import require_auth_or_api_key
from src.api.schemas.scans import (
    ScanListResponse,
    ScanRequest,
    ScanRunResponse,
    ScanTriggerResponse,
)
from src.auth.jwt import decode_token
from src.config import get_db_url
from src.database.repository import Repository
from src.domain.models import ScanFilter, ScanType
from src.events import scan_bus

router = APIRouter(prefix="/scans", tags=["scans"])

_KEEPALIVE_TIMEOUT = 30  # seconds


def _get_db_url() -> str:
    return get_db_url()


def _dt_to_str(val: object) -> str | None:
    """Convert a datetime to ISO string, pass through strings, return None for None."""
    if val is None:
        return None
    if isinstance(val, str):
        return val
    if isinstance(val, datetime):
        return val.isoformat()
    return str(val)


def _row_to_response(row: dict) -> ScanRunResponse:
    """Convert a repository scan-run dict to a ScanRunResponse."""
    return ScanRunResponse(
        id=row["id"],
        scan_type=row["scan_type"],
        filters_json=row["filters_json"],
        status=row["status"],
        cards_total=row["cards_total"],
        cards_processed=row["cards_processed"],
        cards_failed=row["cards_failed"],
        observations_saved=row["observations_saved"],
        error_summary=row.get("error_summary"),
        started_at=_dt_to_str(row.get("started_at")),
        finished_at=_dt_to_str(row.get("finished_at")),
        created_at=_dt_to_str(row.get("created_at")) or "",
    )


def _validate_stream_auth(
    token: str | None,
    api_key: str | None,
    request: Request,
) -> str:
    """Validate SSE stream authentication via query-param token or API key.

    Returns user_id string on success; raises HTTPException(401) on failure.
    """
    # Try JWT token
    if token:
        try:
            payload = decode_token(token)
            user_id = payload.get("sub")
            if user_id:
                db_url = _get_db_url()
                repo = Repository(db_url)
                user_row = repo.get_user_by_id(int(user_id))
                if user_row and user_row.is_active:
                    return str(user_row.id)
        except JWTError:
            pass

    # Try API key
    expected = os.environ.get("TCG_API_KEY")
    if expected is not None and api_key == expected:
        return "api_key_user"

    # Dev mode: no TCG_API_KEY and no token → allow
    if expected is None and not token:
        return "api_key_user"

    raise HTTPException(status_code=401, detail="Authentication required")


@router.post("", response_model=ScanTriggerResponse)
async def trigger_scan(
    request: ScanRequest,
    _user_id: str = Depends(require_auth_or_api_key),
):
    """Trigger a new collection price scan in a background thread."""
    from src.collectors.scan import run_scan

    db_url = _get_db_url()

    scan_filter = ScanFilter(
        scan_type=ScanType(request.scan_type),
        set_codes=request.set_codes,
        format_name=request.format_name,
        rarities=request.rarities,
        card_ids=request.card_ids,
        limit=request.limit,
    )

    # Create scan run immediately so we can return the ID
    repo = Repository(db_url)
    scan_id = repo.create_scan_run(scan_filter.scan_type.value, scan_filter.to_json())

    # Launch in background thread (scan uses its own event loop)
    def _run() -> None:
        from src.services.scan_hooks import default_registry

        asyncio.run(
            run_scan(
                db_url=db_url,
                scan_filter=scan_filter,
                dry_run=request.dry_run,
                run_id=scan_id,
                on_complete=default_registry.notify,
            )
        )

    thread = threading.Thread(target=_run, daemon=True)
    thread.start()

    return ScanTriggerResponse(scan_id=scan_id, status="pending")


@router.get("", response_model=ScanListResponse)
async def list_scans(
    limit: int = 20,
    offset: int = 0,
    scan_type: str | None = None,
    status: str | None = None,
):
    """List scan runs with optional filters."""
    repo = Repository(_get_db_url())
    runs = repo.list_scan_runs(limit=limit, offset=offset, scan_type=scan_type, status=status)
    return ScanListResponse(
        scans=[_row_to_response(r) for r in runs],
        total=len(runs),
    )


@router.get("/{scan_id}/stream")
async def stream_scan(
    scan_id: int,
    request: Request,
    token: str | None = None,
    api_key: str | None = None,
):
    """Stream scan progress via Server-Sent Events (SSE).

    Auth is provided via ``?token=<jwt>`` or ``?api_key=<key>`` query params
    because EventSource does not support custom headers.
    """
    _validate_stream_auth(token, api_key, request)

    repo = Repository(_get_db_url())
    run = repo.get_scan_run(scan_id)
    if not run:
        raise HTTPException(status_code=404, detail="Scan run not found")

    # If the scan is already finished, return a single final event and close
    if run["status"] in ("completed", "failed"):
        from src.domain.events import ScanEvent

        final_event = ScanEvent(
            event_type="scan_complete",
            scan_id=scan_id,
            timestamp=_dt_to_str(run.get("finished_at")) or datetime.now().isoformat(),
            cards_processed=run["cards_processed"],
            cards_total=run["cards_total"],
            cards_failed=run["cards_failed"],
            observations_saved=run["observations_saved"],
            error=run.get("error_summary"),
        )

        async def _final_generator() -> AsyncGenerator[str, None]:
            yield f"event: scan_complete\ndata: {final_event.to_sse_json()}\n\n"

        return StreamingResponse(
            _final_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )

    # Subscribe to live events
    queue = scan_bus.subscribe(scan_id)

    async def _event_generator() -> AsyncGenerator[str, None]:
        try:
            while True:
                # Check if client disconnected
                if await request.is_disconnected():
                    break

                try:
                    event = await asyncio.wait_for(queue.get(), timeout=_KEEPALIVE_TIMEOUT)
                    yield f"event: {event.event_type}\ndata: {event.to_sse_json()}\n\n"
                    if event.event_type == "scan_complete":
                        break
                except asyncio.TimeoutError:
                    # Send keepalive comment to prevent proxy timeouts
                    yield ": keepalive\n\n"
        finally:
            scan_bus.unsubscribe(scan_id, queue)

    return StreamingResponse(
        _event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/{scan_id}", response_model=ScanRunResponse)
async def get_scan(scan_id: int):
    """Get details of a specific scan run."""
    repo = Repository(_get_db_url())
    run = repo.get_scan_run(scan_id)
    if not run:
        raise HTTPException(status_code=404, detail="Scan run not found")
    return _row_to_response(run)
