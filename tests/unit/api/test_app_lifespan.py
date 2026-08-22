"""Tests for FastAPI lifespan integration with ScanScheduler (F37-T07)."""

from __future__ import annotations

import os
from unittest.mock import patch

from fastapi.testclient import TestClient

from src.api.app import create_app


class TestLifespanSchedulerDisabled:
    """App startup with scheduler disabled."""

    def test_no_errors_when_disabled(self) -> None:
        with patch.dict(os.environ, {"TCG_SCHEDULER_DISABLED": "1"}):
            app = create_app()
            with TestClient(app) as client:
                resp = client.get("/health")
                assert resp.status_code == 200
                assert resp.json()["status"] == "ok"

    def test_no_scheduler_attribute_when_disabled(self) -> None:
        with patch.dict(os.environ, {"TCG_SCHEDULER_DISABLED": "1"}):
            app = create_app()
            with TestClient(app):
                assert not hasattr(app.state, "scheduler")


class TestLifespanSchedulerEnabled:
    """App startup with scheduler enabled."""

    def test_scheduler_starts_and_stops(self) -> None:
        with patch.dict(os.environ, {"TCG_SCHEDULER_DISABLED": "0"}):
            app = create_app()
            with TestClient(app) as client:
                # Scheduler should be on app.state
                assert hasattr(app.state, "scheduler")
                assert app.state.scheduler is not None

                # Health check still works
                resp = client.get("/health")
                assert resp.status_code == 200

            # After exiting context, scheduler should be shut down
            assert app.state.scheduler._scheduler is None

    def test_schedules_router_mounted(self) -> None:
        with patch.dict(os.environ, {"TCG_SCHEDULER_DISABLED": "1"}):
            app = create_app()
            with TestClient(app) as client:
                # Verify schedules endpoint is reachable (returns 401/403 without auth, not 404)
                resp = client.get("/api/v1/schedules")
                # Should not be 404 (route exists even if auth fails)
                assert resp.status_code != 404
