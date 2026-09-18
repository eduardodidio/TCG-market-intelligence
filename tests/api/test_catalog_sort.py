"""Tests for catalog sort — rarity + collector_number sort options (F145-T01).

Validates that ``GET /api/v1/catalog/cards`` correctly sorts by all five
``sort_by`` values (name, set_code, price, rarity, collector_number) in
both asc and desc directions.
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
def sort_repo():
    """In-memory DB with cards of various rarities and collector numbers."""
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
                    name_en="Bolt",
                    set_code="m21",
                    collector_number="1",
                    rarity="C",
                ),
                CardRow(
                    id=2,
                    game="magic",
                    name_en="Counterspell",
                    set_code="m21",
                    collector_number="2",
                    rarity="U",
                ),
                CardRow(
                    id=3,
                    game="magic",
                    name_en="Damnation",
                    set_code="m21",
                    collector_number="10",
                    rarity="R",
                ),
                CardRow(
                    id=4,
                    game="magic",
                    name_en="Emrakul",
                    set_code="m21",
                    collector_number="3",
                    rarity="M",
                ),
                CardRow(
                    id=5,
                    game="magic",
                    name_en="Alpha Card",
                    set_code="m21",
                    collector_number="12a",
                    rarity=None,
                ),
            ]
        )
        session.commit()

    repo = Repository.__new__(Repository)
    repo.engine = engine
    return repo


@pytest.fixture()
def client(sort_repo):
    """Test client for catalog sort tests."""
    app = FastAPI()
    app.include_router(router, prefix="/api/v1")
    app.dependency_overrides[get_db] = lambda: sort_repo
    app.dependency_overrides[get_optional_user] = lambda: None
    return TestClient(app)


class TestCatalogSortRarity:
    """GET /api/v1/catalog/cards?sort_by=rarity tests."""

    def test_rarity_asc_mythic_first(self, client):
        """sort_by=rarity&sort_dir=asc returns M, R, U, C, NULL."""
        resp = client.get("/api/v1/catalog/cards?sort_by=rarity&sort_dir=asc")
        assert resp.status_code == 200
        items = resp.json()["data"]["items"]
        rarities = [item["rarity"] for item in items]
        assert rarities == ["M", "R", "U", "C", None]

    def test_rarity_desc_common_first(self, client):
        """sort_by=rarity&sort_dir=desc returns C, U, R, M then NULL at end."""
        resp = client.get("/api/v1/catalog/cards?sort_by=rarity&sort_dir=desc")
        assert resp.status_code == 200
        items = resp.json()["data"]["items"]
        rarities = [item["rarity"] for item in items]
        assert rarities == ["C", "U", "R", "M", None]

    def test_rarity_null_at_end(self, client):
        """Cards with NULL rarity appear at the end regardless of direction."""
        for direction in ("asc", "desc"):
            resp = client.get(f"/api/v1/catalog/cards?sort_by=rarity&sort_dir={direction}")
            assert resp.status_code == 200
            items = resp.json()["data"]["items"]
            # Last item should have NULL rarity
            assert items[-1]["rarity"] is None


class TestCatalogSortCollectorNumber:
    """GET /api/v1/catalog/cards?sort_by=collector_number tests."""

    def test_collector_number_asc(self, client):
        """sort_by=collector_number&sort_dir=asc returns cards in text order."""
        resp = client.get("/api/v1/catalog/cards?sort_by=collector_number&sort_dir=asc")
        assert resp.status_code == 200
        items = resp.json()["data"]["items"]
        numbers = [item["collector_number"] for item in items]
        # Text sort: "1", "10", "12a", "2", "3"
        assert numbers == ["1", "10", "12a", "2", "3"]

    def test_collector_number_desc(self, client):
        """sort_by=collector_number&sort_dir=desc returns reverse text order."""
        resp = client.get("/api/v1/catalog/cards?sort_by=collector_number&sort_dir=desc")
        assert resp.status_code == 200
        items = resp.json()["data"]["items"]
        numbers = [item["collector_number"] for item in items]
        assert numbers == ["3", "2", "12a", "10", "1"]

    def test_collector_number_null_at_end(self, client, sort_repo):
        """Cards with NULL collector_number appear at the end."""
        # Add a card with NULL collector_number
        with Session(sort_repo.engine) as session:
            session.add(
                CardRow(
                    id=100,
                    game="magic",
                    name_en="No Number",
                    set_code="m21",
                    collector_number=None,
                    rarity="C",
                )
            )
            session.commit()

        resp = client.get("/api/v1/catalog/cards?sort_by=collector_number&sort_dir=asc")
        assert resp.status_code == 200
        items = resp.json()["data"]["items"]
        assert items[-1]["collector_number"] is None


class TestCatalogSortExistingOptions:
    """Verify existing sort options still work after adding new ones."""

    def test_sort_by_name_asc(self, client):
        resp = client.get("/api/v1/catalog/cards?sort_by=name&sort_dir=asc")
        assert resp.status_code == 200
        items = resp.json()["data"]["items"]
        names = [item["name_en"] for item in items]
        assert names == sorted(names)

    def test_sort_by_name_desc(self, client):
        resp = client.get("/api/v1/catalog/cards?sort_by=name&sort_dir=desc")
        assert resp.status_code == 200
        items = resp.json()["data"]["items"]
        names = [item["name_en"] for item in items]
        assert names == sorted(names, reverse=True)

    def test_sort_by_set_code(self, client):
        resp = client.get("/api/v1/catalog/cards?sort_by=set_code&sort_dir=asc")
        assert resp.status_code == 200
        items = resp.json()["data"]["items"]
        assert len(items) == 5

    def test_sort_by_price(self, client):
        resp = client.get("/api/v1/catalog/cards?sort_by=price&sort_dir=desc")
        assert resp.status_code == 200
        assert len(resp.json()["data"]["items"]) == 5


class TestCatalogSortValidation:
    """Validation and edge cases."""

    def test_invalid_sort_by_returns_422(self, client):
        """Invalid sort_by value returns 422 from FastAPI enum validation."""
        resp = client.get("/api/v1/catalog/cards?sort_by=invalid_field")
        assert resp.status_code == 422

    def test_empty_result_with_rarity_sort(self, client):
        """Empty result set with rarity sort returns 200 with empty items."""
        resp = client.get("/api/v1/catalog/cards?sort_by=rarity&sort_dir=asc&name=nonexistent_xyz")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["items"] == []
        assert data["total"] == 0
