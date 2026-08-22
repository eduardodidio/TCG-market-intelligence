"""Pydantic schemas for deck ranking and value endpoints."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class DeckRankingEntry(BaseModel):
    id: int
    name: str
    description: str | None = None
    total_cards: int
    unique_cards: int
    owned_cards: int
    ownership_pct: float
    total_value: float | None
    priced_cards: int
    unpriced_cards: int
    value_change: float | None
    value_change_pct: float | None
    sparkline: list[float]
    currency: str
    created_at: datetime
    updated_at: datetime


class DeckRankingResponse(BaseModel):
    decks: list[DeckRankingEntry]
    total: int
    sort_by: str
    period: str


class DeckValuePointSchema(BaseModel):
    date: str
    value: float


class DeckValueDetailSchema(BaseModel):
    deck_id: int
    total_value: float | None
    priced_cards: int
    unpriced_cards: int
    value_change: float | None
    value_change_pct: float | None
    value_series: list[DeckValuePointSchema]
    currency: str
    period: str
