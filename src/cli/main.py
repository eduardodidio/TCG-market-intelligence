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
@click.option("--concurrency", default=3, type=int, help="Max concurrent cards to process")
@click.option("--no-resume", is_flag=True, help="Re-process all cards (ignore already-collected)")
def backfill(db, set_filter, limit, dry_run, delay, history_days, concurrency, no_resume):
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
            concurrency=concurrency,
            resume=not no_resume,
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


@cli.command("match-report")
@click.option("--db", default="sqlite:///tcg_market.db", help="Database URL")
@click.option("--limit", default=None, type=int, help="Max cards to process")
@click.option("--delay", default=1.0, type=float, help="Seconds between requests")
@click.option("--concurrency", default=3, type=int, help="Max concurrent searches")
@click.option(
    "--output", default=None, type=click.Path(), help="Write detailed JSON report to file"
)
def match_report(db, limit, delay, concurrency, output):
    """Dry-run match report: check MYP coverage for collection cards."""
    from src.collectors.match_report import format_report, run_match_report

    summary = asyncio.run(
        run_match_report(
            db_url=db,
            limit=limit,
            delay=delay,
            concurrency=concurrency,
            output=output,
        )
    )
    click.echo(format_report(summary))


@cli.command("db-backup")
@click.option("--db", default="sqlite:///tcg_market.db", help="Database URL")
@click.option("--backup-dir", default="backups", help="Directory for backups")
def db_backup(db, backup_dir):
    """Create a timestamped backup of the SQLite database."""
    from src.database.backup import backup_database, extract_db_path

    db_path = extract_db_path(db)
    try:
        path = backup_database(db_path, backup_dir=backup_dir)
        size_mb = path.stat().st_size / (1024 * 1024)
        click.echo(f"Backup created: {path} ({size_mb:.2f} MB)")
    except FileNotFoundError as exc:
        click.echo(f"Error: {exc}", err=True)
        raise SystemExit(1) from exc


@cli.command("db-cleanup")
@click.option("--db", default="sqlite:///tcg_market.db", help="Database URL")
@click.option("--dry-run", is_flag=True, help="Show what would be deleted without deleting")
@click.option("--no-backup", is_flag=True, help="Skip automatic backup before cleanup")
def db_cleanup(db, dry_run, no_backup):
    """Remove cards, source_cards, and observations not in your collection."""
    from src.database.cleanup import cleanup_non_collection_data

    try:
        result = cleanup_non_collection_data(
            db_url=db,
            dry_run=dry_run,
            skip_backup=no_backup,
        )
    except ValueError as exc:
        click.echo(f"Error: {exc}", err=True)
        raise SystemExit(1) from exc

    prefix = "[DRY RUN] Would delete" if dry_run else "Deleted"
    click.echo("")
    click.echo(f"  {prefix}:")
    click.echo(f"    Cards:              {result.cards_deleted}")
    click.echo(f"    Source cards:        {result.source_cards_deleted}")
    click.echo(f"    Price observations:  {result.observations_deleted}")

    if result.cards_deleted == 0 and result.source_cards_deleted == 0:
        click.echo("\n  Nothing to clean -- all data belongs to your collection.")

    if result.backup_path:
        click.echo(f"\n  Backup saved to: {result.backup_path}")
    click.echo("")


@cli.command("snapshot-prices")
@click.option("--db", default="sqlite:///tcg_market.db", help="Database URL")
@click.option("--limit", default=None, type=int, help="Max cards to process")
@click.option("--dry-run", is_flag=True, help="Don't write to database")
@click.option("--delay", default=1.0, type=float, help="Seconds between requests")
@click.option("--concurrency", default=3, type=int, help="Max concurrent requests")
def snapshot_prices(db, limit, dry_run, delay, concurrency):
    """Daily price snapshot from JSON-LD on product pages."""
    from src.collectors.snapshot_prices import run_snapshot_prices

    summary = asyncio.run(
        run_snapshot_prices(
            db_url=db,
            limit=limit,
            dry_run=dry_run,
            delay=delay,
            concurrency=concurrency,
        )
    )
    _print_snapshot_summary(summary, dry_run)


@cli.command("sync-collection")
@click.option("--db", default="sqlite:///tcg_market.db", help="Database URL")
@click.option("--limit", default=None, type=int, help="Max cards to process")
@click.option("--dry-run", is_flag=True, help="Don't write to database")
@click.option("--delay", default=1.0, type=float, help="Seconds between requests")
@click.option("--history-days", default=365, type=int, help="Days of history to fetch")
@click.option("--concurrency", default=3, type=int, help="Max concurrent requests")
@click.option("--force", is_flag=True, help="Re-process already-linked entries")
def sync_collection(db, limit, dry_run, delay, history_days, concurrency, force):
    """Sync user collection with MYP price data."""
    from src.collectors.sync_collection import run_sync_collection

    summary = asyncio.run(
        run_sync_collection(
            db_url=db,
            limit=limit,
            dry_run=dry_run,
            delay=delay,
            history_days=history_days,
            concurrency=concurrency,
            skip_matched=not force,
        )
    )
    _print_sync_summary(summary, dry_run)


def _print_sync_summary(summary, dry_run):
    """Format and print collection sync summary to stdout."""
    click.echo("")
    click.echo("=" * 60)
    if dry_run:
        click.echo("  DRY RUN — no data was written")
    click.echo("  COLLECTION SYNC SUMMARY")
    click.echo(f"  Total entries:           {summary.total_entries}")
    click.echo(f"  Skipped (already linked): {summary.skipped_already_linked}")
    click.echo(f"  Searched:                 {summary.searched}")
    click.echo(f"  Matched:                  {summary.matched}")
    click.echo(f"  Ambiguous:                {summary.ambiguous:>3}")
    click.echo(f"  Unmatched:                {summary.unmatched:>3}")
    click.echo(f"  Cards created:            {summary.cards_created}")
    click.echo(f"  Observations saved:     {summary.observations_saved:,}")
    if summary.finished_at:
        elapsed = (summary.finished_at - summary.started_at).total_seconds()
        minutes = elapsed / 60
        click.echo(f"  Elapsed:                {elapsed:.1f}s ({minutes:.1f} min)")
    click.echo("=" * 60)

    if summary.errors:
        click.echo(f"\n  Errors ({len(summary.errors)}):")
        for err in summary.errors[:20]:
            click.echo(
                f"    - [{err.set_code}/{err.collector_number}] {err.name_en}: "
                f"{err.error_type} — {err.error_message[:80]}"
            )
        if len(summary.errors) > 20:
            click.echo(f"    ... and {len(summary.errors) - 20} more")


def _print_snapshot_summary(summary, dry_run):
    """Format and print snapshot prices summary to stdout."""
    click.echo("")
    click.echo("=" * 60)
    if dry_run:
        click.echo("  DRY RUN -- no data was written")
    click.echo("  SNAPSHOT PRICES SUMMARY")
    click.echo(f"  Total entries:           {summary.total_entries}")
    click.echo(f"  Fetched:                 {summary.fetched}")
    click.echo(f"  Stored:                  {summary.stored}")
    click.echo(f"  Skipped (existing):      {summary.skipped_existing}")
    click.echo(f"  Skipped (zero price):    {summary.skipped_zero_price}")
    click.echo(f"  Errors:                  {summary.errors}")
    if summary.finished_at:
        elapsed = (summary.finished_at - summary.started_at).total_seconds()
        click.echo(f"  Elapsed:                 {elapsed:.1f}s")
    click.echo("=" * 60)

    if summary.error_details:
        click.echo(f"\n  Error details ({len(summary.error_details)}):")
        for err in summary.error_details[:20]:
            click.echo(f"    - {err.external_id}: {err.error_type} -- {err.error_message[:80]}")
        if len(summary.error_details) > 20:
            click.echo(f"    ... and {len(summary.error_details) - 20} more")


@cli.command()
@click.option("--host", default="0.0.0.0", help="Host to bind to")
@click.option("--port", default=8000, type=int, help="Port to bind to")
def serve(host, port):
    """Start the REST API server."""
    from src.api.app import run_server

    run_server(host=host, port=port)


if __name__ == "__main__":
    cli()
