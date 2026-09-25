"""Source contract for metagame adapters (F173-T04)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Literal, Protocol

FORMATS: tuple[str, ...] = (
    "commander",
    "standard",
    "pioneer",
    "modern",
    "legacy",
    "vintage",
    "pauper",
)

_WUBRG = "WUBRG"


@dataclass(frozen=True)
class MetaCardEntry:
    name: str
    quantity: int
    board: Literal["main", "side", "commander"] = "main"
    set_code: str | None = None
    collector_number: str | None = None


@dataclass(frozen=True)
class MetaDeckEntry:
    source: str
    format: str
    external_id: str
    archetype: str
    rank: int
    meta_share_pct: Decimal | None
    deck_count: int | None
    colors: str | None
    commander_name: str | None
    source_url: str
    event_date: date | None
    cards: tuple[MetaCardEntry, ...]


class MetaSource(Protocol):
    name: str
    formats: tuple[str, ...]

    def fetch_top_decks(self, fmt: str, *, limit: int = 20) -> list[MetaDeckEntry]: ...


def normalize_colors(colors: str | None) -> str | None:
    """Return the WUBRG letters in ``colors`` in canonical order, uppercase, deduped.

    Non-WUBRG characters (e.g. ``C``, separators) are dropped. Empty/None → None.
    """
    if not colors:
        return None
    present = set(colors.upper())
    result = "".join(c for c in _WUBRG if c in present)
    return result or None
