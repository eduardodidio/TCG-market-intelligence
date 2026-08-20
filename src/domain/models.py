from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from enum import Enum


class Game(str, Enum):
    MAGIC = "magic"
    POKEMON = "pokemon"
    YUGIOH = "yugioh"


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
class CardAnalytics:
    """Composite analytics result for a single card."""

    external_id: str
    source: str
    moving_averages: list[MovingAverage] = field(default_factory=list)
    extremes: PriceExtremes | None = None
    volatility: Volatility | None = None
    momentum: Momentum | None = None
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
