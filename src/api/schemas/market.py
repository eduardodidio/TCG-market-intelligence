from __future__ import annotations

from datetime import date
from decimal import Decimal

from pydantic import BaseModel


class MoverEntry(BaseModel):
    card_id: int
    name_en: str
    set_code: str | None = None
    price_start: Decimal
    price_end: Decimal
    change_pct: Decimal
    currency: str = "BRL"


class MoversResponse(BaseModel):
    gainers: list[MoverEntry] = []
    losers: list[MoverEntry] = []


class MarketStats(BaseModel):
    total_cards: int
    total_observations: int
    avg_price: Decimal | None = None
    date_range_start: date | None = None
    date_range_end: date | None = None
    currency: str = "BRL"
