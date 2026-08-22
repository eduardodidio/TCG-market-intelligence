"""Shared market data schemas used by multiple routers and features."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel


class CardPriceInfo(BaseModel):
    """Price info that can be embedded in any card representation."""

    card_id: int
    latest_price: Decimal | None = None
    price_date: date | None = None
    currency: str = "BRL"


class MarketCardSummary(BaseModel):
    """Card summary with market data -- shared base for consumer features."""

    card_id: int
    name_en: str
    name_pt: str | None = None
    set_code: str | None = None
    collector_number: str | None = None
    image_url: str | None = None
    price: CardPriceInfo | None = None


class MoverInfo(BaseModel):
    """Price movement data for a card over a period."""

    card_id: int
    name_en: str
    name_pt: str | None = None
    set_code: str | None = None
    price_start: Decimal | None = None
    price_end: Decimal | None = None
    change_pct: Decimal | None = None
    currency: str = "BRL"


class MarketSummary(BaseModel):
    """Pre-computed daily market summary."""

    total_cards: int
    total_observations: int
    avg_price: Decimal | None = None
    date_range_start: date | None = None
    date_range_end: date | None = None
    currency: str = "BRL"
    computed_at: datetime | None = None


class MoversResult(BaseModel):
    """Top movers response."""

    gainers: list[MoverInfo] = []
    losers: list[MoverInfo] = []
    period: str = "30d"
    currency: str = "BRL"
    computed_at: datetime | None = None
