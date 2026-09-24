"""Pure history-key resolution and per-day merge for collection price charts.

A collection entry's price history is spread over several series
(``source`` + ``external_id``) that are not all linked through
``source_cards``:

* Liga sweep / refresh / scan write ``liga/liga_{card_id}`` and
  ``liga/liga_{card_id}_foil`` directly (no ``source_cards`` row).
* Manual prices live under ``manual/manual_{card_id}``.
* ``source_cards`` link MYP (``myp/<id>``) and the Liga catalog
  (``liga/liga_catalog_{set}_{num}``); MYP JSON-LD snapshots reuse the
  same ``external_id`` under ``jsonld_snapshot``.
* The daily carry-forward (F168) writes ``daily_snapshot`` rows reusing
  the ``external_id`` of the series it copied.

This module decides which of those series belong to one variant
(foil / normal) and collapses them to at most one point per day by source
priority.  It has no DB or framework imports so it can be unit-tested in
isolation (see ``src/collection/matcher.py`` for the same pattern).

Contract: ``tasks/features/F176-collection-price-history/_brief/02-key-resolution.md``.
Diagnosis (F176-T01) confirmed the contract unchanged: a source_card is
foil only when its ``external_id`` ends with ``_foil``; MYP without that
suffix stays out of the foil series.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date

from src.domain.models import HistoricalPrice

# Same value as ``src.collectors.price_snapshot.SNAPSHOT_SOURCE``; not imported
# to keep this module free of collector/DB dependencies (a test asserts equality).
SNAPSHOT_SOURCE = "daily_snapshot"

# Mirrors ``Repository.SOURCE_PRIORITY`` (src/database/repository.py) — keep in
# sync.  Lower wins.  ``daily_snapshot`` is a carry-forward of the other
# sources, so it only fills days that have no real observation.
SOURCE_PRIORITY: dict[str, int] = {
    "manual": 0,
    "liga": 1,
    "jsonld_snapshot": 2,
    "myp": 3,
    SNAPSHOT_SOURCE: 9,
}
UNKNOWN_SOURCE_PRIORITY = 5

_FOIL_SUFFIX = "_foil"


@dataclass(frozen=True)
class SeriesKey:
    """Identifies one stored price series."""

    source: str
    external_id: str


def source_priority(source: str) -> int:
    """Return the merge priority of *source* (lower wins)."""
    return SOURCE_PRIORITY.get(source, UNKNOWN_SOURCE_PRIORITY)


def resolve_history_keys(
    card_id: int,
    source_cards: Iterable[tuple[str, str]],
    is_foil: bool,
) -> list[SeriesKey]:
    """Return the series that make up the history of one card variant.

    Order is deterministic (direct Liga, manual, then ``source_cards`` in
    the given order) and duplicates are removed.  Foil and normal series
    never mix: the foil variant uses ``liga_{id}_foil`` and ``_foil``
    source_cards only; the normal variant excludes both.

    Raises:
        ValueError: if *card_id* is not a positive integer.
    """
    if isinstance(card_id, bool) or not isinstance(card_id, int) or card_id <= 0:
        raise ValueError(f"card_id must be a positive integer, got {card_id!r}")

    liga_id = f"liga_{card_id}{_FOIL_SUFFIX}" if is_foil else f"liga_{card_id}"
    manual_id = f"manual_{card_id}"

    keys: list[SeriesKey] = [
        SeriesKey("liga", liga_id),
        SeriesKey(SNAPSHOT_SOURCE, liga_id),
        SeriesKey("manual", manual_id),
        SeriesKey(SNAPSHOT_SOURCE, manual_id),
    ]
    for source, external_id in source_cards:
        if external_id.endswith(_FOIL_SUFFIX) != is_foil:
            continue
        keys.append(SeriesKey(source, external_id))
        keys.append(SeriesKey("jsonld_snapshot", external_id))
        keys.append(SeriesKey(SNAPSHOT_SOURCE, external_id))

    return list(dict.fromkeys(keys))


def merge_series_by_priority(
    observations: Iterable[HistoricalPrice],
) -> list[HistoricalPrice]:
    """Collapse observations to at most one per day, ascending by date.

    Observations without ``median_price`` are ignored.  For each day the
    observation with the lowest :func:`source_priority` wins; ties are
    broken by the lexicographically smallest ``external_id``.
    """
    best: dict[date, HistoricalPrice] = {}
    for obs in observations:
        if obs.median_price is None:
            continue
        current = best.get(obs.observed_at)
        if current is None or _rank(obs) < _rank(current):
            best[obs.observed_at] = obs
    return [best[day] for day in sorted(best)]


def _rank(obs: HistoricalPrice) -> tuple[int, str]:
    return (source_priority(obs.source), obs.external_id)
