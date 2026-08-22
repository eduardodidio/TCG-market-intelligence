"""Ban engine analysis functions for collection cards (F42).

Pure functions — no class state, receive repo as parameter.
Read-only: never writes to card_legalities.
"""

from __future__ import annotations

from src.api.schemas.ban_engine import (
    BannedCollectionCard,
    BanSummary,
    CardLegalityWithChange,
)
from src.database.repository import Repository
from src.utils.set_code_map import map_to_scryfall_set_code


def _scryfall_image_url(set_code: str, collector_number: str) -> str:
    mapped = map_to_scryfall_set_code(set_code)
    return (
        f"https://api.scryfall.com/cards/{mapped}/{collector_number}"
        f"?format=image&version=normal"
    )


_STATUS_ORDER = {"banned": 0, "restricted": 1, "legal": 2, "not_legal": 3}


def get_banned_collection_cards(
    repo: Repository,
    user_id: str,
    format_filter: str | None = None,
    days: int = 30,
) -> list[BannedCollectionCard]:
    """Get banned/restricted cards in the user's collection, enriched with change info."""
    rows = repo.get_banned_collection_cards(user_id, format_filter)
    recently_changed_ids = repo.get_recently_changed_card_ids(user_id, days)

    return [
        BannedCollectionCard(
            entry_id=r["entry_id"],
            card_id=r["card_id"],
            name_en=r["name_en"],
            name_pt=r["name_pt"],
            set_code=r["set_code"],
            collector_number=r["collector_number"],
            quantity=r["quantity"],
            format=r["format"],
            status=r["status"],
            effective_date=r["effective_date"],
            recently_changed=r["card_id"] in recently_changed_ids,
            image_url=_scryfall_image_url(r["set_code"], r["collector_number"]),
        )
        for r in rows
    ]


def get_ban_summary(
    repo: Repository,
    user_id: str,
    days: int = 30,
) -> BanSummary:
    """Aggregate ban summary for the user's collection."""
    counts = repo.get_collection_ban_summary(user_id)
    recently_changed_ids = repo.get_recently_changed_card_ids(user_id, days)

    # Extract distinct formats from banned cards
    banned_rows = repo.get_banned_collection_cards(user_id)
    formats_affected = sorted({r["format"] for r in banned_rows})

    return BanSummary(
        banned_count=counts["banned_count"],
        restricted_count=counts["restricted_count"],
        recently_changed_count=len(recently_changed_ids),
        formats_affected=formats_affected,
    )


def get_card_legalities_with_changes(
    repo: Repository,
    card_id: int,
    days: int = 30,
) -> list[CardLegalityWithChange]:
    """Get all legalities for a card, sorted by severity."""
    rows = repo.get_card_legalities_with_history(card_id, days)
    items = [
        CardLegalityWithChange(
            format=r["format"],
            status=r["status"],
            effective_date=r["effective_date"],
            recently_changed=r["recently_changed"],
            change_date=r["change_date"],
            old_status=r["old_status"],
        )
        for r in rows
    ]
    # Sort: banned first, then restricted, then legal, then not_legal
    items.sort(key=lambda x: _STATUS_ORDER.get(x.status, 4))
    return items
