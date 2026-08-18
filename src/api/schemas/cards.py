from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class CardSummary(BaseModel):
    id: int
    game: str
    name_en: str
    name_pt: str | None = None
    set_code: str | None = None
    collector_number: str | None = None
    latest_price: Decimal | None = None

    model_config = ConfigDict(from_attributes=True)


class SourceCardSchema(BaseModel):
    source: str
    external_id: str
    sku: str | None = None
    url: str

    model_config = ConfigDict(from_attributes=True)


class CardDetail(BaseModel):
    id: int
    game: str
    name_en: str
    name_pt: str | None = None
    set_code: str | None = None
    collector_number: str | None = None
    latest_price: Decimal | None = None
    source_cards: list[SourceCardSchema] = []
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PriceObservation(BaseModel):
    observed_at: date
    median_price: Decimal | None = None
    tcg_price: Decimal | None = None
    last_sold_price: Decimal | None = None
    quantity_available: int | None = None
    currency: str = "BRL"


class CardListParams(BaseModel):
    game: str | None = None
    set: str | None = Field(default=None, alias="set")
    name: str | None = None
    cursor: str | None = None
    limit: int = Field(default=50, ge=1, le=200)


HistoryPeriod = Literal["30d", "90d", "180d", "1y", "3y"]


class HistoryParams(BaseModel):
    period: HistoryPeriod = "90d"
