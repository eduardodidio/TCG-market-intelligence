"""Pydantic schemas for card analytics metrics (F34)."""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel


class MovingAverageSchema(BaseModel):
    period: int
    value: float


class PriceExtremesSchema(BaseModel):
    ath_price: float
    ath_date: date
    atl_price: float
    atl_date: date


class VolatilitySchema(BaseModel):
    period_days: int
    std_dev: float
    coefficient_of_variation: float


class MomentumSchema(BaseModel):
    period_days: int
    rate_of_change: float
    trend_direction: str


class PerformanceScoreSchema(BaseModel):
    score: int
    label: str
    period_days: int


class PeriodComparisonSchema(BaseModel):
    current_avg: float
    previous_avg: float
    delta: float
    delta_pct: float
    period_days: int


class CardMetricsResponse(BaseModel):
    entry_id: int
    card_id: int
    period: str
    currency: str
    moving_averages: list[MovingAverageSchema] = []
    extremes: PriceExtremesSchema | None = None
    volatility: VolatilitySchema | None = None
    momentum: MomentumSchema | None = None
    performance: PerformanceScoreSchema | None = None
    period_comparison: PeriodComparisonSchema | None = None
    data_points: int = 0
