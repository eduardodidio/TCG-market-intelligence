"""Tests for PostgreSQL guard behavior on SQLite-only features."""

from __future__ import annotations

import pytest

from src.database.backup import extract_db_path


class TestBackupGuard:
    def test_raises_for_postgresql_url(self):
        with pytest.raises(ValueError, match="only supported for SQLite"):
            extract_db_path("postgresql://localhost/db")

    def test_raises_for_mysql_url(self):
        with pytest.raises(ValueError, match="only supported for SQLite"):
            extract_db_path("mysql://localhost/db")

    def test_raises_for_generic_url(self):
        with pytest.raises(ValueError, match="only supported for SQLite"):
            extract_db_path("mssql+pyodbc://server/db")

    def test_allows_sqlite_relative(self):
        result = extract_db_path("sqlite:///tcg_market.db")
        assert result == "tcg_market.db"

    def test_allows_sqlite_absolute(self):
        result = extract_db_path("sqlite:////data/tcg_market.db")
        assert result == "/data/tcg_market.db"

    def test_allows_sqlite_memory(self):
        result = extract_db_path("sqlite:///:memory:")
        assert result == ":memory:"
