#!/usr/bin/env python3
"""One-time backfill script for historical USD/BRL exchange rates.

Fetches the last 365 days of PTAX rates from the Brazilian Central Bank
(BCB) and stores them in the exchange_rates table.

Usage:
    python scripts/backfill_exchange_rates.py [--db sqlite:///tcg_market.db] [--days 365]

This script is idempotent -- safe to re-run. Existing rates are updated
via upsert (INSERT ON CONFLICT DO UPDATE).
"""

from __future__ import annotations

import asyncio
import sys
from datetime import date, timedelta

import click
import structlog

structlog.configure(
    processors=[
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.dev.ConsoleRenderer(),
    ],
)

log = structlog.get_logger()


@click.command()
@click.option("--db", default="sqlite:///tcg_market.db", help="Database URL")
@click.option("--days", default=365, type=int, help="Number of days to backfill")
def main(db: str, days: int) -> None:
    """Fetch historical PTAX rates and store them."""
    from src.database.repository import Repository
    from src.providers.bcb.client import fetch_rate_range

    repo = Repository(db_url=db)
    end = date.today()
    start = end - timedelta(days=days)

    log.info("backfill_start", start=str(start), end=str(end), days=days)
    click.echo(f"Fetching PTAX rates from {start} to {end} ({days} days)...")

    rates = asyncio.run(fetch_rate_range(start, end))

    if not rates:
        log.warning("backfill_no_rates", message="BCB returned no rates for the period")
        click.echo("No rates returned from BCB. The API may be unavailable.")
        sys.exit(1)

    log.info("backfill_fetched", count=len(rates))
    click.echo(f"Fetched {len(rates)} rates. Storing...")

    repo.bulk_upsert_rates(rates)

    log.info("backfill_complete", stored=len(rates))
    click.echo(f"Done. Stored {len(rates)} exchange rates.")

    # Show summary
    latest = repo.get_latest_rate()
    if latest:
        click.echo(f"Latest rate: {latest.rate_date} -> {latest.rate}")


if __name__ == "__main__":
    main()
