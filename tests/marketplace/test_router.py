"""Tests for marketplace API router (F69-T03).

Covers: endpoints, auth requirements, error handling.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from src.api.app import create_app
from src.database.repository import Repository
from src.domain.models import User


@pytest.fixture()
def repo(tmp_path):
    db_path = tmp_path / "test_mkt_router.db"
    db_url = f"sqlite:///{db_path}"
    return Repository(db_url=db_url)


@pytest.fixture()
def test_user():
    return User(
        id=1,
        email="test@example.com",
        display_name="Test",
        auth_provider="email",
        is_admin=False,
    )


@pytest.fixture()
def test_user_2():
    return User(
        id=2,
        email="buyer@example.com",
        display_name="Buyer",
        auth_provider="email",
        is_admin=False,
    )


@pytest.fixture()
def client(repo, test_user):
    app = create_app()

    def override_db():
        yield repo

    def override_user():
        return test_user

    def override_optional_user():
        return test_user

    from src.api.deps import get_current_user, get_db, get_optional_user

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_current_user] = override_user
    app.dependency_overrides[get_optional_user] = override_optional_user

    return TestClient(app)


class TestSharingEndpoints:
    def test_get_sharing_status_default(self, client):
        resp = client.get("/api/v1/marketplace/sharing")
        assert resp.status_code == 200
        data = resp.json()
        assert data["is_shared"] is False

    def test_toggle_sharing_on(self, client):
        resp = client.patch(
            "/api/v1/marketplace/sharing",
            json={"is_shared": True},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["is_shared"] is True
        assert "share_code" in data

    def test_toggle_sharing_off(self, client):
        client.patch("/api/v1/marketplace/sharing", json={"is_shared": True})
        resp = client.patch(
            "/api/v1/marketplace/sharing",
            json={"is_shared": False},
        )
        assert resp.status_code == 200
        assert resp.json()["is_shared"] is False


class TestListingsEndpoints:
    def test_browse_empty_listings(self, client):
        resp = client.get("/api/v1/marketplace/listings")
        assert resp.status_code == 200
        data = resp.json()
        assert data["listings"] == []
        assert data["count"] == 0

    def test_get_shared_collection_not_found(self, client):
        resp = client.get("/api/v1/marketplace/listings/nonexistent")
        assert resp.status_code == 404


class TestInterestEndpoints:
    def test_express_interest_invalid_share_code(self, client):
        resp = client.post(
            "/api/v1/marketplace/interest",
            json={"share_code": "bad", "entry_id": 1},
        )
        assert resp.status_code == 404

    def test_respond_not_found(self, client):
        resp = client.post(
            "/api/v1/marketplace/respond/9999",
            json={"action": "accept"},
        )
        assert resp.status_code == 400


class TestMyTradesEndpoint:
    def test_my_trades_empty(self, client):
        resp = client.get("/api/v1/marketplace/my-trades")
        assert resp.status_code == 200
        data = resp.json()
        assert data["trades"] == []


class TestAgreementEndpoint:
    def test_confirm_not_found(self, client):
        resp = client.post("/api/v1/marketplace/agree/9999")
        assert resp.status_code == 400
