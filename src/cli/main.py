"""CLI entry point for the collector."""

from __future__ import annotations

import asyncio
import os

import click
import structlog

structlog.configure(
    processors=[
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.dev.ConsoleRenderer(),
    ],
)


def _resolve_db(ctx, param, value):
    """Click callback: resolve --db to auto-detected URL when None."""
    if value is None:
        from src.config import get_db_url

        return get_db_url()
    return value


@click.group()
def cli():
    """TEDHC Market — Data Collector"""
    pass


@cli.command()
@click.option(
    "--db",
    default=None,
    callback=_resolve_db,
    is_eager=True,
    expose_value=True,
    help="Database URL (default: auto-detect)",
)
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
@click.option(
    "--db",
    default=None,
    callback=_resolve_db,
    is_eager=True,
    expose_value=True,
    help="Database URL (default: auto-detect)",
)
@click.option("--delay", default=1.0, type=float, help="Seconds between requests")
@click.option("--history-days", default=30, type=int, help="Days of history to fetch")
def update(db, delay, history_days):
    """Incremental update: fetch recent data for known cards."""
    from src.collectors.backfill import run_update

    summary = asyncio.run(run_update(db_url=db, delay=delay, history_days=history_days))
    _print_summary(summary, False)


@cli.command("retry-failed")
@click.option(
    "--db",
    default=None,
    callback=_resolve_db,
    is_eager=True,
    expose_value=True,
    help="Database URL (default: auto-detect)",
)
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
@click.option(
    "--db",
    default=None,
    callback=_resolve_db,
    is_eager=True,
    expose_value=True,
    help="Database URL (default: auto-detect)",
)
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
@click.option(
    "--db",
    default=None,
    callback=_resolve_db,
    is_eager=True,
    expose_value=True,
    help="Database URL (default: auto-detect)",
)
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
@click.option(
    "--db",
    default=None,
    callback=_resolve_db,
    is_eager=True,
    expose_value=True,
    help="Database URL (default: auto-detect)",
)
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
@click.option(
    "--db",
    default=None,
    callback=_resolve_db,
    is_eager=True,
    expose_value=True,
    help="Database URL (default: auto-detect)",
)
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
@click.option(
    "--db",
    default=None,
    callback=_resolve_db,
    is_eager=True,
    expose_value=True,
    help="Database URL (default: auto-detect)",
)
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


@cli.command("db-clear-prices")
@click.option(
    "--db",
    default=None,
    help="Database URL (default from TCG_DATABASE_URL or sqlite:///tcg_market.db)",
)
@click.option("--source", required=True, help="Source to clear (e.g. jsonld_snapshot, myp)")
@click.option("--confirm", is_flag=True, help="Required to actually delete")
@click.option("--skip-backup", is_flag=True, help="Skip pre-delete backup")
def db_clear_prices(db, source, confirm, skip_backup):
    """Clear all price observations for a given source."""
    from src.config import get_db_url
    from src.database.cleanup import clear_prices_by_source

    db_url = db or get_db_url()

    try:
        result = clear_prices_by_source(
            db_url=db_url,
            source=source,
            dry_run=not confirm,
            skip_backup=skip_backup,
        )
    except ValueError as exc:
        click.echo(f"Error: {exc}", err=True)
        raise SystemExit(1) from exc

    if result.dry_run:
        click.echo(
            f"\n  [DRY RUN] Would delete {result.deleted} price observations (source='{source}')."
        )
        click.echo("  Pass --confirm to actually delete.\n")
    else:
        click.echo(f"\n  Deleted {result.deleted} price observations (source='{source}').")
        if result.backup_path:
            click.echo(f"  Backup saved to: {result.backup_path}")
        click.echo("")


@cli.command("snapshot-prices")
@click.option(
    "--db",
    default=None,
    callback=_resolve_db,
    is_eager=True,
    expose_value=True,
    help="Database URL (default: auto-detect)",
)
@click.option("--limit", default=None, type=int, help="Max cards to process")
@click.option("--dry-run", is_flag=True, help="Don't write to database")
@click.option("--delay", default=1.0, type=float, help="Seconds between requests")
@click.option("--concurrency", default=3, type=int, help="Max concurrent requests")
@click.option(
    "--provider",
    type=click.Choice(["auto", "liga", "myp"]),
    default="auto",
    help="Price provider: auto (registry), liga, or myp",
)
def snapshot_prices(db, limit, dry_run, delay, concurrency, provider):
    """Daily price snapshot from JSON-LD on product pages."""
    from src.collectors.snapshot_prices import run_snapshot_prices

    if provider == "liga":
        click.echo("Note: LigaMagic not yet wired for snapshots — using MYP.")

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
@click.option(
    "--db",
    default=None,
    callback=_resolve_db,
    is_eager=True,
    expose_value=True,
    help="Database URL (default: auto-detect)",
)
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


def _resolve_provider(provider_name: str, delay: float = 1.0):
    """Create a provider based on the --provider flag.

    Args:
        provider_name: "auto", "liga", or "myp".
        delay: Delay between requests for MYP.

    Returns:
        Tuple of (provider_instance_or_None, effective_provider_name).
        For Liga, returns (None, "liga") — the scan orchestrator handles
        Liga internally via ``provider_name="liga"``.
    """
    if provider_name == "myp":
        from src.providers.myp.provider import MypCardsProvider, MypConfig

        config = MypConfig(delay_seconds=delay)
        return MypCardsProvider(config), "myp"

    if provider_name == "liga":
        # Liga is handled internally by run_scan via provider_name="liga"
        return None, "liga"

    # "auto" — default to Liga
    return None, "liga"


@cli.command()
@click.option(
    "--db",
    default=None,
    callback=_resolve_db,
    is_eager=True,
    expose_value=True,
    help="Database URL (default: auto-detect)",
)
@click.option(
    "--type",
    "scan_type",
    type=click.Choice(["collection", "set", "format", "custom"]),
    default="collection",
    help="Scan type",
)
@click.option("--set", "set_codes", default=None, help="Comma-separated set codes")
@click.option("--format", "format_name", default=None, help="Format name filter")
@click.option("--rarity", default=None, help="Comma-separated rarities")
@click.option("--card-ids", default=None, help="Comma-separated card IDs")
@click.option("--limit", default=None, type=int, help="Max cards to process")
@click.option("--dry-run", is_flag=True, help="Don't write to database")
@click.option("--delay", default=1.0, type=float, help="Seconds between requests")
@click.option("--concurrency", default=3, type=int, help="Max concurrent requests")
@click.option(
    "--provider",
    type=click.Choice(["auto", "liga", "myp"]),
    default="liga",
    help="Price provider: liga (default), myp, or auto (defaults to liga)",
)
def scan(
    db,
    scan_type,
    set_codes,
    format_name,
    rarity,
    card_ids,
    limit,
    dry_run,
    delay,
    concurrency,
    provider,
):
    """Run a price scan with optional filters."""
    from src.collectors.scan import run_scan
    from src.domain.models import ScanFilter, ScanType

    sf = ScanFilter(
        scan_type=ScanType(scan_type),
        set_codes=set_codes.split(",") if set_codes else None,
        format_name=format_name,
        rarities=rarity.split(",") if rarity else None,
        card_ids=[int(x) for x in card_ids.split(",")] if card_ids else None,
        limit=limit,
    )

    resolved_provider, effective_provider_name = _resolve_provider(provider, delay)

    result = asyncio.run(
        run_scan(
            db_url=db,
            scan_filter=sf,
            dry_run=dry_run,
            delay=delay,
            concurrency=concurrency,
            provider=resolved_provider,
            provider_name=effective_provider_name,
        )
    )
    _print_scan_summary(result, dry_run)


@cli.command("scan-history")
@click.option(
    "--db",
    default=None,
    callback=_resolve_db,
    is_eager=True,
    expose_value=True,
    help="Database URL (default: auto-detect)",
)
@click.option("--limit", default=20, type=int, help="Max runs to show")
@click.option("--type", "scan_type", default=None, help="Filter by scan type")
@click.option("--status", default=None, help="Filter by status")
def scan_history(db, limit, scan_type, status):
    """List past scan runs with metrics."""
    from src.database.repository import Repository

    repo = Repository(db)
    runs = repo.list_scan_runs(limit=limit, scan_type=scan_type, status=status)
    _print_scan_history(runs)


def _print_scan_summary(scan_run, dry_run=False):
    """Print scan result summary."""
    prefix = "[DRY RUN] " if dry_run else ""
    click.echo(f"\n{prefix}Scan #{scan_run.id} — {scan_run.status}")
    click.echo(f"  Type:         {scan_run.scan_type}")
    click.echo(f"  Cards total:  {scan_run.cards_total}")
    click.echo(f"  Processed:    {scan_run.cards_processed}")
    click.echo(f"  Failed:       {scan_run.cards_failed}")
    click.echo(f"  Observations: {scan_run.observations_saved}")
    if scan_run.error_summary:
        click.echo(f"  Errors:       {scan_run.error_summary}")


def _print_scan_history(runs):
    """Print scan history table."""
    if not runs:
        click.echo("No scan runs found.")
        return
    click.echo(
        f"{'ID':>5} {'Type':<12} {'Status':<10} {'Total':>6} {'OK':>5} "
        f"{'Fail':>5} {'Obs':>5} {'Started':<20}"
    )
    click.echo("-" * 75)
    for r in runs:
        started = str(r.get("started_at", ""))[:19] if r.get("started_at") else "-"
        click.echo(
            f"{r['id']:>5} {r.get('scan_type', '?'):<12} {r.get('status', '?'):<10} "
            f"{r.get('cards_total', 0):>6} {r.get('cards_processed', 0):>5} "
            f"{r.get('cards_failed', 0):>5} {r.get('observations_saved', 0):>5} {started:<20}"
        )


@cli.command("update-exchange-rate")
@click.option(
    "--db",
    default=None,
    callback=_resolve_db,
    is_eager=True,
    expose_value=True,
    help="Database URL (default: auto-detect)",
)
@click.option("--date", "target_date", default=None, help="Date (YYYY-MM-DD), defaults to today")
@click.option("--backfill-days", default=0, type=int, help="Fetch rates for last N days")
def update_exchange_rate(db, target_date, backfill_days):
    """Fetch USD/BRL exchange rate from BCB PTAX and store it."""
    from datetime import date as date_type
    from datetime import timedelta

    from src.database.repository import Repository
    from src.providers.bcb.client import fetch_daily_rate, fetch_rate_range

    repo = Repository(db_url=db)

    if backfill_days > 0:
        end = date_type.today()
        start = end - timedelta(days=backfill_days)
        click.echo(f"Fetching PTAX rates from {start} to {end}...")
        rates = asyncio.run(fetch_rate_range(start, end))
        if rates:
            repo.bulk_upsert_rates(rates)
            click.echo(f"Stored {len(rates)} exchange rates.")
        else:
            click.echo("No rates returned from BCB.")
    else:
        if target_date:
            d = date_type.fromisoformat(target_date)
        else:
            d = date_type.today()
        click.echo(f"Fetching PTAX rate for {d}...")
        rate = asyncio.run(fetch_daily_rate(d))
        if rate:
            repo.upsert_exchange_rate(rate)
            click.echo(f"Stored rate: 1 USD = R$ {rate.rate}")
        else:
            click.echo(f"No rate available for {d} (weekend/holiday?).")


@cli.command("migrate-user")
@click.option(
    "--db",
    default=None,
    callback=_resolve_db,
    is_eager=True,
    expose_value=True,
    help="Database URL (default: auto-detect)",
)
@click.option("--old-id", default="eduardo", help="Old user ID to migrate from")
@click.option("--new-id", required=True, help="New user ID to migrate to")
def migrate_user(db, old_id, new_id):
    """Migrate collection entries from old user ID to new user ID."""
    from src.database.repository import Repository

    repo = Repository(db_url=db)
    count = repo.migrate_collection_user(old_id, new_id)
    if count > 0:
        click.echo(f"Migrated {count} collection entries from '{old_id}' to '{new_id}'.")
    else:
        click.echo(f"No collection entries found for user '{old_id}'.")


@cli.command("seed-users")
@click.option(
    "--db",
    default=None,
    callback=_resolve_db,
    is_eager=True,
    expose_value=True,
    help="Database URL (default: auto-detect)",
)
def seed_users(db):
    """Create initial seed users (idempotent)."""
    from src.auth.passwords import hash_password
    from src.database.repository import Repository

    log = structlog.get_logger()

    password = os.environ.get("TCG_SEED_PASSWORD", "mudar@123")

    SEED_USERS = [
        {
            "email": "eduardorutkoskididio@gmail.com",
            "display_name": "Eduardo Didio",
        },
    ]

    repo = Repository(db_url=db)
    for user_data in SEED_USERS:
        existing = repo.get_user_by_email(user_data["email"])
        if existing:
            # Ensure existing seed user has is_admin=1
            if not getattr(existing, "is_admin", 0):
                repo.update_user(existing.id, is_admin=1)
                click.echo(f"  Updated is_admin=1: {user_data['email']}")
            log.info("user_exists_skipped", email=user_data["email"])
            click.echo(f"  Skipped (exists): {user_data['email']}")
            continue

        pw_hash = hash_password(password)
        user_row = repo.create_user(
            email=user_data["email"],
            display_name=user_data["display_name"],
            auth_provider="email",
            password_hash=pw_hash,
        )
        # Set admin flag
        repo.update_user(user_row.id, is_admin=1)

        # Grant initial 10k credits for admin users
        repo.update_credit_balance(
            user_id=user_row.id,
            delta=10_000,
            reason="initial_credits",
        )

        log.info("user_created", email=user_data["email"], is_admin=True, credits=10_000)
        click.echo(f"  Created: {user_data['email']} (admin, 10000 credits)")

    # Associate all collection entries with the primary (first) seed user
    primary = repo.get_user_by_email(SEED_USERS[0]["email"])
    if primary:
        primary_uid = str(primary.id)
        from sqlalchemy import update
        from sqlalchemy.orm import Session as SaSession

        from src.database.models import UserCollectionRow

        with SaSession(repo.engine) as session:
            result = session.execute(
                update(UserCollectionRow)
                .where(UserCollectionRow.user_id != primary_uid)
                .values(user_id=primary_uid)
            )
            session.commit()
            reassigned = result.rowcount  # type: ignore[union-attr]

        if reassigned:
            log.info("collection_reassigned", user_id=primary_uid, count=reassigned)
            click.echo(f"  Reassigned {reassigned} collection entries to user {primary.email}")
        else:
            click.echo("  No collection entries needed reassignment.")

    click.echo("\nSeed users done.")


@cli.command("banlist-sync")
@click.option(
    "--db",
    default=None,
    callback=_resolve_db,
    is_eager=True,
    expose_value=True,
    help="Database URL (default: auto-detect)",
)
@click.option(
    "--bulk/--no-bulk", default=True, help="Use bulk NDJSON download (default) or per-card API"
)
@click.option("--limit", default=None, type=int, help="Max cards to process")
def banlist_sync(db, bulk, limit):
    """Sync ban list / legality data from Scryfall."""
    from src.collectors.banlist_sync import run_banlist_sync

    summary = asyncio.run(
        run_banlist_sync(
            db_url=db,
            bulk=bulk,
            limit=limit,
        )
    )
    _print_banlist_sync_summary(summary)


def _print_banlist_sync_summary(summary):
    """Format and print banlist sync summary to stdout."""
    click.echo("")
    click.echo("=" * 60)
    click.echo("  BANLIST SYNC SUMMARY")
    click.echo(f"  Cards processed:         {summary.cards_processed}")
    click.echo(f"  Legalities upserted:     {summary.legalities_upserted}")
    click.echo(f"  Changes detected:        {summary.changes_detected}")
    click.echo(f"  Errors:                  {summary.errors}")
    if summary.finished_at:
        elapsed = (summary.finished_at - summary.started_at).total_seconds()
        minutes = elapsed / 60
        click.echo(f"  Duration:                {elapsed:.1f}s ({minutes:.1f} min)")
    click.echo("=" * 60)


@cli.command("schedule-list")
@click.option(
    "--db",
    default=None,
    callback=_resolve_db,
    is_eager=True,
    expose_value=True,
    help="Database URL (default: auto-detect)",
)
@click.option(
    "--status",
    type=click.Choice(["active", "paused", "disabled"]),
    default=None,
    help="Filter by status",
)
def schedule_list(db, status):
    """List all scheduled scans."""
    from src.database.repository import Repository

    repo = Repository(db_url=db)
    schedules = repo.list_scheduled_scans(status=status)

    if not schedules:
        click.echo("No schedules found.")
        return

    click.echo(
        f"{'ID':>4}  {'Name':<20} {'Cron':<15} {'Status':<10} "
        f"{'Last Run':<20} {'Next Run':<20} {'Errors':>8}"
    )
    click.echo("-" * 100)
    for s in schedules:
        last_run = str(s.get("last_run_at", ""))[:19] if s.get("last_run_at") else "-"
        next_run = str(s.get("next_run_at", ""))[:19] if s.get("next_run_at") else "-"
        errors = f"{s.get('error_count', 0)}/{s.get('max_retries', 3)}"
        click.echo(
            f"{s['id']:>4}  {s['name']:<20} {s['cron_expression']:<15} "
            f"{s['status']:<10} {last_run:<20} {next_run:<20} {errors:>8}"
        )


@cli.command("schedule-add")
@click.option(
    "--db",
    default=None,
    callback=_resolve_db,
    is_eager=True,
    expose_value=True,
    help="Database URL (default: auto-detect)",
)
@click.option("--name", required=True, help="Schedule name")
@click.option("--cron", required=True, help="Cron expression (e.g. '0 6 * * *')")
@click.option("--type", "scan_type", default="collection", help="Scan type")
@click.option("--filters", default="{}", help="JSON filters")
@click.option("--description", default=None, help="Description")
@click.option(
    "--max-retries", default=3, type=int, help="Max consecutive failures before auto-pause"
)
@click.option("--user-id", default="1", help="User ID for the schedule owner")
def schedule_add(db, name, cron, scan_type, filters, description, max_retries, user_id):
    """Add a new scheduled scan."""
    from croniter import croniter

    from src.database.repository import Repository
    from src.scheduler.service import validate_cron

    # Validate cron
    try:
        validate_cron(cron)
    except ValueError as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)

    repo = Repository(db_url=db)
    schedule_id = repo.create_scheduled_scan(
        user_id=user_id,
        name=name,
        cron_expression=cron,
        scan_type=scan_type,
        filters_json=filters,
        description=description,
        max_retries=max_retries,
    )

    # Compute next run for display
    it = croniter(cron)
    next_run = it.get_next()

    click.echo(f"Schedule created: ID={schedule_id}, name='{name}'")
    click.echo(f"  Cron: {cron}")
    click.echo(f"  Next run: {next_run}")


@cli.command("schedule-remove")
@click.option(
    "--db",
    default=None,
    callback=_resolve_db,
    is_eager=True,
    expose_value=True,
    help="Database URL (default: auto-detect)",
)
@click.argument("schedule_id", type=int)
def schedule_remove(db, schedule_id):
    """Remove a scheduled scan by ID."""
    from src.database.repository import Repository

    repo = Repository(db_url=db)
    deleted = repo.delete_scheduled_scan(schedule_id)
    if deleted:
        click.echo(f"Schedule {schedule_id} deleted.")
    else:
        click.echo(f"Error: Schedule {schedule_id} not found.", err=True)
        raise SystemExit(1)


@cli.command("canonize-all")
@click.option("--user-id", required=True, help="User ID to canonize for")
@click.option("--limit", type=int, default=None, help="Max entries to process")
@click.option("--concurrency", type=int, default=3, help="Parallel MYP calls")
@click.option("--dry-run", is_flag=True, help="Show unlinked count without processing")
@click.option(
    "--db",
    default=None,
    callback=_resolve_db,
    is_eager=True,
    expose_value=True,
    help="Database URL (default: auto-detect)",
)
def canonize_all(user_id, limit, concurrency, dry_run, db):
    """Bulk-canonize all unlinked collection entries."""
    from src.collectors.bulk_canonize import _get_unlinked_entries, bulk_canonize
    from src.database.repository import Repository

    repo = Repository(db_url=db)
    engine = repo.engine

    if dry_run:
        entries = _get_unlinked_entries(engine, user_id, limit=None)
        click.echo(f"\n  Unlinked entries: {len(entries)}")
        click.echo("  DRY RUN — no processing performed.\n")
        return

    from src.providers.myp.provider import MypCardsProvider

    async def _run():
        provider = MypCardsProvider()
        try:
            return await bulk_canonize(
                engine=engine,
                user_id=user_id,
                provider=provider,
                concurrency=concurrency,
                limit=limit,
                repo=repo,
            )
        finally:
            await provider.close()

    result = asyncio.run(_run())
    _print_canonize_summary(result)


def _print_canonize_summary(result):
    """Format and print bulk canonize summary to stdout."""
    click.echo("")
    click.echo("=" * 60)
    click.echo("  BULK CANONIZE SUMMARY")
    click.echo(f"  Total:          {result.total}")
    click.echo(f"  Canonized:      {result.canonized}")
    click.echo(f"  Failed:         {result.failed}")
    click.echo(f"  Skipped:        {result.skipped}")
    click.echo(f"  Rate limited:   {result.rate_limited}")
    click.echo("=" * 60)

    if result.errors:
        click.echo(f"\n  Errors ({len(result.errors)}):")
        for err in result.errors[:20]:
            click.echo(f"    - entry {err['entry_id']}: {err['error'][:80]}")
        if len(result.errors) > 20:
            click.echo(f"    ... and {len(result.errors) - 20} more")
    click.echo("")


@cli.command("liga-sweep")
@click.option(
    "--db",
    default=None,
    help="Database URL (default from TCG_DATABASE_URL or sqlite:///tcg_market.db)",
)
@click.option("--batch-size", default=20, type=int, help="Cards per batch")
@click.option("--batch-pause", default=60, type=int, help="Seconds between batches")
@click.option("--delay", default=5.0, type=float, help="Seconds between cards")
@click.option(
    "--max-age-days", default=7, type=int, help="Skip cards with Liga price newer than N days"
)
@click.option("--limit", default=None, type=int, help="Max total cards to process")
@click.option("--dry-run", is_flag=True, help="Show eligible count without fetching")
@click.option("--set", "set_filter", default=None, help="Only sweep this set code")
def liga_sweep(db, batch_size, batch_pause, delay, max_age_days, limit, dry_run, set_filter):
    """Sweep entire collection through LigaMagic with configurable pacing."""
    from src.collectors.liga_sweep import run_liga_sweep

    result = asyncio.run(
        run_liga_sweep(
            db_url=db,
            batch_size=batch_size,
            batch_pause=batch_pause,
            delay=delay,
            max_age_days=max_age_days,
            limit=limit,
            dry_run=dry_run,
            set_filter=set_filter,
        )
    )
    _print_liga_sweep_summary(result)


def _print_liga_sweep_summary(result):
    """Format and print Liga sweep summary to stdout."""
    click.echo("")
    click.echo("=" * 60)
    if result.dry_run:
        click.echo("  DRY RUN -- no data was fetched")
    click.echo("  LIGA SWEEP SUMMARY")
    click.echo(f"  Eligible cards:          {result.total_eligible}")
    click.echo(f"  Processed:               {result.total_processed}")
    click.echo(f"  Prices found:            {result.prices_found}")
    click.echo(f"  Prices not found:        {result.prices_not_found}")
    click.echo(f"  Errors:                  {result.errors}")
    click.echo(f"  Batches completed:       {result.batches_completed}")
    click.echo("=" * 60)


@cli.command("snapshot-portfolio")
@click.option(
    "--db",
    default=None,
    callback=_resolve_db,
    is_eager=True,
    expose_value=True,
    help="Database URL (default: auto-detect)",
)
@click.option(
    "--user-id", default=None, help="Snapshot a specific user (default: all active users)"
)
def snapshot_portfolio(db, user_id):
    """Take a daily portfolio value snapshot for all (or one) user(s)."""
    from src.collectors.portfolio_snapshot import take_snapshot
    from src.database.repository import Repository

    repo = Repository(db_url=db)

    if user_id:
        result = take_snapshot(user_id, repo)
        click.echo(f"  Snapshot: user={result['user_id']}, value=R$ {result['value']:.2f}")
    else:
        from sqlalchemy.orm import Session as SaSession

        from src.database.models import UserRow

        with SaSession(repo.engine) as session:
            users = (
                session.execute(
                    __import__("sqlalchemy").select(UserRow).where(UserRow.is_active == 1)
                )
                .scalars()
                .all()
            )
            user_ids = [str(u.id) for u in users]

        if not user_ids:
            click.echo("No active users found.")
            return

        total_value = 0
        for uid in user_ids:
            result = take_snapshot(uid, repo)
            val = float(result["value"])
            total_value += val
            click.echo(f"  Snapshot: user={uid}, value=R$ {val:.2f}")

        click.echo(
            f"\nSnapshotted {len(user_ids)} users, total portfolio value: R$ {total_value:.2f}"
        )


@cli.command("db-reset-scans")
@click.option(
    "--db",
    default=None,
    callback=_resolve_db,
    is_eager=True,
    expose_value=True,
    help="Database URL (default: auto-detect)",
)
@click.option("--confirm", is_flag=True, help="Confirm deletion of all scan runs")
def db_reset_scans(db, confirm):
    """Delete all scan run records."""
    if not confirm:
        click.echo("Pass --confirm to delete all scan runs.")
        return
    from src.database.repository import Repository

    repo = Repository(db)
    count = repo.delete_all_scan_runs()
    click.echo(f"Deleted {count} scan runs.")


@cli.command("reset-prices")
@click.option(
    "--db",
    default=None,
    help="Database URL (default from TCG_DATABASE_URL or sqlite:///tcg_market.db)",
)
@click.option(
    "--source",
    default=None,
    help="Only delete observations from this source (e.g. liga, myp, manual, jsonld_snapshot)",
)
@click.option("--confirm", is_flag=True, help="Required to actually delete (without it, dry-run)")
def reset_prices(db, source, confirm):
    """Reset (delete) all price observations, optionally filtered by source.

    Unlike db-clear-prices, this command has NO protected-source restrictions
    and can delete liga/manual observations. Use with care.
    """
    from sqlalchemy import func, select
    from sqlalchemy.orm import Session

    from src.config import get_db_url
    from src.database.backup import backup_database, extract_db_path
    from src.database.models import PriceObservationRow
    from src.database.repository import Repository

    db_url = db or get_db_url()
    repo = Repository(db_url=db_url)

    # Count rows that would be deleted
    with Session(repo.engine) as session:
        stmt = select(func.count()).select_from(PriceObservationRow)
        if source is not None:
            stmt = stmt.where(PriceObservationRow.source == source)
        count = session.execute(stmt).scalar() or 0

    source_label = f"source='{source}'" if source else "ALL sources"
    click.echo(f"\n  Price observations matching {source_label}: {count}")

    if not confirm:
        click.echo("  [DRY RUN] No rows deleted. Pass --confirm to actually delete.\n")
        return

    if count == 0:
        click.echo("  Nothing to delete.\n")
        return

    # Backup before deleting
    db_path = extract_db_path(db_url)
    backup_path = backup_database(db_path)

    # Delete
    deleted = repo.delete_all_price_observations(source=source)

    # VACUUM to reclaim space
    from sqlalchemy import text

    with repo.engine.connect() as conn:
        conn.execute(text("VACUUM"))
        conn.commit()

    click.echo(f"  Deleted {deleted} price observations.")
    click.echo(f"  Backup saved to: {backup_path}\n")


@cli.command("db-reset")
@click.option(
    "--db",
    default=None,
    help="Database URL (default from TCG_DATABASE_URL or sqlite:///tcg_market.db)",
)
@click.option("--confirm", is_flag=True, help="Required to actually delete")
@click.option("--skip-backup", is_flag=True, help="Skip pre-delete backup")
def db_reset(db, confirm, skip_backup):
    """Reset prices + remove non-collection cards. Preserves collection, users, decks."""
    from src.config import get_db_url
    from src.database.cleanup import reset_database

    db_url = db or get_db_url()

    try:
        result = reset_database(
            db_url=db_url,
            dry_run=not confirm,
            skip_backup=skip_backup,
        )
    except ValueError as exc:
        click.echo(f"Error: {exc}", err=True)
        raise SystemExit(1) from exc

    if result.dry_run:
        click.echo("")
        click.echo("  DATABASE RESET PREVIEW (dry-run)")
        click.echo("")
        click.echo("  Will delete:")
        click.echo(f"    Price observations:     {result.prices_deleted:,}")
        click.echo(f"    Scan runs:              {result.scan_runs_deleted:,}")
        click.echo(f"    Portfolio snapshots:     {result.portfolio_snapshots_deleted:,}")
        click.echo(f"    Collection errors:      {result.collection_errors_deleted:,}")
        click.echo(f"    Cards (non-collection): {result.cards_deleted:,}")
        click.echo(f"    Source cards:            {result.source_cards_deleted:,}")
        click.echo(f"    Card legalities:        {result.legalities_deleted:,}")
        click.echo(f"    Legality history:       {result.legality_history_deleted:,}")
        click.echo("")
        click.echo("  Will keep:")
        click.echo(f"    Cards (in collection):  {result.cards_kept:,}")
        click.echo("")
        click.echo("  Pass --confirm to execute.")
        click.echo("")
    else:
        click.echo("")
        click.echo("  DATABASE RESET COMPLETE")
        click.echo("")
        click.echo("  Deleted:")
        click.echo(f"    Price observations:     {result.prices_deleted:,}")
        click.echo(f"    Scan runs:              {result.scan_runs_deleted:,}")
        click.echo(f"    Portfolio snapshots:     {result.portfolio_snapshots_deleted:,}")
        click.echo(f"    Collection errors:      {result.collection_errors_deleted:,}")
        click.echo(f"    Cards (non-collection): {result.cards_deleted:,}")
        click.echo(f"    Source cards:            {result.source_cards_deleted:,}")
        click.echo(f"    Card legalities:        {result.legalities_deleted:,}")
        click.echo(f"    Legality history:       {result.legality_history_deleted:,}")
        click.echo("")
        click.echo(f"  Cards kept (in collection): {result.cards_kept:,}")
        if result.backup_path:
            click.echo(f"  Backup saved to: {result.backup_path}")
        click.echo("")


@cli.command("error-cleanup")
@click.option("--db", default=None, help="Database URL")
@click.option(
    "--max-age-days",
    default=None,
    type=int,
    help="Max age in days (default from TCG_ERROR_MAX_AGE_DAYS or 30)",
)
@click.option(
    "--max-entries",
    default=None,
    type=int,
    help="Max entries to keep (default from TCG_ERROR_MAX_ENTRIES or 10000)",
)
@click.option("--dry-run", is_flag=True, help="Show what would be removed without removing")
def error_cleanup(db, max_age_days, max_entries, dry_run):
    """Clean up old error logs from database and JSONL file."""
    from src.config import (
        get_db_url,
        get_error_log_dir,
        get_error_max_age_days,
        get_error_max_entries,
    )
    from src.database.repository import Repository
    from src.errors.retention import cleanup_db, cleanup_jsonl

    db_url = db or get_db_url()
    age = max_age_days if max_age_days is not None else get_error_max_age_days()
    entries = max_entries if max_entries is not None else get_error_max_entries()

    repo = Repository(db_url=db_url)
    jsonl_path = os.path.join(get_error_log_dir(), "errors.jsonl")

    click.echo(f"\n  Error Cleanup (max_age_days={age}, max_entries={entries})")

    if dry_run:
        click.echo("  [DRY RUN] No entries will be removed.\n")
        # Show current counts
        from sqlalchemy import func, select
        from sqlalchemy.orm import Session

        from src.database.models import ErrorLogRow

        with Session(repo.engine) as session:
            db_count = session.execute(select(func.count()).select_from(ErrorLogRow)).scalar() or 0

        jsonl_count = 0
        if os.path.exists(jsonl_path):
            with open(jsonl_path, "r") as f:
                jsonl_count = sum(1 for line in f if line.strip())

        click.echo(f"  Database entries: {db_count}")
        click.echo(f"  JSONL entries:    {jsonl_count}\n")
        return

    # Run cleanup
    db_removed = cleanup_db(repo, age, entries)
    jsonl_removed = cleanup_jsonl(jsonl_path, age, entries)

    click.echo(f"  Database entries removed: {db_removed}")
    click.echo(f"  JSONL entries removed:    {jsonl_removed}\n")


@cli.command("push-prices")
@click.option(
    "--db",
    default=None,
    callback=_resolve_db,
    is_eager=True,
    expose_value=True,
    help="Database URL (default: auto-detect)",
)
@click.option(
    "--remote", required=True, help="Remote API base URL (e.g. https://tedhc.onrender.com)"
)
@click.option(
    "--api-key", envvar="TCG_API_KEY", default=None, help="API key for remote ($TCG_API_KEY)"
)
@click.option("--delay", default=5.0, type=float, help="Seconds between Liga requests")
@click.option("--limit", default=None, type=int, help="Max cards to process")
@click.option("--dry-run", is_flag=True, help="Fetch prices but don't push to remote")
@click.option("--max-age-days", default=None, type=int, help="Skip cards scanned within N days")
def push_prices(db, remote, api_key, delay, limit, dry_run, max_age_days):
    """Scan collection prices via Liga locally, push results to remote API.

    Runs LigaMagic price scan on your local machine (requires Playwright),
    then POSTs the price observations to the remote Render deployment.

    Example:
        collector push-prices --remote https://tedhc.onrender.com --api-key SECRET
    """
    asyncio.run(_push_prices_async(db, remote, api_key, delay, limit, dry_run, max_age_days))


async def _push_prices_async(db, remote, api_key, delay, limit, dry_run, max_age_days):
    from datetime import date
    from decimal import Decimal

    import httpx

    from src.collection.converter import is_foil_entry
    from src.database.repository import Repository
    from src.domain.models import ScanFilter
    from src.providers.liga.provider import LigaMagicProvider

    repo = Repository(db_url=db)
    scan_filter = ScanFilter(limit=limit)
    entries = repo.get_cards_for_liga_scan(scan_filter, max_age_days=max_age_days)
    total = len(entries)

    if total == 0:
        click.echo("No cards to scan.")
        return

    click.echo(f"Found {total} cards to scan via Liga.")

    provider = LigaMagicProvider()
    observations = []
    processed = 0
    failed = 0

    try:
        await provider.open()

        for i, entry in enumerate(entries, 1):
            card_id = entry["card_id"]
            card_name = entry.get("name_en") or entry.get("name_pt", "")
            is_foil = is_foil_entry(entry.get("extras"))

            if not card_name:
                click.echo(f"  [{i}/{total}] Skipped (no name) card_id={card_id}")
                continue

            try:
                prices = await provider.search_card(card_name)

                if is_foil:
                    foil = prices.get("foil", {})
                    price: Decimal | None = foil.get("low") or foil.get("mid") or foil.get("high")
                    external_id = f"liga_{card_id}_foil"
                else:
                    normal = prices.get("normal", {})
                    price = normal.get("low") or normal.get("mid") or normal.get("high")
                    external_id = f"liga_{card_id}"

                if price is not None:
                    observations.append(
                        {
                            "source": "liga",
                            "external_id": external_id,
                            "observed_at": date.today().isoformat(),
                            "median_price": str(price),
                            "currency": "BRL",
                        }
                    )
                    click.echo(f"  [{i}/{total}] {card_name}: R${price}")
                    processed += 1
                else:
                    click.echo(f"  [{i}/{total}] {card_name}: no price")
                    failed += 1

            except Exception as exc:
                click.echo(f"  [{i}/{total}] {card_name}: ERROR {exc}")
                failed += 1

            if i < total:
                await asyncio.sleep(delay)

    finally:
        await provider.close()

    click.echo(f"\nScan complete: {processed} prices, {failed} failed, {total} total.")

    if not observations:
        click.echo("No prices to push.")
        return

    if dry_run:
        click.echo(f"[DRY RUN] Would push {len(observations)} observations to {remote}")
        return

    # Push to remote
    remote_url = remote.rstrip("/") + "/api/v1/prices/ingest"
    headers = {}
    if api_key:
        headers["X-API-Key"] = api_key

    click.echo(f"Pushing {len(observations)} observations to {remote_url}...")

    # Send in batches of 500
    batch_size = 500
    total_inserted = 0
    for start in range(0, len(observations), batch_size):
        batch = observations[start : start + batch_size]
        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(
                remote_url,
                json={"observations": batch},
                headers=headers,
            )
        if resp.status_code == 200:
            result = resp.json().get("data", {})
            inserted = result.get("inserted", 0)
            total_inserted += inserted
            click.echo(f"  Batch {start // batch_size + 1}: {inserted} inserted")
        else:
            click.echo(f"  Batch {start // batch_size + 1}: FAILED {resp.status_code} {resp.text}")

    click.echo(f"\nDone! {total_inserted} prices pushed to remote.")


@cli.command("push-db")
@click.option(
    "--db",
    default=None,
    callback=_resolve_db,
    is_eager=True,
    expose_value=True,
    help="Database URL (default: auto-detect)",
)
@click.option(
    "--remote", required=True, help="Remote API base URL (e.g. https://tedhc.onrender.com)"
)
@click.option(
    "--api-key", envvar="TCG_API_KEY", default=None, help="API key for remote ($TCG_API_KEY)"
)
def push_db(db, remote, api_key):
    """Upload local SQLite database to the remote deployment.

    Use this after a Render restart to restore your collection data.

    Example:
        collector push-db --remote https://tedhc.onrender.com --api-key SECRET
    """
    import httpx

    # Extract file path from sqlite URL
    raw = db.replace("sqlite:///", "", 1)
    db_path = os.path.join(os.getcwd(), raw) if not os.path.isabs(raw) else raw

    if not os.path.exists(db_path):
        click.echo(f"Database file not found: {db_path}")
        raise SystemExit(1)

    size_mb = os.path.getsize(db_path) / (1024 * 1024)
    click.echo(f"Uploading {db_path} ({size_mb:.1f} MB) to {remote}...")

    url = remote.rstrip("/") + "/api/v1/db/restore"
    headers = {}
    if api_key:
        headers["X-API-Key"] = api_key

    with open(db_path, "rb") as f:
        resp = httpx.post(
            url,
            files={"file": ("tcg_market.db", f, "application/octet-stream")},
            headers=headers,
            timeout=300.0,
        )

    if resp.status_code == 200:
        data = resp.json().get("data", {})
        click.echo(f"OK — {data.get('status', 'done')}, {data.get('size_bytes', 0)} bytes")
    else:
        click.echo(f"FAILED: {resp.status_code} {resp.text}")
        raise SystemExit(1)


@cli.command("pull-db")
@click.option(
    "--remote", required=True, help="Remote API base URL (e.g. https://tedhc.onrender.com)"
)
@click.option(
    "--api-key", envvar="TCG_API_KEY", default=None, help="API key for remote ($TCG_API_KEY)"
)
@click.option(
    "--output",
    default="tcg_market_remote.db",
    help="Output file path (default: tcg_market_remote.db)",
)
def pull_db(remote, api_key, output):
    """Download the remote SQLite database to a local file.

    Use this to backup the remote DB before a Render restart.

    Example:
        collector pull-db --remote https://tedhc.onrender.com --api-key SECRET
    """
    import httpx

    url = remote.rstrip("/") + "/api/v1/db/backup"
    headers = {}
    if api_key:
        headers["X-API-Key"] = api_key

    click.echo(f"Downloading database from {remote}...")

    with httpx.stream("GET", url, headers=headers, timeout=120.0) as resp:
        if resp.status_code != 200:
            click.echo(f"FAILED: {resp.status_code}")
            raise SystemExit(1)

        with open(output, "wb") as f:
            for chunk in resp.iter_bytes(chunk_size=8192):
                f.write(chunk)

    size_mb = os.path.getsize(output) / (1024 * 1024)
    click.echo(f"OK — saved to {output} ({size_mb:.1f} MB)")


@cli.command("backup-r2")
@click.option(
    "--db",
    default=None,
    callback=_resolve_db,
    is_eager=True,
    expose_value=True,
    help="Database URL (default: auto-detect)",
)
def backup_r2(db):
    """Force a Litestream snapshot to R2 (requires litestream binary + R2 env vars)."""
    import shutil
    import subprocess

    if not shutil.which("litestream"):
        click.echo("Error: litestream binary not found in PATH.", err=True)
        raise SystemExit(1)

    config = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "litestream.yml"
    )
    if not os.path.exists(config):
        config = "litestream.yml"

    if not os.environ.get("LITESTREAM_REPLICA_BUCKET"):
        click.echo("Error: LITESTREAM_REPLICA_BUCKET env var not set.", err=True)
        raise SystemExit(1)

    from src.database.backup import extract_db_path

    db_path = extract_db_path(db)
    click.echo(f"Triggering Litestream snapshot for {db_path}...")

    result = subprocess.run(
        ["litestream", "snapshots", "-config", config, db_path],
        capture_output=True,
        text=True,
    )
    if result.returncode == 0:
        click.echo(f"Current snapshots:\n{result.stdout}")
    else:
        click.echo(f"Warning: could not list snapshots: {result.stderr}")

    result = subprocess.run(
        ["litestream", "replicate", "-config", config, "-exec", "true"],
        capture_output=True,
        text=True,
        timeout=30,
    )
    if result.returncode == 0:
        click.echo("Snapshot pushed to R2 successfully.")
    else:
        click.echo(f"Error: {result.stderr}", err=True)
        raise SystemExit(1)


@cli.command("restore-r2")
@click.option(
    "--db",
    default=None,
    callback=_resolve_db,
    is_eager=True,
    expose_value=True,
    help="Database URL (default: auto-detect)",
)
@click.option("--confirm", is_flag=True, help="Required to overwrite local database")
def restore_r2(db, confirm):
    """Restore SQLite database from R2 via Litestream."""
    import shutil
    import subprocess

    if not shutil.which("litestream"):
        click.echo("Error: litestream binary not found in PATH.", err=True)
        raise SystemExit(1)

    if not os.environ.get("LITESTREAM_REPLICA_BUCKET"):
        click.echo("Error: LITESTREAM_REPLICA_BUCKET env var not set.", err=True)
        raise SystemExit(1)

    from src.database.backup import extract_db_path

    db_path = extract_db_path(db)

    if not confirm:
        click.echo(f"This will overwrite {db_path} with the latest R2 backup.")
        click.echo("Pass --confirm to proceed.")
        return

    config = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "litestream.yml"
    )
    if not os.path.exists(config):
        config = "litestream.yml"

    # Backup current DB before overwriting
    if os.path.exists(db_path):
        from src.database.backup import backup_database

        backup_path = backup_database(db_path)
        click.echo(f"Current DB backed up to: {backup_path}")

    click.echo(f"Restoring {db_path} from R2...")
    result = subprocess.run(
        ["litestream", "restore", "-config", config, "-if-replica-exists", db_path],
        capture_output=True,
        text=True,
    )
    if result.returncode == 0:
        if os.path.exists(db_path):
            size_mb = os.path.getsize(db_path) / (1024 * 1024)
            click.echo(f"Restored successfully ({size_mb:.1f} MB).")
        else:
            click.echo("No replica found in R2. Database not restored.")
    else:
        click.echo(f"Error: {result.stderr}", err=True)
        raise SystemExit(1)


@cli.command()
@click.option("--host", default="0.0.0.0", help="Host to bind to")
@click.option("--port", default=8000, type=int, help="Port to bind to")
@click.option(
    "--production",
    is_flag=True,
    default=False,
    help="Run in production mode (no reload, respect $PORT)",
)
def serve(host, port, production):
    """Start the REST API server."""
    from src.api.app import run_server

    run_server(host=host, port=port, production=production)


if __name__ == "__main__":
    cli()
