"""Pydantic schemas for exchange rate endpoints."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel


class ExchangeRateSchema(BaseModel):
    rate_date: date
    from_currency: str = "USD"
    to_currency: str = "BRL"
    rate: Decimal
    source: str = "bcb_ptax"
    created_at: datetime | None = None


class ExchangeRateHistorySchema(BaseModel):
    rates: list[ExchangeRateSchema]
    count: int
