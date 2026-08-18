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
