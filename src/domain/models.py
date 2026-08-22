from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from enum import Enum


class Game(str, Enum):
    MAGIC = "magic"
    POKEMON = "pokemon"
    YUGIOH = "yugioh"


class Currency(str, Enum):
    BRL = "BRL"
    USD = "USD"
    PILA = "PILA"


class Condition(str, Enum):
    NM = "NM"
    SP = "SP"
    MP = "MP"
    HP = "HP"
    DMG = "DMG"


class Finish(str, Enum):
    NORMAL = "normal"
    FOIL = "foil"
    ETCHED = "etched"


@dataclass
class CardIdentity:
    """Unique identity of a card across sources."""

    game: str
    name_en: str
    name_pt: str | None = None
    set_code: str | None = None
    collector_number: str | None = None


@dataclass
class SourceCard:
    """A card as seen by a specific source/provider."""

    source: str
    external_id: str
    url: str
    sku: str | None = None
    identity: CardIdentity | None = None


@dataclass
class PriceSnapshot:
    """Current price data for a card from a source."""

    source: str
    external_id: str
    observed_at: datetime
    min_price: Decimal | None = None
    avg_price: Decimal | None = None
    tcg_price: Decimal | None = None
    last_sold_price: Decimal | None = None
    quantity_available: int | None = None
    currency: str = "BRL"


@dataclass
class HistoricalPrice:
    """A single historical price observation (immutable)."""

    source: str
    external_id: str
    observed_at: date
    median_price: Decimal | None = None
    tcg_price: Decimal | None = None
    last_sold_price: Decimal | None = None
    quantity_available: int | None = None
    last_sold_meta: str | None = None
    currency: str = "BRL"


@dataclass
class CollectionError:
    """Record of a failed collection attempt."""

    source: str
    external_id: str | None
    url: str
    error_type: str
    error_message: str
    http_status: int | None = None
    timestamp: datetime = field(default_factory=datetime.now)
    attempt: int = 1


@dataclass
class CollectionSummary:
    """Summary of a collection run."""

    cards_discovered: int = 0
    cards_processed: int = 0
    cards_failed: int = 0
    observations_saved: int = 0
    errors: list[CollectionError] = field(default_factory=list)
    started_at: datetime = field(default_factory=datetime.now)
    finished_at: datetime | None = None


# --- Analytics domain models ---


@dataclass
class MovingAverage:
    """Result of a moving average calculation over a price series."""

    period: int
    value: Decimal
    price_field: str
    calculated_at: date


@dataclass
class PriceExtremes:
    """All-time high and all-time low for a price field."""

    ath_price: Decimal
    ath_date: date
    atl_price: Decimal
    atl_date: date
    price_field: str


@dataclass
class Volatility:
    """Price volatility metrics over a given period."""

    period_days: int
    std_dev: Decimal
    coefficient_of_variation: Decimal
    price_field: str


@dataclass
class Momentum:
    """Price momentum / rate of change over a given period."""

    period_days: int
    rate_of_change: Decimal
    trend_direction: str
    price_field: str


@dataclass
class MypSearchResult:
    """A single result from the MYP search API."""

    external_id: str
    name: str
    slug: str
    url: str
    sku: str | None = None
    set_code: str | None = None
    collector_number: str | None = None
    image_url: str | None = None


@dataclass
class JsonLdPrice:
    """Price extracted from JSON-LD offers block on a product page."""

    price: Decimal | None
    currency: str = "BRL"
    availability: str = "Unknown"  # "InStock" | "OutOfStock" | "Unknown"


@dataclass
class PerformanceScore:
    """Composite performance indicator for a price series."""

    score: int  # 0-100
    label: str  # "strong" | "moderate" | "weak" | "declining"
    period_days: int
    price_field: str


@dataclass
class PeriodComparison:
    """Current period vs previous period of equal length."""

    current_avg: Decimal
    previous_avg: Decimal
    delta: Decimal
    delta_pct: Decimal
    period_days: int
    price_field: str


@dataclass
class CardAnalytics:
    """Composite analytics result for a single card."""

    external_id: str
    source: str
    moving_averages: list[MovingAverage] = field(default_factory=list)
    extremes: PriceExtremes | None = None
    volatility: Volatility | None = None
    momentum: Momentum | None = None
    performance: PerformanceScore | None = None
    period_comparison: PeriodComparison | None = None
    computed_at: datetime = field(default_factory=datetime.now)


# --- Collection sync domain models ---


@dataclass
class SyncError:
    """Record of an error during collection sync."""

    entry_id: int
    name_en: str | None
    set_code: str
    collector_number: str
    error_type: str
    error_message: str


@dataclass
class SyncResult:
    """Outcome of syncing a single collection entry."""

    entry_id: int
    name_en: str | None
    set_code: str
    collector_number: str
    status: str  # "synced" | "unmatched" | "ambiguous" | "skipped" | "error" | "no_name"
    card_id: int | None = None
    observations_count: int = 0
    match_confidence: str | None = None
    error_message: str | None = None


@dataclass
class SyncSummary:
    """Summary of a collection sync run."""

    total_entries: int = 0
    skipped_already_linked: int = 0
    searched: int = 0
    matched: int = 0
    ambiguous: int = 0
    unmatched: int = 0
    cards_created: int = 0
    observations_saved: int = 0
    errors: list[SyncError] = field(default_factory=list)
    results: list[SyncResult] = field(default_factory=list)
    started_at: datetime = field(default_factory=datetime.now)
    finished_at: datetime | None = None


# --- JSON-LD snapshot domain models ---


@dataclass
class SnapshotSummary:
    """Summary of a price snapshot run."""

    total_entries: int = 0
    fetched: int = 0
    stored: int = 0
    skipped_existing: int = 0
    skipped_zero_price: int = 0
    errors: int = 0
    error_details: list[CollectionError] = field(default_factory=list)
    started_at: datetime = field(default_factory=datetime.now)
    finished_at: datetime | None = None


# --- Collection scan domain models ---


class ScanStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ScanType(str, Enum):
    COLLECTION = "collection"
    SET = "set"
    FORMAT = "format"
    CUSTOM = "custom"


@dataclass
class ScanFilter:
    """Filter criteria for a collection scan run."""

    scan_type: ScanType = ScanType.COLLECTION
    set_codes: list[str] | None = None
    format_name: str | None = None
    rarities: list[str] | None = None
    card_ids: list[int] | None = None
    collection_only: bool = True
    limit: int | None = None

    def to_json(self) -> str:
        import json

        return json.dumps(
            {
                "scan_type": self.scan_type.value,
                "set_codes": self.set_codes,
                "format_name": self.format_name,
                "rarities": self.rarities,
                "card_ids": self.card_ids,
                "collection_only": self.collection_only,
                "limit": self.limit,
            }
        )

    @classmethod
    def from_json(cls, raw: str) -> "ScanFilter":
        import json

        data = json.loads(raw)
        return cls(
            scan_type=ScanType(data.get("scan_type", "collection")),
            set_codes=data.get("set_codes"),
            format_name=data.get("format_name"),
            rarities=data.get("rarities"),
            card_ids=data.get("card_ids"),
            collection_only=data.get("collection_only", True),
            limit=data.get("limit"),
        )


@dataclass
class ScanRun:
    """State of a single collection scan execution."""

    id: int | None = None
    scan_type: str = "collection"
    filters_json: str = "{}"
    status: str = "pending"
    cards_total: int = 0
    cards_processed: int = 0
    cards_failed: int = 0
    observations_saved: int = 0
    error_summary: str | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None


# --- Exchange rate / multi-currency domain models ---


@dataclass
class ExchangeRate:
    """A single exchange rate observation (e.g. USD->BRL)."""

    rate_date: date
    from_currency: str = "USD"
    to_currency: str = "BRL"
    rate: Decimal = Decimal("0")
    source: str = "bcb_ptax"


@dataclass
class ConvertedPrice:
    """Price converted to a target currency at a specific exchange rate."""

    value: Decimal | None
    currency: str
    exchange_rate: Decimal | None = None
    rate_date: date | None = None


# --- Authentication domain models ---


class LegalityStatus(str, Enum):
    LEGAL = "legal"
    NOT_LEGAL = "not_legal"
    BANNED = "banned"
    RESTRICTED = "restricted"


@dataclass
class CardLegality:
    """Legality of a card in a specific format."""

    card_id: int
    format: str
    status: str
    effective_date: date | None = None


@dataclass
class LegalityChange:
    """Record of a legality status change."""

    card_id: int
    format: str
    old_status: str | None
    new_status: str
    changed_at: datetime = field(default_factory=datetime.now)
    source: str = "scryfall_sync"


@dataclass
class BanlistSyncSummary:
    """Summary of a ban list sync run."""

    cards_processed: int = 0
    legalities_upserted: int = 0
    changes_detected: int = 0
    errors: int = 0
    started_at: datetime = field(default_factory=datetime.now)
    finished_at: datetime | None = None


class AuthProvider(str, Enum):
    EMAIL = "email"
    GOOGLE = "google"
    MICROSOFT = "microsoft"
    APPLE = "apple"


@dataclass
class User:
    """Authenticated user."""

    id: int
    email: str
    display_name: str | None = None
    avatar_url: str | None = None
    auth_provider: str = "email"
    preferred_currency: str = "BRL"
    preferred_language: str = "en"
    is_active: bool = True


# --- Scheduled scan domain models ---


class ScheduleStatus(str, Enum):
    ACTIVE = "active"
    PAUSED = "paused"
    DISABLED = "disabled"


@dataclass
class ScheduledScan:
    """Configuration for a recurring price scan schedule."""

    id: int | None = None
    name: str = ""
    description: str | None = None
    cron_expression: str = "0 6 * * *"
    scan_type: str = "collection"
    filters_json: str = "{}"
    status: str = "active"
    last_run_id: int | None = None
    last_run_at: datetime | None = None
    next_run_at: datetime | None = None
    error_count: int = 0
    max_retries: int = 3
    created_at: datetime | None = None
    updated_at: datetime | None = None


# --- Ban impact analysis domain models ---


@dataclass
class BanImpactAnalysis:
    """Price impact analysis around a ban/unban event (stub)."""

    card_id: int
    format: str
    old_status: str | None
    new_status: str
    changed_at: datetime
    window_days: int = 7
    price_before: float | None = None
    price_after: float | None = None
    absolute_change: float | None = None
    percent_change: float | None = None
    data_available: bool = False


# --- Deck valuation domain models ---


@dataclass
class DeckValuation:
    """Result of computing a deck's total value from card prices."""

    total_value: Decimal | None
    priced_cards: int
    unpriced_cards: int


@dataclass
class DeckValuePoint:
    """A single point in a deck value time series."""

    date: date
    total_value: Decimal


@dataclass
class DeckValueChange:
    """Value change between two points in time."""

    current: Decimal
    previous: Decimal
    delta: Decimal
    delta_pct: Decimal


# --- Deck domain models ---


@dataclass
class DeckSummary:
    """Summary view of a user deck."""

    id: int
    name: str
    description: str | None = None
    total_cards: int = 0
    unique_cards: int = 0
    owned_cards: int = 0
    ownership_pct: float = 0.0
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)


@dataclass
class TrendingScore:
    """Composite trending score for a single card over a period."""

    card_id: int
    change_pct: Decimal  # raw % change (positive or negative)
    change_abs: Decimal  # absolute price change
    consistency: Decimal  # 0-1, fraction of daily deltas in same direction
    observation_count: int  # data points in the period window
    observation_density: Decimal  # observation_count / period_days (0-1, capped)
    composite_score: Decimal  # weighted score 0-100
    direction: str  # "up" | "down"
    price_start: Decimal
    price_end: Decimal
    latest_date: date  # date of most recent observation


@dataclass
class DeckCardDetail:
    """A single card within a deck, with ownership info."""

    id: int
    name_en: str
    set_code: str | None = None
    collector_number: str | None = None
    quantity: int = 1
    card_id: int | None = None
    in_collection: bool = False
    owned_quantity: int = 0
    collection_entry_id: int | None = None
    image_url: str | None = None
    latest_price: float | None = None
