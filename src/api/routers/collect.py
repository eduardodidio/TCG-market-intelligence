from __future__ import annotations

import asyncio

from fastapi import APIRouter, Depends

from src.api.deps import get_db, verify_api_key
from src.api.jobs import job_tracker
from src.api.schemas.collect import (
    BackfillRequest,
    CollectionHealth,
    JobStatus,
    UpdateRequest,
)
from src.api.schemas.envelope import ApiResponse, success_response
from src.database.repository import Repository

router = APIRouter(prefix="/collect", tags=["collection"])


@router.get("/health", response_model=ApiResponse[CollectionHealth])
async def collection_health(
    repo: Repository = Depends(get_db),
) -> ApiResponse[CollectionHealth]:
    """Return collection pipeline health status."""
    from datetime import datetime, timedelta

    last_date = repo.get_latest_observation_date()
    total_cards = repo.get_source_card_count()
    stale_cards_count = repo.get_stale_cards_count()
    recent_errors_count = repo.get_recent_errors_count()

    last_collection_at: str | None = None
    next_expected_at: str | None = None
    if last_date is not None:
        last_collection_at = last_date.isoformat()
        next_dt = datetime.combine(last_date, datetime.min.time()) + timedelta(hours=24)
        next_expected_at = next_dt.date().isoformat()

    # Determine status
    if recent_errors_count > 0:
        status = "error"
    elif total_cards > 0 and stale_cards_count > total_cards * 0.5:
        status = "stale"
    elif last_collection_at is None:
        status = "stale"
    else:
        status = "healthy"

    data = CollectionHealth(
        last_collection_at=last_collection_at,
        next_expected_at=next_expected_at,
        total_cards=total_cards,
        stale_cards_count=stale_cards_count,
        recent_errors_count=recent_errors_count,
        status=status,
    )
    return success_response(data=data)


@router.post("/backfill", response_model=ApiResponse[JobStatus])
async def trigger_backfill(
    request: BackfillRequest,
    repo: Repository = Depends(get_db),
    _auth: None = Depends(verify_api_key),
) -> ApiResponse[JobStatus]:
    job_id = job_tracker.start(
        "backfill",
        {
            "set": request.set,
            "limit": request.limit,
            "history_days": request.history_days,
        },
    )

    asyncio.create_task(_run_backfill_job(job_id, request.set, request.limit, request.history_days))

    data = JobStatus(
        job_id=job_id,
        status="started",
        message=f"Backfill started for set {request.set}",
    )
    return success_response(data=data)


@router.post("/update", response_model=ApiResponse[JobStatus])
async def trigger_update(
    request: UpdateRequest,
    repo: Repository = Depends(get_db),
    _auth: None = Depends(verify_api_key),
) -> ApiResponse[JobStatus]:
    job_id = job_tracker.start("update", {"set": request.set})

    asyncio.create_task(_run_update_job(job_id))

    suffix = f" for set {request.set}" if request.set else " for all sets"
    data = JobStatus(
        job_id=job_id,
        status="started",
        message=f"Update started{suffix}",
    )
    return success_response(data=data)


async def _run_backfill_job(
    job_id: str,
    set_filter: str,
    limit: int | None,
    history_days: int,
) -> None:
    try:
        from src.collectors.backfill import run_backfill

        summary = await run_backfill(
            set_filter=set_filter,
            limit=limit,
            history_days=history_days,
        )
        job_tracker.complete(
            job_id,
            f"Processed {summary.cards_processed} cards, "
            f"{summary.observations_saved} observations",
        )
    except Exception as e:
        job_tracker.fail(job_id, str(e))


async def _run_update_job(job_id: str) -> None:
    try:
        from src.collectors.backfill import run_update

        summary = await run_update()
        job_tracker.complete(
            job_id,
            f"Updated {summary.cards_processed} cards, "
            f"{summary.observations_saved} observations",
        )
    except Exception as e:
        job_tracker.fail(job_id, str(e))
