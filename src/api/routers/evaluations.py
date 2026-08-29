"""Evaluation list (watchlist) endpoints."""

from __future__ import annotations

import structlog
from fastapi import APIRouter, Depends
from fastapi.exceptions import HTTPException

from src.api.deps import get_current_user, get_db
from src.api.schemas.envelope import ApiResponse, success_response
from src.api.schemas.evaluations import (
    EvalCreateRequest,
    EvalEntryResponse,
    EvalPromoteResponse,
)
from src.database.repository import Repository
from src.domain.models import User

log = structlog.get_logger()

router = APIRouter(prefix="/evaluations", tags=["evaluations"])

MAX_EVALUATION_ENTRIES = 50


def _image_url(set_code: str | None, collector_number: str | None) -> str | None:
    """Build Scryfall image URL from set_code + collector_number."""
    if set_code and collector_number:
        sc = set_code.lower()
        cn = collector_number
        return f"https://api.scryfall.com/cards/{sc}/{cn}?format=image&version=normal"
    return None


def _to_response(entry: dict) -> EvalEntryResponse:
    return EvalEntryResponse(
        id=entry["id"],
        card_name=entry["card_name"],
        set_code=entry["set_code"],
        collector_number=entry["collector_number"],
        liga_url=entry["liga_url"],
        price_at_add=entry["price_at_add"],
        card_id=entry["card_id"],
        image_url=_image_url(entry["set_code"], entry["collector_number"]),
        created_at=entry["created_at"],
    )


@router.post("", response_model=ApiResponse[EvalEntryResponse], status_code=201)
def create_evaluation(
    body: EvalCreateRequest,
    repo: Repository = Depends(get_db),
    user: User = Depends(get_current_user),
) -> ApiResponse[EvalEntryResponse]:
    """Add a card to the evaluation list. Max 50 per user."""
    count = repo.count_evaluation_entries(user.id)
    if count >= MAX_EVALUATION_ENTRIES:
        raise HTTPException(status_code=400, detail="Evaluation list limit reached (50)")

    entry_id = repo.create_evaluation_entry(
        user_id=user.id,
        card_name=body.card_name,
        set_code=body.set_code,
        collector_number=body.collector_number,
        liga_url=body.liga_url,
        source_data_json=body.source_data_json,
        price_at_add=body.price_at_add,
        card_id=body.card_id,
    )
    entry = repo.get_evaluation_entry(entry_id)
    if entry is None:
        raise HTTPException(status_code=500, detail="Failed to create evaluation entry")

    log.info("evaluation_entry_created", entry_id=entry_id, user_id=user.id)
    return success_response(data=_to_response(entry))


@router.get("", response_model=ApiResponse[list[EvalEntryResponse]])
def list_evaluations(
    repo: Repository = Depends(get_db),
    user: User = Depends(get_current_user),
) -> ApiResponse[list[EvalEntryResponse]]:
    """List evaluation entries for the current user."""
    entries = repo.list_evaluation_entries(user.id)
    return success_response(data=[_to_response(e) for e in entries])


@router.delete("/{entry_id}", status_code=200)
def delete_evaluation(
    entry_id: int,
    repo: Repository = Depends(get_db),
    user: User = Depends(get_current_user),
) -> ApiResponse[dict]:
    """Remove an evaluation entry (hard delete). IDOR check enforced."""
    entry = repo.get_evaluation_entry(entry_id)
    if entry is None:
        raise HTTPException(status_code=404, detail="Evaluation entry not found")
    if entry["user_id"] != user.id:
        raise HTTPException(status_code=404, detail="Evaluation entry not found")

    repo.delete_evaluation_entry(entry_id)
    log.info("evaluation_entry_deleted", entry_id=entry_id, user_id=user.id)
    return success_response(data={"deleted": True})


@router.post("/{entry_id}/promote", response_model=ApiResponse[EvalPromoteResponse])
def promote_evaluation(
    entry_id: int,
    repo: Repository = Depends(get_db),
    user: User = Depends(get_current_user),
) -> ApiResponse[EvalPromoteResponse]:
    """Promote an evaluation entry to the user's collection, then delete it."""
    entry = repo.get_evaluation_entry(entry_id)
    if entry is None:
        raise HTTPException(status_code=404, detail="Evaluation entry not found")
    if entry["user_id"] != user.id:
        raise HTTPException(status_code=404, detail="Evaluation entry not found")

    # Create collection entry via batch_add (reuses existing logic)
    from sqlalchemy.orm import Session

    from src.collection.batch_add import BatchAddEntry, batch_add_entries

    batch_entry = BatchAddEntry(
        name_en=entry["card_name"],
        set_code=entry["set_code"],
        collector_number=entry["collector_number"],
        quantity=1,
    )

    user_id_str = str(user.id)
    with Session(repo.engine) as session:
        try:
            result = batch_add_entries(session, user_id_str, [batch_entry])
            session.commit()
        except Exception:
            session.rollback()
            raise

    if result.added == 0:
        raise HTTPException(
            status_code=400,
            detail="Failed to add card to collection",
        )

    # Delete the evaluation entry
    repo.delete_evaluation_entry(entry_id)

    # Find the created collection entry id
    from src.database.models import UserCollectionRow

    with Session(repo.engine) as session:
        from sqlalchemy import select

        stmt = (
            select(UserCollectionRow.id)
            .where(
                UserCollectionRow.user_id == user_id_str,
                UserCollectionRow.name_en == entry["card_name"],
            )
            .order_by(UserCollectionRow.id.desc())
            .limit(1)
        )
        collection_entry_id = session.execute(stmt).scalar() or 0

    log.info(
        "evaluation_entry_promoted",
        entry_id=entry_id,
        collection_entry_id=collection_entry_id,
        user_id=user.id,
    )

    return success_response(
        data=EvalPromoteResponse(
            collection_entry_id=collection_entry_id,
            card_name=entry["card_name"],
        )
    )
