"""Tests for schedule management API endpoints (F37-T05).

Uses TestClient with mocked scheduler and in-memory DB.
Updated for F90-T01: responses now use ApiResponse envelope.
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


def _create_schedule(client, headers, name="Daily Scan", cron="0 6 * * *"):
    """Helper: create a schedule and return the data dict from the envelope."""
    resp = client.post(
        "/api/v1/schedules",
        json={
            "name": name,
            "cron_expression": cron,
            "scan_type": "collection",
        },
        headers=headers,
    )
    assert resp.status_code == 201
    body = resp.json()
    assert "data" in body
    return body["data"]


class TestCreateSchedule:
    """POST /api/v1/schedules."""

    def test_create_schedule_201(self, client) -> None:
        headers = _setup_user(client)
        data = _create_schedule(client, headers)
        assert data["name"] == "Daily Scan"
        assert data["cron_expression"] == "0 6 * * *"
        assert data["status"] == "active"

    def test_create_schedule_envelope_shape(self, client) -> None:
        """Verify the response matches the ApiResponse envelope format."""
        headers = _setup_user(client)
        resp = client.post(
            "/api/v1/schedules",
            json={
                "name": "Envelope Test",
                "cron_expression": "0 6 * * *",
                "scan_type": "collection",
            },
            headers=headers,
        )
        assert resp.status_code == 201
        body = resp.json()
        # Must have the standard envelope keys
        assert "data" in body
        assert "meta" in body
        assert "errors" in body
        assert isinstance(body["errors"], list)
        assert len(body["errors"]) == 0
        # Data must contain the schedule
        assert body["data"]["name"] == "Envelope Test"
        assert "id" in body["data"]
        # Meta must have request_id
        assert "request_id" in body["meta"]

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
        _create_schedule(client, headers, "S1", "0 6 * * *")
        _create_schedule(client, headers, "S2", "0 12 * * *")

        resp = client.get("/api/v1/schedules", headers=headers)
        assert resp.status_code == 200
        body = resp.json()
        assert "data" in body
        assert body["data"]["total"] == 2
        assert len(body["data"]["schedules"]) == 2

    def test_list_schedules_envelope_shape(self, client) -> None:
        """Verify the list response has correct envelope."""
        headers = _setup_user(client)
        resp = client.get("/api/v1/schedules", headers=headers)
        assert resp.status_code == 200
        body = resp.json()
        assert "data" in body
        assert "meta" in body
        assert "errors" in body
        assert body["data"]["schedules"] == []
        assert body["data"]["total"] == 0


class TestGetSchedule:
    """GET /api/v1/schedules/{id}."""

    def test_get_existing(self, client) -> None:
        headers = _setup_user(client)
        created = _create_schedule(client, headers, "Test")
        schedule_id = created["id"]

        resp = client.get(f"/api/v1/schedules/{schedule_id}", headers=headers)
        assert resp.status_code == 200
        body = resp.json()
        assert body["data"]["name"] == "Test"

    def test_get_nonexistent_404(self, client) -> None:
        headers = _setup_user(client)
        resp = client.get("/api/v1/schedules/99999", headers=headers)
        assert resp.status_code == 404


class TestUpdateSchedule:
    """PATCH /api/v1/schedules/{id}."""

    def test_update_name(self, client) -> None:
        headers = _setup_user(client)
        created = _create_schedule(client, headers, "Original")
        schedule_id = created["id"]

        resp = client.patch(
            f"/api/v1/schedules/{schedule_id}",
            json={"name": "Updated"},
            headers=headers,
        )
        assert resp.status_code == 200
        assert resp.json()["data"]["name"] == "Updated"

    def test_update_status_to_paused(self, client) -> None:
        headers = _setup_user(client)
        created = _create_schedule(client, headers, "S1")
        schedule_id = created["id"]

        resp = client.patch(
            f"/api/v1/schedules/{schedule_id}",
            json={"status": "paused"},
            headers=headers,
        )
        assert resp.status_code == 200
        assert resp.json()["data"]["status"] == "paused"

    def test_update_envelope_shape(self, client) -> None:
        """Verify PATCH response uses envelope."""
        headers = _setup_user(client)
        created = _create_schedule(client, headers, "PatchTest")
        schedule_id = created["id"]

        resp = client.patch(
            f"/api/v1/schedules/{schedule_id}",
            json={"name": "PatchUpdated"},
            headers=headers,
        )
        assert resp.status_code == 200
        body = resp.json()
        assert "data" in body
        assert "meta" in body
        assert "errors" in body
        assert body["data"]["name"] == "PatchUpdated"

    def test_update_no_changes(self, client) -> None:
        """PATCH with empty body returns current data in envelope."""
        headers = _setup_user(client)
        created = _create_schedule(client, headers, "NoChange")
        schedule_id = created["id"]

        resp = client.patch(
            f"/api/v1/schedules/{schedule_id}",
            json={},
            headers=headers,
        )
        assert resp.status_code == 200
        body = resp.json()
        assert "data" in body
        assert body["data"]["name"] == "NoChange"

    def test_update_invalid_cron_422(self, client) -> None:
        headers = _setup_user(client)
        created = _create_schedule(client, headers, "S1")
        schedule_id = created["id"]

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
        created = _create_schedule(client, headers, "To Delete")
        schedule_id = created["id"]

        resp = client.delete(f"/api/v1/schedules/{schedule_id}", headers=headers)
        assert resp.status_code == 200
        body = resp.json()
        assert "data" in body
        assert body["data"]["status"] == "deleted"

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
        created = _create_schedule(client, headers, "S1")
        schedule_id = created["id"]

        # No scheduler available (TCG_SCHEDULER_DISABLED=1)
        resp = client.post(
            f"/api/v1/schedules/{schedule_id}/trigger",
            headers=headers,
        )
        assert resp.status_code == 503


class TestCreateThenListRoundTrip:
    """Integration: create schedule, verify it appears in list."""

    def test_created_schedule_appears_in_list(self, client) -> None:
        """After POST, the new schedule must appear in GET list."""
        headers = _setup_user(client)
        _create_schedule(client, headers, "RoundTrip")

        resp = client.get("/api/v1/schedules", headers=headers)
        assert resp.status_code == 200
        body = resp.json()
        names = [s["name"] for s in body["data"]["schedules"]]
        assert "RoundTrip" in names
        assert body["data"]["total"] >= 1

    def test_update_then_verify_in_list(self, client) -> None:
        """After PATCH, the updated name must appear in GET list."""
        headers = _setup_user(client)
        created = _create_schedule(client, headers, "Before")
        schedule_id = created["id"]

        client.patch(
            f"/api/v1/schedules/{schedule_id}",
            json={"name": "After"},
            headers=headers,
        )

        resp = client.get("/api/v1/schedules", headers=headers)
        names = [s["name"] for s in resp.json()["data"]["schedules"]]
        assert "After" in names
        assert "Before" not in names
