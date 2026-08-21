from __future__ import annotations

from pydantic import BaseModel, ConfigDict, field_validator

from src.api.schemas.cards import PriceObservation, SourceCardSchema


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
    latest_price: float | None = None
    image_url: str | None = None

    model_config = ConfigDict(from_attributes=True)


class CollectionCardDetail(CollectionCard):
    """Extended detail view for a single collection entry."""

    price_history: list[PriceObservation] = []
    source_cards: list[SourceCardSchema] = []
    scryfall_url: str | None = None
    ligamagic_url: str | None = None


class CollectionSummary(BaseModel):
    total_unique: int
    total_cards: int
    total_value: float | None = None
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


class SnapshotRequest(BaseModel):
    limit: int | None = None
    dry_run: bool = False

    @field_validator("limit")
    @classmethod
    def limit_must_be_positive(cls, v: int | None) -> int | None:
        if v is not None and v <= 0:
            msg = "limit must be a positive integer"
            raise ValueError(msg)
        return v
