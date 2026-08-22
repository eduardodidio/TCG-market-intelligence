from __future__ import annotations

import logging
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, Query
from fastapi.exceptions import HTTPException

from src.api.deps import get_currency_converter_dep, get_db, get_market_data_service
from src.api.schemas.envelope import ApiResponse, success_response
from src.api.schemas.market import (
    MarketStats,
    MoverEntry,
    MoversResponse,
)
from src.api.schemas.market_summary import MarketSummaryResponse
from src.api.schemas.trending import TrendingCardEntry, TrendingResponse
from src.database.repository import Repository
from src.services.currency import CurrencyConverter
from src.services.market_data import MarketDataService
from src.services.trending import TrendingService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/market", tags=["market"])

MOVERS_PERIOD_MAP = {"7d": 7, "30d": 30, "90d": 90}
TRENDING_PERIOD_MAP = {"7d": 7, "30d": 30, "90d": 90}

# ---------------------------------------------------------------------------
# Simple module-level cache (30-min TTL)
# ---------------------------------------------------------------------------

_endpoint_cache: dict[str, tuple[datetime, object]] = {}
_CACHE_TTL = timedelta(minutes=30)


def _get_cached(key: str) -> object | None:
    entry = _endpoint_cache.get(key)
    if entry and datetime.now() - entry[0] < _CACHE_TTL:
        return entry[1]
    return None


def _set_cached(key: str, value: object) -> None:
    _endpoint_cache[key] = (datetime.now(), value)


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


# ---------------------------------------------------------------------------
# GET /market/summary — aggregate market summary
# ---------------------------------------------------------------------------


@router.get("/summary", response_model=ApiResponse[MarketSummaryResponse])
def get_summary(
    period: str = Query(default="30d"),
    currency: str = Query(default="BRL", pattern="^(BRL|USD|PILA)$"),
    service: MarketDataService = Depends(get_market_data_service),
    repo: Repository = Depends(get_db),
):
    if period not in MOVERS_PERIOD_MAP:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid period. Must be one of: {', '.join(MOVERS_PERIOD_MAP.keys())}",
        )

    cache_key = f"summary:{period}:{currency}"
    cached = _get_cached(cache_key)
    if cached is not None:
        return success_response(data=cached)

    # Get basic market stats via the service
    summary = service.get_market_summary(currency=currency)

    # Get ALL movers for the period to compute directional counts
    days = MOVERS_PERIOD_MAP[period]
    gainers_raw, losers_raw = repo.get_movers(days=days, limit=9999)

    # Each tuple: (card_id, name_en, name_pt, set_code, price_start, price_end, change_pct)
    all_movers = gainers_raw + losers_raw

    gainers_count = sum(1 for m in all_movers if m[6] > 0)
    losers_count = sum(1 for m in all_movers if m[6] < 0)
    unchanged_count = sum(1 for m in all_movers if m[6] == 0)

    # Compute average price change percentage
    if all_movers:
        avg_change = sum(float(m[6]) for m in all_movers) / len(all_movers)
    else:
        avg_change = None

    # Determine market direction
    if gainers_count > losers_count:
        direction = "up"
    elif losers_count > gainers_count:
        direction = "down"
    else:
        direction = "flat"

    data = MarketSummaryResponse(
        total_cards_tracked=summary.total_cards,
        total_observations=summary.total_observations,
        avg_price=float(summary.avg_price) if summary.avg_price is not None else None,
        avg_price_change_pct=round(avg_change, 4) if avg_change is not None else None,
        gainers_count=gainers_count,
        losers_count=losers_count,
        unchanged_count=unchanged_count,
        market_direction=direction,
        period=period,
        currency=summary.currency,
        computed_at=datetime.now(),
    )

    _set_cached(cache_key, data)
    return success_response(data=data)


# ---------------------------------------------------------------------------
# GET /market/volatile — most volatile cards
# ---------------------------------------------------------------------------


@router.get("/volatile", response_model=ApiResponse[TrendingResponse])
def get_volatile(
    period: str = Query(default="30d"),
    limit: int = Query(default=10, ge=1, le=50),
    currency: str = Query(default="BRL", pattern="^(BRL|USD|PILA)$"),
    trending_svc: TrendingService = Depends(get_trending_service),
    converter: CurrencyConverter = Depends(get_currency_converter_dep),
    repo: Repository = Depends(get_db),
):
    if period not in TRENDING_PERIOD_MAP:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid period. Must be one of: {', '.join(TRENDING_PERIOD_MAP.keys())}",
        )

    cache_key = f"volatile:{period}:{currency}:{limit}"
    cached = _get_cached(cache_key)
    if cached is not None:
        return success_response(data=cached)

    days = TRENDING_PERIOD_MAP[period]

    try:
        # Get both gainers and losers from TrendingService
        gainers_resp = trending_svc.get_trending("up", days, 50, converter, currency)
        losers_resp = trending_svc.get_trending("down", days, 50, converter, currency)

        # Merge both lists, dedup by card_id
        seen: set[int] = set()
        all_cards: list[TrendingCardEntry] = []
        for card in gainers_resp.cards + losers_resp.cards:
            if card.card_id not in seen:
                seen.add(card.card_id)
                all_cards.append(card)

        # Rank by volatility: |change_pct| * (1 - consistency)
        # High absolute change AND low consistency = high volatility
        all_cards.sort(
            key=lambda c: abs(c.change_pct) * (1 - c.consistency),
            reverse=True,
        )

        volatile_cards = all_cards[:limit]
    except Exception:
        logger.warning("TrendingService failed for volatile endpoint, falling back to movers")
        # Fallback: use repo.get_movers sorted by |change_pct|
        gainers_raw, losers_raw = repo.get_movers(days=days, limit=9999)
        all_movers = gainers_raw + losers_raw
        all_movers.sort(key=lambda m: abs(float(m[6])), reverse=True)

        volatile_cards = [
            TrendingCardEntry(
                card_id=m[0],
                name_en=m[1],
                name_pt=m[2],
                set_code=m[3],
                price_start=float(m[4]) if m[4] is not None else 0.0,
                price_end=float(m[5]) if m[5] is not None else 0.0,
                change_pct=float(m[6]),
                change_abs=float(m[5] - m[4]) if m[4] is not None and m[5] is not None else 0.0,
                consistency=0.0,
                composite_score=0.0,
                observation_count=0,
                currency=currency,
            )
            for m in all_movers[:limit]
        ]

    data = TrendingResponse(
        cards=volatile_cards,
        period=period,
        direction="volatile",
        computed_at=datetime.now(),
        cached=False,
    )

    _set_cached(cache_key, data)
    return success_response(data=data)
