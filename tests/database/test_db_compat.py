"""Tests for database dialect compatibility layer."""

from __future__ import annotations

from sqlalchemy import create_engine

from src.database.compat import dialect_insert, is_sqlite
from src.database.models import CardRow, PriceObservationRow


class TestIsSqlite:
    def test_sqlite_memory(self):
        engine = create_engine("sqlite:///:memory:")
        assert is_sqlite(engine) is True

    def test_sqlite_file(self):
        engine = create_engine("sqlite:///test.db")
        assert is_sqlite(engine) is True

    def test_non_sqlite(self):
        """Mock a non-SQLite engine by overriding dialect name."""
        engine = create_engine("sqlite:///:memory:")
        original = engine.dialect.name
        engine.dialect.name = "postgresql"
        try:
            assert is_sqlite(engine) is False
        finally:
            engine.dialect.name = original


class TestDialectInsert:
    def test_sqlite_insert_has_conflict_methods(self):
        engine = create_engine("sqlite:///:memory:")
        stmt = dialect_insert(engine, CardRow)
        assert hasattr(stmt, "on_conflict_do_nothing")
        assert hasattr(stmt, "on_conflict_do_update")

    def test_sqlite_insert_returns_sqlite_dialect(self):
        engine = create_engine("sqlite:///:memory:")
        stmt = dialect_insert(engine, PriceObservationRow)
        assert "sqlite" in type(stmt).__module__

    def test_pg_insert_returns_pg_dialect(self):
        """Verify PG dialect import path works (no actual PG connection needed)."""
        engine = create_engine("sqlite:///:memory:")
        engine.dialect.name = "postgresql"
        try:
            stmt = dialect_insert(engine, CardRow)
            assert "postgresql" in type(stmt).__module__
            assert hasattr(stmt, "on_conflict_do_nothing")
            assert hasattr(stmt, "on_conflict_do_update")
        finally:
            engine.dialect.name = "sqlite"

    def test_sqlite_insert_accepts_different_tables(self):
        """Dialect insert works for multiple model classes."""
        engine = create_engine("sqlite:///:memory:")
        stmt_card = dialect_insert(engine, CardRow)
        stmt_price = dialect_insert(engine, PriceObservationRow)
        # Both should be valid insert statements from the same dialect
        assert "sqlite" in type(stmt_card).__module__
        assert "sqlite" in type(stmt_price).__module__
