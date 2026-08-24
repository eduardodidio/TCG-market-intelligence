"""Tests for the ScanRunRow database model."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import Session

from src.database.models import Base, ScanRunRow


class TestScanRunRowTableCreation:
    """Verify scan_runs table is created correctly."""

    def test_create_all_creates_scan_runs_table(self) -> None:
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(engine)

        inspector = inspect(engine)
        table_names = inspector.get_table_names()
        assert "scan_runs" in table_names

    def test_scan_runs_table_has_expected_columns(self) -> None:
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(engine)

        inspector = inspect(engine)
        columns = {col["name"] for col in inspector.get_columns("scan_runs")}
        expected = {
            "id",
            "scan_type",
            "filters_json",
            "status",
            "cards_total",
            "cards_processed",
            "cards_failed",
            "observations_saved",
            "error_summary",
            "started_at",
            "finished_at",
            "created_at",
        }
        assert expected == columns

    def test_scan_runs_table_has_indexes(self) -> None:
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(engine)

        inspector = inspect(engine)
        indexes = inspector.get_indexes("scan_runs")
        index_names = {idx["name"] for idx in indexes}
        assert "ix_scan_runs_status" in index_names
        assert "ix_scan_runs_type_date" in index_names


class TestScanRunRowInsertAllFields:
    """Insert with all fields and read back."""

    def test_insert_and_read_all_fields(self) -> None:
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(engine)

        now = datetime(2026, 8, 20, 12, 0, 0)
        row = ScanRunRow(
            scan_type="full",
            filters_json='{"set_code": "MH3"}',
            status="completed",
            cards_total=100,
            cards_processed=95,
            cards_failed=5,
            observations_saved=90,
            error_summary="5 cards returned 404",
            started_at=now,
            finished_at=now,
            created_at=now,
        )

        with Session(engine) as session:
            session.add(row)
            session.commit()
            session.refresh(row)

            assert row.id is not None
            assert row.scan_type == "full"
            assert row.filters_json == '{"set_code": "MH3"}'
            assert row.status == "completed"
            assert row.cards_total == 100
            assert row.cards_processed == 95
            assert row.cards_failed == 5
            assert row.observations_saved == 90
            assert row.error_summary == "5 cards returned 404"
            assert row.started_at == now
            assert row.finished_at == now
            assert row.created_at == now


class TestScanRunRowDefaults:
    """Insert with only required fields and verify defaults."""

    def test_defaults_applied(self) -> None:
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(engine)

        row = ScanRunRow(scan_type="collection")

        with Session(engine) as session:
            session.add(row)
            session.commit()
            session.refresh(row)

            assert row.id is not None
            assert row.scan_type == "collection"
            assert row.filters_json == "{}"
            assert row.status == "pending"
            assert row.cards_total == 0
            assert row.cards_processed == 0
            assert row.cards_failed == 0
            assert row.observations_saved == 0
            assert row.created_at is not None


class TestScanRunRowNullableFields:
    """Nullable fields accept None."""

    def test_nullable_fields_accept_none(self) -> None:
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(engine)

        row = ScanRunRow(
            scan_type="partial",
            error_summary=None,
            started_at=None,
            finished_at=None,
        )

        with Session(engine) as session:
            session.add(row)
            session.commit()
            session.refresh(row)

            assert row.error_summary is None
            assert row.started_at is None
            assert row.finished_at is None
