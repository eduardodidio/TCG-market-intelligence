"""Tests for OpenAPI metadata and tag descriptions (F102-T03)."""

from __future__ import annotations

import os

import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def client():
    os.environ["TCG_SCHEDULER_DISABLED"] = "1"
    from src.api.app import create_app

    app = create_app()
    return TestClient(app, raise_server_exceptions=False)


class TestOpenAPIMetadata:
    """Verify that the OpenAPI schema has proper metadata."""

    def test_info_title(self, client):
        resp = client.get("/openapi.json")
        assert resp.status_code == 200
        data = resp.json()
        assert data["info"]["title"] == "TEDHC Market API"

    def test_info_version(self, client):
        resp = client.get("/openapi.json")
        data = resp.json()
        assert data["info"]["version"] == "1.0.0"

    def test_info_description(self, client):
        resp = client.get("/openapi.json")
        data = resp.json()
        desc = data["info"]["description"]
        assert "REST API for TCG market intelligence" in desc
        assert "Brazilian market" in desc

    def test_tags_have_descriptions(self, client):
        resp = client.get("/openapi.json")
        data = resp.json()
        tags = data.get("tags", [])
        assert len(tags) > 0
        # Each tag must have a non-empty description
        for tag in tags:
            assert "name" in tag
            assert "description" in tag
            assert len(tag["description"]) > 0, f"Tag {tag['name']} has empty description"

    def test_expected_tags_present(self, client):
        resp = client.get("/openapi.json")
        data = resp.json()
        tag_names = {t["name"] for t in data.get("tags", [])}
        expected = {
            "auth",
            "admin",
            "cards",
            "collection",
            "decks",
            "credits",
            "market",
            "scans",
            "schedules",
            "catalog",
            "alerts",
            "achievements",
            "marketplace",
            "evaluations",
            "banlist",
        }
        missing = expected - tag_names
        assert not missing, f"Missing tags: {missing}"

    def test_docs_endpoint_returns_200(self, client):
        resp = client.get("/docs")
        assert resp.status_code == 200

    def test_redoc_endpoint_returns_200(self, client):
        resp = client.get("/redoc")
        assert resp.status_code == 200
