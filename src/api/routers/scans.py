"""Scan runs router — trigger, list, and inspect collection price scans."""

from __future__ import annotations

import asyncio
import os
import threading
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException

from src.api.deps import require_auth_or_api_key
from src.api.schemas.scans import (
    ScanListResponse,
    ScanRequest,
    ScanRunResponse,
    ScanTriggerResponse,
)
from src.database.repository import Repository
from src.domain.models import ScanFilter, ScanType

router = APIRouter(prefix="/scans", tags=["scans"])


def _get_db_url() -> str:
    return os.environ.get("TCG_DATABASE_URL", "sqlite:///tcg_market.db")


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
        asyncio.run(
            run_scan(
                db_url=db_url,
                scan_filter=scan_filter,
                dry_run=request.dry_run,
                run_id=scan_id,
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


@router.get("/{scan_id}", response_model=ScanRunResponse)
async def get_scan(scan_id: int):
    """Get details of a specific scan run."""
    repo = Repository(_get_db_url())
    run = repo.get_scan_run(scan_id)
    if not run:
        raise HTTPException(status_code=404, detail="Scan run not found")
    return _row_to_response(run)
