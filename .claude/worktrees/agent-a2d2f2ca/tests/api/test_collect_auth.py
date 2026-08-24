from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from src.api.deps import get_db, verify_api_key
from src.api.routers.collect import router

# ---------------------------------------------------------------------------
# Unit tests for verify_api_key dependency
# ---------------------------------------------------------------------------


class TestVerifyApiKeyUnit:
    def test_no_env_var_allows_all(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """When TCG_API_KEY is not set, any request passes (dev mode)."""
        monkeypatch.delenv("TCG_API_KEY", raising=False)
        # Should not raise regardless of header value
        assert verify_api_key(None) is None
        assert verify_api_key("anything") is None

    def test_valid_key(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """When TCG_API_KEY is set and header matches, request passes."""
        monkeypatch.setenv("TCG_API_KEY", "secret-key-42")
        assert verify_api_key("secret-key-42") is None

    def test_missing_header_raises_401(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """When TCG_API_KEY is set but header is missing, 401 is raised."""
        monkeypatch.setenv("TCG_API_KEY", "secret-key-42")
        with pytest.raises(HTTPException) as exc_info:
            verify_api_key(None)
        assert exc_info.value.status_code == 401
        assert "Invalid or missing API key" in exc_info.value.detail

    def test_wrong_key_raises_401(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """When TCG_API_KEY is set and header has wrong value, 401 is raised."""
        monkeypatch.setenv("TCG_API_KEY", "secret-key-42")
        with pytest.raises(HTTPException) as exc_info:
            verify_api_key("wrong-key")
        assert exc_info.value.status_code == 401


# ---------------------------------------------------------------------------
# Integration tests — collect endpoints with auth guard
# ---------------------------------------------------------------------------


def _make_app() -> FastAPI:
    """Create a fresh FastAPI app with the collect router and mocked DB."""
    test_app = FastAPI()
    test_app.include_router(router)
    test_app.dependency_overrides[get_db] = lambda: MagicMock()
    return test_app


class TestCollectAuthIntegration:
    @patch("src.api.routers.collect.asyncio.create_task")
    def test_update_requires_key_when_configured(
        self, mock_create_task: MagicMock, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """POST /collect/update returns 401 without a valid X-API-Key."""
        monkeypatch.setenv("TCG_API_KEY", "prod-key-99")
        mock_create_task.return_value = AsyncMock()
        app = _make_app()
        client = TestClient(app)

        # No header -> 401
        resp = client.post("/collect/update", json={})
        assert resp.status_code == 401

        # Wrong header -> 401
        resp = client.post(
            "/collect/update",
            json={},
            headers={"X-API-Key": "bad-key"},
        )
        assert resp.status_code == 401

        # Correct header -> 200
        resp = client.post(
            "/collect/update",
            json={},
            headers={"X-API-Key": "prod-key-99"},
        )
        assert resp.status_code == 200

    @patch("src.api.routers.collect.asyncio.create_task")
    def test_backfill_requires_key_when_configured(
        self, mock_create_task: MagicMock, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """POST /collect/backfill returns 401 without a valid X-API-Key."""
        monkeypatch.setenv("TCG_API_KEY", "prod-key-99")
        mock_create_task.return_value = AsyncMock()
        app = _make_app()
        client = TestClient(app)

        # No header -> 401
        resp = client.post("/collect/backfill", json={"set": "dmr"})
        assert resp.status_code == 401

        # Correct header -> 200
        resp = client.post(
            "/collect/backfill",
            json={"set": "dmr"},
            headers={"X-API-Key": "prod-key-99"},
        )
        assert resp.status_code == 200

    @patch("src.api.routers.collect.asyncio.create_task")
    def test_update_works_without_key_in_dev_mode(
        self, mock_create_task: MagicMock, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """When TCG_API_KEY is not set, POST /collect/update works without any header."""
        monkeypatch.delenv("TCG_API_KEY", raising=False)
        mock_create_task.return_value = AsyncMock()
        app = _make_app()
        client = TestClient(app)

        resp = client.post("/collect/update", json={})
        assert resp.status_code == 200

    def test_health_no_key_required(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """GET /collect/health works even when TCG_API_KEY is set (no auth on GETs)."""
        monkeypatch.setenv("TCG_API_KEY", "prod-key-99")
        app = _make_app()

        # The health endpoint calls repo methods — mock them on the MagicMock
        mock_repo = MagicMock()
        mock_repo.get_latest_observation_date.return_value = None
        mock_repo.get_source_card_count.return_value = 0
        mock_repo.get_stale_cards_count.return_value = 0
        mock_repo.get_recent_errors_count.return_value = 0
        app.dependency_overrides[get_db] = lambda: mock_repo

        client = TestClient(app)

        # No X-API-Key header — should still return 200
        resp = client.get("/collect/health")
        assert resp.status_code == 200
