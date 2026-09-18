"""Bulk import acquisition prices from HTML purchase files.

Reads all HTML files from docs/comprasEmLojas/, parses them,
matches to user collection, and applies matches with confidence >= 0.85.

Usage:
    python scripts/bulk_import_purchases.py [--dry-run] [--user-id eduardo]
"""

from __future__ import annotations

import argparse
import glob
import os
import sys

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


from src.config import get_db_url
from src.database.repository import Repository
from src.services.purchase_matcher import match_purchases
from src.services.purchase_parser import parse_purchase_html

CONFIDENCE_THRESHOLD = 0.85
HTML_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "docs",
    "comprasEmLojas",
)


def load_collection(repo: Repository, user_id: str):
    """Load all collection entries for a user."""
    entries = []
    offset = 0
    batch_size = 500
    while True:
        batch = repo.list_collection(
            user_id, sort_by="name", sort_dir="asc", offset=offset, limit=batch_size
        )
        entries.extend(batch)
        if len(batch) < batch_size:
            break
        offset += batch_size
    return entries


def main():
    parser = argparse.ArgumentParser(description="Bulk import purchase HTML files")
    parser.add_argument("--dry-run", action="store_true", help="Preview only, don't apply")
    parser.add_argument("--user-id", default="eduardo", help="User ID (default: eduardo)")
    parser.add_argument(
        "--min-confidence",
        type=float,
        default=CONFIDENCE_THRESHOLD,
        help=f"Minimum confidence to auto-apply (default: {CONFIDENCE_THRESHOLD})",
    )
    parser.add_argument("--overwrite", action="store_true", help="Overwrite existing prices")
    args = parser.parse_args()

    # Find HTML files
    html_files = sorted(glob.glob(os.path.join(HTML_DIR, "*.html")))
    if not html_files:
        print(f"No HTML files found in {HTML_DIR}")
        return

    print(f"Found {len(html_files)} HTML files in {HTML_DIR}")
    print(
        f"User: {args.user_id} | Min confidence: {args.min_confidence} | "
        f"Overwrite: {args.overwrite} | Dry-run: {args.dry_run}"
    )
    print("-" * 70)

    # Parse all files
    all_items = []
    all_orders = []
    parse_errors = []

    for fpath in html_files:
        fname = os.path.basename(fpath)
        try:
            with open(fpath, "r", encoding="utf-8") as f:
                content = f.read()
        except UnicodeDecodeError:
            with open(fpath, "r", encoding="latin-1") as f:
                content = f.read()

        try:
            orders = parse_purchase_html(content, fname)
            for order in orders:
                all_orders.append(order)
                all_items.extend(order.items)
            print(
                f"  Parsed: {fname} -> {len(orders)} order(s), "
                f"{sum(len(o.items) for o in orders)} item(s)"
            )
        except ValueError as e:
            parse_errors.append((fname, str(e)))
            print(f"  ERROR:  {fname} -> {e}")

    print(f"\nTotal: {len(all_orders)} orders, {len(all_items)} items parsed")
    if parse_errors:
        print(f"Parse errors: {len(parse_errors)}")

    # Connect to DB and load collection
    repo = Repository(get_db_url())
    collection = load_collection(repo, args.user_id)
    print(f"Collection: {len(collection)} entries for user '{args.user_id}'")

    # Match
    report = match_purchases(all_items, collection)
    print("\nMatching results:")
    print(f"  Matched:   {report.total_matched}")
    print(f"  Unmatched: {len(report.unmatched)}")
    if report.warnings:
        print(f"  Warnings:  {len(report.warnings)}")
        for w in report.warnings:
            print(f"    - {w}")

    # Filter by confidence and overwrite policy
    to_apply = []
    skipped_low_conf = 0
    skipped_has_price = 0

    for m in report.matched:
        if m.confidence < args.min_confidence:
            skipped_low_conf += 1
            continue
        if m.already_has_price and not args.overwrite:
            skipped_has_price += 1
            continue
        to_apply.append(m)

    print(f"\nReady to apply: {len(to_apply)}")
    print(f"  Skipped (low confidence <{args.min_confidence}): {skipped_low_conf}")
    print(f"  Skipped (already has price): {skipped_has_price}")

    # Show what will be applied
    if to_apply:
        print(f"\n{'Card':<40} {'Set':<6} {'Price':>10} {'Conf':>5} {'Method':<10}")
        print("-" * 75)
        for m in to_apply:
            item = m.parsed_item
            name = (item.card_name_en or item.card_name_pt or "?")[:39]
            set_code = (item.set_code or "?")[:5]
            price = f"R$ {item.unit_price:.2f}"
            print(
                f"  {name:<38} {set_code:<6} {price:>10} {m.confidence:>5.2f} {m.match_method:<10}"
            )

    # Show unmatched
    if report.unmatched:
        print(f"\nUnmatched items ({len(report.unmatched)}):")
        for u in report.unmatched[:20]:
            item = u.parsed_item
            name = (item.card_name_pt or item.card_name_en or "?")[:50]
            print(
                f"  - {name} [{item.set_code or '?'}] R$ {item.unit_price:.2f} "
                f"({u.skip_reason})"
            )
        if len(report.unmatched) > 20:
            print(f"  ... and {len(report.unmatched) - 20} more")

    if args.dry_run:
        print("\n[DRY RUN] No changes applied.")
        return

    if not to_apply:
        print("\nNothing to apply.")
        return

    # Apply
    print(f"\nApplying {len(to_apply)} updates...")
    applied = 0
    errors = 0

    with repo.transaction() as session:
        for m in to_apply:
            item = m.parsed_item
            updates = {"acquisition_price": item.unit_price}
            if item.order_date:
                updates["acquired_at"] = item.order_date
            try:
                repo.update_collection_entry(
                    m.collection_entry_id,
                    args.user_id,
                    updates,
                    session=session,
                )
                applied += 1
            except Exception as e:
                errors += 1
                print(f"  Error updating entry {m.collection_entry_id}: {e}")

    print(f"\nDone! Applied: {applied}, Errors: {errors}")


if __name__ == "__main__":
    main()
