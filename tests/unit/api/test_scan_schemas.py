from __future__ import annotations

from src.api.schemas.scans import (
    ScanListResponse,
    ScanPreviewResponse,
    ScanRequest,
    ScanRunResponse,
    ScanTriggerResponse,
)


class TestScanRequestDefaults:
    def test_empty_request_has_defaults(self) -> None:
        req = ScanRequest()
        assert req.scan_type == "collection"
        assert req.provider == "liga"
        assert req.dry_run is False
        assert req.set_codes is None
        assert req.format_name is None
        assert req.rarities is None
        assert req.card_ids is None
        assert req.limit is None
        assert req.max_age_days is None

    def test_max_age_days_set(self) -> None:
        req = ScanRequest(max_age_days=7)
        assert req.max_age_days == 7

    def test_provider_defaults_to_liga(self) -> None:
        req = ScanRequest()
        assert req.provider == "liga"

    def test_provider_can_be_myp(self) -> None:
        req = ScanRequest(provider="myp")
        assert req.provider == "myp"


class TestScanRequestWithFilters:
    def test_set_codes_parsed(self) -> None:
        req = ScanRequest(set_codes=["dmr", "one"])
        assert req.set_codes == ["dmr", "one"]

    def test_card_ids_parsed(self) -> None:
        req = ScanRequest(card_ids=[1, 2, 3], limit=10, dry_run=True)
        assert req.card_ids == [1, 2, 3]
        assert req.limit == 10
        assert req.dry_run is True

    def test_rarities_and_format(self) -> None:
        req = ScanRequest(rarities=["mythic", "rare"], format_name="standard")
        assert req.rarities == ["mythic", "rare"]
        assert req.format_name == "standard"


class TestScanRunResponse:
    def test_from_dict(self) -> None:
        data = {
            "id": 42,
            "scan_type": "collection",
            "filters_json": '{"set_codes": ["dmr"]}',
            "status": "completed",
            "cards_total": 100,
            "cards_processed": 95,
            "cards_failed": 5,
            "observations_saved": 90,
            "error_summary": None,
            "started_at": "2026-08-20T10:00:00",
            "finished_at": "2026-08-20T10:05:00",
            "created_at": "2026-08-20T09:59:00",
        }
        resp = ScanRunResponse(**data)
        assert resp.id == 42
        assert resp.scan_type == "collection"
        assert resp.status == "completed"
        assert resp.cards_total == 100
        assert resp.cards_processed == 95
        assert resp.cards_failed == 5
        assert resp.observations_saved == 90
        assert resp.error_summary is None
        assert resp.started_at == "2026-08-20T10:00:00"
        assert resp.finished_at == "2026-08-20T10:05:00"
        assert resp.created_at == "2026-08-20T09:59:00"

    def test_provider_field_optional(self) -> None:
        data = {
            "id": 1,
            "scan_type": "collection",
            "filters_json": "{}",
            "status": "completed",
            "cards_total": 10,
            "cards_processed": 10,
            "cards_failed": 0,
            "observations_saved": 10,
            "provider": "liga",
            "created_at": "2026-08-20T10:00:00",
        }
        resp = ScanRunResponse(**data)
        assert resp.provider == "liga"

    def test_provider_field_defaults_to_none(self) -> None:
        data = {
            "id": 1,
            "scan_type": "collection",
            "filters_json": "{}",
            "status": "completed",
            "cards_total": 10,
            "cards_processed": 10,
            "cards_failed": 0,
            "observations_saved": 10,
            "created_at": "2026-08-20T10:00:00",
        }
        resp = ScanRunResponse(**data)
        assert resp.provider is None

    def test_error_summary_optional(self) -> None:
        data = {
            "id": 1,
            "scan_type": "collection",
            "filters_json": "{}",
            "status": "failed",
            "cards_total": 10,
            "cards_processed": 0,
            "cards_failed": 10,
            "observations_saved": 0,
            "error_summary": "timeout after 30s",
            "started_at": None,
            "finished_at": None,
            "created_at": "2026-08-20T09:00:00",
        }
        resp = ScanRunResponse(**data)
        assert resp.error_summary == "timeout after 30s"
        assert resp.started_at is None


class TestScanListResponse:
    def test_wraps_list_with_total(self) -> None:
        scan_data = {
            "id": 1,
            "scan_type": "collection",
            "filters_json": "{}",
            "status": "completed",
            "cards_total": 50,
            "cards_processed": 50,
            "cards_failed": 0,
            "observations_saved": 50,
            "error_summary": None,
            "started_at": "2026-08-20T10:00:00",
            "finished_at": "2026-08-20T10:01:00",
            "created_at": "2026-08-20T09:59:00",
        }
        resp = ScanListResponse(
            scans=[ScanRunResponse(**scan_data)],
            total=1,
        )
        assert resp.total == 1
        assert len(resp.scans) == 1
        assert resp.scans[0].id == 1


class TestScanPreviewResponse:
    def test_preview_response_fields(self) -> None:
        resp = ScanPreviewResponse(card_count=10, skipped_count=3, credit_cost=10)
        assert resp.card_count == 10
        assert resp.skipped_count == 3
        assert resp.credit_cost == 10

    def test_preview_response_zero_cost(self) -> None:
        resp = ScanPreviewResponse(card_count=5, skipped_count=0, credit_cost=0)
        assert resp.credit_cost == 0


class TestScanTriggerResponse:
    def test_returns_scan_id_and_status(self) -> None:
        resp = ScanTriggerResponse(scan_id=7, status="queued")
        assert resp.scan_id == 7
        assert resp.status == "queued"
