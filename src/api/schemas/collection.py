from __future__ import annotations

from pydantic import BaseModel, ConfigDict, field_validator

from src.api.schemas.cards import PriceChangeSummary, PriceObservation, SourceCardSchema


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
    price_source: str | None = None
    currency: str = "BRL"
    image_url: str | None = None

    model_config = ConfigDict(from_attributes=True)


class CollectionCardDetail(CollectionCard):
    """Extended detail view for a single collection entry."""

    price_history: list[PriceObservation] = []
    source_cards: list[SourceCardSchema] = []
    scryfall_url: str | None = None
    ligamagic_url: str | None = None


class CollectionHistoryResponse(BaseModel):
    observations: list[PriceObservation] = []
    summary: PriceChangeSummary | None = None


class CollectionSummary(BaseModel):
    total_unique: int
    total_cards: int
    total_value: float | None = None
    linked_count: int
    priced_count: int = 0
    sets_count: int
    currency: str = "BRL"
    banned_count: int = 0
    recently_changed_count: int = 0


class ImportResult(BaseModel):
    imported: int
    skipped: int
    linked: int
    total_csv_rows: int
    new_entry_ids: list[int] = []
    canonize_scheduled: bool = False


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


class ManualPriceRequest(BaseModel):
    """Request body for manual price entry."""

    price: float
    currency: str = "BRL"

    @field_validator("price")
    @classmethod
    def price_must_be_positive(cls, v: float) -> float:
        if v <= 0:
            msg = "price must be a positive number"
            raise ValueError(msg)
        if v > 99999.99:
            msg = "price must not exceed 99999.99"
            raise ValueError(msg)
        return v

    @field_validator("currency")
    @classmethod
    def currency_must_be_valid(cls, v: str) -> str:
        if v not in ("BRL", "USD", "PILA"):
            msg = "currency must be BRL, USD, or PILA"
            raise ValueError(msg)
        return v


class BulkCanonizeResult(BaseModel):
    """Summary of a bulk canonize run."""

    total: int
    canonized: int
    failed: int
    skipped: int
    rate_limited: int


class LigaStatusResponse(BaseModel):
    """Liga price coverage stats for a user's collection."""

    total_cards: int
    liga_priced: int
    liga_stale: int
    liga_missing: int
    unlinked: int
    coverage_pct: float
    last_liga_scan: str | None = None
