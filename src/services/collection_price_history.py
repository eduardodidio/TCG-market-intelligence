"""Collection price history: load, merge and describe one card variant's series.

Single source of truth for the collection history, collection metrics and
card history endpoints (F176).  Key resolution and the per-day merge live in
the pure module :mod:`src.collection.price_history_keys`; this service only
adds the database reads.  Queries go through ``Session(repo.engine)`` so
``repository.py`` stays untouched (same pattern as
``src/collectors/portfolio_backfill.py``).

``meta`` is returned as a plain dict compatible with
``src.api.schemas.collection.PriceHistoryMeta`` — the router builds the
schema, the service layer does not depend on the API layer.

Contract: ``tasks/features/F176-collection-price-history/_brief/04-api-ui.md``
and ADR 0017.
"""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any

from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import Session

from src.collection.price_history_keys import (
    SNAPSHOT_SOURCE,
    SeriesKey,
    merge_series_by_priority,
    resolve_history_keys,
    source_priority,
)
from src.collectors.price_snapshot import BACKFILL_SOURCE
from src.database.models import PriceObservationRow
from src.database.repository import Repository
from src.domain.models import HistoricalPrice

# Carry-forward sources: never count as a "real" observation (ADR 0017 §4).
SNAPSHOT_SOURCES = frozenset({SNAPSHOT_SOURCE, BACKFILL_SOURCE})


def _with_backfill_keys(keys: list[SeriesKey]) -> list[SeriesKey]:
    """Add the ``daily_snapshot_backfill`` twin of every ``daily_snapshot`` key.

    ADR 0017 (Governance amendment 5): backfilled rows use the same keys per
    variant as ``daily_snapshot``.
    """
    expanded: list[SeriesKey] = []
    for key in keys:
        expanded.append(key)
        if key.source == SNAPSHOT_SOURCE:
            expanded.append(SeriesKey(BACKFILL_SOURCE, key.external_id))
    return list(dict.fromkeys(expanded))


def _keys_filter(keys: list[SeriesKey]):
    return or_(
        *[
            and_(
                PriceObservationRow.source == k.source,
                PriceObservationRow.external_id == k.external_id,
            )
            for k in keys
        ]
    )


def load_series(
    repo: Repository,
    keys: list[SeriesKey],
    days: int | None,
    today: date | None = None,
) -> list[HistoricalPrice]:
    """Load every observation of *keys* in a single query, ordered by date ASC.

    When *days* is set only observations on or after ``today - days`` are
    returned (inclusive).  Empty *keys* returns ``[]`` without querying.
    """
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


def first_real_observation(repo: Repository, keys: list[SeriesKey]) -> date | None:
    """Return the date of the first priced, non-snapshot observation of *keys*.

    Looks at the whole history (no period filter).
    """
    real_keys = [k for k in keys if k.source not in SNAPSHOT_SOURCES]
    if not real_keys:
        return None
    stmt = select(func.min(PriceObservationRow.observed_at)).where(
        _keys_filter(real_keys),
        PriceObservationRow.median_price.is_not(None),
    )
    with Session(repo.engine) as session:
        return session.execute(stmt).scalar_one_or_none()


def build_history(
    repo: Repository,
    card_id: int,
    is_foil: bool,
    days: int | None,
    today: date | None = None,
) -> tuple[list[HistoricalPrice], dict[str, Any]]:
    """Return the merged (1 point/day) history of one card variant plus its meta."""
    source_cards = repo.get_source_cards_for_card(card_id)
    keys = _with_backfill_keys(
        resolve_history_keys(card_id, [(sc.source, sc.external_id) for sc in source_cards], is_foil)
    )
    merged = merge_series_by_priority(load_series(repo, keys, days, today=today))

    snapshot_points = sum(1 for p in merged if p.source in SNAPSHOT_SOURCES)
    meta: dict[str, Any] = {
        "variant": "foil" if is_foil else "normal",
        "sources": sorted({p.source for p in merged}, key=lambda s: (source_priority(s), s)),
        "first_observed_at": first_real_observation(repo, keys),
        "last_observed_at": merged[-1].observed_at if merged else None,
        "real_points": len(merged) - snapshot_points,
        "snapshot_points": snapshot_points,
    }
    return merged, meta
