"""Card-level price history service: variant resolution, 1-point-per-day aggregation, diagnostics.

Resolves all external_id patterns that map to a card_id across sources
(liga, manual, myp, jsonld_snapshot, daily_snapshot, source_cards) and
returns a deduplicated, priority-merged timeline with at most one price
point per calendar day.

This module sits above ``src.collection.price_history_keys`` (pure logic)
and ``src.database.repository`` (data access).  It is intended for
card-detail endpoints that are not foil-aware (the collection-level
variant-aware history lives in ``src.services.collection_price_history``).
"""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any

from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import Session

from src.collection.price_history_keys import (
    BACKFILL_SOURCE,
    SNAPSHOT_SOURCE,
    SeriesKey,
)
from src.database.models import PriceObservationRow
from src.database.repository import Repository
from src.domain.models import HistoricalPrice

# Carry-forward sources (never count as "real" observations).
_SNAPSHOT_SOURCES = frozenset({SNAPSHOT_SOURCE, BACKFILL_SOURCE})

# Source priority for same-day dedup (lower wins).
# Mirrors price_history_keys.SOURCE_PRIORITY but adds liga between
# jsonld_snapshot and daily_snapshot for the card-level view.
SOURCE_PRIORITY: dict[str, int] = {
    "manual": 0,
    "liga": 1,
    "jsonld_snapshot": 2,
    "myp": 3,
    SNAPSHOT_SOURCE: 9,
    BACKFILL_SOURCE: 9,
}
_UNKNOWN_PRIORITY = 5


def _priority(source: str) -> int:
    return SOURCE_PRIORITY.get(source, _UNKNOWN_PRIORITY)


# ------------------------------------------------------------------
# 1) Variant ID resolution
# ------------------------------------------------------------------


def resolve_variant_ids(card_id: int, repo: Repository) -> list[str]:
    """Return every ``external_id`` that may carry price data for *card_id*.

    The returned list is deduplicated and deterministic.  It includes:
    - ``liga_{card_id}`` / ``liga_{card_id}_foil``
    - ``manual_{card_id}``
    - ``myp_{card_id}`` / ``myp_{card_id}_foil``
    - All ``external_id`` values from ``source_cards`` linked to *card_id*
    """
    if isinstance(card_id, bool) or not isinstance(card_id, int) or card_id <= 0:
        raise ValueError(f"card_id must be a positive integer, got {card_id!r}")

    ids: list[str] = [
        f"liga_{card_id}",
        f"liga_{card_id}_foil",
        f"manual_{card_id}",
        f"myp_{card_id}",
        f"myp_{card_id}_foil",
    ]

    source_cards = repo.get_source_cards_for_card(card_id)
    for sc in source_cards:
        if sc.external_id not in ids:
            ids.append(sc.external_id)

    return ids


# ------------------------------------------------------------------
# 2) Price history (1 point per day)
# ------------------------------------------------------------------


def _build_keys_for_card(card_id: int, repo: Repository) -> list[SeriesKey]:
    """Build every ``(source, external_id)`` pair we should query."""
    keys: list[SeriesKey] = []

    liga_id = f"liga_{card_id}"
    liga_foil = f"liga_{card_id}_foil"
    manual_id = f"manual_{card_id}"
    myp_id = f"myp_{card_id}"
    myp_foil = f"myp_{card_id}_foil"

    # Direct patterns
    for ext in (liga_id, liga_foil):
        keys.append(SeriesKey("liga", ext))
        keys.append(SeriesKey(SNAPSHOT_SOURCE, ext))
        keys.append(SeriesKey(BACKFILL_SOURCE, ext))

    keys.append(SeriesKey("manual", manual_id))
    keys.append(SeriesKey(SNAPSHOT_SOURCE, manual_id))
    keys.append(SeriesKey(BACKFILL_SOURCE, manual_id))

    for ext in (myp_id, myp_foil):
        keys.append(SeriesKey("myp", ext))
        keys.append(SeriesKey(SNAPSHOT_SOURCE, ext))
        keys.append(SeriesKey(BACKFILL_SOURCE, ext))

    # source_cards linked to this card
    source_cards = repo.get_source_cards_for_card(card_id)
    for sc in source_cards:
        keys.append(SeriesKey(sc.source, sc.external_id))
        keys.append(SeriesKey("jsonld_snapshot", sc.external_id))
        keys.append(SeriesKey(SNAPSHOT_SOURCE, sc.external_id))
        keys.append(SeriesKey(BACKFILL_SOURCE, sc.external_id))

    # Deduplicate while preserving order
    return list(dict.fromkeys(keys))


def _keys_filter(keys: list[SeriesKey]):
    """Build an OR filter over all (source, external_id) pairs."""
    return or_(
        *[
            and_(
                PriceObservationRow.source == k.source,
                PriceObservationRow.external_id == k.external_id,
            )
            for k in keys
        ]
    )


def _load_observations(
    repo: Repository,
    keys: list[SeriesKey],
    days: int | None,
    today: date | None = None,
) -> list[HistoricalPrice]:
    """Load all price observations matching *keys*, optionally filtered by date range."""
    if not keys:
        return []

    stmt = (
        select(PriceObservationRow)
        .where(_keys_filter(keys))
        .order_by(PriceObservationRow.observed_at.asc())
    )
    if days is not None:
        cutoff = (today or date.today()) - timedelta(days=days)
        stmt = stmt.where(PriceObservationRow.observed_at >= cutoff)

    with Session(repo.engine) as session:
        rows = session.execute(stmt).scalars().all()
        return [
            HistoricalPrice(
                source=r.source,
                external_id=r.external_id,
                observed_at=r.observed_at,
                median_price=r.median_price,
                tcg_price=r.tcg_price,
                last_sold_price=r.last_sold_price,
                quantity_available=r.quantity_available,
                last_sold_meta=r.last_sold_meta,
                currency=r.currency,
            )
            for r in rows
        ]


def _merge_one_per_day(observations: list[HistoricalPrice]) -> list[dict]:
    """Collapse to 1 point per day, keeping the highest-priority source.

    Returns a list of dicts sorted by date ASC:
    ``[{"date": "2026-11-24", "price": 12.50, "source": "liga"}, ...]``
    """
    best: dict[date, HistoricalPrice] = {}
    for obs in observations:
        if obs.median_price is None:
            continue
        current = best.get(obs.observed_at)
        if current is None or _rank(obs) < _rank(current):
            best[obs.observed_at] = obs

    return [
        {
            "date": day.isoformat(),
            "price": float(best[day].median_price),
            "source": best[day].source,
        }
        for day in sorted(best)
    ]


def _rank(obs: HistoricalPrice) -> tuple[int, str]:
    return (_priority(obs.source), obs.external_id)


def get_price_history(
    card_id: int,
    repo: Repository,
    days: int = 90,
    today: date | None = None,
) -> list[dict]:
    """Return 1 price point per day for *card_id*, sorted by date ASC.

    Each element: ``{"date": "YYYY-MM-DD", "price": <float>, "source": "<src>"}``
    """
    keys = _build_keys_for_card(card_id, repo)
    observations = _load_observations(repo, keys, days, today=today)
    return _merge_one_per_day(observations)


# ------------------------------------------------------------------
# 3) Price diagnostics
# ------------------------------------------------------------------


def get_price_diagnostics(
    card_id: int,
    repo: Repository,
) -> dict[str, Any]:
    """Return diagnostic info about all price observations for *card_id*.

    Returns:
        {
            "total_observations": int,
            "by_source": {"liga": 5, "myp": 10, ...},
            "first_seen": "YYYY-MM-DD" | None,
            "last_seen": "YYYY-MM-DD" | None,
            "days_with_data": int,
            "total_days_in_range": int,
        }
    """
    keys = _build_keys_for_card(card_id, repo)
    if not keys:
        return _empty_diagnostics()

    with Session(repo.engine) as session:
        # Total count
        total_stmt = select(func.count(PriceObservationRow.id)).where(
            _keys_filter(keys),
            PriceObservationRow.median_price.is_not(None),
        )
        total = session.execute(total_stmt).scalar() or 0

        if total == 0:
            return _empty_diagnostics()

        # By source
        source_stmt = (
            select(
                PriceObservationRow.source,
                func.count(PriceObservationRow.id).label("cnt"),
            )
            .where(
                _keys_filter(keys),
                PriceObservationRow.median_price.is_not(None),
            )
            .group_by(PriceObservationRow.source)
        )
        by_source = {row[0]: row[1] for row in session.execute(source_stmt).all()}

        # Date range
        range_stmt = select(
            func.min(PriceObservationRow.observed_at).label("first"),
            func.max(PriceObservationRow.observed_at).label("last"),
        ).where(
            _keys_filter(keys),
            PriceObservationRow.median_price.is_not(None),
        )
        range_row = session.execute(range_stmt).one()
        first_seen = range_row[0]
        last_seen = range_row[1]

        # Distinct days with data
        days_stmt = select(func.count(func.distinct(PriceObservationRow.observed_at))).where(
            _keys_filter(keys),
            PriceObservationRow.median_price.is_not(None),
        )
        days_with_data = session.execute(days_stmt).scalar() or 0

        total_days_in_range = 0
        if first_seen and last_seen:
            total_days_in_range = (last_seen - first_seen).days + 1

    return {
        "total_observations": total,
        "by_source": by_source,
        "first_seen": first_seen.isoformat() if first_seen else None,
        "last_seen": last_seen.isoformat() if last_seen else None,
        "days_with_data": days_with_data,
        "total_days_in_range": total_days_in_range,
    }


def _empty_diagnostics() -> dict[str, Any]:
    return {
        "total_observations": 0,
        "by_source": {},
        "first_seen": None,
        "last_seen": None,
        "days_with_data": 0,
        "total_days_in_range": 0,
    }
