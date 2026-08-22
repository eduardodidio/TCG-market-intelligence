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
    format: str
    old_status: str | None = None
    new_status: str
    changed_at: datetime


class SyncTriggerRequest(BaseModel):
    bulk: bool = True
    limit: int | None = None
