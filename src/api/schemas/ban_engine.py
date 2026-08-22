"""Pydantic schemas for the ban engine (F42)."""

from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel


class BannedCollectionCard(BaseModel):
    entry_id: int
    card_id: int
    name_en: str | None = None
    name_pt: str | None = None
    set_code: str
    collector_number: str
    quantity: int
    format: str
    status: str  # "banned" | "restricted"
    effective_date: date | None = None
    recently_changed: bool = False
    change_date: datetime | None = None
    image_url: str | None = None


class BanSummary(BaseModel):
    banned_count: int
    restricted_count: int
    recently_changed_count: int
    formats_affected: list[str]


class CardLegalityWithChange(BaseModel):
    format: str
    status: str
    effective_date: date | None = None
    recently_changed: bool = False
    change_date: datetime | None = None
    old_status: str | None = None
