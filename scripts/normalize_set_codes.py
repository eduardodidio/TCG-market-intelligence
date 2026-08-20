"""One-time migration: normalize set_code to lowercase in cards and source_cards.

After this migration, all set_codes in the database are lowercase, matching
the convention used by the collection CSV importer and Scryfall URLs.

Usage:
    python scripts/normalize_set_codes.py [path/to/tcg_market.db]
"""

from __future__ import annotations

import sqlite3
import sys


def _check_duplicates(cursor: sqlite3.Cursor) -> list[tuple[str, str, str]]:
    """Check for potential duplicate conflicts after lowercasing.

    Returns list of (game, set_code_lower, collector_number) that would
    conflict due to case differences (e.g., both 'DMR' and 'dmr' exist).
    """
    cursor.execute("""
        SELECT game, LOWER(set_code), collector_number
        FROM cards
        WHERE set_code IS NOT NULL
        GROUP BY game, LOWER(set_code), collector_number
        HAVING COUNT(*) > 1
    """)
    return cursor.fetchall()


def normalize(db_path: str) -> None:
    """Lowercase all set_code values in cards and source_cards tables."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Safety check: look for duplicates that would violate unique constraints
    duplicates = _check_duplicates(cursor)
    if duplicates:
        print("ERROR: Found duplicate (game, set_code, collector_number) pairs")
        print("that would conflict after lowercasing:")
        for game, sc, cn in duplicates:
            print(f"  game={game}, set_code={sc}, collector_number={cn}")
        print("\nResolve these manually before running the migration.")
        conn.close()
        sys.exit(1)

    # cards table
    cursor.execute(
        "UPDATE cards SET set_code = LOWER(set_code) "
        "WHERE set_code IS NOT NULL AND set_code != LOWER(set_code)"
    )
    cards_updated = cursor.rowcount

    # source_cards table
    cursor.execute(
        "UPDATE source_cards SET set_code = LOWER(set_code) "
        "WHERE set_code IS NOT NULL AND set_code != LOWER(set_code)"
    )
    source_cards_updated = cursor.rowcount

    conn.commit()
    conn.close()

    print(f"Normalized {cards_updated} cards, {source_cards_updated} source_cards")


if __name__ == "__main__":
    db_path = sys.argv[1] if len(sys.argv) > 1 else "tcg_market.db"
    normalize(db_path)
