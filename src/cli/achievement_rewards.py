"""Standalone `backfill-achievement-rewards` CLI command (F179-T05).

Kept in its own module (not src/cli/main.py) to avoid a circular import:
main.py registers this command via `cli.add_command(backfill_achievement_rewards_cmd)`.
"""

from __future__ import annotations

import click


def _resolve_db(ctx, param, value):
    """Click callback: resolve --db to auto-detected URL when None.

    Duplicated from src.cli.main._resolve_db (5 lines) rather than imported,
    since importing main.py here would create a circular import once main.py
    registers this command.
    """
    if value is None:
        from src.config import get_db_url

        return get_db_url()
    return value


@click.command("backfill-achievement-rewards")
@click.option(
    "--db",
    default=None,
    callback=_resolve_db,
    is_eager=True,
    expose_value=True,
    help="Database URL (default: auto-detect)",
)
@click.option("--dry-run", is_flag=True, help="Show what would be credited without writing")
@click.option("--user-id", type=int, default=None, help="Only backfill this user")
@click.pass_context
def backfill_achievement_rewards_cmd(ctx, db, dry_run, user_id):
    """Credit Treasure rewards for achievements unlocked before F179."""
    from src.database.repository import Repository
    from src.services.achievement_rewards import backfill_all_rewards

    repo = Repository(db_url=db)
    result = backfill_all_rewards(repo, dry_run=dry_run, user_id=user_id)

    click.echo(
        f"Backfill complete: {result['users']} users, {result['credited_rows']} rewards, "
        f"{result['total_tokens']} Tesouros credited (dry-run: {'yes' if dry_run else 'no'})"
    )

    if result["errors"] > 0:
        click.echo(f"WARNING: {result['errors']} user(s) failed during backfill")
        ctx.exit(1)
