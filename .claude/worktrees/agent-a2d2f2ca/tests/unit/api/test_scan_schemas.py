from __future__ import annotations

from src.api.schemas.scans import (
    ScanListResponse,
    ScanRequest,
    ScanRunResponse,
    ScanTriggerResponse,
)


class TestScanRequestDefaults:
    def test_empty_request_has_defaults(self) -> None:
        req = ScanRequest()
        assert req.scan_type == "collection"
        assert req.dry_run is False
        assert req.set_codes is None
        assert req.format_name is None
        assert req.rarities is None
        assert req.card_ids is None
        assert req.limit is None


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


class TestScanTriggerResponse:
    def test_returns_scan_id_and_status(self) -> None:
        resp = ScanTriggerResponse(scan_id=7, status="queued")
        assert resp.scan_id == 7
        assert resp.status == "queued"
