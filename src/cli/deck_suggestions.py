"""Standalone click command: process pending deck suggestions (F172).

Registered on the main CLI group by ``src/cli/main.py``. This module must not
import from ``src.cli.main`` (that would be a circular import).

Exit codes: 0 when the batch ran (even if some requests failed),
2 on a configuration error (unknown provider, missing CLI binary or API key) —
in that case no request is claimed.
"""

from __future__ import annotations

import sys

import click

from src.deck_suggestions.claude_runner import ClaudeRunnerError, get_runner

EXIT_CONFIG_ERROR = 2


@click.command("process-deck-suggestions")
@click.option("--db", default=None, help="Database URL (default: auto-detect)")
@click.option(
    "--limit", default=5, type=int, show_default=True, help="Max requests to process"
)
@click.option(
    "--provider",
    type=click.Choice(["cli", "api"]),
    default=None,
    help="Claude provider (default: $DECK_SUGGEST_PROVIDER or cli)",
)
@click.option("--dry-run", is_flag=True, help="Show pending count without processing")
def process_deck_suggestions(db, limit, provider, dry_run):
    """Ask Claude to build the pending deck suggestions (daily routine)."""
    from src.database.repository import Repository
    from src.deck_suggestions.processor import process_pending_suggestions

    if db is None:
        from src.config import get_db_url

        db = get_db_url()

    if dry_run:
        repo = Repository(db_url=db)
        summary = process_pending_suggestions(repo, None, limit=limit, dry_run=True)
        click.echo(f"Found {summary.total} pending deck suggestion(s).")
        click.echo("[DRY RUN] Would process the above requests.")
        return

    # Validate the provider config before touching the queue: a config error
    # must never claim (and burn an attempt on) any request.
    try:
        runner = get_runner(provider)
        check = getattr(runner, "check", None)
        if callable(check):
            check()
    except ClaudeRunnerError as exc:
        click.echo(f"Error: {exc.message}", err=True)
        sys.exit(EXIT_CONFIG_ERROR)
    except ValueError as exc:  # unknown $DECK_SUGGEST_PROVIDER
        click.echo(f"Error: {exc}", err=True)
        sys.exit(EXIT_CONFIG_ERROR)

    repo = Repository(db_url=db)
    summary = process_pending_suggestions(repo, runner, limit=limit)

    if summary.total == 0:
        click.echo("No pending deck suggestions.")
        return

    click.echo("")
    click.echo("=" * 60)
    click.echo("  DECK SUGGESTION PROCESSING SUMMARY")
    click.echo(f"  Total processed:         {summary.total}")
    click.echo(f"  Done:                    {summary.done}")
    click.echo(f"  Failed:                  {summary.failed}")
    click.echo(f"  Retried:                 {summary.retried}")
    click.echo(f"  Provider:                {runner.provider}")
    click.echo(f"  Model:                   {runner.model}")
    click.echo("=" * 60)
