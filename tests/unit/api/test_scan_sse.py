"""Tests for the SSE scan streaming endpoint (F32-T03)."""

from __future__ import annotations

import asyncio
import json
from unittest.mock import MagicMock, patch

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from src.api.routers.scans import router
from src.domain.events import ScanEvent
from src.events import scan_bus

# Build a minimal FastAPI app with the scans router
_app = FastAPI()
_app.include_router(router, prefix="/api/v1")


@pytest.fixture(autouse=True)
def _reset_bus():
    scan_bus._reset()
    yield
    scan_bus._reset()


def _scan_run_dict(
    scan_id: int = 1,
    status: str = "running",
    cards_total: int = 10,
    cards_processed: int = 0,
    **kwargs,
) -> dict:
    return {
        "id": scan_id,
        "scan_type": "collection",
        "filters_json": "{}",
        "status": status,
        "cards_total": cards_total,
        "cards_processed": cards_processed,
        "cards_failed": kwargs.get("cards_failed", 0),
        "observations_saved": kwargs.get("observations_saved", 0),
        "error_summary": kwargs.get("error_summary"),
        "started_at": kwargs.get("started_at"),
        "finished_at": kwargs.get("finished_at"),
        "created_at": kwargs.get("created_at"),
    }


def _mock_user():
    """Return a mock user row for auth."""
    user = MagicMock()
    user.id = 1
    user.is_active = True
    user.email = "test@example.com"
    user.display_name = "Test"
    user.avatar_url = None
    user.auth_provider = "email"
    user.preferred_currency = "BRL"
    user.preferred_language = "en"
    return user


@pytest.mark.asyncio
class TestScanSSE:
    """Tests for GET /scans/{scan_id}/stream endpoint."""

    async def test_returns_401_without_token(self):
        with patch("src.api.routers.scans.Repository") as MockRepo:
            repo = MockRepo.return_value
            repo.get_scan_run.return_value = _scan_run_dict()
            # Set TCG_API_KEY to require auth
            with patch.dict("os.environ", {"TCG_API_KEY": "secret"}):
                transport = ASGITransport(app=_app)
                async with AsyncClient(transport=transport, base_url="http://test") as client:
                    resp = await client.get("/api/v1/scans/1/stream")
                    assert resp.status_code == 401

    async def test_returns_404_for_nonexistent_scan(self):
        with patch("src.api.routers.scans.Repository") as MockRepo:
            repo = MockRepo.return_value
            repo.get_scan_run.return_value = None
            transport = ASGITransport(app=_app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.get("/api/v1/scans/999/stream")
                assert resp.status_code == 404

    async def test_completed_scan_returns_single_event(self):
        with patch("src.api.routers.scans.Repository") as MockRepo:
            repo = MockRepo.return_value
            repo.get_scan_run.return_value = _scan_run_dict(
                status="completed",
                cards_total=50,
                cards_processed=48,
                cards_failed=2,
                observations_saved=45,
            )
            transport = ASGITransport(app=_app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.get("/api/v1/scans/1/stream")
                assert resp.status_code == 200
                assert "text/event-stream" in resp.headers["content-type"]
                body = resp.text
                assert "event: scan_complete" in body
                # Parse the data line
                for line in body.strip().split("\n"):
                    if line.startswith("data: "):
                        data = json.loads(line[6:])
                        assert data["event_type"] == "scan_complete"
                        assert data["cards_processed"] == 48
                        assert data["cards_total"] == 50

    async def test_failed_scan_returns_single_event(self):
        with patch("src.api.routers.scans.Repository") as MockRepo:
            repo = MockRepo.return_value
            repo.get_scan_run.return_value = _scan_run_dict(
                status="failed",
                error_summary="Too many errors",
            )
            transport = ASGITransport(app=_app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.get("/api/v1/scans/1/stream")
                assert resp.status_code == 200
                body = resp.text
                assert "event: scan_complete" in body
                for line in body.strip().split("\n"):
                    if line.startswith("data: "):
                        data = json.loads(line[6:])
                        assert data["error"] == "Too many errors"

    async def test_streams_events_from_bus(self):
        with patch("src.api.routers.scans.Repository") as MockRepo:
            repo = MockRepo.return_value
            repo.get_scan_run.return_value = _scan_run_dict(status="running")

            transport = ASGITransport(app=_app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                # We need to publish events while the stream is active.
                # Use a background task.
                async def _publish_events():
                    await asyncio.sleep(0.1)
                    # Find the subscriber queue and publish to it
                    scan_bus.publish(
                        ScanEvent(
                            event_type="card_scanned",
                            scan_id=1,
                            timestamp="2026-08-21T10:00:00",
                            external_id="1001",
                            card_name="Lightning Bolt",
                            price_found=True,
                            cards_processed=1,
                            cards_total=1,
                        )
                    )
                    await asyncio.sleep(0.05)
                    scan_bus.publish(
                        ScanEvent(
                            event_type="scan_complete",
                            scan_id=1,
                            timestamp="2026-08-21T10:00:01",
                            cards_processed=1,
                            cards_total=1,
                        )
                    )

                publish_task = asyncio.create_task(_publish_events())

                resp = await client.get("/api/v1/scans/1/stream")
                await publish_task

                assert resp.status_code == 200
                body = resp.text
                assert "event: card_scanned" in body
                assert "event: scan_complete" in body
                assert "Lightning Bolt" in body

    async def test_sse_headers(self):
        with patch("src.api.routers.scans.Repository") as MockRepo:
            repo = MockRepo.return_value
            repo.get_scan_run.return_value = _scan_run_dict(status="completed")

            transport = ASGITransport(app=_app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.get("/api/v1/scans/1/stream")
                assert resp.headers["cache-control"] == "no-cache"
                assert resp.headers["x-accel-buffering"] == "no"

    async def test_auth_with_api_key(self):
        with patch("src.api.routers.scans.Repository") as MockRepo:
            repo = MockRepo.return_value
            repo.get_scan_run.return_value = _scan_run_dict(status="completed")

            with patch.dict("os.environ", {"TCG_API_KEY": "mysecret"}):
                transport = ASGITransport(app=_app)
                async with AsyncClient(transport=transport, base_url="http://test") as client:
                    resp = await client.get("/api/v1/scans/1/stream?api_key=mysecret")
                    assert resp.status_code == 200

    async def test_auth_with_invalid_api_key(self):
        with patch("src.api.routers.scans.Repository") as MockRepo:
            repo = MockRepo.return_value
            repo.get_scan_run.return_value = _scan_run_dict(status="running")

            with patch.dict("os.environ", {"TCG_API_KEY": "mysecret"}):
                transport = ASGITransport(app=_app)
                async with AsyncClient(transport=transport, base_url="http://test") as client:
                    resp = await client.get("/api/v1/scans/1/stream?api_key=wrong")
                    assert resp.status_code == 401
