"""Tests for the alerts API router (F106-T01)."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from src.api.deps import get_current_user, get_db
from src.api.routers.alerts import router
from src.database.models import AlertNotificationRow, CardRow
from src.database.repository import Repository
from src.domain.models import User


def _make_user(user_id: int = 1, is_admin: bool = False) -> User:
    return User(
        id=user_id,
        email="test@example.com",
        display_name="Test User",
        auth_provider="email",
        is_active=True,
        is_admin=is_admin,
    )


@pytest.fixture()
def repo(tmp_path):
    db_path = tmp_path / "test_alerts.db"
    db_url = f"sqlite:///{db_path}"
    return Repository(db_url=db_url)


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
    """Create a test card and return its ID."""
    with Session(repo.engine) as session:
        card = CardRow(
            game="magic",
            name_en="Lightning Bolt",
            set_code="2ed",
            collector_number="157",
        )
        session.add(card)
        session.commit()
        session.refresh(card)
        return card.id


class TestCreateAlert:
    def test_create_alert_success(self, client, card_id):
        resp = client.post(
            "/api/v1/alerts",
            json={"card_id": card_id, "target_price": 10.50, "direction": "below"},
        )
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["card_id"] == card_id
        assert data["target_price"] == 10.50
        assert data["direction"] == "below"
        assert data["is_active"] is True
        assert data["card_name"] == "Lightning Bolt"

    def test_create_alert_above(self, client, card_id):
        resp = client.post(
            "/api/v1/alerts",
            json={"card_id": card_id, "target_price": 50.0, "direction": "above"},
        )
        assert resp.status_code == 200
        assert resp.json()["data"]["direction"] == "above"

    def test_create_alert_invalid_direction(self, client, card_id):
        resp = client.post(
            "/api/v1/alerts",
            json={"card_id": card_id, "target_price": 10.0, "direction": "invalid"},
        )
        assert resp.status_code == 422

    def test_create_alert_negative_price(self, client, card_id):
        resp = client.post(
            "/api/v1/alerts",
            json={"card_id": card_id, "target_price": -5.0, "direction": "below"},
        )
        assert resp.status_code == 422

    def test_create_alert_zero_price(self, client, card_id):
        resp = client.post(
            "/api/v1/alerts",
            json={"card_id": card_id, "target_price": 0, "direction": "below"},
        )
        assert resp.status_code == 422

    def test_create_alert_card_not_found(self, client):
        resp = client.post(
            "/api/v1/alerts",
            json={"card_id": 99999, "target_price": 10.0, "direction": "below"},
        )
        assert resp.status_code == 404

    def test_create_alert_max_limit(self, client, card_id):
        """Verify 409 when exceeding max active alerts."""
        from src.api.routers.alerts import MAX_ACTIVE_ALERTS_PER_USER

        # Create max alerts
        for i in range(MAX_ACTIVE_ALERTS_PER_USER):
            resp = client.post(
                "/api/v1/alerts",
                json={"card_id": card_id, "target_price": float(i + 1), "direction": "below"},
            )
            assert resp.status_code == 200, f"Alert {i} failed: {resp.json()}"

        # One more should fail
        resp = client.post(
            "/api/v1/alerts",
            json={"card_id": card_id, "target_price": 999.0, "direction": "below"},
        )
        assert resp.status_code == 409


class TestListAlerts:
    def test_list_all_alerts(self, client, card_id):
        client.post(
            "/api/v1/alerts",
            json={"card_id": card_id, "target_price": 10.0, "direction": "below"},
        )
        client.post(
            "/api/v1/alerts",
            json={"card_id": card_id, "target_price": 50.0, "direction": "above"},
        )

        resp = client.get("/api/v1/alerts")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert len(data) == 2
        assert resp.json()["meta"]["total"] == 2

    def test_list_active_only(self, client, card_id):
        client.post(
            "/api/v1/alerts",
            json={"card_id": card_id, "target_price": 10.0, "direction": "below"},
        )

        resp = client.get("/api/v1/alerts?status=active")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert all(a["is_active"] for a in data)

    def test_list_empty(self, client):
        resp = client.get("/api/v1/alerts")
        assert resp.status_code == 200
        assert resp.json()["data"] == []


class TestDeleteAlert:
    def test_delete_alert(self, client, card_id):
        resp = client.post(
            "/api/v1/alerts",
            json={"card_id": card_id, "target_price": 10.0, "direction": "below"},
        )
        alert_id = resp.json()["data"]["id"]

        resp = client.delete(f"/api/v1/alerts/{alert_id}")
        assert resp.status_code == 204

        # Verify it's gone
        resp = client.get("/api/v1/alerts")
        assert len(resp.json()["data"]) == 0

    def test_delete_alert_not_found(self, client):
        resp = client.delete("/api/v1/alerts/99999")
        assert resp.status_code == 404

    def test_delete_alert_wrong_user(self, client, card_id, repo):
        """Another user's alert cannot be deleted."""
        # Create alert as user 1
        resp = client.post(
            "/api/v1/alerts",
            json={"card_id": card_id, "target_price": 10.0, "direction": "below"},
        )
        alert_id = resp.json()["data"]["id"]

        # Create app as user 2
        user2 = _make_user(user_id=2)
        repo.create_user(email="user2@example.com", display_name="User 2")

        app2 = FastAPI()
        app2.include_router(router, prefix="/api/v1")
        app2.dependency_overrides[get_db] = lambda: repo
        app2.dependency_overrides[get_current_user] = lambda: user2
        client2 = TestClient(app2)

        resp = client2.delete(f"/api/v1/alerts/{alert_id}")
        assert resp.status_code == 403


class TestNotifications:
    def test_list_notifications_empty(self, client):
        resp = client.get("/api/v1/alerts/notifications")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["notifications"] == []
        assert data["unread_count"] == 0

    def test_list_notifications_with_data(self, client, card_id, repo):
        """Create an alert and manually trigger it, then list notifications."""
        resp = client.post(
            "/api/v1/alerts",
            json={"card_id": card_id, "target_price": 10.0, "direction": "below"},
        )
        alert_id = resp.json()["data"]["id"]

        # Manually create a notification
        with Session(repo.engine) as session:
            notification = AlertNotificationRow(
                alert_id=alert_id,
                card_name="Lightning Bolt",
                old_price=Decimal("15.00"),
                new_price=Decimal("8.00"),
                is_read=0,
                notified_at=datetime.now(),
            )
            session.add(notification)
            session.commit()

        resp = client.get("/api/v1/alerts/notifications")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert len(data["notifications"]) == 1
        assert data["unread_count"] == 1
        assert data["notifications"][0]["card_name"] == "Lightning Bolt"
        assert data["notifications"][0]["new_price"] == 8.0

    def test_mark_all_read(self, client, card_id, repo):
        # Create alert and notification
        resp = client.post(
            "/api/v1/alerts",
            json={"card_id": card_id, "target_price": 10.0, "direction": "below"},
        )
        alert_id = resp.json()["data"]["id"]

        with Session(repo.engine) as session:
            notification = AlertNotificationRow(
                alert_id=alert_id,
                card_name="Lightning Bolt",
                old_price=Decimal("15.00"),
                new_price=Decimal("8.00"),
                is_read=0,
                notified_at=datetime.now(),
            )
            session.add(notification)
            session.commit()

        # Mark all read
        resp = client.patch("/api/v1/alerts/notifications/read")
        assert resp.status_code == 200

        # Verify unread_count is 0
        resp = client.get("/api/v1/alerts/notifications")
        assert resp.json()["data"]["unread_count"] == 0

    def test_unread_only_filter(self, client, card_id, repo):
        resp = client.post(
            "/api/v1/alerts",
            json={"card_id": card_id, "target_price": 10.0, "direction": "below"},
        )
        alert_id = resp.json()["data"]["id"]

        with Session(repo.engine) as session:
            # One read, one unread
            n1 = AlertNotificationRow(
                alert_id=alert_id,
                card_name="Lightning Bolt",
                old_price=Decimal("15.00"),
                new_price=Decimal("8.00"),
                is_read=1,
                notified_at=datetime.now(),
            )
            n2 = AlertNotificationRow(
                alert_id=alert_id,
                card_name="Lightning Bolt",
                old_price=Decimal("12.00"),
                new_price=Decimal("7.00"),
                is_read=0,
                notified_at=datetime.now(),
            )
            session.add_all([n1, n2])
            session.commit()

        resp = client.get("/api/v1/alerts/notifications?unread_only=true")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert len(data["notifications"]) == 1
        assert data["notifications"][0]["is_read"] is False


class TestNoAuth:
    def test_endpoints_require_auth(self, repo):
        """Endpoints should return 401/422 when no auth is provided."""
        app = FastAPI()
        app.include_router(router, prefix="/api/v1")
        app.dependency_overrides[get_db] = lambda: repo
        # No auth override
        client = TestClient(app, raise_server_exceptions=False)

        # All endpoints should fail without auth
        for method, path in [
            ("POST", "/api/v1/alerts"),
            ("GET", "/api/v1/alerts"),
            ("GET", "/api/v1/alerts/notifications"),
            ("DELETE", "/api/v1/alerts/1"),
            ("PATCH", "/api/v1/alerts/notifications/read"),
        ]:
            resp = getattr(client, method.lower())(path)
            # FastAPI returns 401 or 422 when dependency fails
            assert resp.status_code in (
                401,
                422,
                500,
            ), f"{method} {path} returned {resp.status_code}"
