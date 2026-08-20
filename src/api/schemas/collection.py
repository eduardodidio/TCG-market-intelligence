from __future__ import annotations

from decimal import Decimal

from pydantic import BaseModel, ConfigDict


class CollectionCard(BaseModel):
    id: int
    card_id: int | None = None
    set_code: str
    collector_number: str
    name_en: str | None = None
    name_pt: str | None = None
    set_name_en: str | None = None
    quantity: int = 1
    quality: str | None = None
    language: str | None = None
    rarity: str | None = None
    color: str | None = None
    extras: str | None = None
    latest_price: Decimal | None = None
    image_url: str | None = None

    model_config = ConfigDict(from_attributes=True)


class CollectionSummary(BaseModel):
    total_unique: int
    total_cards: int
    total_value: Decimal | None = None
    linked_count: int
    sets_count: int


class ImportResult(BaseModel):
    imported: int
    skipped: int
    linked: int
    total_csv_rows: int


class SyncRequest(BaseModel):
    limit: int | None = None
    history_days: int = 365
    force: bool = False  # if True, re-sync already-linked entries
