"""Tests for POST /admin/jobs/process-price-requests endpoint."""

from __future__ import annotations

from unittest.mock import patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from src.api.deps import get_current_user, get_db
from src.api.routers.admin import router
from src.database.models import CardRow
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
    db_path = tmp_path / "test_admin_ppr.db"
    return Repository(db_url=f"sqlite:///{db_path}")


@pytest.fixture()
def admin_user():
    return _make_user(user_id=1, is_admin=True, email="admin@test.com")


@pytest.fixture()
def regular_user():
    return _make_user(user_id=2, is_admin=False, email="user@test.com")


def _create_card(repo: Repository, name_en: str = "Lightning Bolt") -> int:
    """Insert a card directly via the ORM and return its id."""
    with Session(repo.engine) as session:
        card = CardRow(game="magic", name_en=name_en, set_code="m10", collector_number="146")
        session.add(card)
        session.commit()
        return card.id


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


def test_trigger_returns_started(admin_client, repo, admin_user):
    """POST with pending requests returns started status."""
    card_id = _create_card(repo, "Lightning Bolt")
    repo.create_price_update_request(card_id, admin_user.id)

    with patch("src.collectors.price_request_processor.process_pending_price_requests"):
        with patch("src.config.get_db_url", return_value="sqlite:///test.db"):
            resp = admin_client.post("/api/v1/admin/jobs/process-price-requests")

    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["status"] == "started"
    assert data["pending_count"] >= 1
    assert "scan_id" in data


def test_no_pending_returns_no_pending(admin_client):
    """POST with empty queue returns no_pending status."""
    resp = admin_client.post("/api/v1/admin/jobs/process-price-requests")
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["status"] == "no_pending"


def test_nonadmin_rejected(nonadmin_client):
    """Non-admin user gets 403."""
    resp = nonadmin_client.post("/api/v1/admin/jobs/process-price-requests")
    assert resp.status_code == 403


def test_audit_log_created(admin_client, repo, admin_user):
    """Verify audit entry is created after trigger."""
    card_id = _create_card(repo, "Counterspell")
    repo.create_price_update_request(card_id, admin_user.id)

    with patch("src.collectors.price_request_processor.process_pending_price_requests"):
        with patch("src.config.get_db_url", return_value="sqlite:///test.db"):
            resp = admin_client.post("/api/v1/admin/jobs/process-price-requests")

    assert resp.status_code == 200

    # Check audit log
    logs, total = repo.list_audit_logs(limit=10, offset=0, action="job_trigger")
    matching = [log for log in logs if log.get("action") == "job_trigger"]
    assert len(matching) >= 1


def test_custom_limit_and_delay(admin_client, repo, admin_user):
    """Custom limit and delay query params are accepted."""
    card_id = _create_card(repo, "Sol Ring")
    repo.create_price_update_request(card_id, admin_user.id)

    with patch("src.collectors.price_request_processor.process_pending_price_requests"):
        with patch("src.config.get_db_url", return_value="sqlite:///test.db"):
            resp = admin_client.post("/api/v1/admin/jobs/process-price-requests?limit=50&delay=1.0")

    assert resp.status_code == 200
    assert resp.json()["data"]["status"] == "started"
