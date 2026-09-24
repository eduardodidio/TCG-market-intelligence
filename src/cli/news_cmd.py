"""Standalone `fetch-news` CLI command (F178).

Kept in its own module (not src/cli/main.py) to avoid a circular import:
main.py registers this command via `cli.add_command(fetch_news_command)`.
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


@click.command("fetch-news")
@click.option(
    "--db",
    default=None,
    callback=_resolve_db,
    is_eager=True,
    expose_value=True,
    help="Database URL (default: auto-detect)",
)
@click.option(
    "--max-per-source",
    default=20,
    type=click.IntRange(1, 200),
    help="Max entries per feed source (1-200)",
)
@click.option("--check-sources", is_flag=True, help="Dry run: report source status, write nothing")
@click.option("--source", "source_names", multiple=True, help="Restrict to named source(s)")
@click.pass_context
def fetch_news_command(ctx, db, max_per_source, check_sources, source_names):
    """Fetch MTG news from RSS/Atom sources."""
    from src.services.news_fetcher import fetch_news, load_sources

    sources = None
    if source_names:
        wanted = {name.lower() for name in source_names}
        all_sources = load_sources()
        sources = [s for s in all_sources if s["name"].lower() in wanted]
        found = {s["name"].lower() for s in sources}
        missing = wanted - found
        if missing:
            raise click.UsageError(f"Unknown source(s): {', '.join(sorted(missing))}")

    if check_sources:
        stats = fetch_news(None, max_per_source=max_per_source, sources=sources, dry_run=True)
    else:
        from src.database.repository import Repository

        repo = Repository(db_url=db)
        stats = fetch_news(repo, max_per_source=max_per_source, sources=sources)

    click.echo("")
    click.echo("=" * 60)
    click.echo("  NEWS FETCH SUMMARY")
    click.echo(f"  Fetched:  {stats['fetched']}")
    click.echo(f"  New:      {stats['new']}")
    click.echo(f"  Skipped:  {stats['skipped']}")
    click.echo(f"  Errors:   {stats['errors']}")
    click.echo("=" * 60)
    for source_report in stats["sources"]:
        if source_report["ok"]:
            click.echo(
                f"  [OK]  {source_report['name']}"
                f"  http={source_report['http_status']}"
                f"  entries={source_report['entries']}"
                f"  new={source_report['new']}"
            )
        else:
            click.echo(
                f"  [FAIL] {source_report['name']}"
                f"  http={source_report['http_status']}"
                f"  error={source_report['error']}"
            )
    click.echo("=" * 60)
    click.echo("")

    if stats["sources"] and not any(s["ok"] for s in stats["sources"]):
        ctx.exit(1)
