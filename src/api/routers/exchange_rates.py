"""Exchange rate API endpoints (T07)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from src.api.deps import get_db, verify_api_key
from src.api.schemas.envelope import ApiResponse, success_response
from src.api.schemas.exchange_rates import ExchangeRateHistorySchema, ExchangeRateSchema
from src.database.repository import Repository

router = APIRouter(prefix="/exchange-rates", tags=["exchange-rates"])


@router.get("/current", response_model=ApiResponse[ExchangeRateSchema])
def get_current_rate(repo: Repository = Depends(get_db)):
    """Get the latest exchange rate."""
    row = repo.get_latest_rate()
    if row is None:
        return success_response(data=None)

    data = ExchangeRateSchema(
        rate_date=row.rate_date,
        from_currency=row.from_currency,
        to_currency=row.to_currency,
        rate=row.rate,
        source=row.source,
        created_at=row.created_at,
    )
    return success_response(data=data)


@router.get("/history", response_model=ApiResponse[ExchangeRateHistorySchema])
def get_rate_history(
    days: int = Query(default=30, ge=1, le=365),
    repo: Repository = Depends(get_db),
):
    """Get exchange rate history for the last N days."""
    rows = repo.get_rate_history(days=days)
    rates = [
        ExchangeRateSchema(
            rate_date=r.rate_date,
            from_currency=r.from_currency,
            to_currency=r.to_currency,
            rate=r.rate,
            source=r.source,
            created_at=r.created_at,
        )
        for r in rows
    ]
    data = ExchangeRateHistorySchema(rates=rates, count=len(rates))
    return success_response(data=data)


@router.post("/refresh", response_model=ApiResponse[ExchangeRateSchema])
async def refresh_rate(
    repo: Repository = Depends(get_db),
    _auth: None = Depends(verify_api_key),
):
    """Trigger a BCB PTAX rate fetch for today."""
    from src.providers.bcb.client import fetch_daily_rate

    rate = await fetch_daily_rate()
    if rate is None:
        return success_response(data=None)

    repo.upsert_exchange_rate(rate)
    data = ExchangeRateSchema(
        rate_date=rate.rate_date,
        from_currency=rate.from_currency,
        to_currency=rate.to_currency,
        rate=rate.rate,
        source=rate.source,
    )
    return success_response(data=data)
