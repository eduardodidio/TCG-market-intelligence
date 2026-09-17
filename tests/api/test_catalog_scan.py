"""Tests for POST /catalog/scan endpoint (F131-T03)."""

from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from src.api.deps import get_credit_service, get_current_user, get_db
from src.api.routers.catalog import router
from src.database.models import (
    Base,
    CardRow,
    CreditBalanceRow,
    PriceUpdateRequestRow,
    UserRow,
)
from src.database.repository import Repository
from src.domain.models import User


@pytest.fixture()
def scan_repo():
    """In-memory DB with catalog cards and a user with credits."""
    engine = create_engine(
        "sqlite:///:memory:",
        echo=False,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        # Create user
        user = UserRow(
            id=1,
            email="test@test.com",
            display_name="Test",
            auth_provider="local",
            is_active=1,
            is_admin=0,
        )
        session.add(user)
        session.flush()

        # Give user 500 credits
        session.add(CreditBalanceRow(user_id=1, balance=500))

        # 5 catalog cards in set "mh3"
        for i in range(1, 6):
            session.add(
                CardRow(
                    id=i,
                    game="magic",
                    name_en=f"Card {i}",
                    set_code="mh3",
                    collector_number=str(i),
                )
            )

        # 2 catalog cards in set "fdn"
        for i in range(6, 8):
            session.add(
                CardRow(
                    id=i,
                    game="magic",
                    name_en=f"Card {i}",
                    set_code="fdn",
                    collector_number=str(i),
                )
            )
        session.commit()

    repo = Repository.__new__(Repository)
    repo.engine = engine
    return repo


def _make_user() -> User:
    return User(id=1, email="test@test.com", display_name="Test", is_admin=False)


@pytest.fixture()
def client(scan_repo):
    """Client with authenticated user and credit service."""
    from src.credits.service import CreditService

    app = FastAPI()
    app.include_router(router, prefix="/api/v1")
    app.dependency_overrides[get_db] = lambda: scan_repo
    app.dependency_overrides[get_current_user] = lambda: _make_user()
    app.dependency_overrides[get_credit_service] = lambda: CreditService(scan_repo)
    return TestClient(app)


@pytest.fixture()
def client_no_auth(scan_repo):
    """Client without authentication override (will fail auth)."""
    app = FastAPI()
    app.include_router(router, prefix="/api/v1")
    app.dependency_overrides[get_db] = lambda: scan_repo
    # No get_current_user override — auth will fail
    return TestClient(app)


class TestCatalogScanEndpoint:
    """POST /api/v1/catalog/scan tests."""

    def test_scan_valid_set_returns_queued(self, client, scan_repo):
        """POST with valid set_code returns 200 with queued status."""
        resp = client.post(
            "/api/v1/catalog/scan",
            json={"set_code": "mh3"},
        )
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["status"] == "queued"
        assert data["set_code"] == "mh3"
        assert data["card_count"] == 5
        assert data["total_cost"] == 5

    def test_scan_creates_price_update_requests(self, client, scan_repo):
        """Verify price_update_requests rows are created for each card."""
        client.post("/api/v1/catalog/scan", json={"set_code": "mh3"})

        with Session(scan_repo.engine) as session:
            requests = (
                session.execute(
                    select(PriceUpdateRequestRow).where(PriceUpdateRequestRow.status == "pending")
                )
                .scalars()
                .all()
            )

        assert len(requests) == 5
        card_ids = {r.card_id for r in requests}
        assert card_ids == {1, 2, 3, 4, 5}

    def test_scan_deduplicates_pending_requests(self, client, scan_repo):
        """Second scan for same set should not create duplicate requests."""
        client.post("/api/v1/catalog/scan", json={"set_code": "mh3"})
        client.post("/api/v1/catalog/scan", json={"set_code": "mh3"})

        with Session(scan_repo.engine) as session:
            requests = (
                session.execute(
                    select(PriceUpdateRequestRow).where(PriceUpdateRequestRow.status == "pending")
                )
                .scalars()
                .all()
            )

        # Should still be 5, not 10
        assert len(requests) == 5

    def test_scan_nonexistent_set_returns_404(self, client):
        """POST with nonexistent set_code returns 404."""
        resp = client.post(
            "/api/v1/catalog/scan",
            json={"set_code": "nonexistent"},
        )
        assert resp.status_code == 404

    def test_scan_missing_set_code_returns_422(self, client):
        """POST without set_code returns 422."""
        resp = client.post("/api/v1/catalog/scan", json={})
        assert resp.status_code == 422

    def test_scan_insufficient_credits_returns_402(self, scan_repo):
        """POST with insufficient credits returns 402."""
        from src.credits.service import CreditService

        # Set balance to 2 (but set has 5 cards)
        with Session(scan_repo.engine) as session:
            row = session.execute(
                select(CreditBalanceRow).where(CreditBalanceRow.user_id == 1)
            ).scalar_one()
            row.balance = 2
            session.commit()

        app = FastAPI()
        app.include_router(router, prefix="/api/v1")
        app.dependency_overrides[get_db] = lambda: scan_repo
        app.dependency_overrides[get_current_user] = lambda: _make_user()
        app.dependency_overrides[get_credit_service] = lambda: CreditService(scan_repo)
        client = TestClient(app)

        resp = client.post(
            "/api/v1/catalog/scan",
            json={"set_code": "mh3"},
        )
        assert resp.status_code == 402

    def test_scan_deducts_credits(self, client, scan_repo):
        """Verify credits are deducted after successful scan."""
        with Session(scan_repo.engine) as session:
            before = session.execute(
                select(CreditBalanceRow.balance).where(CreditBalanceRow.user_id == 1)
            ).scalar_one()

        client.post("/api/v1/catalog/scan", json={"set_code": "mh3"})

        with Session(scan_repo.engine) as session:
            after = session.execute(
                select(CreditBalanceRow.balance).where(CreditBalanceRow.user_id == 1)
            ).scalar_one()

        assert after == before - 5  # 5 cards * 1 credit each

    def test_scan_different_set(self, client, scan_repo):
        """Scan a different set works independently."""
        resp = client.post(
            "/api/v1/catalog/scan",
            json={"set_code": "fdn"},
        )
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["set_code"] == "fdn"
        assert data["card_count"] == 2
        assert data["total_cost"] == 2

    def test_scan_set_code_normalized_to_lowercase(self, client):
        """Set code should be normalized to lowercase."""
        resp = client.post(
            "/api/v1/catalog/scan",
            json={"set_code": "MH3"},
        )
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["set_code"] == "mh3"
