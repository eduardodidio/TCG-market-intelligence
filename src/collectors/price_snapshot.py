"""Daily price snapshot service.

``run_daily_snapshot`` carries the latest *real* price (any source other
than the synthetic ones below) of every ``external_id`` forward into a
``price_observations`` row with ``source='daily_snapshot'`` for today.  The
carry-forward stops ``MAX_CARRY_FORWARD_DAYS`` after the last real
observation, so abandoned cards do not get an eternal flat line.

``backfill_snapshots`` fills past gaps by forward-filling real observations
(never before the first real one, never with today's price).  Its rows use
``source='daily_snapshot_backfill'`` so they can be told apart from real
daily snapshots and deleted if needed (ADR 0017).

The unique constraint on ``(source, external_id, observed_at)`` plus
``on_conflict_do_nothing`` in ``insert_price_observations`` makes both
functions idempotent.
"""

from __future__ import annotations

import logging
from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import func, literal_column, select
from sqlalchemy.orm import Session

from src.database.models import PriceObservationRow
from src.database.repository import Repository
from src.domain.models import HistoricalPrice

logger = logging.getLogger(__name__)

SNAPSHOT_SOURCE = "daily_snapshot"
BACKFILL_SOURCE = "daily_snapshot_backfill"
# Sources written by this module; they are never a price source themselves.
SYNTHETIC_SOURCES = (SNAPSHOT_SOURCE, BACKFILL_SOURCE)
BATCH_SIZE = 500
MAX_BACKFILL_DAYS = 90
MAX_CARRY_FORWARD_DAYS = 30


def _real_filter():
    return (
        PriceObservationRow.source.not_in(SYNTHETIC_SOURCES),
        PriceObservationRow.median_price.is_not(None),
    )


def _latest_real_prices(
    repo: Repository,
    since: date | None = None,
    until: date | None = None,
) -> list[tuple[str, date, Decimal]]:
    """Return ``(external_id, observed_at, median_price)`` of the latest real
    observation per external_id, optionally restricted to ``[since, until]``.
    """
    conditions = list(_real_filter())
    if since is not None:
        conditions.append(PriceObservationRow.observed_at >= since)
    if until is not None:
        conditions.append(PriceObservationRow.observed_at <= until)

    cte = (
        select(
            PriceObservationRow.external_id,
            PriceObservationRow.observed_at,
            PriceObservationRow.median_price,
            func.row_number()
            .over(
                partition_by=PriceObservationRow.external_id,
                order_by=(
                    PriceObservationRow.observed_at.desc(),
                    PriceObservationRow.id.desc(),
                ),
            )
            .label("rn"),
        )
        .where(*conditions)
        .cte("latest_real")
    )
    stmt = select(cte.c.external_id, cte.c.observed_at, cte.c.median_price).where(
        cte.c.rn == literal_column("1")
    )
    with Session(repo.engine) as session:
        return [(r[0], r[1], r[2]) for r in session.execute(stmt).all()]


def _ids_observed_on(repo: Repository, day: date) -> set[str]:
    """Return external_ids with any observation (any source) on *day*."""
    stmt = (
        select(PriceObservationRow.external_id)
        .where(PriceObservationRow.observed_at == day)
        .distinct()
    )
    with Session(repo.engine) as session:
        return {r[0] for r in session.execute(stmt).all()}


def run_daily_snapshot(repo: Repository, today: date | None = None) -> int:
    """Carry each card's latest real price forward into today's snapshot.

    Only external_ids whose last real observation is at most
    ``MAX_CARRY_FORWARD_DAYS`` old get a point, and ids that already have
    any observation today are skipped.

    Returns count of new observations inserted.
    """
    today = today or date.today()
    latest = _latest_real_prices(
        repo, since=today - timedelta(days=MAX_CARRY_FORWARD_DAYS), until=today
    )
    if not latest:
        return 0

    observed_today = _ids_observed_on(repo, today)
    observations = [
        HistoricalPrice(
            source=SNAPSHOT_SOURCE,
            external_id=external_id,
            observed_at=today,
            median_price=median_price,
        )
        for external_id, _observed_at, median_price in latest
        if external_id not in observed_today
    ]
    return repo.insert_price_observations(observations)


def _real_ids_since(repo: Repository, since: date, until: date) -> list[str]:
    stmt = (
        select(PriceObservationRow.external_id)
        .where(
            *_real_filter(),
            PriceObservationRow.observed_at >= since,
            PriceObservationRow.observed_at <= until,
        )
        .distinct()
        .order_by(PriceObservationRow.external_id)
    )
    with Session(repo.engine) as session:
        return [r[0] for r in session.execute(stmt).all()]


def _forward_fill_page(
    repo: Repository,
    external_ids: list[str],
    window_start: date,
    today: date,
) -> list[HistoricalPrice]:
    """Build backfill rows for one page of external_ids.

    Real observations older than ``window_start - MAX_CARRY_FORWARD_DAYS``
    cannot cover any day in the window, so they are not loaded.
    """
    load_from = window_start - timedelta(days=MAX_CARRY_FORWARD_DAYS)
    real_stmt = (
        select(
            PriceObservationRow.external_id,
            PriceObservationRow.observed_at,
            PriceObservationRow.median_price,
        )
        .where(
            *_real_filter(),
            PriceObservationRow.external_id.in_(external_ids),
            PriceObservationRow.observed_at >= load_from,
            PriceObservationRow.observed_at <= today,
        )
        .order_by(
            PriceObservationRow.external_id,
            PriceObservationRow.observed_at,
            PriceObservationRow.id,
        )
    )
    occupied_stmt = (
        select(PriceObservationRow.external_id, PriceObservationRow.observed_at)
        .where(
            PriceObservationRow.external_id.in_(external_ids),
            PriceObservationRow.observed_at >= window_start,
            PriceObservationRow.observed_at <= today,
        )
        .distinct()
    )
    with Session(repo.engine) as session:
        real_rows = session.execute(real_stmt).all()
        occupied = {(r[0], r[1]) for r in session.execute(occupied_stmt).all()}

    # Latest real price per (external_id, day); ordering makes the last row win.
    real_by_id: dict[str, dict[date, Decimal]] = {}
    for external_id, observed_at, median_price in real_rows:
        real_by_id.setdefault(external_id, {})[observed_at] = median_price

    observations: list[HistoricalPrice] = []
    for external_id, prices in real_by_id.items():
        last_date: date | None = None
        last_price: Decimal | None = None
        day = load_from
        while day <= today:
            if day in prices:
                last_date, last_price = day, prices[day]
            elif (
                day >= window_start
                and last_date is not None
                and (day - last_date).days <= MAX_CARRY_FORWARD_DAYS
                and (external_id, day) not in occupied
            ):
                observations.append(
                    HistoricalPrice(
                        source=BACKFILL_SOURCE,
                        external_id=external_id,
                        observed_at=day,
                        median_price=last_price,
                    )
                )
            day += timedelta(days=1)
    return observations


def backfill_snapshots(
    repo: Repository,
    days: int = 1,
    dry_run: bool = False,
    today: date | None = None,
) -> int:
    """Forward-fill gaps of the last ``days`` days from real observations.

    For every external_id with real observations and every day ``d`` in
    ``[today - days + 1, today]`` that has no observation at all, inserts a
    ``daily_snapshot_backfill`` row with the price of the latest real
    observation ``<= d`` — only if that observation is at most
    ``MAX_CARRY_FORWARD_DAYS`` old.  Nothing is ever created before the
    first real observation.

    With ``dry_run=True`` nothing is written; the return value is the count
    that would be inserted.

    Raises:
        ValueError: if ``days < 1``.
    """
    if days < 1:
        raise ValueError(f"days must be >= 1, got {days}")
    if days > MAX_BACKFILL_DAYS:
        logger.warning(
            "days=%d exceeds maximum %d, capping at %d",
            days,
            MAX_BACKFILL_DAYS,
            MAX_BACKFILL_DAYS,
        )
        days = MAX_BACKFILL_DAYS

    today = today or date.today()
    window_start = today - timedelta(days=days - 1)
    external_ids = _real_ids_since(
        repo, window_start - timedelta(days=MAX_CARRY_FORWARD_DAYS), today
    )
    if not external_ids:
        logger.info("No real observations in range, nothing to backfill.")
        return 0

    logger.info(
        "Backfilling %d external_ids over %d days (dry_run=%s).",
        len(external_ids),
        days,
        dry_run,
    )
    total = 0
    for page_start in range(0, len(external_ids), BATCH_SIZE):
        page = external_ids[page_start : page_start + BATCH_SIZE]
        observations = _forward_fill_page(repo, page, window_start, today)
        if dry_run:
            total += len(observations)
        else:
            total += repo.insert_price_observations(observations)
        logger.info(
            "Processed %d / %d external_ids...",
            min(page_start + BATCH_SIZE, len(external_ids)),
            len(external_ids),
        )
    return total
