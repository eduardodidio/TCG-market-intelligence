from __future__ import annotations

import asyncio

from fastapi import APIRouter, Depends

from src.api.deps import get_db
from src.api.jobs import job_tracker
from src.api.schemas.collect import (
    BackfillRequest,
    JobStatus,
    UpdateRequest,
)
from src.api.schemas.envelope import ApiResponse, success_response
from src.database.repository import Repository

router = APIRouter(prefix="/collect", tags=["collection"])


@router.post("/backfill", response_model=ApiResponse[JobStatus])
async def trigger_backfill(
    request: BackfillRequest,
    repo: Repository = Depends(get_db),
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
