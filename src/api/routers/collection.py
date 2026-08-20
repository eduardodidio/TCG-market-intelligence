from __future__ import annotations

import asyncio
import base64
import os

from fastapi import APIRouter, Depends, Query

from src.api.deps import get_db, verify_api_key
from src.api.jobs import job_tracker
from src.api.schemas.collect import JobStatus
from src.api.schemas.collection import (
    CollectionCard,
    CollectionSummary,
    ImportResult,
    SyncRequest,
)
from src.api.schemas.envelope import ApiResponse, paginated_response, success_response
from src.database.repository import Repository

router = APIRouter(prefix="/collection", tags=["collection"])

FAKE_USER_ID = "eduardo"


def _encode_cursor(row_id: int) -> str:
    return base64.urlsafe_b64encode(str(row_id).encode()).decode()


def _decode_cursor(cursor: str) -> int | None:
    try:
        return int(base64.urlsafe_b64decode(cursor).decode())
    except (ValueError, Exception):
        return None


def _scryfall_image_url(set_code: str, collector_number: str) -> str:
    return (
        f"https://api.scryfall.com/cards/{set_code.lower()}/{collector_number}"
        f"?format=image&version=normal"
    )


@router.get("", response_model=ApiResponse[list[CollectionCard]])
def list_collection(
    name: str | None = None,
    set: str | None = Query(None, alias="set"),
    cursor: str | None = None,
    limit: int = Query(default=50, ge=1, le=200),
    repo: Repository = Depends(get_db),
):
    after_id = _decode_cursor(cursor) if cursor else None
    rows = repo.list_collection(
        user_id=FAKE_USER_ID,
        name_search=name,
        set_code=set,
        after_id=after_id,
        limit=limit,
    )

    has_next = len(rows) > limit
    if has_next:
        rows = rows[:limit]

    # Batch-fetch latest prices for linked cards
    linked_card_ids = [r.card_id for r in rows if r.card_id is not None]
    latest_prices = repo.get_latest_prices_batch(linked_card_ids) if linked_card_ids else {}

    data = [
        CollectionCard(
            id=r.id,
            card_id=r.card_id,
            set_code=r.set_code,
            collector_number=r.collector_number,
            name_en=r.name_en,
            name_pt=r.name_pt,
            set_name_en=r.set_name_en,
            quantity=r.quantity,
            quality=r.quality,
            language=r.language,
            rarity=r.rarity,
            color=r.color,
            extras=r.extras,
            latest_price=(
                latest_prices[r.card_id].median_price
                if r.card_id and latest_prices.get(r.card_id)
                else None
            ),
            image_url=_scryfall_image_url(r.set_code, r.collector_number),
        )
        for r in rows
    ]

    next_cursor = _encode_cursor(rows[-1].id) if has_next and rows else None
    total = repo.count_collection(FAKE_USER_ID, name_search=name, set_code=set)

    return paginated_response(data=data, cursor=next_cursor, total=total)


@router.get("/summary", response_model=ApiResponse[CollectionSummary])
def collection_summary(repo: Repository = Depends(get_db)):
    summary = repo.get_collection_summary(FAKE_USER_ID)
    total_value = repo.get_collection_total_value(FAKE_USER_ID)
    data = CollectionSummary(
        total_unique=summary["total_unique"],
        total_cards=summary["total_cards"],
        total_value=total_value,
        linked_count=summary["linked_count"],
        sets_count=summary["sets_count"],
    )
    return success_response(data=data)


@router.get("/sets")
def collection_sets(repo: Repository = Depends(get_db)):
    sets = repo.get_collection_sets(FAKE_USER_ID)
    data = [{"set_code": s[0], "set_name": s[1], "count": s[2]} for s in sets]
    return success_response(data=data)


@router.post("/import", response_model=ApiResponse[ImportResult])
def import_collection(repo: Repository = Depends(get_db)):
    """Import collection from the default CSV file."""
    from pathlib import Path

    from src.collection.importer import import_collection_csv

    csv_path = Path("docs/colecaoImport/export_1b19325b553f22c3260d042d65c1d7dcb07f2743.csv")
    if not csv_path.exists():
        from fastapi.exceptions import HTTPException

        raise HTTPException(status_code=404, detail="Collection CSV not found")

    result = import_collection_csv(
        engine=repo.engine,
        csv_path=csv_path,
        user_id=FAKE_USER_ID,
    )
    return success_response(data=ImportResult(**result))


@router.post("/sync", response_model=ApiResponse[JobStatus])
async def trigger_sync(
    request: SyncRequest,
    repo: Repository = Depends(get_db),
    _auth: None = Depends(verify_api_key),
) -> ApiResponse[JobStatus]:
    """Trigger a collection sync as a background job."""
    job_id = job_tracker.start(
        "collection_sync",
        {
            "limit": request.limit,
            "history_days": request.history_days,
            "force": request.force,
        },
    )

    asyncio.create_task(
        _run_sync_job(
            job_id,
            limit=request.limit,
            history_days=request.history_days,
            force=request.force,
        )
    )

    data = JobStatus(
        job_id=job_id,
        status="started",
        message="Collection sync started",
    )
    return success_response(data=data)


async def _run_sync_job(
    job_id: str,
    limit: int | None,
    history_days: int,
    force: bool,
) -> None:
    try:
        from src.collectors.sync_collection import run_sync_collection

        db_url = os.environ.get("TCG_DATABASE_URL", "sqlite:///tcg_market.db")
        summary = await run_sync_collection(
            db_url=db_url,
            limit=limit,
            history_days=history_days,
            skip_matched=not force,
        )
        job_tracker.complete(
            job_id,
            f"Synced {summary.matched} cards, " f"{summary.observations_saved} observations saved",
        )
    except Exception as e:
        job_tracker.fail(job_id, str(e))
