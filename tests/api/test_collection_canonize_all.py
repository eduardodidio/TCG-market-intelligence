"""Integration tests for POST /collection/canonize-all endpoint."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.api.deps import get_db, require_auth_or_api_key
from src.api.routers.collection import router
from src.collectors.bulk_canonize import BulkCanonizeResult

_TEST_USER_ID = "eduardo"

_PATCH_PROVIDER = "src.providers.myp.provider.MypCardsProvider"
_PATCH_BULK_CANONIZE = "src.collectors.bulk_canonize.bulk_canonize"


def _make_app(mock_repo: MagicMock, user_id: str = _TEST_USER_ID) -> FastAPI:
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_db] = lambda: mock_repo
    app.dependency_overrides[require_auth_or_api_key] = lambda: user_id
    return app


def _make_app_no_auth(mock_repo: MagicMock) -> FastAPI:
    """App with no auth override — requires real auth."""
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_db] = lambda: mock_repo
    # Do NOT override require_auth_or_api_key
    return app


class TestCanonizeAllEndpointAuthRequired:
    """POST /collection/canonize-all returns 401 without token."""

    def test_canonize_all_endpoint_auth_required(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setenv("TCG_API_KEY", "prod-key-99")
        mock_repo = MagicMock()
        app = _make_app_no_auth(mock_repo)
        client = TestClient(app, raise_server_exceptions=False)

        resp = client.post("/collection/canonize-all")
        assert resp.status_code == 401


class TestCanonizeAllEndpointReturns200:
    """POST /collection/canonize-all returns 200 with BulkCanonizeResult."""

    @patch(_PATCH_PROVIDER)
    @patch(_PATCH_BULK_CANONIZE)
    def test_canonize_all_endpoint_returns_200(self, mock_bulk_canonize, mock_provider_cls):
        mock_bulk_canonize.return_value = BulkCanonizeResult(
            total=5,
            canonized=3,
            failed=1,
            skipped=0,
            rate_limited=1,
        )

        mock_provider = AsyncMock()
        mock_provider.close = AsyncMock()
        mock_provider_cls.return_value = mock_provider

        mock_repo = MagicMock()
        app = _make_app(mock_repo)
        client = TestClient(app)

        resp = client.post("/collection/canonize-all")
        assert resp.status_code == 200

        body = resp.json()
        assert body["data"]["total"] == 5
        assert body["data"]["canonized"] == 3
        assert body["data"]["failed"] == 1
        assert body["data"]["skipped"] == 0
        assert body["data"]["rate_limited"] == 1


class TestCanonizeAllEndpointAcceptsLimitParam:
    """Query param limit forwarded to service."""

    @patch(_PATCH_PROVIDER)
    @patch(_PATCH_BULK_CANONIZE)
    def test_canonize_all_endpoint_accepts_limit_param(self, mock_bulk_canonize, mock_provider_cls):
        mock_bulk_canonize.return_value = BulkCanonizeResult(
            total=2,
            canonized=2,
            failed=0,
            skipped=0,
            rate_limited=0,
        )

        mock_provider = AsyncMock()
        mock_provider.close = AsyncMock()
        mock_provider_cls.return_value = mock_provider

        mock_repo = MagicMock()
        app = _make_app(mock_repo)
        client = TestClient(app)

        resp = client.post("/collection/canonize-all?limit=10")
        assert resp.status_code == 200

        # Verify limit was passed to bulk_canonize
        call_kwargs = mock_bulk_canonize.call_args
        assert call_kwargs.kwargs.get("limit") == 10 or call_kwargs[1].get("limit") == 10
