"""Scan runs router — trigger, list, inspect, and stream collection price scans."""

from __future__ import annotations

import asyncio
import os
import threading
from collections.abc import AsyncGenerator
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from jose import JWTError
from starlette.responses import StreamingResponse

from src.api.deps import get_credit_service, get_current_user, require_auth_or_api_key
from src.api.schemas.scans import (
    ScanListResponse,
    ScanPreviewResponse,
    ScanRequest,
    ScanRunResponse,
    ScanTriggerResponse,
)
from src.auth.jwt import decode_token
from src.config import get_db_url
from src.credits.constants import CARD_REFRESH_COST
from src.credits.service import CreditService
from src.database.repository import Repository
from src.domain.models import ScanFilter, ScanType, User
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


def _extract_provider(filters_json: str) -> str | None:
    """Extract provider from filters_json if present."""
    import json as _json

    try:
        data = _json.loads(filters_json)
        return data.get("provider")
    except (ValueError, TypeError):
        return None


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
        provider=_extract_provider(row["filters_json"]),
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


@router.get("/preview", response_model=ScanPreviewResponse)
async def preview_scan(
    max_age_days: int | None = Query(None, ge=1),
    user: User = Depends(get_current_user),
    credit_svc: CreditService = Depends(get_credit_service),
):
    """Preview how many cards a bulk scan would process and the credit cost."""
    repo = Repository(_get_db_url())
    scan_filter = ScanFilter()
    user_id_str = str(user.id)
    all_entries = repo.get_cards_for_liga_scan(scan_filter, user_id=user_id_str, max_age_days=None)
    eligible = repo.get_cards_for_liga_scan(
        scan_filter, user_id=user_id_str, max_age_days=max_age_days
    )
    card_count = len(eligible)
    skipped = len(all_entries) - card_count
    cost = 0 if user.is_admin else card_count * CARD_REFRESH_COST
    return ScanPreviewResponse(
        card_count=card_count,
        skipped_count=skipped,
        credit_cost=cost,
    )


@router.post("", response_model=ScanTriggerResponse)
async def trigger_scan(
    request: ScanRequest,
    _user_id: str = Depends(require_auth_or_api_key),
    user: User = Depends(get_current_user),
    credit_svc: CreditService = Depends(get_credit_service),
):
    """Trigger a new collection price scan in a background thread."""
    from src.collectors.liga_scan import run_liga_scan
    from src.collectors.scan import run_scan

    db_url = _get_db_url()
    provider_name = request.provider if request.provider in ("liga", "myp") else "liga"

    scan_filter = ScanFilter(
        scan_type=ScanType(request.scan_type),
        set_codes=request.set_codes,
        format_name=request.format_name,
        rarities=request.rarities,
        card_ids=request.card_ids,
        limit=request.limit,
    )

    # Per-card credit guard — admin bypass; deduct BEFORE launch (async task)
    if not user.is_admin:
        repo_for_count = Repository(db_url)
        eligible = repo_for_count.get_cards_for_liga_scan(
            scan_filter, user_id=str(user.id), max_age_days=request.max_age_days
        )
        cost = len(eligible) * CARD_REFRESH_COST
        if not credit_svc.check_sufficient(user.id, cost):
            balance = credit_svc.get_balance(user.id)
            raise HTTPException(
                status_code=402,
                detail={
                    "code": "INSUFFICIENT_CREDITS",
                    "balance": balance.balance,
                    "cost": cost,
                    "message": "Not enough treasure tokens.",
                },
            )
        credit_svc.deduct(user.id, cost, "bulk_scan", reference_id="scan")

    # Encode provider and max_age_days in filters_json for traceability
    import json as _json

    filters_data = _json.loads(scan_filter.to_json())
    filters_data["provider"] = provider_name
    if request.max_age_days is not None:
        filters_data["max_age_days"] = request.max_age_days
    filters_json = _json.dumps(filters_data)

    # Create scan run immediately so we can return the ID
    repo = Repository(db_url)
    scan_id = repo.create_scan_run(scan_filter.scan_type.value, filters_json)

    # Launch in background thread (scan uses its own event loop)
    def _run() -> None:
        from src.services.scan_hooks import default_registry

        if provider_name == "liga":
            asyncio.run(
                run_liga_scan(
                    db_url=db_url,
                    scan_filter=scan_filter,
                    dry_run=request.dry_run,
                    run_id=scan_id,
                    on_complete=default_registry.notify,
                    max_age_days=request.max_age_days,
                )
            )
        else:
            asyncio.run(
                run_scan(
                    db_url=db_url,
                    scan_filter=scan_filter,
                    dry_run=request.dry_run,
                    run_id=scan_id,
                    on_complete=default_registry.notify,
                    provider_name=provider_name,
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
