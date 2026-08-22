from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from fastapi.exceptions import HTTPException

from src.api.deps import get_currency_converter_dep, get_db, get_market_data_service
from src.api.schemas.envelope import ApiResponse, success_response
from src.api.schemas.market import (
    MarketStats,
    MoverEntry,
    MoversResponse,
)
from src.api.schemas.trending import TrendingResponse
from src.database.repository import Repository
from src.services.currency import CurrencyConverter
from src.services.market_data import MarketDataService
from src.services.trending import TrendingService

router = APIRouter(prefix="/market", tags=["market"])

MOVERS_PERIOD_MAP = {"7d": 7, "30d": 30, "90d": 90}
TRENDING_PERIOD_MAP = {"7d": 7, "30d": 30, "90d": 90}

# Lazy singleton for TrendingService (cache persists across requests)
_trending_service: TrendingService | None = None


def get_trending_service(repo: Repository = Depends(get_db)) -> TrendingService:
    global _trending_service  # noqa: PLW0603
    if _trending_service is None:
        _trending_service = TrendingService(repo)
    return _trending_service


@router.get("/movers", response_model=ApiResponse[MoversResponse])
def get_movers(
    period: str = Query(default="30d"),
    limit: int = Query(default=10, ge=1, le=50),
    currency: str = Query(default="BRL", pattern="^(BRL|USD|PILA)$"),
    service: MarketDataService = Depends(get_market_data_service),
):
    if period not in MOVERS_PERIOD_MAP:
        raise HTTPException(
            status_code=422,
            detail=(f"Invalid period. Must be one of: {', '.join(MOVERS_PERIOD_MAP.keys())}"),
        )

    result = service.get_top_movers(period=period, limit=limit, currency=currency)

    # Map shared MoverInfo -> existing MoverEntry for backward compat
    gainers = [
        MoverEntry(
            card_id=g.card_id,
            name_en=g.name_en,
            name_pt=g.name_pt,
            set_code=g.set_code,
            price_start=g.price_start,
            price_end=g.price_end,
            change_pct=g.change_pct,
            currency=g.currency,
        )
        for g in result.gainers
    ]
    losers = [
        MoverEntry(
            card_id=lo.card_id,
            name_en=lo.name_en,
            name_pt=lo.name_pt,
            set_code=lo.set_code,
            price_start=lo.price_start,
            price_end=lo.price_end,
            change_pct=lo.change_pct,
            currency=lo.currency,
        )
        for lo in result.losers
    ]

    data = MoversResponse(gainers=gainers, losers=losers)
    return success_response(data=data)


@router.get("/stats", response_model=ApiResponse[MarketStats])
def get_stats(
    game: str | None = None,
    currency: str = Query(default="BRL", pattern="^(BRL|USD|PILA)$"),
    service: MarketDataService = Depends(get_market_data_service),
):
    summary = service.get_market_summary(currency=currency, game=game)

    data = MarketStats(
        total_cards=summary.total_cards,
        total_observations=summary.total_observations,
        avg_price=summary.avg_price,
        date_range_start=summary.date_range_start,
        date_range_end=summary.date_range_end,
        currency=summary.currency,
    )
    return success_response(data=data)


@router.get("/trending/gainers", response_model=ApiResponse[TrendingResponse])
def get_trending_gainers(
    period: str = Query(default="30d"),
    limit: int = Query(default=20, ge=1, le=50),
    currency: str = Query(default="BRL", pattern="^(BRL|USD|PILA)$"),
    service: TrendingService = Depends(get_trending_service),
    converter: CurrencyConverter = Depends(get_currency_converter_dep),
):
    if period not in TRENDING_PERIOD_MAP:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid period. Must be one of: {', '.join(TRENDING_PERIOD_MAP.keys())}",
        )
    days = TRENDING_PERIOD_MAP[period]
    data = service.get_trending("up", days, limit, converter, currency)
    data.period = period
    return success_response(data=data)


@router.get("/trending/losers", response_model=ApiResponse[TrendingResponse])
def get_trending_losers(
    period: str = Query(default="30d"),
    limit: int = Query(default=20, ge=1, le=50),
    currency: str = Query(default="BRL", pattern="^(BRL|USD|PILA)$"),
    service: TrendingService = Depends(get_trending_service),
    converter: CurrencyConverter = Depends(get_currency_converter_dep),
):
    if period not in TRENDING_PERIOD_MAP:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid period. Must be one of: {', '.join(TRENDING_PERIOD_MAP.keys())}",
        )
    days = TRENDING_PERIOD_MAP[period]
    data = service.get_trending("down", days, limit, converter, currency)
    data.period = period
    return success_response(data=data)
