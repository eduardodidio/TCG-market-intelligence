"""Portfolio snapshot service — captures daily collection value per user."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import structlog

from src.database.repository import Repository

log = structlog.get_logger()


def take_snapshot(user_id: str, repo: Repository) -> dict:
    """Take a portfolio value snapshot for a user.

    Queries the current collection total value (BRL, qty-weighted)
    and summary stats, then upserts into portfolio_snapshots for today.

    Returns a dict with snapshot data: user_id, date, value,
    priced_count, total_cards.
    """
    total_value = repo.get_collection_total_value(user_id)
    summary = repo.get_collection_summary(user_id)

    snapshot_date = date.today()
    value = total_value or Decimal("0")
    priced_count = summary.get("priced_count", 0)
    total_cards = summary.get("total_cards", 0)

    repo.upsert_portfolio_snapshot(
        user_id=user_id,
        snapshot_date=snapshot_date,
        total_value_brl=value,
        priced_card_count=priced_count,
        total_card_count=total_cards,
    )

    log.info(
        "portfolio_snapshot_taken",
        user_id=user_id,
        date=str(snapshot_date),
        value=str(value),
        priced_count=priced_count,
        total_cards=total_cards,
    )

    return {
        "user_id": user_id,
        "date": snapshot_date,
        "value": value,
        "priced_count": priced_count,
        "total_cards": total_cards,
    }
