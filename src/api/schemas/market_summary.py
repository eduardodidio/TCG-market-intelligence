"""Pydantic schemas for the market summary endpoint (F40)."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class MarketSummaryResponse(BaseModel):
    total_cards_tracked: int
    total_observations: int
    avg_price: float | None
    avg_price_change_pct: float | None
    gainers_count: int
    losers_count: int
    unchanged_count: int
    market_direction: str  # "up" | "down" | "flat"
    period: str
    currency: str
    computed_at: datetime
