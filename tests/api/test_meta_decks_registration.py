"""F173-T15 — meta-decks router is registered in the real ``create_app()``."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from src.api.app import create_app
from src.api.deps import get_db, get_optional_user
from src.database.repository import Repository


@pytest.fixture
def client(tmp_path):
    repo = Repository(db_url=f"sqlite:///{tmp_path / 'meta_reg.db'}")
    app = create_app()
    app.dependency_overrides[get_db] = lambda: repo
    app.dependency_overrides[get_optional_user] = lambda: None
    return TestClient(app)


def test_formats_route_registered(client):
    resp = client.get("/api/v1/meta-decks/formats")
    assert resp.status_code == 200
    assert "data" in resp.json()


def test_list_route_registered(client):
    resp = client.get("/api/v1/meta-decks", params={"format": "modern"})
    assert resp.status_code == 200


def test_invalid_format_returns_422_envelope(client):
    resp = client.get("/api/v1/meta-decks", params={"format": "foo"})
    assert resp.status_code == 422
    assert resp.json()["errors"][0]["code"] == "VALIDATION_ERROR"


def test_unknown_deck_id_is_not_spa_fallback(client):
    resp = client.get("/api/v1/meta-decks/999999")
    assert resp.status_code == 404


def test_routes_listed_in_openapi():
    paths = create_app().openapi()["paths"]
    assert "/api/v1/meta-decks" in paths
    assert "/api/v1/meta-decks/formats" in paths
    assert "/api/v1/meta-decks/{deck_id}" in paths
