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
@click.option("--db", default="sqlite:///tcg_market.db", help="Database URL")
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
def scan(
    db, scan_type, set_codes, format_name, rarity, card_ids, limit, dry_run, delay, concurrency
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

    result = asyncio.run(
        run_scan(
            db_url=db,
            scan_filter=sf,
            dry_run=dry_run,
            delay=delay,
            concurrency=concurrency,
        )
    )
    _print_scan_summary(result, dry_run)


@cli.command("scan-history")
@click.option("--db", default="sqlite:///tcg_market.db", help="Database URL")
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
@click.option("--db", default="sqlite:///tcg_market.db", help="Database URL")
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
@click.option("--db", default="sqlite:///tcg_market.db", help="Database URL")
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
@click.option("--db", default="sqlite:///tcg_market.db", help="Database URL")
def seed_users(db):
    """Create initial seed users (idempotent)."""
    import secrets

    from src.auth.passwords import hash_password
    from src.database.repository import Repository

    log = structlog.get_logger()

    password = os.environ.get("TCG_SEED_PASSWORD")
    if password is None:
        password = secrets.token_urlsafe(16)
        click.echo(f"  No TCG_SEED_PASSWORD set — generated password: {password}")

    SEED_USERS = [
        {
            "email": "eduardorutkoskididio@gmail.com",
            "display_name": "Eduardo Didio",
        },
        {"email": "anderson.serafim", "display_name": "Anderson Serafim"},
    ]

    repo = Repository(db_url=db)
    for user_data in SEED_USERS:
        existing = repo.get_user_by_email(user_data["email"])
        if existing:
            log.info("user_exists_skipped", email=user_data["email"])
            click.echo(f"  Skipped (exists): {user_data['email']}")
            continue

        pw_hash = hash_password(password)
        repo.create_user(
            email=user_data["email"],
            display_name=user_data["display_name"],
            auth_provider="email",
            password_hash=pw_hash,
        )
        log.info("user_created", email=user_data["email"])
        click.echo(f"  Created: {user_data['email']}")

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
@click.option("--db", default="sqlite:///tcg_market.db", help="Database URL")
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
@click.option("--db", default="sqlite:///tcg_market.db", help="Database URL")
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
@click.option("--db", default="sqlite:///tcg_market.db", help="Database URL")
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
@click.option("--db", default="sqlite:///tcg_market.db", help="Database URL")
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
@click.option("--db", default="sqlite:///tcg_market.db", help="Database URL")
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


@cli.command()
@click.option("--host", default="0.0.0.0", help="Host to bind to")
@click.option("--port", default=8000, type=int, help="Port to bind to")
def serve(host, port):
    """Start the REST API server."""
    from src.api.app import run_server

    run_server(host=host, port=port)


if __name__ == "__main__":
    cli()
