from __future__ import annotations

import base64
from datetime import date

from fastapi import APIRouter, Depends, Query
from fastapi.exceptions import HTTPException

from src.api.deps import get_currency_converter_dep, get_db
from src.api.schemas.cards import (
    CardDetail,
    CardSummary,
    PriceObservation,
    SourceCardSchema,
)
from src.api.schemas.envelope import (
    ApiResponse,
    paginated_response,
    success_response,
)
from src.database.repository import Repository
from src.services.currency import CurrencyConverter

router = APIRouter(prefix="/cards", tags=["cards"])

PERIOD_MAP = {
    "30d": 30,
    "90d": 90,
    "180d": 180,
    "1y": 365,
    "3y": 1095,
}


def encode_cursor(card_id: int) -> str:
    return base64.urlsafe_b64encode(str(card_id).encode()).decode()


def decode_cursor(cursor: str) -> int | None:
    try:
        return int(base64.urlsafe_b64decode(cursor).decode())
    except (ValueError, Exception):
        return None


@router.get("", response_model=ApiResponse[list[CardSummary]])
def list_cards(
    game: str | None = None,
    set: str | None = Query(None, alias="set"),
    name: str | None = None,
    cursor: str | None = None,
    limit: int = Query(default=50, ge=1, le=200),
    currency: str = Query(default="BRL", pattern="^(BRL|USD)$"),
    repo: Repository = Depends(get_db),
    converter: CurrencyConverter = Depends(get_currency_converter_dep),
):
    after_id = decode_cursor(cursor) if cursor else None
    rows = repo.list_cards(
        game=game,
        set_code=set,
        name_search=name,
        after_id=after_id,
        limit=limit,
    )

    has_next = len(rows) > limit
    if has_next:
        rows = rows[:limit]

    card_ids = [r.id for r in rows]
    latest_prices = repo.get_latest_prices_batch(card_ids)

    data = []
    for r in rows:
        obs = latest_prices.get(r.id)
        raw_price = obs.median_price if obs else None
        price = converter.convert(raw_price, date.today(), currency) if raw_price else None
        data.append(
            CardSummary(
                id=r.id,
                game=r.game,
                name_en=r.name_en,
                name_pt=r.name_pt,
                set_code=r.set_code,
                collector_number=r.collector_number,
                latest_price=price,
                currency=currency,
            )
        )

    next_cursor = encode_cursor(rows[-1].id) if has_next and rows else None
    total = repo.count_cards(game=game, set_code=set, name_search=name)

    return paginated_response(data=data, cursor=next_cursor, total=total)


@router.get("/{card_id}", response_model=ApiResponse[CardDetail])
def get_card(
    card_id: int,
    currency: str = Query(default="BRL", pattern="^(BRL|USD)$"),
    repo: Repository = Depends(get_db),
    converter: CurrencyConverter = Depends(get_currency_converter_dep),
):
    card = repo.get_card_by_id(card_id)
    if not card:
        raise HTTPException(status_code=404, detail="Card not found")

    source_cards = repo.get_source_cards_for_card(card_id)
    latest_prices = repo.get_latest_prices_batch([card_id])
    obs = latest_prices.get(card_id)
    raw_price = obs.median_price if obs else None
    price = converter.convert(raw_price, date.today(), currency) if raw_price else None

    data = CardDetail(
        id=card.id,
        game=card.game,
        name_en=card.name_en,
        name_pt=card.name_pt,
        set_code=card.set_code,
        collector_number=card.collector_number,
        latest_price=price,
        currency=currency,
        source_cards=[SourceCardSchema.model_validate(sc) for sc in source_cards],
        created_at=card.created_at,
        updated_at=card.updated_at,
    )

    return success_response(data=data)


@router.get(
    "/{card_id}/history",
    response_model=ApiResponse[list[PriceObservation]],
)
def get_history(
    card_id: int,
    period: str = Query(default="90d"),
    currency: str = Query(default="BRL", pattern="^(BRL|USD)$"),
    repo: Repository = Depends(get_db),
    converter: CurrencyConverter = Depends(get_currency_converter_dep),
):
    if period not in PERIOD_MAP:
        raise HTTPException(
            status_code=422,
            detail=("Invalid period. Must be one of: " + ", ".join(PERIOD_MAP.keys())),
        )

    card = repo.get_card_by_id(card_id)
    if not card:
        raise HTTPException(status_code=404, detail="Card not found")

    source_cards = repo.get_source_cards_for_card(card_id)
    if not source_cards:
        return success_response(data=[])

    days = PERIOD_MAP[period]
    all_observations = []
    for sc in source_cards:
        prices = repo.get_price_series(
            source=[sc.source, "jsonld_snapshot"],
            external_id=sc.external_id,
            days=days,
        )
        all_observations.extend(prices)

    all_observations.sort(key=lambda p: p.observed_at)

    data = [
        PriceObservation(
            observed_at=p.observed_at,
            median_price=converter.convert(p.median_price, p.observed_at, currency),
            tcg_price=converter.convert(p.tcg_price, p.observed_at, currency),
            last_sold_price=converter.convert(p.last_sold_price, p.observed_at, currency),
            quantity_available=p.quantity_available,
            currency=currency,
        )
        for p in all_observations
    ]

    return success_response(data=data)
