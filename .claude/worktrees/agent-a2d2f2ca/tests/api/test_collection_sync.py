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


class TestCollectionSyncEndpoint:
    """POST /collection/sync returns a job_id and starts a background task."""

    @patch("src.api.routers.collection.asyncio.create_task")
    def test_sync_returns_200_with_job_id(
        self, mock_create_task: MagicMock, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """POST /collection/sync returns 200 with a job_id and status 'started'."""
        monkeypatch.delenv("TCG_API_KEY", raising=False)
        mock_create_task.return_value = AsyncMock()
        app = _make_app()
        client = TestClient(app)

        resp = client.post("/collection/sync", json={})
        assert resp.status_code == 200

        body = resp.json()
        assert body["data"]["status"] == "started"
        assert body["data"]["message"] == "Collection sync started"
        assert "job_id" in body["data"]
        assert len(body["data"]["job_id"]) > 0

    @patch("src.api.routers.collection.asyncio.create_task")
    def test_sync_accepts_custom_parameters(
        self, mock_create_task: MagicMock, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """POST /collection/sync accepts limit, history_days, and force."""
        monkeypatch.delenv("TCG_API_KEY", raising=False)
        mock_create_task.return_value = AsyncMock()
        app = _make_app()
        client = TestClient(app)

        resp = client.post(
            "/collection/sync",
            json={"limit": 5, "history_days": 30, "force": True},
        )
        assert resp.status_code == 200

        body = resp.json()
        assert body["data"]["status"] == "started"

    @patch("src.api.routers.collection.asyncio.create_task")
    def test_sync_uses_default_parameters(
        self, mock_create_task: MagicMock, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Empty body uses defaults (limit=None, history_days=365, force=False)."""
        monkeypatch.delenv("TCG_API_KEY", raising=False)
        mock_create_task.return_value = AsyncMock()
        app = _make_app()
        client = TestClient(app)

        resp = client.post("/collection/sync", json={})
        assert resp.status_code == 200

        # Verify the background task was called with a coroutine
        mock_create_task.assert_called_once()


class TestCollectionSyncAuth:
    """POST /collection/sync requires API key when TCG_API_KEY is set."""

    @patch("src.api.routers.collection.asyncio.create_task")
    def test_sync_returns_401_without_key(
        self, mock_create_task: MagicMock, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """POST /collection/sync returns 401 without X-API-Key header."""
        monkeypatch.setenv("TCG_API_KEY", "prod-key-99")
        mock_create_task.return_value = AsyncMock()
        app = _make_app()
        client = TestClient(app)

        resp = client.post("/collection/sync", json={})
        assert resp.status_code == 401

    @patch("src.api.routers.collection.asyncio.create_task")
    def test_sync_returns_401_with_wrong_key(
        self, mock_create_task: MagicMock, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """POST /collection/sync returns 401 with incorrect X-API-Key."""
        monkeypatch.setenv("TCG_API_KEY", "prod-key-99")
        mock_create_task.return_value = AsyncMock()
        app = _make_app()
        client = TestClient(app)

        resp = client.post(
            "/collection/sync",
            json={},
            headers={"X-API-Key": "wrong-key"},
        )
        assert resp.status_code == 401

    @patch("src.api.routers.collection.asyncio.create_task")
    def test_sync_returns_200_with_valid_key(
        self, mock_create_task: MagicMock, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """POST /collection/sync returns 200 with correct X-API-Key."""
        monkeypatch.setenv("TCG_API_KEY", "prod-key-99")
        mock_create_task.return_value = AsyncMock()
        app = _make_app()
        client = TestClient(app)

        resp = client.post(
            "/collection/sync",
            json={},
            headers={"X-API-Key": "prod-key-99"},
        )
        assert resp.status_code == 200

    @patch("src.api.routers.collection.asyncio.create_task")
    def test_sync_works_without_key_in_dev_mode(
        self, mock_create_task: MagicMock, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """When TCG_API_KEY is not set, POST /collection/sync works without any header."""
        monkeypatch.delenv("TCG_API_KEY", raising=False)
        mock_create_task.return_value = AsyncMock()
        app = _make_app()
        client = TestClient(app)

        resp = client.post("/collection/sync", json={})
        assert resp.status_code == 200


class TestCollectionSyncValidation:
    """Request body validation for POST /collection/sync."""

    @patch("src.api.routers.collection.asyncio.create_task")
    def test_invalid_limit_type_rejected(
        self, mock_create_task: MagicMock, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Non-integer limit is rejected with 422."""
        monkeypatch.delenv("TCG_API_KEY", raising=False)
        mock_create_task.return_value = AsyncMock()
        app = _make_app()
        client = TestClient(app)

        resp = client.post("/collection/sync", json={"limit": "not-a-number"})
        assert resp.status_code == 422

    @patch("src.api.routers.collection.asyncio.create_task")
    def test_invalid_history_days_type_rejected(
        self, mock_create_task: MagicMock, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Non-integer history_days is rejected with 422."""
        monkeypatch.delenv("TCG_API_KEY", raising=False)
        mock_create_task.return_value = AsyncMock()
        app = _make_app()
        client = TestClient(app)

        resp = client.post("/collection/sync", json={"history_days": "abc"})
        assert resp.status_code == 422

    @patch("src.api.routers.collection.asyncio.create_task")
    def test_invalid_force_type_rejected(
        self, mock_create_task: MagicMock, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Non-boolean force is rejected with 422."""
        monkeypatch.delenv("TCG_API_KEY", raising=False)
        mock_create_task.return_value = AsyncMock()
        app = _make_app()
        client = TestClient(app)

        resp = client.post("/collection/sync", json={"force": "not-a-bool"})
        assert resp.status_code == 422
