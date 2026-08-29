"""Tests for CSV importer: encoding auto-detect, new fields, set code normalization.

Covers F91-T02 enhancements to src/collection/importer.py.
"""

from __future__ import annotations

import csv
import tempfile
from pathlib import Path

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from src.collection.importer import _detect_encoding, import_collection_csv
from src.database.models import Base, UserCollectionRow
from src.database.repository import Repository

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_FIELDNAMES = [
    "Card (EN)",
    "Card (PT)",
    "Edicao (Sigla)",
    "Edicao (EN)",
    "Edicao (PTBR)",
    "Card #",
    "Quantidade",
    "Qualidade (M NM SP MP HP D)",
    "Idioma (BR EN DE ES FR IT JP KO RU TW)",
    "Raridade (M R U C)",
    "Cor (W U B R G M A L)",
    "Extras",
    "Comentario",
]


def _write_csv(tmp_dir: str, rows: list[dict], encoding: str = "utf-8") -> Path:
    """Write a CSV file with the given rows and encoding."""
    path = Path(tmp_dir) / "collection.csv"
    with open(path, "w", encoding=encoding, newline="") as f:
        writer = csv.DictWriter(f, fieldnames=_FIELDNAMES)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)
    return path


def _make_row(**overrides) -> dict:
    base = {
        "Card (EN)": "Lightning Bolt",
        "Card (PT)": "Relampago",
        "Edicao (Sigla)": "lea",
        "Edicao (EN)": "Limited Edition Alpha",
        "Edicao (PTBR)": "",
        "Card #": "161",
        "Quantidade": "1",
        "Qualidade (M NM SP MP HP D)": "NM",
        "Idioma (BR EN DE ES FR IT JP KO RU TW)": "EN",
        "Raridade (M R U C)": "C",
        "Cor (W U B R G M A L)": "R",
        "Extras": "",
        "Comentario": "",
    }
    base.update(overrides)
    return base


@pytest.fixture()
def engine():
    eng = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(eng)
    return eng


# ---------------------------------------------------------------------------
# Encoding detection
# ---------------------------------------------------------------------------


class TestDetectEncoding:
    def test_detect_encoding_utf8(self):
        """ASCII/UTF-8 content returns 'utf-8-sig'."""
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "test.csv"
            path.write_text("hello world", encoding="utf-8")
            assert _detect_encoding(path) == "utf-8-sig"

    def test_detect_encoding_latin1(self):
        """Bytes with 0xe3 (a-tilde in cp1252) that aren't valid UTF-8 return 'cp1252'."""
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "test.csv"
            # Write raw bytes: "Irm\xe3os" — valid cp1252 but invalid UTF-8
            path.write_bytes(b"Irm\xe3os da Guerra")
            assert _detect_encoding(path) == "cp1252"


# ---------------------------------------------------------------------------
# New fields: set_name_pt, notes
# ---------------------------------------------------------------------------


class TestNewFields:
    def test_import_reads_set_name_pt(self, engine):
        """CSV with 'Edicao (PTBR)' column populates set_name_pt."""
        with tempfile.TemporaryDirectory() as tmp:
            csv_path = _write_csv(
                tmp,
                [_make_row(**{"Edicao (PTBR)": "Edicao Limitada Alfa"})],
            )
            result = import_collection_csv(engine, csv_path, user_id="u1")
            assert result["imported"] == 1

            with Session(engine) as session:
                entry = session.get(UserCollectionRow, result["new_entry_ids"][0])
                assert entry.set_name_pt == "Edicao Limitada Alfa"

    def test_import_reads_notes(self, engine):
        """CSV with 'Comentario' column populates notes."""
        with tempfile.TemporaryDirectory() as tmp:
            csv_path = _write_csv(
                tmp,
                [_make_row(**{"Comentario": "Mint condition, foil"})],
            )
            result = import_collection_csv(engine, csv_path, user_id="u1")
            assert result["imported"] == 1

            with Session(engine) as session:
                entry = session.get(UserCollectionRow, result["new_entry_ids"][0])
                assert entry.notes == "Mint condition, foil"


# ---------------------------------------------------------------------------
# Set code normalization
# ---------------------------------------------------------------------------


class TestSetCodeNormalization:
    def test_import_normalizes_set_codes(self, engine):
        """CSV with MYP variant code 'smbro' is normalized to 'bro'."""
        with tempfile.TemporaryDirectory() as tmp:
            csv_path = _write_csv(
                tmp,
                [_make_row(**{"Edicao (Sigla)": "smbro"})],
            )
            result = import_collection_csv(engine, csv_path, user_id="u1")
            assert result["imported"] == 1

            with Session(engine) as session:
                entry = session.get(UserCollectionRow, result["new_entry_ids"][0])
                assert entry.set_code == "bro"


# ---------------------------------------------------------------------------
# Encoding round-trip (cp1252 CSV preserves accented chars)
# ---------------------------------------------------------------------------


class TestEncodingRoundTrip:
    def test_import_preserves_accented_chars(self, engine):
        """CSV in cp1252 with accented chars like 'Irmaos' is correctly decoded."""
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "collection.csv"
            # Write CSV in cp1252 encoding (common for Liga exports)
            with open(path, "w", encoding="cp1252", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=_FIELDNAMES)
                writer.writeheader()
                writer.writerow(
                    _make_row(
                        **{
                            "Card (PT)": "Irmãos da Guerra",
                            "Edicao (PTBR)": "A Guerra dos Irmãos",
                            "Comentario": "Condição ótima",
                        }
                    )
                )

            result = import_collection_csv(engine, path, user_id="u1")
            assert result["imported"] == 1

            with Session(engine) as session:
                entry = session.get(UserCollectionRow, result["new_entry_ids"][0])
                assert entry.name_pt == "Irmãos da Guerra"
                assert entry.set_name_pt == "A Guerra dos Irmãos"
                assert entry.notes == "Condição ótima"


# ---------------------------------------------------------------------------
# Backwards compatibility: CSV without new columns
# ---------------------------------------------------------------------------

# Minimal fieldnames without Edicao (PTBR) and Comentario
_LEGACY_FIELDNAMES = [
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


def _write_legacy_csv(tmp_dir: str, rows: list[dict], encoding: str = "utf-8") -> Path:
    """Write a CSV without the new Liga columns."""
    path = Path(tmp_dir) / "collection.csv"
    with open(path, "w", encoding=encoding, newline="") as f:
        writer = csv.DictWriter(f, fieldnames=_LEGACY_FIELDNAMES)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)
    return path


def _make_legacy_row(**overrides) -> dict:
    base = {
        "Card (EN)": "Lightning Bolt",
        "Card (PT)": "Relampago",
        "Edicao (Sigla)": "lea",
        "Edicao (EN)": "Limited Edition Alpha",
        "Card #": "161",
        "Quantidade": "1",
        "Qualidade (M NM SP MP HP D)": "NM",
        "Idioma (BR EN DE ES FR IT JP KO RU TW)": "EN",
        "Raridade (M R U C)": "C",
        "Cor (W U B R G M A L)": "R",
        "Extras": "",
    }
    base.update(overrides)
    return base


class TestBackwardsCompatibility:
    def test_csv_without_new_columns_imports_fine(self, engine):
        """CSV missing 'Edicao (PTBR)' and 'Comentario' columns still imports."""
        with tempfile.TemporaryDirectory() as tmp:
            csv_path = _write_legacy_csv(tmp, [_make_legacy_row()])
            result = import_collection_csv(engine, csv_path, user_id="u1")
            assert result["imported"] == 1
            assert result["skipped"] == 0

            with Session(engine) as session:
                entry = session.get(UserCollectionRow, result["new_entry_ids"][0])
                assert entry.set_name_pt is None
                assert entry.notes is None
                assert entry.name_en == "Lightning Bolt"


class TestEmptyCsv:
    def test_empty_csv_file(self, engine):
        """Empty CSV (header only) imports zero rows without error."""
        with tempfile.TemporaryDirectory() as tmp:
            csv_path = _write_csv(tmp, [])
            result = import_collection_csv(engine, csv_path, user_id="u1")
            assert result["imported"] == 0
            assert result["skipped"] == 0
            assert result["total_csv_rows"] == 0
            assert result["new_entry_ids"] == []

    def test_truly_empty_csv_file(self, engine):
        """Completely empty file (no header) imports zero rows without error."""
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "empty.csv"
            path.write_text("")
            result = import_collection_csv(engine, path, user_id="u1")
            assert result["imported"] == 0
            assert result["skipped"] == 0
            assert result["total_csv_rows"] == 0


# ---------------------------------------------------------------------------
# Migration: _ensure_columns adds set_name_pt and notes to existing DB
# ---------------------------------------------------------------------------


class TestEnsureColumnsMigration:
    def test_ensure_columns_adds_new_columns(self):
        """Repository._ensure_columns adds set_name_pt and notes to user_collection."""
        eng = create_engine("sqlite:///:memory:")
        # Create tables WITHOUT the new columns by using raw DDL
        with eng.begin() as conn:
            conn.execute(
                text("""
                CREATE TABLE user_collection (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id VARCHAR(100) NOT NULL,
                    card_id INTEGER,
                    set_code VARCHAR(20) NOT NULL,
                    collector_number VARCHAR(20) NOT NULL,
                    name_en VARCHAR(500),
                    name_pt VARCHAR(500),
                    set_name_en VARCHAR(200),
                    quantity INTEGER DEFAULT 1,
                    quality VARCHAR(10),
                    language VARCHAR(10),
                    rarity VARCHAR(5),
                    color VARCHAR(10),
                    extras VARCHAR(200),
                    created_at DATETIME
                )
            """)
            )
            # Create other required tables so Repository init doesn't fail
            conn.execute(
                text("""
                CREATE TABLE users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    email VARCHAR(320) UNIQUE NOT NULL,
                    display_name VARCHAR(200),
                    avatar_url VARCHAR(1000),
                    auth_provider VARCHAR(20) NOT NULL,
                    provider_id VARCHAR(200),
                    password_hash VARCHAR(200),
                    password_expires_at DATETIME,
                    preferred_currency VARCHAR(10) DEFAULT 'BRL',
                    preferred_language VARCHAR(10) DEFAULT 'en',
                    is_active INTEGER DEFAULT 1,
                    is_admin INTEGER DEFAULT 0,
                    created_at DATETIME,
                    updated_at DATETIME
                )
            """)
            )

        # Verify columns don't exist yet
        from sqlalchemy import inspect as sa_inspect

        insp = sa_inspect(eng)
        col_names = {c["name"] for c in insp.get_columns("user_collection")}
        assert "set_name_pt" not in col_names
        assert "notes" not in col_names

        # Now create Repository which calls _ensure_columns
        repo = Repository(db_url="sqlite:///:memory:")
        # We need to call _ensure_columns on our specific engine
        # Instead, simulate by calling it directly
        repo.engine = eng
        repo._ensure_columns()

        # Verify columns now exist
        insp = sa_inspect(eng)
        col_names = {c["name"] for c in insp.get_columns("user_collection")}
        assert "set_name_pt" in col_names
        assert "notes" in col_names
