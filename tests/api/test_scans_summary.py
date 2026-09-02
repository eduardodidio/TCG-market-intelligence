"""Tests for F98-T01: computed summary fields on ScanRun API."""

from __future__ import annotations

import json

from src.api.routers.scans import _parse_error_counts
from src.api.schemas.scans import ScanRunResponse
from src.domain.events import ScanEvent


class TestParseErrorCounts:
    """Unit tests for _parse_error_counts helper."""

    def test_none_input_returns_zeros(self) -> None:
        result = _parse_error_counts(None)
        assert result == {"not_found": 0, "rate_limited": 0}

    def test_empty_string_returns_zeros(self) -> None:
        result = _parse_error_counts("")
        assert result == {"not_found": 0, "rate_limited": 0}

    def test_empty_array_returns_zeros(self) -> None:
        result = _parse_error_counts("[]")
        assert result == {"not_found": 0, "rate_limited": 0}

    def test_mixed_errors(self) -> None:
        errors = [
            "Sol Ring: NotFoundError: card not found on MYP",
            "Lightning Bolt: NotFoundError: 404",
            "Black Lotus: RateLimitError: 429 too many requests",
            "Mox Pearl: LigaError: unexpected response",
        ]
        result = _parse_error_counts(json.dumps(errors))
        assert result == {"not_found": 2, "rate_limited": 1}

    def test_invalid_json_returns_zeros(self) -> None:
        result = _parse_error_counts("not valid json {{{")
        assert result == {"not_found": 0, "rate_limited": 0}

    def test_non_array_json_returns_zeros(self) -> None:
        result = _parse_error_counts(json.dumps({"key": "value"}))
        assert result == {"not_found": 0, "rate_limited": 0}

    def test_non_string_elements_are_skipped(self) -> None:
        errors = ["card1: NotFoundError: 404", 42, None, "card2: RateLimitError: 429"]
        result = _parse_error_counts(json.dumps(errors))
        assert result == {"not_found": 1, "rate_limited": 1}


class TestScanRunResponseSchema:
    """Tests for computed fields on ScanRunResponse."""

    def test_has_computed_fields_with_defaults(self) -> None:
        resp = ScanRunResponse(
            id=1,
            scan_type="collection",
            filters_json="{}",
            status="completed",
            cards_total=10,
            cards_processed=10,
            cards_failed=2,
            observations_saved=8,
            created_at="2026-09-01T00:00:00",
        )
        assert resp.not_found_count == 0
        assert resp.rate_limited_count == 0
        assert resp.priced_count == 0

    def test_computed_fields_set_explicitly(self) -> None:
        resp = ScanRunResponse(
            id=1,
            scan_type="collection",
            filters_json="{}",
            status="completed",
            cards_total=10,
            cards_processed=10,
            cards_failed=3,
            observations_saved=7,
            created_at="2026-09-01T00:00:00",
            not_found_count=2,
            rate_limited_count=1,
            priced_count=7,
        )
        assert resp.not_found_count == 2
        assert resp.rate_limited_count == 1
        assert resp.priced_count == 7


class TestScanEventCounts:
    """Tests for ScanEvent not_found_count and rate_limited_count fields."""

    def test_scan_event_serializes_counts(self) -> None:
        event = ScanEvent(
            event_type="scan_complete",
            scan_id=42,
            timestamp="2026-09-01T12:00:00",
            cards_processed=10,
            cards_total=10,
            cards_failed=3,
            observations_saved=7,
            not_found_count=2,
            rate_limited_count=1,
        )
        data = json.loads(event.to_sse_json())
        assert data["not_found_count"] == 2
        assert data["rate_limited_count"] == 1

    def test_scan_event_defaults_to_zero(self) -> None:
        event = ScanEvent(
            event_type="scan_complete",
            scan_id=1,
            timestamp="2026-09-01T12:00:00",
        )
        data = json.loads(event.to_sse_json())
        assert data["not_found_count"] == 0
        assert data["rate_limited_count"] == 0
