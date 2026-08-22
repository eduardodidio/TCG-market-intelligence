"""Tests for ScheduledScan domain models and ScheduledScanRow DB model (F37-T01)."""

from __future__ import annotations

from datetime import datetime

import pytest

from src.database.models import Base, ScheduledScanRow
from src.domain.models import ScheduledScan, ScheduleStatus


class TestScheduleStatus:
    """ScheduleStatus enum tests."""

    def test_has_three_values(self) -> None:
        assert len(ScheduleStatus) == 3

    def test_active_value(self) -> None:
        assert ScheduleStatus("active") == ScheduleStatus.ACTIVE

    def test_paused_value(self) -> None:
        assert ScheduleStatus("paused") == ScheduleStatus.PAUSED

    def test_disabled_value(self) -> None:
        assert ScheduleStatus("disabled") == ScheduleStatus.DISABLED

    def test_invalid_value_raises(self) -> None:
        with pytest.raises(ValueError):
            ScheduleStatus("invalid")


class TestScheduledScan:
    """ScheduledScan dataclass tests."""

    def test_defaults(self) -> None:
        scan = ScheduledScan()
        assert scan.status == "active"
        assert scan.error_count == 0
        assert scan.max_retries == 3
        assert scan.cron_expression == "0 6 * * *"
        assert scan.scan_type == "collection"
        assert scan.filters_json == "{}"
        assert scan.id is None
        assert scan.name == ""
        assert scan.description is None

    def test_all_fields_populated(self) -> None:
        now = datetime(2026, 8, 21, 12, 0, 0)
        scan = ScheduledScan(
            id=1,
            name="Daily Collection",
            description="Scan all collection cards daily",
            cron_expression="0 6 * * *",
            scan_type="collection",
            filters_json='{"collection_only": true}',
            status="paused",
            last_run_id=42,
            last_run_at=now,
            next_run_at=now,
            error_count=2,
            max_retries=5,
            created_at=now,
            updated_at=now,
        )
        assert scan.id == 1
        assert scan.name == "Daily Collection"
        assert scan.description == "Scan all collection cards daily"
        assert scan.status == "paused"
        assert scan.last_run_id == 42
        assert scan.error_count == 2
        assert scan.max_retries == 5


class TestScheduledScanRow:
    """ScheduledScanRow SQLAlchemy model tests."""

    def test_instantiate_with_required_fields(self) -> None:
        row = ScheduledScanRow(
            user_id="1",
            name="Test Schedule",
            cron_expression="0 6 * * *",
            scan_type="collection",
        )
        assert row.name == "Test Schedule"
        assert row.cron_expression == "0 6 * * *"
        assert row.scan_type == "collection"
        assert row.user_id == "1"

    def test_table_name(self) -> None:
        assert ScheduledScanRow.__tablename__ == "scheduled_scans"

    def test_table_in_metadata(self) -> None:
        table_names = [t.name for t in Base.metadata.sorted_tables]
        assert "scheduled_scans" in table_names

    def test_status_index_exists(self) -> None:
        indexes = ScheduledScanRow.__table__.indexes
        index_names = {idx.name for idx in indexes}
        assert "ix_scheduled_scans_status" in index_names
