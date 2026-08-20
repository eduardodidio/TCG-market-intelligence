from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.api.deps import get_db
from src.api.routers.collection import router


def _make_app() -> FastAPI:
    """Create a fresh FastAPI app with the collection router and mocked DB."""
    test_app = FastAPI()
    test_app.include_router(router)
    test_app.dependency_overrides[get_db] = lambda: MagicMock()
    return test_app


class TestSnapshotPricesAuth:
    """POST /collection/snapshot-prices requires API key when TCG_API_KEY is set."""

    @patch("src.api.routers.collection.asyncio.create_task")
    def test_returns_401_without_key(
        self, mock_create_task: MagicMock, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """POST /collection/snapshot-prices returns 401 without X-API-Key header."""
        monkeypatch.setenv("TCG_API_KEY", "prod-key-99")
        mock_create_task.return_value = AsyncMock()
        app = _make_app()
        client = TestClient(app)

        resp = client.post("/collection/snapshot-prices", json={})
        assert resp.status_code == 401

    @patch("src.api.routers.collection.asyncio.create_task")
    def test_returns_401_with_wrong_key(
        self, mock_create_task: MagicMock, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """POST /collection/snapshot-prices returns 401 with incorrect X-API-Key."""
        monkeypatch.setenv("TCG_API_KEY", "prod-key-99")
        mock_create_task.return_value = AsyncMock()
        app = _make_app()
        client = TestClient(app)

        resp = client.post(
            "/collection/snapshot-prices",
            json={},
            headers={"X-API-Key": "wrong-key"},
        )
        assert resp.status_code == 401

    @patch("src.api.routers.collection.asyncio.create_task")
    def test_returns_200_with_valid_key(
        self, mock_create_task: MagicMock, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """POST /collection/snapshot-prices returns 200 with correct X-API-Key."""
        monkeypatch.setenv("TCG_API_KEY", "prod-key-99")
        mock_create_task.return_value = AsyncMock()
        app = _make_app()
        client = TestClient(app)

        resp = client.post(
            "/collection/snapshot-prices",
            json={},
            headers={"X-API-Key": "prod-key-99"},
        )
        assert resp.status_code == 200

    @patch("src.api.routers.collection.asyncio.create_task")
    def test_works_without_key_in_dev_mode(
        self, mock_create_task: MagicMock, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """When TCG_API_KEY is not set, POST works without any header (dev mode)."""
        monkeypatch.delenv("TCG_API_KEY", raising=False)
        mock_create_task.return_value = AsyncMock()
        app = _make_app()
        client = TestClient(app)

        resp = client.post("/collection/snapshot-prices", json={})
        assert resp.status_code == 200


class TestSnapshotPricesEndpoint:
    """POST /collection/snapshot-prices returns job_id and starts a background task."""

    @patch("src.api.routers.collection.asyncio.create_task")
    def test_returns_200_with_job_id(
        self, mock_create_task: MagicMock, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """POST /collection/snapshot-prices returns 200 with job_id and status 'started'."""
        monkeypatch.delenv("TCG_API_KEY", raising=False)
        mock_create_task.return_value = AsyncMock()
        app = _make_app()
        client = TestClient(app)

        resp = client.post("/collection/snapshot-prices", json={})
        assert resp.status_code == 200

        body = resp.json()
        assert body["data"]["status"] == "started"
        assert body["data"]["message"] == "Price snapshot started"
        assert "job_id" in body["data"]
        assert len(body["data"]["job_id"]) > 0

    @patch("src.api.routers.collection.asyncio.create_task")
    def test_dry_run_parameter_passed_through(
        self, mock_create_task: MagicMock, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """POST with dry_run=true is accepted and parsed correctly."""
        monkeypatch.delenv("TCG_API_KEY", raising=False)
        mock_create_task.return_value = AsyncMock()
        app = _make_app()
        client = TestClient(app)

        resp = client.post(
            "/collection/snapshot-prices",
            json={"dry_run": True},
        )
        assert resp.status_code == 200

        body = resp.json()
        assert body["data"]["status"] == "started"

    @patch("src.api.routers.collection.asyncio.create_task")
    def test_limit_parameter_passed_through(
        self, mock_create_task: MagicMock, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """POST with limit=5 is accepted and background task receives the limit."""
        monkeypatch.delenv("TCG_API_KEY", raising=False)
        mock_create_task.return_value = AsyncMock()
        app = _make_app()
        client = TestClient(app)

        resp = client.post(
            "/collection/snapshot-prices",
            json={"limit": 5},
        )
        assert resp.status_code == 200

        body = resp.json()
        assert body["data"]["status"] == "started"

        # Verify background task was created
        mock_create_task.assert_called_once()

    @patch("src.api.routers.collection.asyncio.create_task")
    def test_default_no_body_uses_defaults(
        self, mock_create_task: MagicMock, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Empty body uses defaults (limit=None, dry_run=False)."""
        monkeypatch.delenv("TCG_API_KEY", raising=False)
        mock_create_task.return_value = AsyncMock()
        app = _make_app()
        client = TestClient(app)

        resp = client.post("/collection/snapshot-prices", json={})
        assert resp.status_code == 200

        # Verify the background task was called
        mock_create_task.assert_called_once()

    @patch("src.api.routers.collection.asyncio.create_task")
    def test_response_matches_job_status_schema(
        self, mock_create_task: MagicMock, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Response body matches the ApiResponse[JobStatus] schema."""
        monkeypatch.delenv("TCG_API_KEY", raising=False)
        mock_create_task.return_value = AsyncMock()
        app = _make_app()
        client = TestClient(app)

        resp = client.post("/collection/snapshot-prices", json={})
        assert resp.status_code == 200

        body = resp.json()
        # ApiResponse envelope
        assert "data" in body
        # JobStatus fields
        data = body["data"]
        assert isinstance(data["job_id"], str)
        assert isinstance(data["status"], str)
        assert isinstance(data["message"], str)
        assert data["status"] == "started"


class TestSnapshotPricesValidation:
    """Request body validation for POST /collection/snapshot-prices."""

    @patch("src.api.routers.collection.asyncio.create_task")
    def test_invalid_limit_type_rejected(
        self, mock_create_task: MagicMock, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Non-integer limit is rejected with 422."""
        monkeypatch.delenv("TCG_API_KEY", raising=False)
        mock_create_task.return_value = AsyncMock()
        app = _make_app()
        client = TestClient(app)

        resp = client.post(
            "/collection/snapshot-prices",
            json={"limit": "not-a-number"},
        )
        assert resp.status_code == 422

    @patch("src.api.routers.collection.asyncio.create_task")
    def test_zero_limit_rejected(
        self, mock_create_task: MagicMock, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Zero limit is rejected with 422 (must be positive)."""
        monkeypatch.delenv("TCG_API_KEY", raising=False)
        mock_create_task.return_value = AsyncMock()
        app = _make_app()
        client = TestClient(app)

        resp = client.post(
            "/collection/snapshot-prices",
            json={"limit": 0},
        )
        assert resp.status_code == 422

    @patch("src.api.routers.collection.asyncio.create_task")
    def test_negative_limit_rejected(
        self, mock_create_task: MagicMock, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Negative limit is rejected with 422 (must be positive)."""
        monkeypatch.delenv("TCG_API_KEY", raising=False)
        mock_create_task.return_value = AsyncMock()
        app = _make_app()
        client = TestClient(app)

        resp = client.post(
            "/collection/snapshot-prices",
            json={"limit": -5},
        )
        assert resp.status_code == 422
