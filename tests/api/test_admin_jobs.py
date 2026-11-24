"""Tests for admin job trigger endpoints (F213-T04).

Covers:
- POST /admin/jobs/myp-sweep
- POST /admin/jobs/snapshot-portfolio
- POST /admin/jobs/catalog-seed
- POST /admin/jobs/banlist-sync
- GET  /admin/jobs/status (enhanced with tracked_jobs)
- Rate limiting (409 when same job type already running)
- Non-admin rejection (403)
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.api.deps import get_current_user, get_db
from src.api.job_tracker import JobTracker, job_tracker
from src.api.routers.admin import router
from src.database.repository import Repository
from src.domain.models import User


def _make_user(user_id: int = 1, is_admin: bool = False, email: str = "u@test.com") -> User:
    return User(
        id=user_id,
        email=email,
        display_name="Test User",
        auth_provider="email",
        is_active=True,
        is_admin=is_admin,
    )


@pytest.fixture()
def repo(tmp_path):
    db_path = tmp_path / "test_admin_jobs.db"
    return Repository(db_url=f"sqlite:///{db_path}")


@pytest.fixture()
def admin_user():
    return _make_user(user_id=1, is_admin=True, email="admin@test.com")


@pytest.fixture()
def regular_user():
    return _make_user(user_id=2, is_admin=False, email="user@test.com")


@pytest.fixture(autouse=True)
def _reset_job_tracker():
    """Clear the global job tracker between tests."""
    job_tracker._jobs.clear()
    yield
    job_tracker._jobs.clear()


@pytest.fixture()
def admin_app(repo, admin_user):
    app = FastAPI()
    app.include_router(router, prefix="/api/v1")
    app.dependency_overrides[get_db] = lambda: repo
    app.dependency_overrides[get_current_user] = lambda: admin_user
    user_row = repo.create_user(email=admin_user.email, display_name=admin_user.display_name)
    repo.update_user(user_row.id, is_admin=1)
    return app


@pytest.fixture()
def admin_client(admin_app):
    return TestClient(admin_app)


@pytest.fixture()
def nonadmin_app(repo, regular_user):
    app = FastAPI()
    app.include_router(router, prefix="/api/v1")
    app.dependency_overrides[get_db] = lambda: repo
    app.dependency_overrides[get_current_user] = lambda: regular_user
    repo.create_user(email=regular_user.email, display_name=regular_user.display_name)
    return app


@pytest.fixture()
def nonadmin_client(nonadmin_app):
    return TestClient(nonadmin_app)


# ── MYP sweep ────────────────────────────────────────────────────────


class TestMypSweep:
    def test_trigger_returns_started(self, admin_client):
        with patch("src.config.get_db_url", return_value="sqlite:///test.db"):
            with patch("src.collectors.myp_sweep.run_myp_sweep", new_callable=AsyncMock):
                resp = admin_client.post("/api/v1/admin/jobs/myp-sweep")

        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["status"] == "started"
        assert data["type"] == "myp-sweep"
        assert "job_id" in data

    def test_custom_params(self, admin_client):
        with patch("src.config.get_db_url", return_value="sqlite:///test.db"):
            with patch("src.collectors.myp_sweep.run_myp_sweep", new_callable=AsyncMock):
                resp = admin_client.post("/api/v1/admin/jobs/myp-sweep?max_age_days=7&limit=100")

        assert resp.status_code == 200
        assert resp.json()["data"]["status"] == "started"

    def test_rate_limited_409(self, admin_client):
        """Second call while running returns 409."""
        # Manually start a fake running job
        job_tracker.start("myp-sweep")

        resp = admin_client.post("/api/v1/admin/jobs/myp-sweep")
        assert resp.status_code == 409

    def test_nonadmin_rejected(self, nonadmin_client):
        resp = nonadmin_client.post("/api/v1/admin/jobs/myp-sweep")
        assert resp.status_code == 403


# ── Snapshot portfolio ───────────────────────────────────────────────


class TestSnapshotPortfolio:
    def test_trigger_returns_started(self, admin_client):
        with patch("src.config.get_db_url", return_value="sqlite:///test.db"):
            with patch("src.collectors.portfolio_snapshot.take_snapshot"):
                resp = admin_client.post("/api/v1/admin/jobs/snapshot-portfolio")

        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["status"] == "started"
        assert data["type"] == "snapshot-portfolio"
        assert "job_id" in data

    def test_rate_limited_409(self, admin_client):
        job_tracker.start("snapshot-portfolio")

        resp = admin_client.post("/api/v1/admin/jobs/snapshot-portfolio")
        assert resp.status_code == 409

    def test_nonadmin_rejected(self, nonadmin_client):
        resp = nonadmin_client.post("/api/v1/admin/jobs/snapshot-portfolio")
        assert resp.status_code == 403


# ── Catalog seed ─────────────────────────────────────────────────────


class TestCatalogSeed:
    def test_trigger_returns_started(self, admin_client):
        with patch("src.config.get_db_url", return_value="sqlite:///test.db"):
            with patch("src.catalog.scryfall.download_bulk_data"):
                with patch("src.catalog.seeder.seed_catalog"):
                    resp = admin_client.post("/api/v1/admin/jobs/catalog-seed")

        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["status"] == "started"
        assert data["type"] == "catalog-seed"
        assert "job_id" in data

    def test_rate_limited_409(self, admin_client):
        job_tracker.start("catalog-seed")

        resp = admin_client.post("/api/v1/admin/jobs/catalog-seed")
        assert resp.status_code == 409

    def test_nonadmin_rejected(self, nonadmin_client):
        resp = nonadmin_client.post("/api/v1/admin/jobs/catalog-seed")
        assert resp.status_code == 403


# ── Banlist sync ─────────────────────────────────────────────────────


class TestBanlistSync:
    def test_trigger_returns_started(self, admin_client):
        with patch("src.config.get_db_url", return_value="sqlite:///test.db"):
            with patch("src.collectors.banlist_sync.run_banlist_sync", new_callable=AsyncMock):
                resp = admin_client.post("/api/v1/admin/jobs/banlist-sync")

        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["status"] == "started"
        assert data["type"] == "banlist-sync"
        assert "job_id" in data

    def test_rate_limited_409(self, admin_client):
        job_tracker.start("banlist-sync")

        resp = admin_client.post("/api/v1/admin/jobs/banlist-sync")
        assert resp.status_code == 409

    def test_nonadmin_rejected(self, nonadmin_client):
        resp = nonadmin_client.post("/api/v1/admin/jobs/banlist-sync")
        assert resp.status_code == 403


# ── Job status ───────────────────────────────────────────────────────


class TestJobStatus:
    def test_returns_tracked_jobs(self, admin_client):
        job_tracker.start("myp-sweep")

        resp = admin_client.get("/api/v1/admin/jobs/status")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert "tracked_jobs" in data
        assert "scan_runs" in data
        assert len(data["tracked_jobs"]) == 1
        assert data["tracked_jobs"][0]["job_type"] == "myp-sweep"

    def test_empty_status(self, admin_client):
        resp = admin_client.get("/api/v1/admin/jobs/status")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["tracked_jobs"] == []

    def test_nonadmin_rejected(self, nonadmin_client):
        resp = nonadmin_client.get("/api/v1/admin/jobs/status")
        assert resp.status_code == 403


# ── Job tracker unit tests ───────────────────────────────────────────


class TestJobTracker:
    def test_start_and_list(self):
        tracker = JobTracker()
        job = tracker.start("test-job", {"key": "val"})
        assert job.job_type == "test-job"
        assert job.status.value == "started"

        jobs = tracker.list_jobs()
        assert len(jobs) == 1
        assert jobs[0]["job_id"] == job.job_id

    def test_duplicate_running_raises(self):
        tracker = JobTracker()
        tracker.start("test-job")
        with pytest.raises(ValueError, match="already running"):
            tracker.start("test-job")

    def test_completed_allows_restart(self):
        tracker = JobTracker()
        job1 = tracker.start("test-job")
        tracker.mark_completed(job1.job_id)

        job2 = tracker.start("test-job")
        assert job2.job_id != job1.job_id

    def test_failed_allows_restart(self):
        tracker = JobTracker()
        job1 = tracker.start("test-job")
        tracker.mark_failed(job1.job_id, "boom")

        job2 = tracker.start("test-job")
        assert job2.job_id != job1.job_id

    def test_mark_running(self):
        tracker = JobTracker()
        job = tracker.start("test-job")
        tracker.mark_running(job.job_id)
        assert tracker.get(job.job_id).status.value == "running"

    def test_mark_completed_with_details(self):
        tracker = JobTracker()
        job = tracker.start("test-job")
        tracker.mark_completed(job.job_id, {"count": 42})
        rec = tracker.get(job.job_id)
        assert rec.status.value == "completed"
        assert rec.details["count"] == 42
        assert rec.completed_at is not None

    def test_mark_failed_with_error(self):
        tracker = JobTracker()
        job = tracker.start("test-job")
        tracker.mark_failed(job.job_id, "something broke")
        rec = tracker.get(job.job_id)
        assert rec.status.value == "failed"
        assert rec.error == "something broke"

    def test_is_running(self):
        tracker = JobTracker()
        assert not tracker.is_running("test-job")
        job = tracker.start("test-job")
        assert tracker.is_running("test-job")
        tracker.mark_completed(job.job_id)
        assert not tracker.is_running("test-job")

    def test_prune_old(self):
        """Old completed jobs are pruned when new jobs are started."""
        tracker = JobTracker(max_history=2)

        # Create and complete 5 jobs with different types
        for i in range(5):
            j = tracker.start(f"job-{i}")
            tracker.mark_completed(j.job_id)

        # Total should be less than 5 due to pruning on each start()
        listed = tracker.list_jobs(limit=20)
        assert len(listed) < 5
        # The most recent jobs should still be present
        job_types = {j["job_type"] for j in listed}
        assert "job-4" in job_types

    def test_different_job_types_concurrent(self):
        tracker = JobTracker()
        tracker.start("type-a")
        tracker.start("type-b")
        assert tracker.is_running("type-a")
        assert tracker.is_running("type-b")

    def test_to_dict(self):
        tracker = JobTracker()
        job = tracker.start("test-job", {"param": 1})
        d = tracker.get(job.job_id).to_dict()
        assert d["job_type"] == "test-job"
        assert d["status"] == "started"
        assert d["details"] == {"param": 1}
        assert d["completed_at"] is None
        assert d["error"] is None
