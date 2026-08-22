"""Shared converter: UserCollectionRow -> CollectionEntry."""

from __future__ import annotations

from src.collection.matcher import CollectionEntry
from src.database.models import UserCollectionRow


def row_to_collection_entry(row: UserCollectionRow) -> CollectionEntry:
    """Convert a DB row to a CollectionEntry for the matcher.

    This is the single source of truth for the
    ``UserCollectionRow`` -> ``CollectionEntry`` mapping.
    """
    return CollectionEntry(
        set_code=row.set_code,
        collector_number=row.collector_number,
        name_en=row.name_en,
        name_pt=row.name_pt,
    )
