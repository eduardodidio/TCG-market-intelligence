"""Tests for the wishlist API router (F110-T02)."""

from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from src.api.deps import get_current_user, get_db
from src.api.routers.wishlist import router
from src.database.models import CardRow
from src.database.repository import Repository
from src.domain.models import User


def _make_user(user_id: int = 1) -> User:
    return User(
        id=user_id,
        email="test@example.com",
        display_name="Test User",
        auth_provider="email",
        is_active=True,
        is_admin=False,
    )


@pytest.fixture()
def repo(tmp_path):
    db_path = tmp_path / "test_wishlist_api.db"
    return Repository(db_url=f"sqlite:///{db_path}")


@pytest.fixture()
def user():
    return _make_user()


@pytest.fixture()
def test_app(repo, user):
    app = FastAPI()
    app.include_router(router, prefix="/api/v1")
    app.dependency_overrides[get_db] = lambda: repo
    app.dependency_overrides[get_current_user] = lambda: user
    repo.create_user(email=user.email, display_name=user.display_name)
    return app


@pytest.fixture()
def client(test_app):
    return TestClient(test_app)


@pytest.fixture()
def card_id(repo):
    with Session(repo.engine) as session:
        card = CardRow(
            game="magic",
            name_en="Lightning Bolt",
            name_pt="Raio",
            set_code="2ed",
            collector_number="157",
            image_uri="https://example.com/bolt.jpg",
        )
        session.add(card)
        session.commit()
        session.refresh(card)
        return card.id


@pytest.fixture()
def card_id_2(repo):
    with Session(repo.engine) as session:
        card = CardRow(
            game="magic",
            name_en="Counterspell",
            name_pt="Contrafeitico",
            set_code="2ed",
            collector_number="55",
        )
        session.add(card)
        session.commit()
        session.refresh(card)
        return card.id


class TestAddToWishlist:
    def test_add_success(self, client, card_id):
        resp = client.post("/api/v1/wishlist", json={"card_id": card_id})
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["card_id"] == card_id
        assert data["name_en"] == "Lightning Bolt"
        assert data["is_acquired"] is False

    def test_add_with_notes_and_max_price(self, client, card_id):
        resp = client.post(
            "/api/v1/wishlist",
            json={"card_id": card_id, "notes": "For EDH", "max_price": 5.50},
        )
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["notes"] == "For EDH"
        assert data["max_price"] == 5.50

    def test_add_nonexistent_card(self, client):
        resp = client.post("/api/v1/wishlist", json={"card_id": 99999})
        assert resp.status_code == 404

    def test_add_duplicate_returns_409(self, client, card_id):
        client.post("/api/v1/wishlist", json={"card_id": card_id})
        resp = client.post("/api/v1/wishlist", json={"card_id": card_id})
        assert resp.status_code == 409


class TestListWishlist:
    def test_list_empty(self, client):
        resp = client.get("/api/v1/wishlist")
        assert resp.status_code == 200
        assert resp.json()["data"] == []

    def test_list_items(self, client, card_id, card_id_2):
        client.post("/api/v1/wishlist", json={"card_id": card_id})
        client.post("/api/v1/wishlist", json={"card_id": card_id_2})
        resp = client.get("/api/v1/wishlist")
        assert resp.status_code == 200
        assert len(resp.json()["data"]) == 2

    def test_list_with_search(self, client, card_id, card_id_2):
        client.post("/api/v1/wishlist", json={"card_id": card_id})
        client.post("/api/v1/wishlist", json={"card_id": card_id_2})
        resp = client.get("/api/v1/wishlist?search=bolt")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert len(data) == 1
        assert data[0]["name_en"] == "Lightning Bolt"

    def test_list_pagination(self, client, card_id, card_id_2):
        client.post("/api/v1/wishlist", json={"card_id": card_id})
        client.post("/api/v1/wishlist", json={"card_id": card_id_2})
        resp = client.get("/api/v1/wishlist?limit=1")
        assert resp.status_code == 200
        assert len(resp.json()["data"]) == 1
        assert resp.json()["meta"]["total"] == 2

    def test_list_acquired_filter(self, client, card_id, card_id_2):
        client.post("/api/v1/wishlist", json={"card_id": card_id})
        client.post("/api/v1/wishlist", json={"card_id": card_id_2})
        client.patch(f"/api/v1/wishlist/{card_id}/acquire")
        # Only non-acquired
        resp = client.get("/api/v1/wishlist?acquired=false")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert len(data) == 1
        assert data[0]["name_en"] == "Counterspell"


class TestRemoveFromWishlist:
    def test_remove_success(self, client, card_id):
        client.post("/api/v1/wishlist", json={"card_id": card_id})
        resp = client.delete(f"/api/v1/wishlist/{card_id}")
        assert resp.status_code == 204

    def test_remove_nonexistent(self, client, card_id):
        resp = client.delete(f"/api/v1/wishlist/{card_id}")
        assert resp.status_code == 404


class TestMarkAcquired:
    def test_mark_acquired(self, client, card_id):
        client.post("/api/v1/wishlist", json={"card_id": card_id})
        resp = client.patch(f"/api/v1/wishlist/{card_id}/acquire")
        assert resp.status_code == 200
        assert resp.json()["data"]["acquired"] is True

    def test_mark_nonexistent(self, client, card_id):
        resp = client.patch(f"/api/v1/wishlist/{card_id}/acquire")
        assert resp.status_code == 404


class TestCheckWishlist:
    def test_check_mixed(self, client, card_id, card_id_2):
        client.post("/api/v1/wishlist", json={"card_id": card_id})
        resp = client.get(f"/api/v1/wishlist/check?card_ids={card_id},{card_id_2}")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert card_id in data["wishlisted"]
        assert card_id_2 not in data["wishlisted"]

    def test_check_invalid_format(self, client):
        resp = client.get("/api/v1/wishlist/check?card_ids=abc,def")
        assert resp.status_code == 400
