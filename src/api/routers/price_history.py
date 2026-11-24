"""Price history API endpoints (F213-T07).

Provides card-level and collection-entry-level access to merged price
history and diagnostic metrics.
"""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, Query

from src.api.deps import (
    get_currency_converter_dep,
    get_db,
    require_auth_or_api_key,
)
from src.api.error_codes import ErrorCode, api_error
from src.api.schemas.envelope import ApiResponse, success_response
from src.collection.converter import is_foil_entry
from src.database.repository import Repository
from src.services.currency import CurrencyConverter
from src.services.price_history import get_price_diagnostics, get_price_history

router = APIRouter(prefix="/price-history", tags=["prices"])


# ---------------------------------------------------------------------------
# Schemas (kept local — small and endpoint-specific)
# ---------------------------------------------------------------------------

from pydantic import BaseModel  # noqa: E402


class PriceHistoryPoint(BaseModel):
    date: str
    price: float
    source: str


class PriceHistoryResponse(BaseModel):
    card_id: int
    variant: str
    sources: list[str]
    since: str | None = None
    real_points: int
    snapshot_points: int
    data: list[PriceHistoryPoint]


class PriceMetricsResponse(BaseModel):
    card_id: int
    variant: str
    sources: list[str]
    min_price: float | None = None
    max_price: float | None = None
    avg_price: float | None = None
    current_price: float | None = None
    data_points: int = 0
    trend: str | None = None
    change_pct: float | None = None
    real_points: int = 0
    snapshot_points: int = 0


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _build_history_response(
    repo: Repository,
    converter: CurrencyConverter,
    card_id: int,
    is_foil: bool,
    days: int,
    currency: str,
) -> PriceHistoryResponse:
    """Shared logic for both card-level and collection-entry-level history."""
    observations, meta = get_price_history(repo, card_id, is_foil=is_foil, days=days)

    data = []
    for obs in observations:
        price = converter.convert(obs.median_price, obs.observed_at, currency)
        if price is not None:
            data.append(
                PriceHistoryPoint(
                    date=obs.observed_at.isoformat(),
                    price=float(price),
                    source=obs.source,
                )
            )

    since = meta.get("first_observed_at")
    return PriceHistoryResponse(
        card_id=card_id,
        variant=meta["variant"],
        sources=meta["sources"],
        since=since.isoformat() if since else None,
        real_points=meta["real_points"],
        snapshot_points=meta["snapshot_points"],
        data=data,
    )


def _build_metrics_response(
    repo: Repository,
    converter: CurrencyConverter,
    card_id: int,
    is_foil: bool,
    days: int,
    currency: str,
) -> PriceMetricsResponse:
    """Shared logic for metrics endpoints."""
    diag = get_price_diagnostics(repo, card_id, is_foil=is_foil, days=days)

    # Convert prices to requested currency (use today for point-in-time)
    today = date.today()

    def _conv(val):
        return converter.convert(val, today, currency) if val is not None else None

    min_price = _conv(diag["min_price"])
    max_price = _conv(diag["max_price"])
    avg_price = _conv(diag["avg_price"])
    current_price = _conv(diag["current_price"])

    return PriceMetricsResponse(
        card_id=card_id,
        variant=diag["variant"],
        sources=diag["sources"],
        min_price=float(min_price) if min_price is not None else None,
        max_price=float(max_price) if max_price is not None else None,
        avg_price=float(avg_price) if avg_price is not None else None,
        current_price=float(current_price) if current_price is not None else None,
        data_points=diag["data_points"],
        trend=diag["trend"],
        change_pct=diag["change_pct"],
        real_points=diag["real_points"],
        snapshot_points=diag["snapshot_points"],
    )


# ---------------------------------------------------------------------------
# Card-level endpoints
# ---------------------------------------------------------------------------


@router.get(
    "/cards/{card_id}/history",
    response_model=ApiResponse[PriceHistoryResponse],
)
def get_card_price_history(
    card_id: int,
    days: int = Query(default=90, ge=1, le=365),
    currency: str = Query(default="BRL", pattern="^(BRL|USD|PILA)$"),
    repo: Repository = Depends(get_db),
    converter: CurrencyConverter = Depends(get_currency_converter_dep),
):
    """Get price history for a card by card_id."""
    card = repo.get_card_by_id(card_id)
    if not card:
        raise api_error(404, ErrorCode.RESOURCE_NOT_FOUND, "Card not found")

    data = _build_history_response(
        repo,
        converter,
        card_id,
        is_foil=False,
        days=days,
        currency=currency,
    )
    return success_response(data=data)


@router.get(
    "/cards/{card_id}/metrics",
    response_model=ApiResponse[PriceMetricsResponse],
)
def get_card_price_metrics(
    card_id: int,
    days: int = Query(default=90, ge=1, le=365),
    currency: str = Query(default="BRL", pattern="^(BRL|USD|PILA)$"),
    repo: Repository = Depends(get_db),
    converter: CurrencyConverter = Depends(get_currency_converter_dep),
):
    """Get price metrics (min/max/avg/trend) for a card."""
    card = repo.get_card_by_id(card_id)
    if not card:
        raise api_error(404, ErrorCode.RESOURCE_NOT_FOUND, "Card not found")

    data = _build_metrics_response(
        repo,
        converter,
        card_id,
        is_foil=False,
        days=days,
        currency=currency,
    )
    return success_response(data=data)


# ---------------------------------------------------------------------------
# Collection-entry-level endpoints
# ---------------------------------------------------------------------------


@router.get(
    "/collection/{entry_id}/history",
    response_model=ApiResponse[PriceHistoryResponse],
)
def get_collection_entry_price_history(
    entry_id: int,
    days: int = Query(default=90, ge=1, le=365),
    currency: str = Query(default="BRL", pattern="^(BRL|USD|PILA)$"),
    repo: Repository = Depends(get_db),
    converter: CurrencyConverter = Depends(get_currency_converter_dep),
    user_id: str = Depends(require_auth_or_api_key),
):
    """Get price history for a collection entry."""
    entry = repo.get_collection_entry(entry_id)
    if not entry or entry.user_id != user_id:
        raise api_error(404, ErrorCode.RESOURCE_NOT_FOUND, "Collection entry not found")

    if entry.card_id is None:
        return success_response(
            data=PriceHistoryResponse(
                card_id=0,
                variant="normal",
                sources=[],
                since=None,
                real_points=0,
                snapshot_points=0,
                data=[],
            )
        )

    is_foil = is_foil_entry(entry.extras)
    data = _build_history_response(
        repo,
        converter,
        entry.card_id,
        is_foil=is_foil,
        days=days,
        currency=currency,
    )
    return success_response(data=data)


@router.get(
    "/collection/{entry_id}/metrics",
    response_model=ApiResponse[PriceMetricsResponse],
)
def get_collection_entry_price_metrics(
    entry_id: int,
    days: int = Query(default=90, ge=1, le=365),
    currency: str = Query(default="BRL", pattern="^(BRL|USD|PILA)$"),
    repo: Repository = Depends(get_db),
    converter: CurrencyConverter = Depends(get_currency_converter_dep),
    user_id: str = Depends(require_auth_or_api_key),
):
    """Get price metrics (min/max/avg/trend) for a collection entry."""
    entry = repo.get_collection_entry(entry_id)
    if not entry or entry.user_id != user_id:
        raise api_error(404, ErrorCode.RESOURCE_NOT_FOUND, "Collection entry not found")

    if entry.card_id is None:
        return success_response(data=PriceMetricsResponse(card_id=0, variant="normal", sources=[]))

    is_foil = is_foil_entry(entry.extras)
    data = _build_metrics_response(
        repo,
        converter,
        entry.card_id,
        is_foil=is_foil,
        days=days,
        currency=currency,
    )
    return success_response(data=data)
