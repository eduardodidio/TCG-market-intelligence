"""Tests for collection scan domain models."""

from __future__ import annotations

import json

from src.domain.models import ScanFilter, ScanRun, ScanStatus, ScanType


class TestScanStatus:
    def test_enum_values(self):
        assert ScanStatus.PENDING == "pending"
        assert ScanStatus.RUNNING == "running"
        assert ScanStatus.COMPLETED == "completed"
        assert ScanStatus.FAILED == "failed"
        assert ScanStatus.CANCELLED == "cancelled"

    def test_enum_from_string(self):
        assert ScanStatus("pending") is ScanStatus.PENDING
        assert ScanStatus("completed") is ScanStatus.COMPLETED


class TestScanType:
    def test_enum_values(self):
        assert ScanType.COLLECTION == "collection"
        assert ScanType.SET == "set"
        assert ScanType.FORMAT == "format"
        assert ScanType.CUSTOM == "custom"

    def test_enum_from_string(self):
        assert ScanType("collection") is ScanType.COLLECTION
        assert ScanType("set") is ScanType.SET


class TestScanFilter:
    def test_default_values(self):
        f = ScanFilter()
        assert f.scan_type is ScanType.COLLECTION
        assert f.set_codes is None
        assert f.format_name is None
        assert f.rarities is None
        assert f.card_ids is None
        assert f.collection_only is True
        assert f.limit is None

    def test_round_trip_json_defaults(self):
        original = ScanFilter()
        restored = ScanFilter.from_json(original.to_json())
        assert restored.scan_type == original.scan_type
        assert restored.set_codes == original.set_codes
        assert restored.collection_only == original.collection_only
        assert restored.limit == original.limit

    def test_round_trip_json_all_fields(self):
        original = ScanFilter(
            scan_type=ScanType.SET,
            set_codes=["MH3", "ONE"],
            format_name="modern",
            rarities=["mythic", "rare"],
            card_ids=[1, 2, 3],
            collection_only=False,
            limit=50,
        )
        restored = ScanFilter.from_json(original.to_json())
        assert restored.scan_type == ScanType.SET
        assert restored.set_codes == ["MH3", "ONE"]
        assert restored.format_name == "modern"
        assert restored.rarities == ["mythic", "rare"]
        assert restored.card_ids == [1, 2, 3]
        assert restored.collection_only is False
        assert restored.limit == 50

    def test_from_json_empty_object(self):
        f = ScanFilter.from_json("{}")
        assert f.scan_type is ScanType.COLLECTION
        assert f.collection_only is True
        assert f.set_codes is None
        assert f.limit is None

    def test_to_json_produces_valid_json(self):
        f = ScanFilter(scan_type=ScanType.CUSTOM, card_ids=[10])
        data = json.loads(f.to_json())
        assert data["scan_type"] == "custom"
        assert data["card_ids"] == [10]
        assert data["collection_only"] is True


class TestScanRun:
    def test_default_values(self):
        run = ScanRun()
        assert run.id is None
        assert run.scan_type == "collection"
        assert run.filters_json == "{}"
        assert run.status == "pending"
        assert run.cards_total == 0
        assert run.cards_processed == 0
        assert run.cards_failed == 0
        assert run.observations_saved == 0
        assert run.error_summary is None
        assert run.started_at is None
        assert run.finished_at is None

    def test_custom_values(self):
        from datetime import datetime

        now = datetime.now()
        run = ScanRun(
            id=42,
            scan_type="set",
            filters_json='{"scan_type": "set"}',
            status="running",
            cards_total=100,
            cards_processed=50,
            cards_failed=2,
            observations_saved=48,
            error_summary="2 timeouts",
            started_at=now,
        )
        assert run.id == 42
        assert run.scan_type == "set"
        assert run.status == "running"
        assert run.cards_total == 100
        assert run.cards_processed == 50
        assert run.cards_failed == 2
        assert run.observations_saved == 48
        assert run.error_summary == "2 timeouts"
        assert run.started_at == now
        assert run.finished_at is None
