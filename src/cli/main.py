"""CLI entry point for the collector."""

from __future__ import annotations

import asyncio
import sys

import click
import structlog

structlog.configure(
    processors=[
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.dev.ConsoleRenderer(),
    ],
)


@click.group()
def cli():
    """TCG Market Intelligence — Data Collector"""
    pass


@cli.command()
@click.option("--db", default="sqlite:///tcg_market.db", help="Database URL")
@click.option("--set", "set_filter", default=None, help="Only collect from this set slug")
@click.option("--limit", default=None, type=int, help="Max cards to process")
@click.option("--dry-run", is_flag=True, help="Don't write to database")
@click.option("--delay", default=1.0, type=float, help="Seconds between requests")
@click.option("--history-days", default=1095, type=int, help="Days of history to fetch")
def backfill(db, set_filter, limit, dry_run, delay, history_days):
    """Full backfill: discover all cards, collect history."""
    from src.collectors.backfill import run_backfill

    summary = asyncio.run(
        run_backfill(
            db_url=db,
            set_filter=set_filter,
            limit=limit,
            dry_run=dry_run,
            delay=delay,
            history_days=history_days,
        )
    )
    _print_summary(summary, dry_run)


@cli.command()
@click.option("--db", default="sqlite:///tcg_market.db", help="Database URL")
@click.option("--delay", default=1.0, type=float, help="Seconds between requests")
@click.option("--history-days", default=30, type=int, help="Days of history to fetch")
def update(db, delay, history_days):
    """Incremental update: fetch recent data for known cards."""
    from src.collectors.backfill import run_update

    summary = asyncio.run(run_update(db_url=db, delay=delay, history_days=history_days))
    _print_summary(summary, False)


@cli.command("retry-failed")
@click.option("--db", default="sqlite:///tcg_market.db", help="Database URL")
@click.option("--delay", default=2.0, type=float, help="Seconds between requests")
@click.option("--history-days", default=1095, type=int, help="Days of history to fetch")
def retry_failed(db, delay, history_days):
    """Retry previously failed cards."""
    from src.collectors.backfill import run_retry_failed

    summary = asyncio.run(run_retry_failed(db_url=db, delay=delay, history_days=history_days))
    _print_summary(summary, False)


def _print_summary(summary, dry_run):
    click.echo("")
    click.echo("=" * 60)
    if dry_run:
        click.echo("  DRY RUN — no data was written")
    click.echo(f"  Cards discovered:       {summary.cards_discovered}")
    click.echo(f"  Cards processed:        {summary.cards_processed}")
    click.echo(f"  Cards failed:           {summary.cards_failed}")
    click.echo(f"  Observations saved:     {summary.observations_saved}")
    if summary.finished_at:
        elapsed = (summary.finished_at - summary.started_at).total_seconds()
        click.echo(f"  Elapsed:                {elapsed:.1f}s")
    click.echo("=" * 60)

    if summary.errors:
        click.echo(f"\n  Failed cards ({len(summary.errors)}):")
        for err in summary.errors[:20]:
            click.echo(f"    - {err.external_id}: {err.error_type} — {err.error_message[:80]}")
        if len(summary.errors) > 20:
            click.echo(f"    ... and {len(summary.errors) - 20} more")


if __name__ == "__main__":
    cli()
