"""Unit tests for CSV import returning new entry IDs and canonize_scheduled field.

Test plan scenarios: #13, #14, #15, #18 (F49-T02).
"""

from __future__ import annotations

import csv
import tempfile
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from src.collection.importer import import_collection_csv
from src.database.models import Base, UserCollectionRow


def _create_csv(rows: list[dict], tmp_dir: str) -> Path:
    """Write a CSV file with collection rows and return its path."""
    path = Path(tmp_dir) / "test_collection.csv"
    fieldnames = [
        "Card (EN)",
        "Card (PT)",
        "Edicao (Sigla)",
        "Edicao (EN)",
        "Card #",
        "Quantidade",
        "Qualidade (M NM SP MP HP D)",
        "Idioma (BR EN DE ES FR IT JP KO RU TW)",
        "Raridade (M R U C)",
        "Cor (W U B R G M A L)",
        "Extras",
    ]
    with open(path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)
    return path


def _make_row(
    name_en: str = "Lightning Bolt",
    name_pt: str = "Relampago",
    set_code: str = "lea",
    set_name_en: str = "Limited Edition Alpha",
    number: str = "161",
    qty: str = "1",
) -> dict:
    return {
        "Card (EN)": name_en,
        "Card (PT)": name_pt,
        "Edicao (Sigla)": set_code,
        "Edicao (EN)": set_name_en,
        "Card #": number,
        "Quantidade": qty,
        "Qualidade (M NM SP MP HP D)": "NM",
        "Idioma (BR EN DE ES FR IT JP KO RU TW)": "EN",
        "Raridade (M R U C)": "C",
        "Cor (W U B R G M A L)": "R",
        "Extras": "",
    }


@pytest.fixture()
def engine():
    eng = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(eng)
    return eng


class TestImportReturnsNewEntryIds:
    """#13: ImportResult includes list of newly created entry IDs."""

    def test_import_returns_new_entry_ids(self, engine):
        with tempfile.TemporaryDirectory() as tmp:
            csv_path = _create_csv(
                [
                    _make_row(name_en="Lightning Bolt", set_code="lea", number="161"),
                    _make_row(name_en="Dark Ritual", set_code="lea", number="102"),
                ],
                tmp,
            )

            result = import_collection_csv(engine, csv_path, user_id="user1")

            assert "new_entry_ids" in result
            assert len(result["new_entry_ids"]) == 2
            assert result["imported"] == 2
            # Verify IDs are actual database IDs
            with Session(engine) as session:
                for entry_id in result["new_entry_ids"]:
                    row = session.get(UserCollectionRow, entry_id)
                    assert row is not None
                    assert row.user_id == "user1"

    def test_import_returns_correct_ids_for_single_card(self, engine):
        with tempfile.TemporaryDirectory() as tmp:
            csv_path = _create_csv([_make_row()], tmp)

            result = import_collection_csv(engine, csv_path, user_id="user1")

            assert len(result["new_entry_ids"]) == 1
            assert result["imported"] == 1

    def test_import_returns_empty_ids_for_empty_csv(self, engine):
        with tempfile.TemporaryDirectory() as tmp:
            csv_path = _create_csv([], tmp)

            result = import_collection_csv(engine, csv_path, user_id="user1")

            assert result["new_entry_ids"] == []
            assert result["imported"] == 0


class TestImportSkipsExistingEntries:
    """#14: Duplicate rows not in new_entry_ids (re-import clears and re-creates)."""

    def test_reimport_clears_old_and_returns_new_ids(self, engine):
        """Re-importing replaces all entries — new_entry_ids always populated."""
        with tempfile.TemporaryDirectory() as tmp:
            csv_path = _create_csv([_make_row()], tmp)

            # First import
            result1 = import_collection_csv(engine, csv_path, user_id="user1")
            first_ids = result1["new_entry_ids"]
            assert len(first_ids) == 1

            # Second import (same CSV — clears and re-creates)
            result2 = import_collection_csv(engine, csv_path, user_id="user1")
            second_ids = result2["new_entry_ids"]

            # New entries were created (old ones deleted first)
            assert len(second_ids) == 1
            assert result2["imported"] == 1
            # Verify the entry exists in the database
            with Session(engine) as session:
                row = session.get(UserCollectionRow, second_ids[0])
                assert row is not None
                assert row.user_id == "user1"

    def test_skipped_rows_not_in_new_entry_ids(self, engine):
        """Rows without set_code or collector_number are skipped."""
        with tempfile.TemporaryDirectory() as tmp:
            csv_path = _create_csv(
                [
                    _make_row(name_en="Good Card", set_code="lea", number="161"),
                    _make_row(name_en="Bad Card", set_code="", number=""),  # skipped
                ],
                tmp,
            )

            result = import_collection_csv(engine, csv_path, user_id="user1")

            assert len(result["new_entry_ids"]) == 1
            assert result["imported"] == 1
            assert result["skipped"] == 1


class TestImportResultHasCanonizeScheduled:
    """#15: ImportResult schema field canonize_scheduled present and defaults False."""

    def test_import_result_schema_has_canonize_scheduled_field(self):
        from src.api.schemas.collection import ImportResult

        result = ImportResult(
            imported=1,
            skipped=0,
            linked=1,
            total_csv_rows=1,
        )
        assert hasattr(result, "canonize_scheduled")
        assert result.canonize_scheduled is False

    def test_import_result_schema_canonize_scheduled_can_be_set_true(self):
        from src.api.schemas.collection import ImportResult

        result = ImportResult(
            imported=1,
            skipped=0,
            linked=1,
            total_csv_rows=1,
            canonize_scheduled=True,
        )
        assert result.canonize_scheduled is True

    def test_import_result_schema_has_new_entry_ids_field(self):
        from src.api.schemas.collection import ImportResult

        result = ImportResult(
            imported=1,
            skipped=0,
            linked=1,
            total_csv_rows=1,
            new_entry_ids=[10, 20],
        )
        assert result.new_entry_ids == [10, 20]

    def test_import_result_schema_new_entry_ids_defaults_empty(self):
        from src.api.schemas.collection import ImportResult

        result = ImportResult(
            imported=0,
            skipped=0,
            linked=0,
            total_csv_rows=0,
        )
        assert result.new_entry_ids == []


class TestImportNoNewEntriesSkipsCanonize:
    """#18: When all entries are skipped, no background task should be scheduled."""

    def test_import_all_skipped_returns_empty_new_entry_ids(self, engine):
        """If all rows have missing fields, no entries are created."""
        with tempfile.TemporaryDirectory() as tmp:
            csv_path = _create_csv(
                [
                    _make_row(name_en="Bad Card 1", set_code="", number=""),
                    _make_row(name_en="Bad Card 2", set_code="", number=""),
                ],
                tmp,
            )

            result = import_collection_csv(engine, csv_path, user_id="user1")

            assert result["new_entry_ids"] == []
            assert result["imported"] == 0
            assert result["skipped"] == 2
