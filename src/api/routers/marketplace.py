"""Marketplace API router — listings, trade interest, agreements."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query

from src.api.deps import get_credit_service, get_current_user, get_db, get_optional_user
from src.api.schemas.marketplace import (
    SharingToggle,
    TradeInterestRequest,
    TradeResponse,
)
from src.credits.exceptions import InsufficientCreditsError
from src.credits.service import CreditService
from src.database.repository import Repository
from src.domain.models import User
from src.marketplace.service import MarketplaceService

router = APIRouter(prefix="/marketplace", tags=["marketplace"])


def _get_service(
    repo: Repository = Depends(get_db),
    credit_svc: CreditService = Depends(get_credit_service),
) -> MarketplaceService:
    return MarketplaceService(repo, credit_svc)


@router.get("/sharing")
def get_sharing_status(
    user: User = Depends(get_current_user),
    svc: MarketplaceService = Depends(_get_service),
):
    """Get current sharing status for the authenticated user."""
    return svc.get_sharing_status(user.id)


@router.patch("/sharing")
def toggle_sharing(
    body: SharingToggle,
    user: User = Depends(get_current_user),
    svc: MarketplaceService = Depends(_get_service),
):
    """Toggle collection sharing on/off."""
    return svc.toggle_sharing(user.id, body.is_shared)


@router.get("/listings")
def browse_listings(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    set_code: str | None = Query(None),
    search: str | None = Query(None),
    user: User | None = Depends(get_optional_user),
    svc: MarketplaceService = Depends(_get_service),
):
    """Browse shared collection cards (anonymized). Excludes own cards if authenticated."""
    exclude_id = user.id if user else None
    listings = svc.get_listings(
        limit=limit,
        offset=offset,
        set_code=set_code,
        search=search,
        exclude_user_id=exclude_id,
    )
    return {"listings": listings, "count": len(listings)}


@router.get("/listings/{share_code}")
def get_shared_collection(
    share_code: str,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    search: str | None = Query(None),
    repo: Repository = Depends(get_db),
    svc: MarketplaceService = Depends(_get_service),
):
    """View cards from a specific shared collection (anonymized)."""
    shared = repo.get_shared_collection_by_code(share_code)
    if shared is None:
        raise HTTPException(status_code=404, detail="Shared collection not found")

    listings = repo.list_marketplace_entries(
        limit=limit,
        offset=offset,
        search=search,
        share_code=share_code,
    )
    return {"share_code": share_code, "listings": listings, "count": len(listings)}


@router.post("/interest")
def express_interest(
    body: TradeInterestRequest,
    user: User = Depends(get_current_user),
    svc: MarketplaceService = Depends(_get_service),
):
    """Express interest in trading a card."""
    try:
        result = svc.express_interest(
            buyer_user_id=user.id,
            share_code=body.share_code,
            entry_id=body.entry_id,
            message=body.message,
        )
        return result
    except ValueError as e:
        status = 400
        if "not found" in str(e).lower():
            status = 404
        raise HTTPException(status_code=status, detail=str(e))


@router.get("/my-trades")
def my_trades(
    user: User = Depends(get_current_user),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    svc: MarketplaceService = Depends(_get_service),
):
    """List user's trade interests (as buyer or seller)."""
    trades = svc.get_my_trades(user.id, limit=limit, offset=offset)
    return {"trades": trades, "count": len(trades)}


@router.post("/respond/{interest_id}")
def respond_to_interest(
    interest_id: int,
    body: TradeResponse,
    user: User = Depends(get_current_user),
    svc: MarketplaceService = Depends(_get_service),
):
    """Seller accepts/rejects a trade interest."""
    try:
        return svc.respond_to_interest(interest_id, user.id, body.action)
    except PermissionError:
        raise HTTPException(status_code=403, detail="Only the seller can respond to this interest")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/agree/{interest_id}")
def confirm_agreement(
    interest_id: int,
    user: User = Depends(get_current_user),
    svc: MarketplaceService = Depends(_get_service),
):
    """Confirm trade agreement (buyer or seller).

    When both confirm: check credits, deduct from both, reveal emails.
    """
    try:
        return svc.confirm_agreement(interest_id, user.id)
    except PermissionError:
        raise HTTPException(status_code=403, detail="You are not a participant in this trade")
    except InsufficientCreditsError as e:
        raise HTTPException(
            status_code=402,
            detail={
                "code": "INSUFFICIENT_CREDITS",
                "balance": e.balance,
                "cost": e.cost,
            },
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
