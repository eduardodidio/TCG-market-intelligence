"""Daily price snapshot service.

Reads the latest known price for every card in the database and inserts
a ``price_observations`` row with ``source='daily_snapshot'`` for today's
date.  The unique constraint on ``(source, external_id, observed_at)``
makes this naturally idempotent -- running twice on the same day inserts
zero new rows on the second call.
"""

from __future__ import annotations

import logging
from datetime import date, timedelta

from src.database.repository import Repository
from src.domain.models import HistoricalPrice

logger = logging.getLogger(__name__)

SNAPSHOT_SOURCE = "daily_snapshot"
BATCH_SIZE = 500
MAX_BACKFILL_DAYS = 90


def run_daily_snapshot(repo: Repository) -> int:
    """Snapshot all current prices into daily_snapshot observations.

    Returns count of new observations inserted.
    """
    latest_prices = repo.get_all_latest_prices()
    if not latest_prices:
        return 0

    today = date.today()

    observations = [
        HistoricalPrice(
            source=SNAPSHOT_SOURCE,
            external_id=external_id,
            observed_at=today,
            median_price=median_price,
        )
        for _source, external_id, median_price in latest_prices
    ]

    # insert_price_observations already handles batching (500) and
    # on_conflict_do_nothing for the unique constraint.
    return repo.insert_price_observations(observations)


def backfill_snapshots(repo: Repository, days: int = 1) -> int:
    """Create daily_snapshot observations for cards missing them.

    For each card with a known price but no daily_snapshot rows,
    creates observations for the last ``days`` days using the current
    latest price.

    Returns total count of new observations inserted.
    """
    if days > MAX_BACKFILL_DAYS:
        logger.warning(
            "days=%d exceeds maximum %d, capping at %d",
            days,
            MAX_BACKFILL_DAYS,
            MAX_BACKFILL_DAYS,
        )
        days = MAX_BACKFILL_DAYS

    latest_prices = repo.get_all_latest_prices()
    if not latest_prices:
        logger.info("No priced cards found, nothing to backfill.")
        return 0

    already_have = repo.get_external_ids_with_source(SNAPSHOT_SOURCE)

    missing = [
        (external_id, median_price)
        for _source, external_id, median_price in latest_prices
        if external_id not in already_have
    ]

    if not missing:
        logger.info("All priced cards already have snapshots.")
        return 0

    logger.info(
        "Backfilling %d cards x %d days (%d total observations).",
        len(missing),
        days,
        len(missing) * days,
    )

    today = date.today()
    observations: list[HistoricalPrice] = []

    for i, (external_id, median_price) in enumerate(missing, 1):
        for day_offset in range(days):
            observations.append(
                HistoricalPrice(
                    source=SNAPSHOT_SOURCE,
                    external_id=external_id,
                    observed_at=today - timedelta(days=day_offset),
                    median_price=median_price,
                )
            )
        if i % 1000 == 0:
            logger.info("Prepared %d / %d cards...", i, len(missing))

    return repo.insert_price_observations(observations)
