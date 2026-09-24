"""Standalone `collect-metagame` CLI command (F173-T12).

Kept in its own module (not src/cli/main.py); main.py registers it via
`cli.add_command(collect_metagame_cmd)` (F173-T15).
"""

from __future__ import annotations

import sys

import click

from src.metagame.sources.base import FORMATS


def _resolve_db(ctx, param, value):
    """Click callback: resolve --db to auto-detected URL when None.

    Duplicated from src.cli.main._resolve_db to avoid a circular import once
    main.py registers this command.
    """
    if value is None:
        from src.config import get_db_url

        return get_db_url()
    return value


def _make_fetcher(no_cache: bool):
    """Build the polite fetcher; ``no_cache`` forces every read past the disk cache."""
    from src.metagame.http import PoliteFetcher

    if not no_cache:
        return PoliteFetcher()

    class _NoCacheFetcher(PoliteFetcher):
        def get_text(self, url, *, ttl_hours=None, use_cache=True):
            return super().get_text(url, ttl_hours=ttl_hours, use_cache=False)

    return _NoCacheFetcher()


@click.command("collect-metagame")
@click.option(
    "--db",
    default=None,
    callback=_resolve_db,
    is_eager=True,
    expose_value=True,
    help="Database URL (default: auto-detect)",
)
@click.option(
    "--format",
    "-f",
    "formats",
    multiple=True,
    type=click.Choice(FORMATS),
    help="Format(s) to collect (default: all)",
)
@click.option(
    "--limit",
    default=20,
    type=click.IntRange(1, 50),
    help="Top decks per format (1-50)",
)
@click.option("--dry-run", is_flag=True, help="Fetch and resolve, but write nothing")
@click.option("--no-cache", is_flag=True, help="Ignore the on-disk HTTP cache")
def collect_metagame_cmd(db, formats, limit, dry_run, no_cache):
    """Collect top metagame decks per format (EDHREC + MTGTop8)."""
    from src.database.repository import Repository
    from src.metagame.collector import collect_metagame
    from src.metagame.repository import MetagameRepository
    from src.metagame.sources import SOURCE_FOR_FORMAT, get_sources

    selected = list(formats) or list(SOURCE_FOR_FORMAT)

    repo = Repository(db)
    meta_repo = MetagameRepository.from_repo(repo)
    fetcher = _make_fetcher(no_cache)
    try:
        sources = get_sources(fetcher)
        stats = collect_metagame(meta_repo, sources, selected, limit=limit, dry_run=dry_run)
    finally:
        fetcher.close()

    failed = {e.split(":", 1)[0] for e in stats.errors}
    for fmt in selected:
        source = SOURCE_FOR_FORMAT.get(fmt, "-")
        status = "FAIL" if fmt in failed or f"no source for {fmt}" in stats.errors else "ok"
        click.echo(f"  {fmt:<10} {source:<8} {status}")

    click.echo("")
    click.echo("=" * 60)
    click.echo("  METAGAME COLLECTION SUMMARY" + (" (dry run)" if dry_run else ""))
    click.echo(f"  Formats collected: {stats.formats}/{len(selected)}")
    click.echo(f"  Decks:             {stats.decks}")
    click.echo(f"  Cards:             {stats.cards}")
    click.echo(f"  Unresolved cards:  {stats.unresolved_cards}")
    if stats.errors:
        click.echo("  Errors:")
        for err in stats.errors:
            click.echo(f"    - {err}")
    click.echo("=" * 60)

    if stats.formats == 0 and stats.errors:
        click.echo("All formats failed.", err=True)
        sys.exit(1)
    if stats.errors:
        click.echo(f"WARNING: {len(stats.errors)} format(s) failed.", err=True)
