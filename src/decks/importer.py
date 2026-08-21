"""Deck import orchestrator — parse, store, and link cards."""

from __future__ import annotations

import csv
import io

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from src.database.models import Base, CardRow
from src.database.repository import Repository
from src.decks.parser import parse_deck_text


def import_deck(
    engine,
    user_id: str,
    name: str,
    cards: list[dict],
    description: str | None = None,
) -> dict:
    """Import a list of parsed card dicts as a new deck.

    Returns dict with: deck_id, name, cards_imported, cards_linked.
    """
    Base.metadata.create_all(engine)
    repo = Repository.__new__(Repository)
    repo.engine = engine

    deck = repo.create_deck(user_id, name, description=description)

    # Try to link each card to a canonical card
    cards_linked = 0
    with Session(engine) as session:
        for card in cards:
            card_id = _find_card_id(
                session,
                name_en=card["name_en"],
                set_code=card.get("set_code"),
                collector_number=card.get("collector_number"),
            )
            if card_id is not None:
                card["card_id"] = card_id
                cards_linked += 1

    cards_imported = repo.add_deck_cards(deck.id, cards)

    return {
        "deck_id": deck.id,
        "name": deck.name,
        "cards_imported": cards_imported,
        "cards_linked": cards_linked,
    }


def import_deck_from_text(
    engine,
    user_id: str,
    name: str,
    content: str,
    description: str | None = None,
) -> dict:
    """Parse a text deck list and import it."""
    cards = parse_deck_text(content)
    return import_deck(engine, user_id, name, cards, description=description)


def import_deck_from_csv(
    engine,
    user_id: str,
    name: str,
    csv_content: str,
    description: str | None = None,
) -> dict:
    """Parse a CSV deck list and import it.

    Uses the same column mapping as the collection CSV importer.
    """
    reader = csv.DictReader(io.StringIO(csv_content))
    cards: list[dict] = []

    for row in reader:
        name_en = (row.get("Card (EN)") or "").strip()
        if not name_en:
            continue

        set_code = (row.get("Edicao (Sigla)") or "").strip().lower() or None
        collector_number = (row.get("Card #") or "").strip() or None
        quantity = int(row.get("Quantidade") or "1")

        cards.append(
            {
                "name_en": name_en,
                "set_code": set_code,
                "collector_number": collector_number,
                "quantity": quantity,
            }
        )

    return import_deck(engine, user_id, name, cards, description=description)


def _find_card_id(
    session: Session,
    name_en: str,
    set_code: str | None,
    collector_number: str | None,
) -> int | None:
    """Find a canonical card ID.

    Priority:
    1. Match by (game=magic, set_code, collector_number) — exact
    2. Match by name_en (case-insensitive) — only if unique
    """
    # Tier 1: exact set+number match
    if set_code and collector_number:
        card = session.execute(
            select(CardRow).where(
                CardRow.game == "magic",
                CardRow.set_code == set_code.lower(),
                CardRow.collector_number == collector_number,
            )
        ).scalar_one_or_none()
        if card:
            return card.id

    # Tier 2: unique name match (case-insensitive)
    count = session.execute(
        select(func.count(CardRow.id)).where(func.lower(CardRow.name_en) == name_en.lower())
    ).scalar()
    if count == 1:
        card = session.execute(
            select(CardRow).where(func.lower(CardRow.name_en) == name_en.lower())
        ).scalar_one()
        return card.id

    return None
