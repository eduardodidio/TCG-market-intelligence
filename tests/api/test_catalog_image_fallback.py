"""Tests for catalog image fallback — Scryfall URL for cards with NULL image_uri.

Validates that the catalog API returns a Scryfall redirect URL when a card's
``image_uri`` is NULL in the database (e.g. art series cards).
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
def fallback_repo():
    """In-memory DB with cards: one with image_uri, one without."""
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
                    name_en="The Arkenstone",
                    set_code="ashob",
                    collector_number="44a",
                    image_uri=None,  # Art card — no Scryfall bulk data
                ),
                CardRow(
                    id=2,
                    game="magic",
                    name_en="Lightning Bolt",
                    set_code="m21",
                    collector_number="1",
                    image_uri="https://cards.scryfall.io/normal/front/a/b/abc.jpg",
                ),
            ]
        )
        session.commit()

    repo = Repository.__new__(Repository)
    repo.engine = engine
    return repo


@pytest.fixture()
def client(fallback_repo):
    app = FastAPI()
    app.include_router(router, prefix="/api/v1")
    app.dependency_overrides[get_db] = lambda: fallback_repo
    app.dependency_overrides[get_optional_user] = lambda: None
    return TestClient(app)


class TestCatalogImageFallback:
    """Catalog API applies Scryfall fallback when image_uri is NULL."""

    def test_list_null_image_gets_fallback(self, client):
        """Card with NULL image_uri gets a Scryfall redirect URL."""
        resp = client.get("/api/v1/catalog/cards", params={"name": "Arkenstone"})
        assert resp.status_code == 200
        items = resp.json()["data"]["items"]
        assert len(items) == 1
        assert items[0]["image_uri"] == (
            "https://api.scryfall.com/cards/hob/44?format=image&version=normal"
        )

    def test_list_existing_image_not_overridden(self, client):
        """Card with existing image_uri is not affected by fallback."""
        resp = client.get("/api/v1/catalog/cards", params={"name": "Lightning Bolt"})
        assert resp.status_code == 200
        items = resp.json()["data"]["items"]
        assert len(items) == 1
        assert items[0]["image_uri"] == "https://cards.scryfall.io/normal/front/a/b/abc.jpg"

    def test_detail_null_image_gets_fallback(self, client):
        """Single card detail endpoint applies fallback."""
        resp = client.get("/api/v1/catalog/cards/1")
        assert resp.status_code == 200
        card = resp.json()["data"]
        assert card["image_uri"] == (
            "https://api.scryfall.com/cards/hob/44?format=image&version=normal"
        )

    def test_detail_existing_image_not_overridden(self, client):
        """Single card with image_uri is unaffected."""
        resp = client.get("/api/v1/catalog/cards/2")
        assert resp.status_code == 200
        card = resp.json()["data"]
        assert card["image_uri"] == "https://cards.scryfall.io/normal/front/a/b/abc.jpg"
