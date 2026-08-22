"""Pydantic schemas for the trending cards API (F36)."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class TrendingCardEntry(BaseModel):
    card_id: int
    name_en: str
    name_pt: str | None = None
    set_code: str | None = None
    collector_number: str | None = None
    image_url: str | None = None
    price_start: float
    price_end: float
    change_pct: float
    change_abs: float
    consistency: float  # 0.0-1.0
    composite_score: float  # 0-100
    observation_count: int
    currency: str = "BRL"


class TrendingResponse(BaseModel):
    cards: list[TrendingCardEntry] = []
    period: str  # "7d" | "30d" | "90d"
    direction: str  # "up" | "down"
    computed_at: datetime
    cached: bool = False
