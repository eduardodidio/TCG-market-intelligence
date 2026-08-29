"""Import user card collection from CSV export."""

from __future__ import annotations

import csv
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.database.models import Base, CardRow, UserCollectionRow
from src.utils.set_code_map import map_to_scryfall_set_code


def _detect_encoding(file_path: Path) -> str:
    """Try UTF-8 first (with BOM), fall back to cp1252 for Liga exports."""
    raw = file_path.read_bytes()
    try:
        raw.decode("utf-8-sig")
        return "utf-8-sig"
    except UnicodeDecodeError:
        return "cp1252"


def import_collection_csv(
    engine,
    csv_path: str | Path,
    user_id: str,
) -> dict[str, int | list[int]]:
    """Parse a collection CSV and insert rows into user_collection.

    Returns summary dict with counts and list of new entry IDs.
    """
    Base.metadata.create_all(engine)
    csv_path = Path(csv_path)

    imported = 0
    skipped = 0
    linked = 0
    new_entry_ids: list[int] = []

    encoding = _detect_encoding(csv_path)

    with open(csv_path, encoding=encoding, newline="") as f:
        reader = csv.DictReader(f)
        rows_to_insert: list[dict] = []

        for row in reader:
            set_code = (row.get("Edicao (Sigla)") or "").strip().lower()
            set_code = map_to_scryfall_set_code(set_code)
            collector_number = (row.get("Card #") or "").strip()
            if not set_code or not collector_number:
                skipped += 1
                continue

            name_en = (row.get("Card (EN)") or "").strip() or None
            name_pt = (row.get("Card (PT)") or "").strip() or None
            set_name_en = (row.get("Edicao (EN)") or "").strip() or None
            quantity = int(row.get("Quantidade") or "1")
            quality = (row.get("Qualidade (M NM SP MP HP D)") or "").strip() or None
            language = (row.get("Idioma (BR EN DE ES FR IT JP KO RU TW)") or "").strip() or None
            rarity = (row.get("Raridade (M R U C)") or "").strip() or None
            color = (row.get("Cor (W U B R G M A L)") or "").strip() or None
            extras = (row.get("Extras") or "").strip() or None
            set_name_pt = (row.get("Edicao (PTBR)") or "").strip() or None
            notes = (row.get("Comentario") or "").strip() or None

            rows_to_insert.append(
                {
                    "user_id": user_id,
                    "set_code": set_code,
                    "collector_number": collector_number,
                    "name_en": name_en,
                    "name_pt": name_pt,
                    "set_name_en": set_name_en,
                    "quantity": quantity,
                    "quality": quality,
                    "language": language,
                    "rarity": rarity,
                    "color": color,
                    "extras": extras,
                    "set_name_pt": set_name_pt,
                    "notes": notes,
                }
            )

    with Session(engine) as session:
        try:
            # Clear existing collection for this user before re-import
            session.query(UserCollectionRow).filter(UserCollectionRow.user_id == user_id).delete()

            for data in rows_to_insert:
                # Link to canonical card (both sides are lowercase after normalization)
                card = session.execute(
                    select(CardRow).where(
                        CardRow.game == "magic",
                        CardRow.set_code == data["set_code"],
                        CardRow.collector_number == data["collector_number"],
                    )
                ).scalar_one_or_none()

                if card:
                    card_id = card.id
                else:
                    # Auto-canonize: create canonical card from collection data
                    new_card = CardRow(
                        game="magic",
                        name_en=data["name_en"],
                        name_pt=data["name_pt"],
                        set_code=data["set_code"],
                        collector_number=data["collector_number"],
                    )
                    session.add(new_card)
                    session.flush()
                    card_id = new_card.id

                linked += 1

                row = UserCollectionRow(card_id=card_id, **data)
                session.add(row)
                session.flush()  # populate row.id
                new_entry_ids.append(row.id)
                imported += 1

            session.commit()
        except Exception:
            session.rollback()
            raise

    return {
        "imported": imported,
        "skipped": skipped,
        "linked": linked,
        "total_csv_rows": imported + skipped,
        "new_entry_ids": new_entry_ids,
    }
