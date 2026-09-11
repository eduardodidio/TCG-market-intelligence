"""Tests for catalog cards endpoint with with_ownership param (F122-T03)."""

from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from src.api.deps import get_db, get_optional_user
from src.api.routers.catalog import router
from src.database.models import Base, CardRow, UserCollectionRow
from src.database.repository import Repository
from src.domain.models import User


@pytest.fixture()
def ownership_repo():
    """In-memory DB with catalog cards and a user collection."""
    engine = create_engine(
        "sqlite:///:memory:",
        echo=False,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        # 3 catalog cards in set "mh3"
        c1 = CardRow(id=1, game="magic", name_en="Card A", set_code="mh3", collector_number="1")
        c2 = CardRow(id=2, game="magic", name_en="Card B", set_code="mh3", collector_number="2")
        c3 = CardRow(id=3, game="magic", name_en="Card C", set_code="mh3", collector_number="3")
        session.add_all([c1, c2, c3])
        session.flush()

        # User (id=42) owns cards 1 and 3
        session.add(
            UserCollectionRow(
                user_id="42",
                card_id=1,
                set_code="mh3",
                collector_number="1",
                name_en="Card A",
            )
        )
        session.add(
            UserCollectionRow(
                user_id="42",
                card_id=3,
                set_code="mh3",
                collector_number="3",
                name_en="Card C",
            )
        )
        session.commit()

    repo = Repository.__new__(Repository)
    repo.engine = engine
    return repo


def _make_user() -> User:
    return User(id=42, email="test@test.com", display_name="Test", is_admin=False)


@pytest.fixture()
def client_with_user(ownership_repo):
    """Client with authenticated user."""
    app = FastAPI()
    app.include_router(router, prefix="/api/v1")
    app.dependency_overrides[get_db] = lambda: ownership_repo
    app.dependency_overrides[get_optional_user] = lambda: _make_user()
    return TestClient(app)


@pytest.fixture()
def client_no_user(ownership_repo):
    """Client without authentication."""
    app = FastAPI()
    app.include_router(router, prefix="/api/v1")
    app.dependency_overrides[get_db] = lambda: ownership_repo
    app.dependency_overrides[get_optional_user] = lambda: None
    return TestClient(app)


class TestCatalogWithOwnership:
    def test_with_ownership_returns_owned_field(self, client_with_user):
        resp = client_with_user.get("/api/v1/catalog/cards?set_code=mh3&with_ownership=true")
        assert resp.status_code == 200
        items = resp.json()["data"]["items"]
        assert len(items) == 3

        by_name = {item["name_en"]: item for item in items}
        # Cards 1 and 3 are owned
        assert by_name["Card A"]["owned"] is True
        assert by_name["Card C"]["owned"] is True
        # Card 2 is not owned
        assert by_name["Card B"]["owned"] is False

    def test_without_ownership_owned_is_null(self, client_with_user):
        resp = client_with_user.get("/api/v1/catalog/cards?set_code=mh3")
        assert resp.status_code == 200
        items = resp.json()["data"]["items"]
        for item in items:
            assert item["owned"] is None

    def test_with_ownership_no_user_owned_is_null(self, client_no_user):
        """When with_ownership=true but no auth, owned stays null."""
        resp = client_no_user.get("/api/v1/catalog/cards?set_code=mh3&with_ownership=true")
        assert resp.status_code == 200
        items = resp.json()["data"]["items"]
        for item in items:
            assert item["owned"] is None

    def test_default_with_ownership_is_false(self, client_with_user):
        """Default request does not include ownership data."""
        resp = client_with_user.get("/api/v1/catalog/cards?set_code=mh3")
        assert resp.status_code == 200
        items = resp.json()["data"]["items"]
        for item in items:
            assert item["owned"] is None
