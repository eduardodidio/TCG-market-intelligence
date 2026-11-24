"""One-off script to import Commander decks from docs/decksCommander.txt."""

from __future__ import annotations

import re
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.config import get_db_url
from src.decks.importer import import_deck_from_text

# Pattern: "1 Card Name (SET) 123" or "1 Card Name (SET) 123 (Commander)"
_CARD_RE = re.compile(
    r"^(\d+)\s+"  # quantity
    r"(.+?)\s+"  # card name
    r"\(([A-Za-z0-9]+)\)\s+"  # (SET)
    r"([A-Za-z0-9-]+)"  # collector number
    r"(?:\s+\(Commander\))?"  # optional (Commander) tag
    r"$"
)


def parse_file(filepath: str) -> list[dict]:
    """Parse decksCommander.txt into a list of {name, description, content}."""
    decks: list[dict] = []
    current_name: str | None = None
    current_lines: list[str] = []

    with open(filepath, encoding="utf-8") as f:
        for raw_line in f:
            line = raw_line.strip()

            # Deck header detection
            if line.lower().startswith("nome d") or line.lower().startswith("nome deck"):
                # Save previous deck
                if current_name and current_lines:
                    decks.append({"name": current_name, "content": "\n".join(current_lines)})
                # Extract deck name after the colon/dash
                for sep in (":", "-", "="):
                    if sep in line:
                        current_name = line.split(sep, 1)[1].strip()
                        break
                else:
                    current_name = line
                current_lines = []
                continue

            # Non-header line that looks like a deck title
            # (no quantity prefix, non-empty, no card pattern)
            if line and not line[0].isdigit() and not _CARD_RE.match(line) and not current_name:
                current_name = line
                current_lines = []
                continue

            # Also catch deck names without "Nome" prefix (like "Giada a abençoada")
            if line and not line[0].isdigit() and not _CARD_RE.match(line):
                # Save previous deck
                if current_name and current_lines:
                    decks.append({"name": current_name, "content": "\n".join(current_lines)})
                current_name = line
                current_lines = []
                continue

            if not line:
                continue

            # Convert card line: "1 Card Name (SET) 123" -> "1 Card Name [SET:123]"
            m = _CARD_RE.match(line)
            if m:
                qty, name, set_code, collector_num = m.groups()
                current_lines.append(f"{qty} {name} [{set_code}:{collector_num}]")

    # Save last deck
    if current_name and current_lines:
        decks.append({"name": current_name, "content": "\n".join(current_lines)})

    return decks


def main():
    filepath = Path(__file__).resolve().parent.parent / "docs" / "decksCommander.txt"
    if not filepath.exists():
        print(f"File not found: {filepath}")
        sys.exit(1)

    decks = parse_file(str(filepath))
    print(f"Found {len(decks)} decks to import:\n")
    for d in decks:
        card_count = len(d["content"].splitlines())
        print(f"  - {d['name']} ({card_count} cards)")

    # Get DB engine
    from sqlalchemy import create_engine

    db_url = get_db_url()
    engine = create_engine(db_url, pool_pre_ping=True)

    # Find admin user
    from sqlalchemy.orm import Session

    from src.database.models import UserRow

    with Session(engine) as session:
        admin = session.query(UserRow).filter(UserRow.is_admin == 1).first()
        if not admin:
            print("\nNo admin user found. Run 'seed-users' first.")
            sys.exit(1)
        user_id = str(admin.id)
        print(f"\nImporting as user: {admin.display_name} (id={user_id})")

    print()
    for deck_data in decks:
        result = import_deck_from_text(
            engine=engine,
            user_id=user_id,
            name=deck_data["name"],
            content=deck_data["content"],
            description="Commander deck (imported from decksCommander.txt)",
        )
        print(
            f"  Imported '{result['name']}': "
            f"{result['cards_imported']} cards, "
            f"{result['cards_linked']} linked to DB"
        )

    print("\nDone!")


if __name__ == "__main__":
    main()
