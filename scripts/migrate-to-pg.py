#!/usr/bin/env python3
"""One-time migration from SQLite to PostgreSQL (Neon).

Usage:
    python scripts/migrate-to-pg.py \
        --source sqlite:///tcg_market.db \
        --target "postgresql://user:pass@host/db?sslmode=require"

    Or using environment variables:
    DATABASE_URL="postgresql://..." python scripts/migrate-to-pg.py

    Dry-run (shows row counts without writing):
    python scripts/migrate-to-pg.py --dry-run
"""

from __future__ import annotations

import os
import sys
import time

import click
from sqlalchemy import MetaData, create_engine, text
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.exc import SQLAlchemyError

# Table migration order respecting FK dependencies.
# Level 0: no foreign keys (independent tables)
# Level 1: depends on level-0 tables only
# Level 2: depends on level-1 tables
MIGRATION_ORDER: list[str] = [
    # Level 0 — no FKs
    "users",
    "cards",
    "scan_runs",
    "exchange_rates",
    "scheduled_scans",
    "collection_errors",
    "portfolio_snapshots",
    "audit_log",
    "error_log",
    "price_observations",
    # Level 1 — depends on users or cards
    "source_cards",
    "user_collection",
    "card_legalities",
    "legality_history",
    "evaluation_entries",
    "decks",
    "credit_balances",
    "credit_transactions",
    "shared_collections",
    "achievements",
    "wishlist",
    "price_alerts",
    # Level 2 — depends on level-1 tables
    "deck_cards",
    "trade_interests",
    "alert_notifications",
    # Level 3
    "trade_agreements",
]

BATCH_SIZE = 1000


def _table_has_id_pk(table) -> bool:
    """Check if a table has an integer 'id' primary key (for sequence reset)."""
    for col in table.primary_key.columns:
        if col.name == "id" and str(col.type).upper().startswith("INT"):
            return True
    return False


def _migrate_table(
    source_engine,
    target_engine,
    source_meta: MetaData,
    target_meta: MetaData,
    table_name: str,
    dry_run: bool,
) -> int:
    """Migrate a single table from source to target. Returns row count."""
    source_table = source_meta.tables[table_name]
    target_table = target_meta.tables[table_name]

    with source_engine.connect() as src_conn:
        total = src_conn.execute(text(f"SELECT COUNT(*) FROM {table_name}")).scalar()

        if dry_run:
            return total

        rows_migrated = 0
        result = src_conn.execute(source_table.select())

        while True:
            batch = result.fetchmany(BATCH_SIZE)
            if not batch:
                break

            rows_as_dicts = [dict(row._mapping) for row in batch]

            with target_engine.begin() as tgt_conn:
                stmt = pg_insert(target_table).values(rows_as_dicts)
                # ON CONFLICT DO NOTHING makes the script re-runnable
                if target_table.primary_key.columns:
                    pk_cols = [col.name for col in target_table.primary_key.columns]
                    stmt = stmt.on_conflict_do_nothing(index_elements=pk_cols)
                else:
                    stmt = stmt.on_conflict_do_nothing()

                tgt_conn.execute(stmt)

            rows_migrated += len(batch)

    return rows_migrated


def _reset_sequences(target_engine, target_meta: MetaData, tables: list[str]):
    """Reset PostgreSQL sequences for all tables with integer 'id' PKs."""
    click.echo("\nResetting sequences...")
    with target_engine.begin() as conn:
        for table_name in tables:
            if table_name not in target_meta.tables:
                continue
            table = target_meta.tables[table_name]
            if not _table_has_id_pk(table):
                continue

            try:
                seq_name = conn.execute(
                    text(f"SELECT pg_get_serial_sequence('{table_name}', 'id')")
                ).scalar()

                if seq_name is None:
                    # Table may use GENERATED ALWAYS or have no sequence
                    continue

                conn.execute(
                    text(
                        f"SELECT setval('{seq_name}', "
                        f"COALESCE((SELECT MAX(id) FROM {table_name}), 0) + 1, "
                        f"false)"
                    )
                )
                click.echo(f"  {table_name}.id sequence reset")
            except SQLAlchemyError as exc:
                click.echo(
                    f"  WARNING: could not reset sequence for {table_name}: {exc}",
                    err=True,
                )


@click.command()
@click.option(
    "--source",
    default="sqlite:///tcg_market.db",
    show_default=True,
    help="Source SQLite connection string.",
)
@click.option(
    "--target",
    default=None,
    help="Target PostgreSQL connection string. Defaults to DATABASE_URL env var.",
)
@click.option(
    "--dry-run",
    is_flag=True,
    default=False,
    help="Show what would be migrated without writing.",
)
@click.option(
    "--batch-size",
    default=BATCH_SIZE,
    show_default=True,
    help="Number of rows per INSERT batch.",
)
def migrate(source: str, target: str | None, dry_run: bool, batch_size: int):
    """Migrate all data from SQLite to PostgreSQL (Neon).

    Tables are migrated in FK dependency order. Uses ON CONFLICT DO NOTHING
    so the script is safe to re-run.
    """
    global BATCH_SIZE
    BATCH_SIZE = batch_size

    if target is None:
        target = os.environ.get("DATABASE_URL")
        if not target:
            click.echo(
                "ERROR: --target not provided and DATABASE_URL not set.",
                err=True,
            )
            sys.exit(1)

    # Validate connection strings
    if "sqlite" not in source.lower():
        click.echo(f"WARNING: source does not look like SQLite: {source}", err=True)
    if "postgresql" not in target.lower() and "postgres" not in target.lower():
        click.echo("ERROR: target must be a PostgreSQL connection string.", err=True)
        sys.exit(1)

    click.echo(f"Source: {source}")
    click.echo(f"Target: {target[:40]}..." if len(target) > 40 else f"Target: {target}")
    if dry_run:
        click.echo("Mode:   DRY RUN (no writes)")
    click.echo()

    # Connect
    try:
        source_engine = create_engine(source)
        with source_engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        click.echo("Source connection OK")
    except Exception as exc:
        click.echo(f"ERROR: cannot connect to source: {exc}", err=True)
        sys.exit(1)

    try:
        target_engine = create_engine(target)
        with target_engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        click.echo("Target connection OK")
    except Exception as exc:
        click.echo(f"ERROR: cannot connect to target: {exc}", err=True)
        sys.exit(1)

    # Reflect metadata from both databases
    source_meta = MetaData()
    source_meta.reflect(bind=source_engine)
    source_tables = set(source_meta.tables.keys())

    target_meta = MetaData()
    target_meta.reflect(bind=target_engine)
    target_tables = set(target_meta.tables.keys())

    click.echo(f"\nSource tables: {len(source_tables)}")
    click.echo(f"Target tables: {len(target_tables)}")

    # Determine which tables to migrate
    tables_to_migrate = []
    skipped = []
    for table_name in MIGRATION_ORDER:
        if table_name not in source_tables:
            skipped.append((table_name, "not in source"))
            continue
        if table_name not in target_tables:
            skipped.append((table_name, "not in target"))
            continue
        tables_to_migrate.append(table_name)

    # Check for tables in source that are not in MIGRATION_ORDER
    unordered = source_tables - set(MIGRATION_ORDER)
    # Filter out internal SQLite tables and _old migration leftovers
    unordered = {
        t
        for t in unordered
        if not t.startswith("sqlite_") and not t.endswith("_old") and not t.startswith("alembic")
    }

    if unordered:
        click.echo(
            f"\nWARNING: tables in source but not in MIGRATION_ORDER: {unordered}",
            err=True,
        )
        click.echo("These tables will NOT be migrated. Add them to MIGRATION_ORDER.")

    if skipped:
        click.echo("\nSkipped tables:")
        for name, reason in skipped:
            click.echo(f"  {name}: {reason}")

    click.echo(f"\nMigrating {len(tables_to_migrate)} tables...")
    click.echo("-" * 60)

    total_rows = 0
    start_all = time.time()
    results = []

    for table_name in tables_to_migrate:
        start_table = time.time()
        try:
            count = _migrate_table(
                source_engine,
                target_engine,
                source_meta,
                target_meta,
                table_name,
                dry_run,
            )
            elapsed = time.time() - start_table
            action = "found" if dry_run else "migrated"
            click.echo(f"  {table_name:<30s} {count:>8d} rows {action} ({elapsed:.1f}s)")
            total_rows += count
            results.append((table_name, count, None))
        except Exception as exc:
            elapsed = time.time() - start_table
            click.echo(f"  {table_name:<30s} ERROR ({elapsed:.1f}s): {exc}", err=True)
            results.append((table_name, 0, str(exc)))

    # Reset sequences (only for actual migration, not dry-run)
    if not dry_run:
        _reset_sequences(target_engine, target_meta, tables_to_migrate)

    # Summary
    elapsed_all = time.time() - start_all
    click.echo("-" * 60)
    action = "found" if dry_run else "migrated"
    click.echo(f"Total: {total_rows} rows {action} in {elapsed_all:.1f}s")

    errors = [r for r in results if r[2] is not None]
    if errors:
        click.echo(f"\n{len(errors)} table(s) had errors:")
        for name, _, err in errors:
            click.echo(f"  {name}: {err}")
        sys.exit(1)

    if dry_run:
        click.echo("\nDry run complete. No data was written.")
    else:
        click.echo("\nMigration complete!")


if __name__ == "__main__":
    migrate()
