from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, field_validator

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
    is_foil: bool = False
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


class ValuationSnapshot(BaseModel):
    """A single portfolio snapshot data point."""

    date: str
    value: float | None = None
    priced_count: int = 0
    total_count: int = 0


class ValuationResponse(BaseModel):
    """Portfolio valuation with change calculation."""

    current_value: float | None = None
    previous_value: float | None = None
    change_pct: float | None = None
    change_abs: float | None = None
    currency: str = "BRL"
    snapshots: list[ValuationSnapshot] = []


class LigaStatusResponse(BaseModel):
    """Liga price coverage stats for a user's collection."""

    total_cards: int
    liga_priced: int
    liga_stale: int
    liga_missing: int
    unlinked: int
    coverage_pct: float
    last_liga_scan: str | None = None


# --- Batch collection management schemas ---

VALID_QUALITY_CODES = {"M", "NM", "SP", "MP", "HP", "D"}
VALID_LANGUAGE_CODES = {"BR", "EN", "DE", "ES", "FR", "IT", "JP", "KO", "RU", "TW"}


class CollectionUpdateRequest(BaseModel):
    """Partial update for a collection entry."""

    quantity: int | None = None
    quality: str | None = Field(None, pattern=r"^(M|NM|SP|MP|HP|D)$")
    language: str | None = Field(None, pattern=r"^(BR|EN|DE|ES|FR|IT|JP|KO|RU|TW)$")
    extras: str | None = None

    @field_validator("quantity")
    @classmethod
    def quantity_must_be_positive(cls, v: int | None) -> int | None:
        if v is not None and v < 1:
            msg = "quantity must be >= 1"
            raise ValueError(msg)
        return v


class BulkUpdateRequest(BaseModel):
    """Batch update for multiple collection entries."""

    ids: list[int]
    updates: CollectionUpdateRequest

    @field_validator("ids")
    @classmethod
    def ids_max_200(cls, v: list[int]) -> list[int]:
        if len(v) > 200:
            msg = "Maximum 200 entries per bulk operation"
            raise ValueError(msg)
        if len(v) == 0:
            msg = "ids must not be empty"
            raise ValueError(msg)
        return v


class BulkDeleteRequest(BaseModel):
    """Batch delete for multiple collection entries."""

    ids: list[int]

    @field_validator("ids")
    @classmethod
    def ids_max_200(cls, v: list[int]) -> list[int]:
        if len(v) > 200:
            msg = "Maximum 200 entries per bulk operation"
            raise ValueError(msg)
        if len(v) == 0:
            msg = "ids must not be empty"
            raise ValueError(msg)
        return v


class BulkUpdateResponse(BaseModel):
    """Response for bulk update operations."""

    affected: int


class BulkDeleteResponse(BaseModel):
    """Response for bulk delete operations."""

    deleted: int


# --- Batch add schemas ---


class BatchAddEntry(BaseModel):
    """A single card entry for batch add."""

    name_en: str
    set_code: str | None = None
    collector_number: str | None = None
    quantity: int = 1
    quality: str | None = None
    language: str | None = None
    extras: str | None = None

    @field_validator("quantity")
    @classmethod
    def quantity_must_be_positive(cls, v: int) -> int:
        if v < 1:
            msg = "quantity must be >= 1"
            raise ValueError(msg)
        return v

    @field_validator("quality")
    @classmethod
    def quality_must_be_valid(cls, v: str | None) -> str | None:
        if v is not None and v not in VALID_QUALITY_CODES:
            msg = f"quality must be one of {sorted(VALID_QUALITY_CODES)}"
            raise ValueError(msg)
        return v

    @field_validator("language")
    @classmethod
    def language_must_be_valid(cls, v: str | None) -> str | None:
        if v is not None and v not in VALID_LANGUAGE_CODES:
            msg = f"language must be one of {sorted(VALID_LANGUAGE_CODES)}"
            raise ValueError(msg)
        return v


class BatchParseRequest(BaseModel):
    """Request body for batch text parsing (preview)."""

    text: str


class ParsedLineResponse(BaseModel):
    """Parsed result of a single text line."""

    line_number: int
    raw_text: str
    quantity: int = 1
    name: str = ""
    set_code: str | None = None
    quality: str | None = None
    language: str | None = None
    extras: str | None = None
    error: str | None = None


class BatchParseResponse(BaseModel):
    """Response for batch text parsing."""

    entries: list[ParsedLineResponse]


class BatchAddRequest(BaseModel):
    """Request body for batch add."""

    entries: list[BatchAddEntry]

    @field_validator("entries")
    @classmethod
    def entries_max_500(cls, v: list[BatchAddEntry]) -> list[BatchAddEntry]:
        if len(v) > 500:
            msg = "Maximum 500 entries per batch"
            raise ValueError(msg)
        if len(v) == 0:
            msg = "entries must not be empty"
            raise ValueError(msg)
        return v


class BatchAddErrorResponse(BaseModel):
    """Error detail for a single failed entry."""

    line: int
    text: str
    error: str


class BatchAddResultResponse(BaseModel):
    """Response for batch add operation."""

    added: int
    errors: list[BatchAddErrorResponse] = []
