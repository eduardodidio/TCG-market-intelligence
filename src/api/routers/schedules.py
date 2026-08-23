"""Schedules router -- CRUD + manual trigger for scheduled scans (F37)."""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Request

from src.api.deps import get_current_user_id
from src.api.schemas.schedules import (
    ScheduleCreateRequest,
    ScheduleListResponse,
    ScheduleResponse,
    ScheduleTriggerResponse,
    ScheduleUpdateRequest,
)
from src.config import get_db_url
from src.database.repository import Repository
from src.scheduler.service import validate_cron

router = APIRouter(prefix="/schedules", tags=["schedules"])

MAX_SCHEDULES_PER_USER = 10


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


def _row_to_response(row: dict) -> ScheduleResponse:
    """Convert a repository schedule dict to a ScheduleResponse."""
    return ScheduleResponse(
        id=row["id"],
        name=row["name"],
        description=row.get("description"),
        cron_expression=row["cron_expression"],
        scan_type=row["scan_type"],
        filters_json=row["filters_json"],
        status=row["status"],
        last_run_id=row.get("last_run_id"),
        last_run_at=_dt_to_str(row.get("last_run_at")),
        next_run_at=_dt_to_str(row.get("next_run_at")),
        error_count=row.get("error_count", 0),
        max_retries=row.get("max_retries", 3),
        created_at=_dt_to_str(row.get("created_at")) or "",
        updated_at=_dt_to_str(row.get("updated_at")) or "",
    )


def _get_scheduler(request: Request):
    """Get the ScanScheduler instance from app state, if available."""
    return getattr(request.app.state, "scheduler", None)


@router.post("", response_model=ScheduleResponse, status_code=201)
async def create_schedule(
    body: ScheduleCreateRequest,
    request: Request,
    user_id: str = Depends(get_current_user_id),
):
    """Create a new scheduled scan."""
    try:
        validate_cron(body.cron_expression)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))

    repo = Repository(_get_db_url())

    # Enforce per-user limit
    count = repo.count_scheduled_scans(user_id)
    if count >= MAX_SCHEDULES_PER_USER:
        raise HTTPException(
            status_code=400,
            detail=f"Maximum {MAX_SCHEDULES_PER_USER} schedules per user",
        )

    schedule_id = repo.create_scheduled_scan(
        user_id=user_id,
        name=body.name,
        cron_expression=body.cron_expression,
        scan_type=body.scan_type,
        filters_json=body.filters_json,
        description=body.description,
        max_retries=body.max_retries,
    )

    # Register with APScheduler if available
    scheduler = _get_scheduler(request)
    if scheduler:
        try:
            scheduler.add_schedule(schedule_id)
        except Exception:
            pass  # best-effort; schedule will be picked up on restart

    row = repo.get_scheduled_scan(schedule_id)
    return _row_to_response(row)


@router.get("", response_model=ScheduleListResponse)
async def list_schedules(
    status: str | None = None,
    limit: int = 50,
    offset: int = 0,
    user_id: str = Depends(get_current_user_id),
):
    """List schedules for the authenticated user."""
    repo = Repository(_get_db_url())
    schedules = repo.list_scheduled_scans(
        user_id=user_id, status=status, limit=limit, offset=offset
    )
    total = repo.count_scheduled_scans(user_id, status=status)
    return ScheduleListResponse(
        schedules=[_row_to_response(s) for s in schedules],
        total=total,
    )


@router.get("/{schedule_id}", response_model=ScheduleResponse)
async def get_schedule(
    schedule_id: int,
    user_id: str = Depends(get_current_user_id),
):
    """Get details of a specific schedule."""
    repo = Repository(_get_db_url())
    row = repo.get_scheduled_scan(schedule_id)
    if row is None or row["user_id"] != user_id:
        raise HTTPException(status_code=404, detail="Schedule not found")
    return _row_to_response(row)


@router.patch("/{schedule_id}", response_model=ScheduleResponse)
async def update_schedule(
    schedule_id: int,
    body: ScheduleUpdateRequest,
    request: Request,
    user_id: str = Depends(get_current_user_id),
):
    """Update schedule fields. Re-syncs APScheduler job if cron or status changes."""
    repo = Repository(_get_db_url())
    existing = repo.get_scheduled_scan(schedule_id)
    if existing is None or existing["user_id"] != user_id:
        raise HTTPException(status_code=404, detail="Schedule not found")

    updates = body.model_dump(exclude_none=True)
    if not updates:
        return _row_to_response(existing)

    # Validate new cron expression
    if "cron_expression" in updates:
        try:
            validate_cron(updates["cron_expression"])
        except ValueError as e:
            raise HTTPException(status_code=422, detail=str(e))

    repo.update_scheduled_scan(schedule_id, **updates)

    # Re-sync APScheduler if needed
    scheduler = _get_scheduler(request)
    if scheduler:
        if "cron_expression" in updates:
            # Remove and re-add with new cron
            scheduler.remove_schedule(schedule_id)
            scheduler.add_schedule(schedule_id)
        elif "status" in updates:
            if updates["status"] == "paused":
                scheduler.pause_schedule(schedule_id)
            elif updates["status"] == "active":
                scheduler.resume_schedule(schedule_id)

    row = repo.get_scheduled_scan(schedule_id)
    return _row_to_response(row)


@router.delete("/{schedule_id}")
async def delete_schedule(
    schedule_id: int,
    request: Request,
    user_id: str = Depends(get_current_user_id),
):
    """Delete a schedule and remove its APScheduler job."""
    repo = Repository(_get_db_url())
    existing = repo.get_scheduled_scan(schedule_id)
    if existing is None or existing["user_id"] != user_id:
        raise HTTPException(status_code=404, detail="Schedule not found")

    # Remove from APScheduler
    scheduler = _get_scheduler(request)
    if scheduler:
        scheduler.remove_schedule(schedule_id)

    repo.delete_scheduled_scan(schedule_id)
    return {"status": "deleted"}


@router.post("/{schedule_id}/trigger", response_model=ScheduleTriggerResponse)
async def trigger_schedule(
    schedule_id: int,
    request: Request,
    user_id: str = Depends(get_current_user_id),
):
    """Manually trigger a schedule to run immediately."""
    repo = Repository(_get_db_url())
    existing = repo.get_scheduled_scan(schedule_id)
    if existing is None or existing["user_id"] != user_id:
        raise HTTPException(status_code=404, detail="Schedule not found")

    scheduler = _get_scheduler(request)
    if scheduler is None:
        raise HTTPException(status_code=503, detail="Scheduler not available")

    scan_id = scheduler.trigger_now(schedule_id)
    return ScheduleTriggerResponse(
        schedule_id=schedule_id,
        scan_id=scan_id,
        status="pending",
    )
