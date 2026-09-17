"""Tests for catalog search — case-insensitive LOWER() matching (F131-T04).

Validates that the ``name`` filter on ``GET /api/v1/catalog/cards`` is
case-insensitive for both English (``name_en``) and Portuguese (``name_pt``)
card names, using ``LOWER()`` wrapping on both the column and the search
parameter.
"""

from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from src.api.deps import get_db, get_optional_user
from src.api.routers.catalog import router
from src.database.models import Base, CardRow
from src.database.repository import Repository


@pytest.fixture()
def search_repo():
    """In-memory DB with cards that have both English and Portuguese names."""
    engine = create_engine(
        "sqlite:///:memory:",
        echo=False,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        session.add_all(
            [
                CardRow(
                    id=1,
                    game="magic",
                    name_en="Lightning Bolt",
                    name_pt="Relampago",
                    set_code="m21",
                    collector_number="1",
                ),
                CardRow(
                    id=2,
                    game="magic",
                    name_en="Counterspell",
                    name_pt="Contrafeitico",
                    set_code="m21",
                    collector_number="2",
                ),
                CardRow(
                    id=3,
                    game="magic",
                    name_en="Dark Ritual",
                    name_pt="Ritual Sombrio",
                    set_code="m21",
                    collector_number="3",
                ),
                CardRow(
                    id=4,
                    game="magic",
                    name_en="Sol Ring",
                    name_pt=None,
                    set_code="cmm",
                    collector_number="1",
                ),
            ]
        )
        session.commit()

    repo = Repository.__new__(Repository)
    repo.engine = engine
    return repo


@pytest.fixture()
def client(search_repo):
    """Test client for catalog search tests."""
    app = FastAPI()
    app.include_router(router, prefix="/api/v1")
    app.dependency_overrides[get_db] = lambda: search_repo
    app.dependency_overrides[get_optional_user] = lambda: None
    return TestClient(app)


class TestCatalogSearchCaseInsensitive:
    """GET /api/v1/catalog/cards?name=... case-insensitive matching."""

    def test_lowercase_matches_titlecase_en(self, client):
        """Search 'lightning bolt' (lowercase) matches 'Lightning Bolt'."""
        resp = client.get("/api/v1/catalog/cards?name=lightning bolt")
        assert resp.status_code == 200
        items = resp.json()["data"]["items"]
        assert len(items) == 1
        assert items[0]["name_en"] == "Lightning Bolt"

    def test_uppercase_matches_titlecase_en(self, client):
        """Search 'LIGHTNING BOLT' (uppercase) matches 'Lightning Bolt'."""
        resp = client.get("/api/v1/catalog/cards?name=LIGHTNING BOLT")
        assert resp.status_code == 200
        items = resp.json()["data"]["items"]
        assert len(items) == 1
        assert items[0]["name_en"] == "Lightning Bolt"

    def test_mixed_case_matches_en(self, client):
        """Search 'lIgHtNiNg' (mixed case) matches 'Lightning Bolt'."""
        resp = client.get("/api/v1/catalog/cards?name=lIgHtNiNg")
        assert resp.status_code == 200
        items = resp.json()["data"]["items"]
        assert len(items) == 1
        assert items[0]["name_en"] == "Lightning Bolt"

    def test_lowercase_matches_portuguese_name(self, client):
        """Search 'relampago' matches card with name_pt='Relampago'."""
        resp = client.get("/api/v1/catalog/cards?name=relampago")
        assert resp.status_code == 200
        items = resp.json()["data"]["items"]
        assert len(items) == 1
        assert items[0]["name_pt"] == "Relampago"

    def test_uppercase_matches_portuguese_name(self, client):
        """Search 'RITUAL SOMBRIO' matches card with name_pt='Ritual Sombrio'."""
        resp = client.get("/api/v1/catalog/cards?name=RITUAL SOMBRIO")
        assert resp.status_code == 200
        items = resp.json()["data"]["items"]
        assert len(items) == 1
        assert items[0]["name_pt"] == "Ritual Sombrio"

    def test_partial_match_case_insensitive(self, client):
        """Search 'counter' (partial, lowercase) matches 'Counterspell'."""
        resp = client.get("/api/v1/catalog/cards?name=counter")
        assert resp.status_code == 200
        items = resp.json()["data"]["items"]
        assert len(items) == 1
        assert items[0]["name_en"] == "Counterspell"

    def test_empty_string_returns_all(self, client):
        """Search with empty name returns all cards (no filter applied)."""
        resp = client.get("/api/v1/catalog/cards?name=")
        assert resp.status_code == 200
        items = resp.json()["data"]["items"]
        # Empty string should not filter — all 4 cards returned
        assert len(items) == 4

    def test_nonexistent_name_returns_empty(self, client):
        """Search for a name that does not exist returns empty results."""
        resp = client.get("/api/v1/catalog/cards?name=Nonexistent Card XYZ")
        assert resp.status_code == 200
        items = resp.json()["data"]["items"]
        assert len(items) == 0

    def test_search_matches_en_or_pt(self, client):
        """Search matches on either name_en OR name_pt (OR logic)."""
        # "ritual" matches name_en="Dark Ritual" AND name_pt="Ritual Sombrio"
        # both belong to the same card (id=3), so 1 result
        resp = client.get("/api/v1/catalog/cards?name=ritual")
        assert resp.status_code == 200
        items = resp.json()["data"]["items"]
        assert len(items) == 1
        assert items[0]["name_en"] == "Dark Ritual"
