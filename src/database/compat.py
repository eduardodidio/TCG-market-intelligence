"""Database dialect compatibility layer.

Supports both SQLite (local dev) and PostgreSQL (Neon production).
"""

from __future__ import annotations

from sqlalchemy import Engine


def is_sqlite(engine: Engine) -> bool:
    """Return True if the engine uses the SQLite dialect."""
    return engine.dialect.name == "sqlite"


def dialect_insert(engine: Engine, table):
    """Return a dialect-specific insert() for upsert support.

    Both SQLite and PostgreSQL support .on_conflict_do_update() and
    .on_conflict_do_nothing() but require their own dialect insert.
    """
    if is_sqlite(engine):
        from sqlalchemy.dialects.sqlite import insert
    else:
        from sqlalchemy.dialects.postgresql import insert
    return insert(table)
