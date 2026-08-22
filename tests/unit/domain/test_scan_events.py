"""Tests for ScanEvent domain model (F32-T01)."""

from __future__ import annotations

import json
from decimal import Decimal

from src.domain.events import ScanEvent


class TestScanEvent:
    """Tests for ScanEvent dataclass."""

    def test_create_card_scanned_event(self):
        event = ScanEvent(
            event_type="card_scanned",
            scan_id=42,
            timestamp="2026-08-21T10:00:00",
            external_id="1001",
            card_name="Lightning Bolt",
            price_found=True,
            price=Decimal("12.50"),
            currency="BRL",
            cards_processed=5,
            cards_total=10,
            cards_failed=0,
            observations_saved=5,
        )
        assert event.event_type == "card_scanned"
        assert event.scan_id == 42
        assert event.card_name == "Lightning Bolt"
        assert event.price == Decimal("12.50")
        assert event.cards_total == 10

    def test_create_scan_started_event(self):
        event = ScanEvent(
            event_type="scan_started",
            scan_id=1,
            timestamp="2026-08-21T10:00:00",
            cards_total=50,
        )
        assert event.event_type == "scan_started"
        assert event.cards_total == 50
        assert event.external_id is None
        assert event.card_name is None

    def test_create_scan_complete_event(self):
        event = ScanEvent(
            event_type="scan_complete",
            scan_id=1,
            timestamp="2026-08-21T10:05:00",
            cards_processed=48,
            cards_total=50,
            cards_failed=2,
            observations_saved=45,
        )
        assert event.event_type == "scan_complete"
        assert event.cards_processed == 48
        assert event.cards_failed == 2

    def test_defaults(self):
        event = ScanEvent(
            event_type="scan_started",
            scan_id=1,
            timestamp="2026-08-21T10:00:00",
        )
        assert event.price_found is False
        assert event.price is None
        assert event.currency is None
        assert event.error is None
        assert event.cards_processed == 0
        assert event.cards_total == 0

    def test_to_sse_json_with_price(self):
        event = ScanEvent(
            event_type="card_scanned",
            scan_id=42,
            timestamp="2026-08-21T10:00:00",
            external_id="1001",
            card_name="Lightning Bolt",
            price_found=True,
            price=Decimal("12.50"),
            currency="BRL",
            cards_processed=5,
            cards_total=10,
        )
        result = json.loads(event.to_sse_json())
        assert result["event_type"] == "card_scanned"
        assert result["scan_id"] == 42
        assert result["price"] == 12.5
        assert result["card_name"] == "Lightning Bolt"
        assert isinstance(result["price"], float)

    def test_to_sse_json_without_price(self):
        event = ScanEvent(
            event_type="card_scanned",
            scan_id=1,
            timestamp="2026-08-21T10:00:00",
            external_id="1001",
            card_name="Forest",
            price_found=False,
        )
        result = json.loads(event.to_sse_json())
        assert result["price"] is None
        assert result["price_found"] is False

    def test_to_sse_json_is_valid_json_string(self):
        event = ScanEvent(
            event_type="scan_started",
            scan_id=1,
            timestamp="2026-08-21T10:00:00",
            cards_total=100,
        )
        raw = event.to_sse_json()
        assert isinstance(raw, str)
        parsed = json.loads(raw)
        assert parsed["event_type"] == "scan_started"
        assert parsed["cards_total"] == 100

    def test_to_sse_json_with_error(self):
        event = ScanEvent(
            event_type="card_scanned",
            scan_id=1,
            timestamp="2026-08-21T10:00:00",
            external_id="999",
            error="Connection timeout",
            cards_failed=1,
        )
        result = json.loads(event.to_sse_json())
        assert result["error"] == "Connection timeout"
        assert result["cards_failed"] == 1
