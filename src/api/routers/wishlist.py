"""Wishlist CRUD API router (F110-T02)."""

from __future__ import annotations

from decimal import Decimal

import structlog
from fastapi import APIRouter, Depends, Query
from fastapi.exceptions import HTTPException
from sqlalchemy.orm import Session

from src.api.deps import get_current_user, get_db
from src.api.schemas.envelope import ApiResponse, success_response
from src.api.schemas.wishlist import WishlistAddRequest, WishlistCheckResponse, WishlistItem
from src.database.models import CardRow
from src.database.repository import Repository
from src.domain.models import User

log = structlog.get_logger()

router = APIRouter(prefix="/wishlist", tags=["wishlist"])

MAX_WISHLIST_ITEMS = 200


@router.get("", response_model=ApiResponse[list[WishlistItem]])
def list_wishlist(
    search: str | None = Query(None),
    acquired: bool | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    user: User = Depends(get_current_user),
    repo: Repository = Depends(get_db),
):
    """List the current user's wishlist items."""
    if acquired is not None and acquired:
        # Only acquired items: fetch all, filter in-memory
        all_items, _ = repo.get_wishlist(
            user.id,
            include_acquired=True,
            search=search,
            limit=1000,
            offset=0,
        )
        filtered = [i for i in all_items if i.is_acquired == 1]
        total = len(filtered)
        items = filtered[offset : offset + limit]
    elif acquired is not None and not acquired:
        items, total = repo.get_wishlist(
            user.id,
            include_acquired=False,
            search=search,
            limit=limit,
            offset=offset,
        )
    else:
        items, total = repo.get_wishlist(
            user.id,
            include_acquired=True,
            search=search,
            limit=limit,
            offset=offset,
        )

    # Enrich with image_uri from cards table
    card_ids = [item.card_id for item in items]
    image_map: dict[int, str | None] = {}
    if card_ids:
        with Session(repo.engine) as session:
            from sqlalchemy import select

            rows = session.execute(
                select(CardRow.id, CardRow.image_uri).where(CardRow.id.in_(card_ids))
            ).all()
            image_map = {r.id: r.image_uri for r in rows}

    result = [
        WishlistItem(
            id=item.id,
            card_id=item.card_id,
            name_en=item.name_en,
            name_pt=item.name_pt,
            set_code=item.set_code,
            collector_number=item.collector_number,
            notes=item.notes,
            max_price=float(item.max_price) if item.max_price is not None else None,
            is_acquired=bool(item.is_acquired),
            acquired_at=item.acquired_at.isoformat() if item.acquired_at else None,
            created_at=item.created_at.isoformat() if item.created_at else "",
            image_uri=image_map.get(item.card_id),
        )
        for item in items
    ]

    return success_response(result, total=total)


@router.post("", response_model=ApiResponse[WishlistItem])
def add_to_wishlist(
    request: WishlistAddRequest,
    user: User = Depends(get_current_user),
    repo: Repository = Depends(get_db),
):
    """Add a card to the user's wishlist."""
    # Check card exists
    with Session(repo.engine) as session:
        card = session.get(CardRow, request.card_id)
        if card is None:
            raise HTTPException(status_code=404, detail="Card not found")
        card_name_en = card.name_en
        card_name_pt = card.name_pt
        card_set_code = card.set_code
        card_collector_number = card.collector_number
        card_image_uri = card.image_uri

    # Check max items
    existing_ids = repo.get_wishlist_card_ids(user.id)
    if len(existing_ids) >= MAX_WISHLIST_ITEMS:
        raise HTTPException(
            status_code=409,
            detail=f"Maximum {MAX_WISHLIST_ITEMS} wishlist items allowed",
        )

    row = repo.add_wishlist_item(
        user_id=user.id,
        card_id=request.card_id,
        name_en=card_name_en,
        name_pt=card_name_pt,
        set_code=card_set_code,
        collector_number=card_collector_number,
        notes=request.notes,
        max_price=Decimal(str(request.max_price)) if request.max_price is not None else None,
    )

    if row is None:
        raise HTTPException(status_code=409, detail="Card already in wishlist")

    return success_response(
        WishlistItem(
            id=row.id,
            card_id=row.card_id,
            name_en=row.name_en,
            name_pt=row.name_pt,
            set_code=row.set_code,
            collector_number=row.collector_number,
            notes=row.notes,
            max_price=float(row.max_price) if row.max_price is not None else None,
            is_acquired=bool(row.is_acquired),
            acquired_at=None,
            created_at=row.created_at.isoformat() if row.created_at else "",
            image_uri=card_image_uri,
        )
    )


@router.delete("/{card_id}", status_code=204)
def remove_from_wishlist(
    card_id: int,
    user: User = Depends(get_current_user),
    repo: Repository = Depends(get_db),
):
    """Remove a card from the user's wishlist."""
    removed = repo.remove_wishlist_item(user.id, card_id)
    if not removed:
        raise HTTPException(status_code=404, detail="Wishlist item not found")


@router.patch("/{card_id}/acquire", response_model=ApiResponse[dict])
def mark_acquired(
    card_id: int,
    user: User = Depends(get_current_user),
    repo: Repository = Depends(get_db),
):
    """Mark a wishlist item as acquired."""
    updated = repo.mark_wishlist_acquired(user.id, card_id)
    if not updated:
        raise HTTPException(status_code=404, detail="Wishlist item not found")
    return success_response({"acquired": True})


@router.get("/check", response_model=ApiResponse[WishlistCheckResponse])
def check_wishlist(
    card_ids: str = Query(..., description="Comma-separated card IDs"),
    user: User = Depends(get_current_user),
    repo: Repository = Depends(get_db),
):
    """Check which card_ids are in the user's wishlist."""
    try:
        ids = [int(x.strip()) for x in card_ids.split(",") if x.strip()]
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid card_ids format")

    wishlisted_ids = repo.get_wishlist_card_ids(user.id)
    matching = [cid for cid in ids if cid in wishlisted_ids]
    return success_response(WishlistCheckResponse(wishlisted=matching))
