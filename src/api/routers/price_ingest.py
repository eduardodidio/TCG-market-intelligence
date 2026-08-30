"""Price ingest router — accepts externally-fetched price observations.

Designed for the push-prices CLI: run Liga scan locally, POST results here.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import structlog
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from src.api.deps import get_db, require_auth_or_api_key
from src.api.schemas.envelope import ApiResponse, success_response
from src.database.repository import Repository
from src.domain.models import HistoricalPrice

log = structlog.get_logger()

router = APIRouter(prefix="/prices", tags=["prices"])


class PriceObservationIn(BaseModel):
    source: str = Field(..., description="Price source (e.g. 'liga', 'jsonld_snapshot')")
    external_id: str = Field(..., description="External ID for the price observation")
    observed_at: date = Field(..., description="Date the price was observed")
    median_price: Decimal | None = None
    currency: str = "BRL"


class IngestRequest(BaseModel):
    observations: list[PriceObservationIn] = Field(
        ..., min_length=1, max_length=5000, description="Price observations to ingest"
    )


class IngestResult(BaseModel):
    received: int
    inserted: int


@router.post("/ingest", response_model=ApiResponse[IngestResult])
def ingest_prices(
    body: IngestRequest,
    user_id: str = Depends(require_auth_or_api_key),
    repo: Repository = Depends(get_db),
):
    """Ingest a batch of price observations from an external source.

    Requires authentication via JWT or API key. Duplicates are silently
    skipped (INSERT ON CONFLICT DO NOTHING).
    """
    prices = [
        HistoricalPrice(
            source=obs.source,
            external_id=obs.external_id,
            observed_at=obs.observed_at,
            median_price=obs.median_price,
            currency=obs.currency,
        )
        for obs in body.observations
    ]

    inserted = repo.insert_price_observations(prices)

    log.info(
        "prices_ingested",
        user_id=user_id,
        received=len(prices),
        inserted=inserted,
    )

    return success_response(
        data=IngestResult(received=len(prices), inserted=inserted),
    )
