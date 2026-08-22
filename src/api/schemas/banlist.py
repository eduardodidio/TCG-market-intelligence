"""Pydantic schemas for the banlist router."""

from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel


class BanListEntry(BaseModel):
    card_id: int
    name_en: str | None = None
    name_pt: str | None = None
    set_code: str | None = None
    collector_number: str | None = None
    format: str
    status: str
    effective_date: date | None = None
    image_url: str | None = None


class CardLegalitySchema(BaseModel):
    format: str
    status: str
    effective_date: date | None = None


class LegalityHistoryEntry(BaseModel):
    card_id: int
    name_en: str | None = None
    name_pt: str | None = None
    set_code: str | None = None
    collector_number: str | None = None
    format: str
    old_status: str | None = None
    new_status: str
    changed_at: datetime
    image_url: str | None = None


class LegalityHistoryResponse(BaseModel):
    items: list[LegalityHistoryEntry]
    total: int
    limit: int
    offset: int


class CardBanHistoryEntry(BaseModel):
    id: int
    format: str
    old_status: str | None = None
    new_status: str
    changed_at: datetime
    source: str


class BanImpactSchema(BaseModel):
    format: str
    old_status: str | None = None
    new_status: str
    changed_at: datetime
    window_days: int
    price_before: float | None = None
    price_after: float | None = None
    absolute_change: float | None = None
    percent_change: float | None = None
    data_available: bool


class SyncTriggerRequest(BaseModel):
    bulk: bool = True
    limit: int | None = None
