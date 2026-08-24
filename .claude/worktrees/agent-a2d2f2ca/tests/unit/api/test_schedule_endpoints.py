"""Tests for schedule management API endpoints (F37-T05).

Uses TestClient with mocked scheduler and in-memory DB.
"""

from __future__ import annotations

import os
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from src.api.app import create_app

_USER_COUNTER = 0


@pytest.fixture(autouse=True)
def disable_scheduler():
    """Disable scheduler during tests."""
    with patch.dict(os.environ, {"TCG_SCHEDULER_DISABLED": "1"}):
        yield


@pytest.fixture()
def app(tmp_path):
    """Create test FastAPI app with isolated DB."""
    db_path = str(tmp_path / "test.db").replace("\\", "/")
    db_url = f"sqlite:///{db_path}"
    with patch.dict(os.environ, {"TCG_DATABASE_URL": db_url}):
        yield create_app()


@pytest.fixture()
def client(app):
    """Create a test client."""
    return TestClient(app)


def _setup_user(client):
    """Register a unique user and return auth headers."""
    global _USER_COUNTER
    _USER_COUNTER += 1
    email = f"test{_USER_COUNTER}@example.com"
    client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": "testpass123",
            "display_name": "Test User",
        },
    )
    resp = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "testpass123"},
    )
    data = resp.json()
    token = data.get("data", {}).get("access_token") or data.get("access_token", "")
    return {"Authorization": f"Bearer {token}"}


class TestCreateSchedule:
    """POST /api/v1/schedules."""

    def test_create_schedule_201(self, client) -> None:
        headers = _setup_user(client)
        resp = client.post(
            "/api/v1/schedules",
            json={
                "name": "Daily Scan",
                "cron_expression": "0 6 * * *",
                "scan_type": "collection",
            },
            headers=headers,
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "Daily Scan"
        assert data["cron_expression"] == "0 6 * * *"
        assert data["status"] == "active"

    def test_create_invalid_cron_422(self, client) -> None:
        headers = _setup_user(client)
        resp = client.post(
            "/api/v1/schedules",
            json={
                "name": "Bad Cron",
                "cron_expression": "not a cron",
                "scan_type": "collection",
            },
            headers=headers,
        )
        assert resp.status_code == 422

    def test_create_sub_hour_cron_422(self, client) -> None:
        headers = _setup_user(client)
        resp = client.post(
            "/api/v1/schedules",
            json={
                "name": "Too frequent",
                "cron_expression": "*/5 * * * *",
                "scan_type": "collection",
            },
            headers=headers,
        )
        assert resp.status_code == 422


class TestListSchedules:
    """GET /api/v1/schedules."""

    def test_list_schedules(self, client) -> None:
        headers = _setup_user(client)
        # Create two schedules
        client.post(
            "/api/v1/schedules",
            json={"name": "S1", "cron_expression": "0 6 * * *"},
            headers=headers,
        )
        client.post(
            "/api/v1/schedules",
            json={"name": "S2", "cron_expression": "0 12 * * *"},
            headers=headers,
        )
        resp = client.get("/api/v1/schedules", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 2
        assert len(data["schedules"]) == 2


class TestGetSchedule:
    """GET /api/v1/schedules/{id}."""

    def test_get_existing(self, client) -> None:
        headers = _setup_user(client)
        create_resp = client.post(
            "/api/v1/schedules",
            json={"name": "Test", "cron_expression": "0 6 * * *"},
            headers=headers,
        )
        schedule_id = create_resp.json()["id"]

        resp = client.get(f"/api/v1/schedules/{schedule_id}", headers=headers)
        assert resp.status_code == 200
        assert resp.json()["name"] == "Test"

    def test_get_nonexistent_404(self, client) -> None:
        headers = _setup_user(client)
        resp = client.get("/api/v1/schedules/99999", headers=headers)
        assert resp.status_code == 404


class TestUpdateSchedule:
    """PATCH /api/v1/schedules/{id}."""

    def test_update_name(self, client) -> None:
        headers = _setup_user(client)
        create_resp = client.post(
            "/api/v1/schedules",
            json={"name": "Original", "cron_expression": "0 6 * * *"},
            headers=headers,
        )
        schedule_id = create_resp.json()["id"]

        resp = client.patch(
            f"/api/v1/schedules/{schedule_id}",
            json={"name": "Updated"},
            headers=headers,
        )
        assert resp.status_code == 200
        assert resp.json()["name"] == "Updated"

    def test_update_status_to_paused(self, client) -> None:
        headers = _setup_user(client)
        create_resp = client.post(
            "/api/v1/schedules",
            json={"name": "S1", "cron_expression": "0 6 * * *"},
            headers=headers,
        )
        schedule_id = create_resp.json()["id"]

        resp = client.patch(
            f"/api/v1/schedules/{schedule_id}",
            json={"status": "paused"},
            headers=headers,
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "paused"

    def test_update_invalid_cron_422(self, client) -> None:
        headers = _setup_user(client)
        create_resp = client.post(
            "/api/v1/schedules",
            json={"name": "S1", "cron_expression": "0 6 * * *"},
            headers=headers,
        )
        schedule_id = create_resp.json()["id"]

        resp = client.patch(
            f"/api/v1/schedules/{schedule_id}",
            json={"cron_expression": "bad"},
            headers=headers,
        )
        assert resp.status_code == 422


class TestDeleteSchedule:
    """DELETE /api/v1/schedules/{id}."""

    def test_delete_existing(self, client) -> None:
        headers = _setup_user(client)
        create_resp = client.post(
            "/api/v1/schedules",
            json={"name": "To Delete", "cron_expression": "0 6 * * *"},
            headers=headers,
        )
        schedule_id = create_resp.json()["id"]

        resp = client.delete(f"/api/v1/schedules/{schedule_id}", headers=headers)
        assert resp.status_code == 200

        # Verify deleted
        resp = client.get(f"/api/v1/schedules/{schedule_id}", headers=headers)
        assert resp.status_code == 404

    def test_delete_nonexistent_404(self, client) -> None:
        headers = _setup_user(client)
        resp = client.delete("/api/v1/schedules/99999", headers=headers)
        assert resp.status_code == 404


class TestTriggerSchedule:
    """POST /api/v1/schedules/{id}/trigger."""

    def test_trigger_without_scheduler_503(self, client) -> None:
        headers = _setup_user(client)
        create_resp = client.post(
            "/api/v1/schedules",
            json={"name": "S1", "cron_expression": "0 6 * * *"},
            headers=headers,
        )
        schedule_id = create_resp.json()["id"]

        # No scheduler available (TCG_SCHEDULER_DISABLED=1)
        resp = client.post(
            f"/api/v1/schedules/{schedule_id}/trigger",
            headers=headers,
        )
        assert resp.status_code == 503
