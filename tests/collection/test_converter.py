"""Tests for src.collection.converter — row_to_collection_entry."""

from __future__ import annotations

from unittest.mock import MagicMock

from src.collection.converter import row_to_collection_entry
from src.collection.matcher import CollectionEntry


def _make_row(
    set_code: str = "dmu",
    collector_number: str = "001",
    name_en: str | None = "Llanowar Elves",
    name_pt: str | None = None,
) -> MagicMock:
    """Create a lightweight mock of UserCollectionRow."""
    row = MagicMock()
    row.set_code = set_code
    row.collector_number = collector_number
    row.name_en = name_en
    row.name_pt = name_pt
    return row


class TestRowToCollectionEntry:
    """Unit tests for row_to_collection_entry."""

    def test_happy_path_full_row(self) -> None:
        row = _make_row(set_code="dmu", collector_number="193", name_en="Llanowar Elves")
        entry = row_to_collection_entry(row)

        assert isinstance(entry, CollectionEntry)
        assert entry.set_code == "dmu"
        assert entry.collector_number == "193"
        assert entry.name_en == "Llanowar Elves"

    def test_name_en_none(self) -> None:
        row = _make_row(name_en=None)
        entry = row_to_collection_entry(row)

        assert entry.name_en is None
        assert entry.set_code == "dmu"
        assert entry.collector_number == "001"

    def test_empty_set_code(self) -> None:
        row = _make_row(set_code="")
        entry = row_to_collection_entry(row)

        assert entry.set_code == ""
        assert entry.collector_number == "001"
        assert entry.name_en == "Llanowar Elves"

    def test_name_pt_populated(self) -> None:
        row = _make_row(name_en="Llanowar Elves", name_pt="Elfos de Llanowar")
        entry = row_to_collection_entry(row)

        assert entry.name_en == "Llanowar Elves"
        assert entry.name_pt == "Elfos de Llanowar"

    def test_name_pt_none(self) -> None:
        row = _make_row(name_en="Llanowar Elves", name_pt=None)
        entry = row_to_collection_entry(row)

        assert entry.name_pt is None

    def test_both_names_none(self) -> None:
        row = _make_row(name_en=None, name_pt=None)
        entry = row_to_collection_entry(row)

        assert entry.name_en is None
        assert entry.name_pt is None
