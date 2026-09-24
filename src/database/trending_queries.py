"""Market-wide trending price series (F175-T03).

Loads price series for the "market" view of Tendências (no user filter),
unioning two sources:

1. ``source_cards`` joined to ``price_observations`` (MYP, jsonld_snapshot, ...).
2. Direct Liga/manual observations whose ``external_id`` encodes the card id
   (``liga_{card_id}``, ``manual_{card_id}``), which have no ``source_cards``
   row and would otherwise be invisible to the market ranking. Foil
   observations (``liga_{card_id}_foil``) are excluded: mixing foil and
   non-foil prices in one series would create spurious trends.
"""

from __future__ import annotations

import re
from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import func, select, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from src.database.models import PriceObservationRow, SourceCardRow

_EXTID_RE = re.compile(r"^(?:liga|manual)_(\d+)$")


def parse_direct_card_id(external_id: str) -> int | None:
    """Extract the card id from a direct non-foil Liga/manual external_id.

    Matches ``liga_{id}`` and ``manual_{id}``. Returns ``None`` for anything
    else, notably ``liga_{id}_foil`` (foil series are not part of the market
    trend) and ``liga_catalog_{set}_{num}`` (which belongs to
    ``source_cards``, not a direct observation).
    """
    match = _EXTID_RE.match(external_id)
    return int(match.group(1)) if match else None


def load_market_trending_prices(
    engine: Engine, period_days: int
) -> dict[int, list[tuple[date, Decimal]]]:
    """Load price series for all cards with observations in the period.

    Returns a dict mapping card_id to a list of (date, median_price)
    tuples, sorted by date ascending. Merges the ``source_cards`` path with
    direct non-foil Liga/manual observations. When several sources land on
    the same date for the same card, the highest price wins for that date.
    """
    cutoff = date.today() - timedelta(days=period_days)

    result: dict[int, list[tuple[date, Decimal]]] = {}

    with Session(engine) as session:
        if "postgresql" in str(engine.url):
            session.execute(text("SET LOCAL statement_timeout = '12s'"))

        # Path 1: source_cards-based prices (MYP, jsonld_snapshot, etc.)
        stmt = (
            select(
                SourceCardRow.card_id,
                PriceObservationRow.observed_at,
                PriceObservationRow.median_price,
            )
            .join(
                PriceObservationRow,
                (PriceObservationRow.external_id == SourceCardRow.external_id)
                & (PriceObservationRow.source.in_([SourceCardRow.source, "jsonld_snapshot"])),
            )
            .where(
                SourceCardRow.card_id.isnot(None),
                PriceObservationRow.observed_at >= cutoff,
                PriceObservationRow.median_price.isnot(None),
            )
            .order_by(SourceCardRow.card_id, PriceObservationRow.observed_at.asc())
        )
        for card_id, obs_date, median_price in session.execute(stmt).all():
            result.setdefault(card_id, []).append((obs_date, Decimal(str(median_price))))

        # Path 2: direct Liga/manual observations (no source_cards row).
        direct_stmt = (
            select(
                PriceObservationRow.external_id,
                PriceObservationRow.observed_at,
                func.max(PriceObservationRow.median_price),
            )
            .where(
                PriceObservationRow.source.in_(["liga", "manual"]),
                PriceObservationRow.observed_at >= cutoff,
                PriceObservationRow.median_price.isnot(None),
            )
            .group_by(PriceObservationRow.external_id, PriceObservationRow.observed_at)
        )
        for external_id, obs_date, median_price in session.execute(direct_stmt).all():
            card_id = parse_direct_card_id(external_id)
            if card_id is None:
                continue
            result.setdefault(card_id, []).append((obs_date, Decimal(str(median_price))))

    # Deduplicate within each card: same date keeps max price.
    for card_id, points in result.items():
        by_date: dict[date, Decimal] = {}
        for d, p in points:
            if d not in by_date or p > by_date[d]:
                by_date[d] = p
        result[card_id] = sorted(by_date.items(), key=lambda x: x[0])

    return result
