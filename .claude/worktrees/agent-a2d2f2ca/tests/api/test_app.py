from __future__ import annotations

import uuid

import pytest
from fastapi.testclient import TestClient

from src.api.app import create_app


@pytest.fixture
def client():
    app = create_app()
    return TestClient(app)


class TestCreateApp:
    def test_returns_fastapi_instance(self):
        from fastapi import FastAPI

        app = create_app()
        assert isinstance(app, FastAPI)

    def test_health_endpoint(self, client):
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}


class TestRouterMounting:
    def test_cards_router_mounted(self, client):
        response = client.get("/api/v1/cards")
        assert response.status_code == 200

    def test_sets_router_mounted(self, client):
        response = client.get("/api/v1/sets")
        assert response.status_code == 200

    def test_market_movers_mounted(self, client):
        response = client.get("/api/v1/market/movers")
        assert response.status_code == 200

    def test_market_stats_mounted(self, client):
        response = client.get("/api/v1/market/stats")
        assert response.status_code == 200


class TestErrorHandling:
    def test_404_returns_envelope(self, client):
        response = client.get("/api/v1/nonexistent")
        assert response.status_code in (404, 405)
        body = response.json()
        assert "errors" in body
        assert "meta" in body

    def test_422_validation_returns_envelope(self, client):
        response = client.get("/api/v1/cards?limit=999")
        assert response.status_code == 422
        body = response.json()
        assert body["data"] is None
        assert len(body["errors"]) > 0
        assert body["errors"][0]["code"] == "VALIDATION_ERROR"


class TestMiddleware:
    def test_request_id_header(self, client):
        response = client.get("/health")
        request_id = response.headers.get("X-Request-ID")
        assert request_id is not None
        uuid.UUID(request_id)

    def test_cors_headers(self, client):
        response = client.options(
            "/health",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "GET",
            },
        )
        assert "access-control-allow-origin" in response.headers


class TestResponseEnvelope:
    def test_response_has_meta_request_id(self, client):
        response = client.get("/api/v1/cards")
        body = response.json()
        assert "meta" in body
        assert "request_id" in body["meta"]
