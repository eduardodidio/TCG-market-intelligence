from __future__ import annotations

from decimal import Decimal

from fastapi import APIRouter, Depends, Query
from fastapi.exceptions import HTTPException

from src.api.deps import get_db
from src.api.schemas.envelope import ApiResponse, success_response
from src.api.schemas.market import (
    MarketStats,
    MoverEntry,
    MoversResponse,
)
from src.database.repository import Repository

router = APIRouter(prefix="/market", tags=["market"])

MOVERS_PERIOD_MAP = {"7d": 7, "30d": 30, "90d": 90}


@router.get("/movers", response_model=ApiResponse[MoversResponse])
def get_movers(
    period: str = Query(default="30d"),
    limit: int = Query(default=10, ge=1, le=50),
    repo: Repository = Depends(get_db),
):
    if period not in MOVERS_PERIOD_MAP:
        raise HTTPException(
            status_code=422,
            detail=("Invalid period. Must be one of: " f"{', '.join(MOVERS_PERIOD_MAP.keys())}"),
        )

    days = MOVERS_PERIOD_MAP[period]
    gainers_raw, losers_raw = repo.get_movers(days=days, limit=limit)

    gainers = [
        MoverEntry(
            card_id=g[0],
            name_en=g[1],
            set_code=g[2],
            price_start=g[3],
            price_end=g[4],
            change_pct=g[5],
        )
        for g in gainers_raw
    ]
    losers = [
        MoverEntry(
            card_id=lo[0],
            name_en=lo[1],
            set_code=lo[2],
            price_start=lo[3],
            price_end=lo[4],
            change_pct=lo[5],
        )
        for lo in losers_raw
    ]

    data = MoversResponse(gainers=gainers, losers=losers)
    return success_response(data=data)


@router.get("/stats", response_model=ApiResponse[MarketStats])
def get_stats(
    game: str | None = None,
    repo: Repository = Depends(get_db),
):
    stats = repo.get_market_stats(game=game)

    avg = stats["avg_price"]
    if avg is not None:
        avg = Decimal(str(round(float(avg), 2)))

    data = MarketStats(
        total_cards=stats["total_cards"],
        total_observations=stats["total_observations"],
        avg_price=avg,
        date_range_start=stats["date_range_start"],
        date_range_end=stats["date_range_end"],
    )
    return success_response(data=data)
