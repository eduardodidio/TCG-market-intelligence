"""Tests for GET /collection/set-completion endpoint (F104-T05)."""

from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from src.api.deps import get_db, require_auth_or_api_key
from src.api.routers.collection import router
from src.database.models import CardRow, UserCollectionRow
from src.database.repository import Repository


@pytest.fixture()
def completion_app(tmp_path):
    """Create a test app with collection entries and catalog cards."""
    db_path = tmp_path / "completion.db"
    repo = Repository(db_url=f"sqlite:///{db_path}")

    with Session(repo.engine) as session:
        # Catalog cards: 3 in SET1, 2 in SET2
        for i in range(3):
            session.add(
                CardRow(
                    game="magic",
                    name_en=f"Card S1-{i}",
                    set_code="SET1",
                    collector_number=str(i + 1),
                )
            )
        for i in range(2):
            session.add(
                CardRow(
                    game="magic",
                    name_en=f"Card S2-{i}",
                    set_code="SET2",
                    collector_number=str(i + 1),
                )
            )
        session.flush()

        # User collection: 2 of 3 from SET1, 1 of 2 from SET2
        session.add(
            UserCollectionRow(
                user_id="user1",
                set_code="SET1",
                collector_number="1",
                name_en="Card S1-0",
            )
        )
        session.add(
            UserCollectionRow(
                user_id="user1",
                set_code="SET1",
                collector_number="2",
                name_en="Card S1-1",
            )
        )
        session.add(
            UserCollectionRow(
                user_id="user1",
                set_code="SET2",
                collector_number="1",
                name_en="Card S2-0",
            )
        )
        session.commit()

    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_db] = lambda: repo
    app.dependency_overrides[require_auth_or_api_key] = lambda: "user1"
    client = TestClient(app)
    return client


class TestSetCompletion:
    def test_returns_completion_data(self, completion_app):
        resp = completion_app.get("/collection/set-completion")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert len(data) == 2

    def test_owned_and_total_counts(self, completion_app):
        resp = completion_app.get("/collection/set-completion")
        data = resp.json()["data"]
        by_set = {d["set_code"]: d for d in data}

        assert by_set["SET1"]["owned"] == 2
        assert by_set["SET1"]["total"] == 3
        assert by_set["SET2"]["owned"] == 1
        assert by_set["SET2"]["total"] == 2

    def test_sorted_by_completion(self, completion_app):
        resp = completion_app.get("/collection/set-completion")
        data = resp.json()["data"]
        # SET1: 2/3 = 66.7%, SET2: 1/2 = 50%
        assert data[0]["set_code"] == "SET1"
        assert data[1]["set_code"] == "SET2"

    def test_set_name_populated(self, completion_app):
        resp = completion_app.get("/collection/set-completion")
        data = resp.json()["data"]
        # set_name falls back to set_code when null
        for item in data:
            assert item["set_name"] is not None

    def test_has_catalog_true_when_catalog_data_exists(self, completion_app):
        """Sets with catalog cards should have has_catalog=True."""
        resp = completion_app.get("/collection/set-completion")
        data = resp.json()["data"]
        by_set = {d["set_code"]: d for d in data}
        assert by_set["SET1"]["has_catalog"] is True
        assert by_set["SET2"]["has_catalog"] is True


@pytest.fixture()
def completion_no_catalog_app(tmp_path):
    """App where collection has cards from a set NOT in the catalog."""
    db_path = tmp_path / "no_catalog.db"
    repo = Repository(db_url=f"sqlite:///{db_path}")

    with Session(repo.engine) as session:
        # No catalog cards for "PROMO" set
        session.add(
            UserCollectionRow(
                user_id="user1",
                set_code="PROMO",
                collector_number="1",
                name_en="Promo Card",
            )
        )
        session.add(
            UserCollectionRow(
                user_id="user1",
                set_code="PROMO",
                collector_number="2",
                name_en="Promo Card 2",
            )
        )
        # Add one set WITH catalog data for comparison
        session.add(
            CardRow(
                game="magic",
                name_en="Real Card",
                set_code="SET1",
                collector_number="1",
            )
        )
        session.add(
            UserCollectionRow(
                user_id="user1",
                set_code="SET1",
                collector_number="1",
                name_en="Real Card",
            )
        )
        session.commit()

    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_db] = lambda: repo
    app.dependency_overrides[require_auth_or_api_key] = lambda: "user1"
    return TestClient(app)


class TestSetCompletionNoCatalog:
    def test_no_catalog_set_has_catalog_false(self, completion_no_catalog_app):
        """Sets without catalog data return has_catalog=False."""
        resp = completion_no_catalog_app.get("/collection/set-completion")
        assert resp.status_code == 200
        data = resp.json()["data"]
        by_set = {d["set_code"]: d for d in data}

        assert by_set["PROMO"]["has_catalog"] is False
        # owned == total when no catalog
        assert by_set["PROMO"]["owned"] == by_set["PROMO"]["total"]
        assert by_set["PROMO"]["owned"] == 2

    def test_catalog_set_has_catalog_true(self, completion_no_catalog_app):
        """Sets with catalog data return has_catalog=True."""
        resp = completion_no_catalog_app.get("/collection/set-completion")
        data = resp.json()["data"]
        by_set = {d["set_code"]: d for d in data}

        assert by_set["SET1"]["has_catalog"] is True
