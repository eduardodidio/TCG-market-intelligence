"""CLI entry point for the collector."""

from __future__ import annotations

import asyncio

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


@cli.group()
def analyze():
    """Analytics commands for price data."""
    pass


@analyze.command("card")
@click.option("--db", default="sqlite:///tcg_market.db", help="Database URL")
@click.option("--source", default="myp", help="Data source")
@click.option("--price-field", default="median_price", help="Price field to analyze")
@click.argument("external_id")
def analyze_card(db, source, price_field, external_id):
    """Compute analytics for a single card by EXTERNAL_ID."""
    from src.analytics.indicators import compute_card_analytics
    from src.database.repository import Repository

    repo = Repository(db_url=db)
    prices = repo.get_price_series(source=source, external_id=external_id)

    if not prices:
        click.echo(f"No data found for card {external_id} (source={source}).")
        return

    analytics = compute_card_analytics(
        prices=prices,
        source=source,
        external_id=external_id,
        price_field=price_field,
    )

    _print_card_analytics(analytics, price_field, len(prices))


@analyze.command("list")
@click.option("--db", default="sqlite:///tcg_market.db", help="Database URL")
@click.option("--source", default="myp", help="Data source")
def analyze_list(db, source):
    """List all cards with observation counts."""
    from src.database.repository import Repository

    repo = Repository(db_url=db)
    cards = repo.get_cards_with_observations(source=source)

    if not cards:
        click.echo(f"No cards found for source={source}.")
        return

    click.echo(f"{'External ID':<20} {'Observations':>12}")
    click.echo("-" * 33)
    for external_id, count in cards:
        click.echo(f"{external_id:<20} {count:>12}")
    click.echo("-" * 33)
    click.echo(f"Total: {len(cards)} cards")


def _print_card_analytics(analytics, price_field, data_points):
    """Format and print card analytics to stdout."""
    click.echo("")
    click.echo(f"=== Card Analytics: {analytics.external_id} ({analytics.source}) ===")
    click.echo(f"Price field: {price_field}")
    click.echo(f"Data points: {data_points}")

    if analytics.moving_averages:
        click.echo("")
        click.echo("Moving Averages:")
        for ma in analytics.moving_averages:
            click.echo(f"  MA({ma.period}):{' ' * (4 - len(str(ma.period)))}R$ {ma.value:.2f}")

    if analytics.extremes:
        click.echo("")
        click.echo("Price Extremes:")
        click.echo(f"  ATH: R$ {analytics.extremes.ath_price:.2f} ({analytics.extremes.ath_date})")
        click.echo(f"  ATL: R$ {analytics.extremes.atl_price:.2f} ({analytics.extremes.atl_date})")

    if analytics.volatility:
        click.echo("")
        click.echo(f"Volatility ({analytics.volatility.period_days}d):")
        click.echo(f"  Std Dev: R$ {analytics.volatility.std_dev:.2f}")
        cov_pct = analytics.volatility.coefficient_of_variation * 100
        click.echo(f"  CoV:     {cov_pct:.1f}%")

    if analytics.momentum:
        click.echo("")
        click.echo(f"Momentum ({analytics.momentum.period_days}d):")
        roc = analytics.momentum.rate_of_change
        sign = "+" if roc > 0 else ""
        click.echo(f"  RoC:   {sign}{roc:.1f}%")
        click.echo(f"  Trend: {analytics.momentum.trend_direction}")

    click.echo("")


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
