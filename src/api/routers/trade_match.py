"""Trade matching API router — duplicates + trade matches (F110-T03/T04)."""

from __future__ import annotations

import structlog
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from src.api.deps import get_current_user, get_db
from src.api.schemas.envelope import ApiResponse, success_response
from src.api.schemas.trade_match import DuplicateCard, MatchedCard, TradeMatch
from src.database.repository import Repository
from src.domain.models import User
from src.marketplace.trade_queries import TradeQueries
from src.services.trade_matcher import find_reverse_matches, find_trade_matches

log = structlog.get_logger()

router = APIRouter(prefix="/trade", tags=["trade-match"])


class SetFacet(BaseModel):
    set_code: str | None = None
    set_name: str | None = None
    count: int


@router.get("/duplicates", response_model=ApiResponse[list[DuplicateCard]])
def list_duplicates(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    search: str | None = Query(None, max_length=100),
    set_code: str | None = Query(None, max_length=10),
    sort_by: str = Query("quantity", pattern="^(quantity|name|set|number|price)$"),
    sort_dir: str = Query("desc", pattern="^(asc|desc)$"),
    user: User = Depends(get_current_user),
    repo: Repository = Depends(get_db),
):
    """List cards the current user has more than one copy of."""
    dupes, total = TradeQueries(repo).list_duplicates(
        user.id,
        limit=limit,
        offset=offset,
        search=search,
        set_code=set_code,
        sort_by=sort_by,
        sort_dir=sort_dir,
    )

    result = [
        DuplicateCard(
            card_id=d["card_id"],
            name_en=d["name_en"],
            name_pt=d.get("name_pt"),
            set_code=d.get("set_code"),
            collector_number=d.get("collector_number"),
            quantity=d["quantity"],
            surplus=d["surplus"],
            quality=d.get("quality"),
            image_uri=d.get("image_uri"),
        )
        for d in dupes
    ]

    return success_response(result, total=total)


@router.get("/duplicates/count", response_model=ApiResponse[dict])
def duplicates_count(
    user: User = Depends(get_current_user),
    repo: Repository = Depends(get_db),
):
    """Count cards the current user has more than one copy of."""
    _, total = repo.get_user_duplicates(user.id, limit=0, offset=0)
    return success_response({"count": total})


@router.get("/duplicates/sets", response_model=ApiResponse[list[SetFacet]])
def list_duplicate_sets(
    user: User = Depends(get_current_user),
    repo: Repository = Depends(get_db),
):
    """List set facets for the current user's duplicates (quantity > 1)."""
    sets = TradeQueries(repo).list_duplicate_sets(user.id)
    return success_response([SetFacet(**s) for s in sets])


@router.get("/matches", response_model=ApiResponse[list[TradeMatch]])
def get_trade_matches(
    limit: int = Query(20, ge=1, le=100),
    user: User = Depends(get_current_user),
    repo: Repository = Depends(get_db),
):
    """Find trade partner suggestions based on wishlist vs others' duplicates."""
    raw_matches = find_trade_matches(user.id, repo, limit=limit)

    result = [
        TradeMatch(
            partner_name=m["partner_name"],
            share_code=m["share_code"],
            matching_card_count=m["matching_card_count"],
            matched_cards=[
                MatchedCard(
                    card_id=c["card_id"],
                    name_en=c["name_en"],
                    set_code=c.get("set_code"),
                    image_uri=c.get("image_uri"),
                    partner_quantity=c["partner_quantity"],
                    your_max_price=c.get("your_max_price"),
                )
                for c in m["matched_cards"]
            ],
        )
        for m in raw_matches
    ]

    return success_response(result)


@router.get("/matches/reverse", response_model=ApiResponse[list[TradeMatch]])
def get_reverse_matches(
    limit: int = Query(20, ge=1, le=100),
    user: User = Depends(get_current_user),
    repo: Repository = Depends(get_db),
):
    """Find users who want the current user's duplicate cards."""
    raw_matches = find_reverse_matches(user.id, repo, limit=limit)

    result = [
        TradeMatch(
            partner_name=m["partner_name"],
            share_code=m["share_code"],
            matching_card_count=m["matching_card_count"],
            matched_cards=[
                MatchedCard(
                    card_id=c["card_id"],
                    name_en=c["name_en"],
                    set_code=c.get("set_code"),
                    image_uri=c.get("image_uri"),
                    partner_quantity=c["partner_quantity"],
                    your_max_price=c.get("your_max_price"),
                )
                for c in m["matched_cards"]
            ],
        )
        for m in raw_matches
    ]

    return success_response(result)
