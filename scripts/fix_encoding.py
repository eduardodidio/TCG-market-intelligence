#!/usr/bin/env python3
"""Fix UTF-8 double-encoding (mojibake) in card names.

When curl_cffi decodes UTF-8 bytes using latin-1 (due to missing charset
header), accented characters get double-encoded.  For example:

    "Contramágica" -> "ContramaÌgica" (mojibake)

This script detects and fixes affected rows in both `source_cards` and
`cards` tables.  It is idempotent: running it on already-correct data
is a no-op.

Usage:
    python scripts/fix_encoding.py [--db-url sqlite:///tcg_market.db] [--dry-run]
"""

from __future__ import annotations

import argparse
import sys

import structlog
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from src.database.models import Base, CardRow, SourceCardRow

log = structlog.get_logger()

DEFAULT_DB_URL = "sqlite:///tcg_market.db"


def fix_mojibake(text: str | None) -> tuple[str | None, bool]:
    """Attempt to fix double-encoded UTF-8 text.

    Returns (fixed_text, was_changed).  If the text is already correct
    or None, returns (original, False).
    """
    if text is None:
        return text, False

    try:
        # If the text can be encoded as latin-1, it might be mojibake.
        # Try to decode those bytes as UTF-8.
        candidate = text.encode("latin-1").decode("utf-8")
        if candidate != text:
            return candidate, True
        return text, False
    except (UnicodeDecodeError, UnicodeEncodeError):
        # Cannot roundtrip -> text is already correct (or has other issues)
        return text, False


def fix_source_cards(session: Session, dry_run: bool = False) -> int:
    """Fix mojibake in source_cards.name_en and name_pt.  Returns count fixed."""
    rows = session.execute(select(SourceCardRow)).scalars().all()
    fixed_count = 0

    for row in rows:
        changed = False

        new_name_en, en_changed = fix_mojibake(row.name_en)
        if en_changed:
            if not dry_run:
                row.name_en = new_name_en
            changed = True

        new_name_pt, pt_changed = fix_mojibake(row.name_pt)
        if pt_changed:
            if not dry_run:
                row.name_pt = new_name_pt
            changed = True

        if changed:
            fixed_count += 1
            log.info(
                "fix_source_card",
                id=row.id,
                external_id=row.external_id,
                name_en_before=row.name_en if not en_changed else f"{row.name_en} (was mojibake)",
                name_pt_before=row.name_pt if not pt_changed else f"{row.name_pt} (was mojibake)",
                dry_run=dry_run,
            )

    return fixed_count


def fix_cards(session: Session, dry_run: bool = False) -> int:
    """Fix mojibake in cards.name_en and name_pt.  Returns count fixed."""
    rows = session.execute(select(CardRow)).scalars().all()
    fixed_count = 0

    for row in rows:
        changed = False

        new_name_en, en_changed = fix_mojibake(row.name_en)
        if en_changed:
            if not dry_run:
                row.name_en = new_name_en
            changed = True

        new_name_pt, pt_changed = fix_mojibake(row.name_pt)
        if pt_changed:
            if not dry_run:
                row.name_pt = new_name_pt
            changed = True

        if changed:
            fixed_count += 1
            log.info(
                "fix_card",
                id=row.id,
                name_en_before=row.name_en if not en_changed else f"{row.name_en} (was mojibake)",
                name_pt_before=row.name_pt if not pt_changed else f"{row.name_pt} (was mojibake)",
                dry_run=dry_run,
            )

    return fixed_count


def main(db_url: str = DEFAULT_DB_URL, dry_run: bool = False) -> dict[str, int]:
    """Run the encoding fix.  Returns summary dict."""
    engine = create_engine(db_url, echo=False)
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        source_fixed = fix_source_cards(session, dry_run=dry_run)
        cards_fixed = fix_cards(session, dry_run=dry_run)

        if not dry_run:
            session.commit()

    summary = {
        "source_cards_fixed": source_fixed,
        "cards_fixed": cards_fixed,
    }

    log.info("encoding_fix_complete", **summary, dry_run=dry_run)
    return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Fix UTF-8 double-encoding in card names")
    parser.add_argument(
        "--db-url",
        default=DEFAULT_DB_URL,
        help=f"SQLAlchemy database URL (default: {DEFAULT_DB_URL})",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print what would be fixed without modifying the database",
    )
    args = parser.parse_args()

    summary = main(db_url=args.db_url, dry_run=args.dry_run)

    print(f"\n{'[DRY RUN] ' if args.dry_run else ''}Encoding fix summary:")
    print(f"  source_cards fixed: {summary['source_cards_fixed']}")
    print(f"  cards fixed:        {summary['cards_fixed']}")

    if summary["source_cards_fixed"] == 0 and summary["cards_fixed"] == 0:
        print("  No mojibake detected -- database is clean.")

    sys.exit(0)
