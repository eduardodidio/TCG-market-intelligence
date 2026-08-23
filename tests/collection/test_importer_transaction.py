"""Tests for import_collection_csv transaction safety (T1-05)."""

from __future__ import annotations

import csv
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from src.collection.importer import import_collection_csv
from src.database.models import Base, UserCollectionRow


def _create_csv(rows: list[dict], tmp_dir: str) -> Path:
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


def _make_row(name_en="Card", set_code="lea", number="1"):
    return {
        "Card (EN)": name_en,
        "Card (PT)": "",
        "Edicao (Sigla)": set_code,
        "Edicao (EN)": "Alpha",
        "Card #": number,
        "Quantidade": "1",
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


class TestImporterTransactionSafety:
    """T1-05: delete+insert wrapped in transaction; rollback on error."""

    def test_existing_collection_preserved_on_error(self, engine):
        """If insert fails mid-way, the old collection should still be intact."""
        with tempfile.TemporaryDirectory() as tmp:
            # First import: 2 cards successfully
            csv_ok = _create_csv(
                [
                    _make_row("Card A", "lea", "1"),
                    _make_row("Card B", "lea", "2"),
                ],
                tmp,
            )
            result = import_collection_csv(engine, csv_ok, user_id="user1")
            assert result["imported"] == 2

            # Verify 2 entries exist
            with Session(engine) as s:
                count_before = s.query(UserCollectionRow).filter_by(user_id="user1").count()
                assert count_before == 2

            # Second import: simulate error during flush
            csv_new = _create_csv(
                [
                    _make_row("Card C", "lea", "3"),
                ],
                tmp,
            )

            original_flush = Session.flush

            def exploding_flush(self, *args, **kwargs):
                """Fail on the second flush (after card creation, during entry insert)."""
                # Count how many UserCollectionRow objects are pending
                pending_collections = [o for o in self.new if isinstance(o, UserCollectionRow)]
                if pending_collections:
                    raise Exception("Simulated DB error")
                return original_flush(self, *args, **kwargs)

            with patch.object(Session, "flush", exploding_flush):
                with pytest.raises(Exception, match="Simulated DB error"):
                    import_collection_csv(engine, csv_new, user_id="user1")

            # Original collection should be preserved (rollback)
            with Session(engine) as s:
                count_after = s.query(UserCollectionRow).filter_by(user_id="user1").count()
                assert count_after == 2


class TestImporterRequiresUserId:
    """T1-04: user_id is required, no default."""

    def test_user_id_is_required_parameter(self):
        import inspect

        sig = inspect.signature(import_collection_csv)
        param = sig.parameters["user_id"]
        assert param.default is inspect.Parameter.empty
