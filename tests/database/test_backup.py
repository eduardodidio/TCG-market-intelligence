"""Tests for src.database.backup -- SQLite backup utility."""

from __future__ import annotations

import sqlite3

import pytest

from src.database.backup import backup_database, extract_db_path


class TestExtractDbPath:
    def test_relative_path(self):
        assert extract_db_path("sqlite:///tcg_market.db") == "tcg_market.db"

    def test_absolute_path_unix(self):
        assert extract_db_path("sqlite:////tmp/data.db") == "/tmp/data.db"

    def test_unsupported_url(self):
        with pytest.raises(ValueError, match="Unsupported database URL"):
            extract_db_path("postgresql://localhost/db")

    def test_empty_path(self):
        # sqlite:/// with nothing after it -> empty string
        assert extract_db_path("sqlite:///") == ""


class TestBackupDatabase:
    def test_creates_valid_sqlite_backup(self, tmp_path):
        """Backup creates a valid SQLite file that contains the same data."""
        db_path = str(tmp_path / "source.db")
        # Create a source DB with some data
        conn = sqlite3.connect(db_path)
        conn.execute("CREATE TABLE t (id INTEGER PRIMARY KEY, val TEXT)")
        conn.execute("INSERT INTO t VALUES (1, 'hello')")
        conn.commit()
        conn.close()

        backup_dir = str(tmp_path / "bkp")
        result = backup_database(db_path, backup_dir=backup_dir)

        assert result.exists()
        assert result.suffix == ".db"
        assert result.parent.name == "bkp"

        # Verify backup contains the data
        bkp_conn = sqlite3.connect(str(result))
        rows = bkp_conn.execute("SELECT * FROM t").fetchall()
        bkp_conn.close()
        assert rows == [(1, "hello")]

    def test_backup_filename_contains_timestamp(self, tmp_path):
        db_path = str(tmp_path / "source.db")
        sqlite3.connect(db_path).close()  # create empty DB

        result = backup_database(db_path, backup_dir=str(tmp_path / "bkp"))
        assert result.name.startswith("tcg_market_")
        assert result.name.endswith(".db")
        # Timestamp part: YYYYMMDD_HHMMSS (15 chars)
        stem = result.stem  # e.g. tcg_market_20260819_143000
        timestamp_part = stem[len("tcg_market_") :]
        assert len(timestamp_part) == 15  # YYYYMMDD_HHMMSS

    def test_backup_creates_directory_if_missing(self, tmp_path):
        db_path = str(tmp_path / "source.db")
        sqlite3.connect(db_path).close()

        nested = str(tmp_path / "a" / "b" / "c")
        result = backup_database(db_path, backup_dir=nested)
        assert result.exists()

    def test_backup_error_when_db_missing(self, tmp_path):
        with pytest.raises(FileNotFoundError, match="Database file not found"):
            backup_database(str(tmp_path / "nonexistent.db"))

    def test_multiple_backups_coexist(self, tmp_path):
        """Two backups in the same directory should not overwrite each other
        (unless called in the exact same second, which is unlikely in tests)."""
        import time

        db_path = str(tmp_path / "source.db")
        sqlite3.connect(db_path).close()

        bkp_dir = str(tmp_path / "bkp")
        path1 = backup_database(db_path, backup_dir=bkp_dir)
        time.sleep(1.1)  # ensure different timestamp
        path2 = backup_database(db_path, backup_dir=bkp_dir)

        assert path1 != path2
        assert path1.exists()
        assert path2.exists()
