"""Tests for AuditLogRow model (F100-T01)."""

from __future__ import annotations

from datetime import datetime

import pytest
from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import Session

from src.database.models import AuditLogRow, Base


@pytest.fixture()
def engine(tmp_path):
    db_path = tmp_path / "test_audit.db"
    eng = create_engine(f"sqlite:///{db_path}", echo=False)
    Base.metadata.create_all(eng)
    return eng


def test_audit_log_table_created(engine):
    """create_all creates the audit_log table."""
    insp = inspect(engine)
    assert "audit_log" in insp.get_table_names()


def test_audit_log_insert_and_read(engine):
    """Can insert an AuditLogRow and read it back with all fields."""
    with Session(engine) as session:
        row = AuditLogRow(
            actor_id=1,
            actor_email="admin@example.com",
            action="user_create",
            target_type="user",
            target_id="42",
            details_json='{"email": "new@example.com"}',
            ip_address="127.0.0.1",
        )
        session.add(row)
        session.commit()
        session.refresh(row)

        assert row.id is not None
        assert row.actor_id == 1
        assert row.actor_email == "admin@example.com"
        assert row.action == "user_create"
        assert row.target_type == "user"
        assert row.target_id == "42"
        assert row.details_json == '{"email": "new@example.com"}'
        assert row.ip_address == "127.0.0.1"
        assert isinstance(row.timestamp, datetime)


def test_audit_log_indexes_exist(engine):
    """Indexes on timestamp, actor_id, and action columns exist."""
    insp = inspect(engine)
    indexes = insp.get_indexes("audit_log")
    index_names = {idx["name"] for idx in indexes}
    assert "ix_audit_log_timestamp" in index_names
    assert "ix_audit_log_actor" in index_names
    assert "ix_audit_log_action" in index_names


def test_audit_log_nullable_fields(engine):
    """target_type, target_id, details_json, ip_address are nullable."""
    with Session(engine) as session:
        row = AuditLogRow(
            actor_id=1,
            actor_email="admin@example.com",
            action="db_backup",
        )
        session.add(row)
        session.commit()
        session.refresh(row)

        assert row.target_type is None
        assert row.target_id is None
        assert row.details_json is None
        assert row.ip_address is None
