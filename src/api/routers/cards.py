from __future__ import annotations

import base64
from datetime import date

from fastapi import APIRouter, Depends, Query

from src.analytics.aggregation import (
    PERIOD_MAP,
    aggregate_series,
    compute_price_change_summary,
)
from src.api.deps import get_currency_converter_dep, get_db, get_optional_user
from src.api.error_codes import ErrorCode, api_error
from src.api.schemas.cards import (
    CardDetail,
    CardSummary,
    PriceObservation,
    SourceCardSchema,
)
from src.api.schemas.collection import CollectionHistoryResponse
from src.api.schemas.envelope import (
    ApiResponse,
    paginated_response,
    success_response,
)
from src.database.repository import Repository
from src.domain.models import User
from src.services.currency import CurrencyConverter

router = APIRouter(prefix="/cards", tags=["cards"])


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
    currency: str = Query(default="BRL", pattern="^(BRL|USD|PILA)$"),
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


@router.get("/price-trends")
def get_price_trends(
    card_ids: str = Query(..., description="Comma-separated card IDs (max 50)"),
    days: int = Query(default=7, ge=1, le=30),
    repo: Repository = Depends(get_db),
):
    """Batch fetch mini price history for multiple cards.

    Returns a dict of card_id -> { prices: [...], change_pct: float | None }.
    Used by sparkline charts in card list views.
    """
    raw_ids = [s.strip() for s in card_ids.split(",") if s.strip()]
    try:
        parsed_ids = [int(x) for x in raw_ids]
    except ValueError:
        raise api_error(
            400, ErrorCode.VALIDATION_ERROR, "card_ids must be comma-separated integers"
        )

    if len(parsed_ids) > 50:
        raise api_error(400, ErrorCode.VALIDATION_LIMIT_EXCEEDED, "Maximum 50 card_ids per request")

    if not parsed_ids:
        return success_response(data={"trends": {}})

    series = repo.get_price_series_batch(parsed_ids, days=days)

    trends: dict[str, dict] = {}
    for card_id in parsed_ids:
        history = series.get(card_id, [])
        prices = [float(hp.median_price) for hp in history if hp.median_price is not None]

        change_pct = None
        if len(prices) >= 2:
            first_val = prices[0]
            last_val = prices[-1]
            if first_val != 0:
                change_pct = round(((last_val - first_val) / first_val) * 100, 1)
            else:
                change_pct = 0.0

        trends[str(card_id)] = {
            "prices": prices,
            "change_pct": change_pct,
        }

    return success_response(data={"trends": trends})


@router.get("/{card_id}", response_model=ApiResponse[CardDetail])
def get_card(
    card_id: int,
    currency: str = Query(default="BRL", pattern="^(BRL|USD|PILA)$"),
    repo: Repository = Depends(get_db),
    converter: CurrencyConverter = Depends(get_currency_converter_dep),
    user: User | None = Depends(get_optional_user),
):
    card = repo.get_card_by_id(card_id)
    if not card:
        raise api_error(404, ErrorCode.RESOURCE_NOT_FOUND, "Card not found")

    source_cards = repo.get_source_cards_for_card(card_id)
    latest_prices = repo.get_latest_prices_batch([card_id])
    obs = latest_prices.get(card_id)
    raw_price = obs.median_price if obs else None
    price = converter.convert(raw_price, date.today(), currency) if raw_price else None

    # Look up collection entry if user is authenticated
    collection_entry_id = None
    if user is not None:
        collection_entry_id = repo.get_collection_entry_id_by_card(
            user_id=str(user.id), card_id=card_id
        )

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
        collection_entry_id=collection_entry_id,
        created_at=card.created_at,
        updated_at=card.updated_at,
    )

    return success_response(data=data)


@router.get(
    "/{card_id}/history",
    response_model=ApiResponse[CollectionHistoryResponse],
)
def get_history(
    card_id: int,
    period: str = Query(default="90d"),
    currency: str = Query(default="BRL", pattern="^(BRL|USD|PILA)$"),
    repo: Repository = Depends(get_db),
    converter: CurrencyConverter = Depends(get_currency_converter_dep),
):
    if period not in PERIOD_MAP:
        raise api_error(
            422,
            ErrorCode.VALIDATION_ERROR,
            "Invalid period. Must be one of: " + ", ".join(PERIOD_MAP.keys()),
        )

    card = repo.get_card_by_id(card_id)
    if not card:
        raise api_error(404, ErrorCode.RESOURCE_NOT_FOUND, "Card not found")

    source_cards = repo.get_source_cards_for_card(card_id)
    if not source_cards:
        return success_response(data=CollectionHistoryResponse(observations=[], summary=None))

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

    observations = [
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

    observations, resolution = aggregate_series(observations, period)
    summary = compute_price_change_summary(observations, period, resolution)

    return success_response(
        data=CollectionHistoryResponse(observations=observations, summary=summary)
    )
