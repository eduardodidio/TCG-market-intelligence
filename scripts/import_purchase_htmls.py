"""One-off script to import acquisition prices from Nerdz/Liga purchase HTMLs.

Reads all .html files from a directory, parses them with the existing
purchase_parser, matches to the user's collection via purchase_matcher,
and applies acquisition prices + dates.

Usage:
    python scripts/import_purchase_htmls.py --dry-run
    python scripts/import_purchase_htmls.py
    python scripts/import_purchase_htmls.py --overwrite
"""

from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

import click

# Ensure project root is on sys.path so src.* imports work
_project_root = str(Path(__file__).resolve().parent.parent)
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from src.config import get_db_url  # noqa: E402
from src.database.repository import Repository  # noqa: E402
from src.services.purchase_matcher import MatchReport, match_purchases  # noqa: E402
from src.services.purchase_parser import ParsedPurchaseItem, parse_purchase_html  # noqa: E402


def _load_full_collection(repo: Repository, user_id: str):
    """Load all collection entries for a user (unpaginated)."""
    from src.database.models import UserCollectionRow

    entries: list[UserCollectionRow] = []
    offset = 0
    batch_size = 500
    while True:
        batch = repo.list_collection(
            user_id,
            sort_by="name",
            sort_dir="asc",
            offset=offset,
            limit=batch_size,
        )
        entries.extend(batch)
        if len(batch) < batch_size:
            break
        offset += batch_size
    return entries


def _read_html(path: Path) -> str:
    """Read HTML file, trying UTF-8 first then latin-1."""
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return path.read_text(encoding="latin-1")


@click.command()
@click.option(
    "--dir",
    "html_dir",
    default="docs/comprasEmLojas",
    help="Directory with HTML files",
)
@click.option("--user-id", default="1", help="User ID to match collection against")
@click.option("--dry-run", is_flag=True, help="Preview without applying")
@click.option("--overwrite", is_flag=True, help="Overwrite existing acquisition prices")
@click.option("--db", default=None, help="Database URL override")
@click.option(
    "--min-confidence",
    default=0.7,
    type=float,
    help="Minimum match confidence threshold (default 0.7)",
)
def main(
    html_dir: str,
    user_id: str,
    dry_run: bool,
    overwrite: bool,
    db: str | None,
    min_confidence: float,
):
    """Import acquisition prices from Nerdz Cards / Liga Magic purchase HTML files."""
    html_path = Path(html_dir)
    if not html_path.is_absolute():
        html_path = Path(_project_root) / html_path

    if not html_path.is_dir():
        click.echo(f"ERROR: Directory not found: {html_path}", err=True)
        sys.exit(1)

    # Collect HTML files, skipping _files/ subdirectories (browser save artifacts)
    html_files = sorted(f for f in html_path.glob("*.html") if "_files" not in f.name)

    if not html_files:
        click.echo(f"No .html files found in {html_path}")
        sys.exit(0)

    click.echo(f"Found {len(html_files)} HTML file(s) in {html_path}")
    click.echo()

    # ---- Phase 1: Parse all HTML files ----
    all_items: list[ParsedPurchaseItem] = []
    total_orders = 0
    files_parsed = 0
    files_skipped = 0

    for html_file in html_files:
        fname = html_file.name
        try:
            content = _read_html(html_file)
            orders = parse_purchase_html(content, fname)
        except ValueError as e:
            click.echo(f"  WARNING: Skipping {fname} - {e}")
            files_skipped += 1
            continue
        except Exception as e:
            click.echo(f"  WARNING: Skipping {fname} - unexpected error: {e}")
            files_skipped += 1
            continue

        file_items = 0
        for order in orders:
            total_orders += 1
            file_items += len(order.items)
            all_items.extend(order.items)

        files_parsed += 1
        click.echo(f"  Parsed: {fname} -> {len(orders)} order(s), {file_items} item(s)")

    click.echo()
    click.echo("--- Parse Summary ---")
    click.echo(f"  Files parsed:  {files_parsed}")
    click.echo(f"  Files skipped: {files_skipped}")
    click.echo(f"  Total orders:  {total_orders}")
    click.echo(f"  Total items:   {len(all_items)}")
    click.echo()

    if not all_items:
        click.echo("No items parsed. Nothing to do.")
        sys.exit(0)

    # ---- Phase 2: Load collection and match ----
    db_url = db or get_db_url()
    click.echo("Connecting to database...")
    repo = Repository(db_url=db_url)

    collection = _load_full_collection(repo, user_id)
    click.echo(f"Loaded {len(collection)} collection entries for user {user_id}")
    click.echo()

    report: MatchReport = match_purchases(all_items, collection)

    click.echo("--- Match Summary ---")
    click.echo(f"  Total parsed:    {report.total_parsed}")
    click.echo(f"  Total matched:   {report.total_matched}")
    click.echo(f"  Total unmatched: {len(report.unmatched)}")
    if report.warnings:
        click.echo(f"  Warnings: {len(report.warnings)}")
        for w in report.warnings:
            click.echo(f"    - {w}")
    click.echo()

    # ---- Phase 3: Filter and prepare updates ----
    updates_to_apply: list[dict] = []
    skipped_low_confidence = 0
    skipped_has_price = 0

    for match in report.matched:
        if match.confidence < min_confidence:
            skipped_low_confidence += 1
            continue

        if match.already_has_price and not overwrite:
            skipped_has_price += 1
            continue

        item = match.parsed_item
        # BRL prices -- no conversion needed (Brazilian stores)
        price = item.unit_price
        acquired_at: date | None = item.order_date

        updates_to_apply.append(
            {
                "entry_id": match.collection_entry_id,
                "price": price,
                "acquired_at": acquired_at,
                "card_name": match.collection_entry_name or "?",
                "parsed_name": (item.card_name_pt or item.card_name_en or "?"),
                "set_code": item.set_code,
                "confidence": match.confidence,
                "method": match.match_method,
                "order": item.order_number,
            }
        )

    click.echo("--- Update Plan ---")
    click.echo(f"  To apply:              {len(updates_to_apply)}")
    click.echo(f"  Skipped (low conf):    {skipped_low_confidence}")
    click.echo(f"  Skipped (has price):   {skipped_has_price}")
    click.echo(f"  Unmatched:             {len(report.unmatched)}")
    click.echo()

    # Print details of what will be applied
    if updates_to_apply:
        click.echo("Updates to apply:")
        for u in updates_to_apply:
            flag = " [OVERWRITE]" if overwrite else ""
            click.echo(
                f"  #{u['entry_id']:>5} | {u['card_name']:<40} | "
                f"R$ {u['price']:>8} | {u['acquired_at'] or 'no date'} | "
                f"conf={u['confidence']:.2f} ({u['method']}){flag}"
            )
        click.echo()

    # Print unmatched for debugging
    if report.unmatched:
        click.echo("Unmatched items:")
        for um in report.unmatched:
            item = um.parsed_item
            name = item.card_name_pt or item.card_name_en or "?"
            click.echo(
                f"  {name:<40} | {item.set_code or '?':>5} "
                f"#{item.collector_number or '?':<5} | "
                f"R$ {item.unit_price:>8} | {item.order_number} | "
                f"reason: {um.skip_reason}"
            )
        click.echo()

    # ---- Phase 4: Apply updates ----
    if dry_run:
        click.echo("DRY RUN -- no changes applied.")
        sys.exit(0)

    if not updates_to_apply:
        click.echo("Nothing to apply.")
        sys.exit(0)

    applied_count = 0
    with repo.transaction() as session:
        for u in updates_to_apply:
            updates_dict: dict = {"acquisition_price": u["price"]}
            if u["acquired_at"]:
                updates_dict["acquired_at"] = u["acquired_at"]

            repo.update_collection_entry(
                u["entry_id"],
                user_id,
                updates_dict,
                session=session,
            )
            applied_count += 1

    click.echo(f"Applied {applied_count} acquisition price(s) successfully.")


if __name__ == "__main__":
    main()
