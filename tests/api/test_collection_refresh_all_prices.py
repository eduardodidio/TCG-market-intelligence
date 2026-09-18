"""Tests for POST /api/v1/collection/refresh-all-prices endpoint (F148-T04).

Queue-based bulk refresh: creates PriceUpdateRequestRow entries for all
distinct card_ids in the user's collection.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from unittest.mock import MagicMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from src.api.routers.collection import router
from src.database.models import (
    Base,
    CardRow,
    PriceUpdateRequestRow,
    UserCollectionRow,
    UserRow,
)
from src.database.repository import Repository
from src.domain.models import User

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_app(
    repo: Repository,
    user: User | None = None,
    credit_balance: int = 1000,
) -> tuple[FastAPI, MagicMock]:
    from src.api.deps import get_credit_service, get_current_user, get_db
    from src.credits.service import CreditService

    app = FastAPI()
    app.include_router(router, prefix="/api/v1")

    def override_db():
        yield repo

    app.dependency_overrides[get_db] = override_db

    if user is not None:
        app.dependency_overrides[get_current_user] = lambda: user

    mock_credit_svc = MagicMock(spec=CreditService)
    mock_credit_svc.check_sufficient.return_value = credit_balance > 0
    app.dependency_overrides[get_credit_service] = lambda: mock_credit_svc

    return app, mock_credit_svc


def _make_repo_and_seed(card_count: int = 3, user_id: int = 1) -> Repository:
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        # Create user
        session.add(
            UserRow(
                id=user_id,
                email="test@test.com",
                display_name="testuser",
                auth_provider="email",
                password_hash="x",
            )
        )
        session.flush()

        # Create cards
        for i in range(1, card_count + 1):
            session.add(
                CardRow(
                    id=i,
                    game="magic",
                    name_en=f"Card {i}",
                    set_code="m10",
                    collector_number=str(i),
                )
            )
        session.flush()

        # Create collection entries (user_id stored as string)
        for i in range(1, card_count + 1):
            session.add(
                UserCollectionRow(
                    user_id=str(user_id),
                    card_id=i,
                    set_code="m10",
                    collector_number=str(i),
                    name_en=f"Card {i}",
                )
            )
        session.commit()

    repo = Repository.__new__(Repository)
    repo.engine = engine
    return repo


@pytest.fixture()
def test_user():
    return User(id=1, email="test@test.com", display_name="testuser")


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestRefreshAllCollectionPrices:
    """Tests for POST /api/v1/collection/refresh-all-prices."""

    def test_queues_all_collection_cards(self, test_user):
        repo = _make_repo_and_seed(card_count=3)
        app, _ = _make_app(repo, user=test_user)
        client = TestClient(app)

        resp = client.post("/api/v1/collection/refresh-all-prices")
        assert resp.status_code == 200
        body = resp.json()
        assert body["data"]["status"] == "queued"
        assert body["data"]["card_count"] == 3
        assert body["data"]["total_cost"] == 3
        assert body["data"]["skipped"] == 0

    def test_creates_price_update_request_rows(self, test_user):
        repo = _make_repo_and_seed(card_count=2)
        app, _ = _make_app(repo, user=test_user)
        client = TestClient(app)

        resp = client.post("/api/v1/collection/refresh-all-prices")
        assert resp.status_code == 200

        with Session(repo.engine) as session:
            rows = session.execute(select(PriceUpdateRequestRow)).scalars().all()
            assert len(rows) == 2
            card_ids = {r.card_id for r in rows}
            assert card_ids == {1, 2}
            for r in rows:
                assert r.status == "pending"
                assert r.user_id == test_user.id

    def test_deduplicates_same_card_id(self, test_user):
        """User may have multiple collection entries for the same card_id."""
        engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(engine)

        with Session(engine) as session:
            session.add(
                UserRow(
                    id=1,
                    email="t@t.com",
                    display_name="t",
                    auth_provider="email",
                    password_hash="x",
                )
            )
            session.flush()
            session.add(
                CardRow(id=1, game="magic", name_en="Bolt", set_code="m10", collector_number="1")
            )
            session.flush()
            # Two collection entries for the same card
            for _ in range(2):
                session.add(
                    UserCollectionRow(
                        user_id="1",
                        card_id=1,
                        set_code="m10",
                        collector_number="1",
                        name_en="Bolt",
                    )
                )
            session.commit()

        repo = Repository.__new__(Repository)
        repo.engine = engine
        app, _ = _make_app(repo, user=test_user)
        client = TestClient(app)

        resp = client.post("/api/v1/collection/refresh-all-prices")
        assert resp.status_code == 200
        assert resp.json()["data"]["card_count"] == 1

    def test_skips_pending_requests_within_24h(self, test_user):
        repo = _make_repo_and_seed(card_count=3)

        # Pre-create a pending request for card_id=1
        with Session(repo.engine) as session:
            session.add(
                PriceUpdateRequestRow(
                    card_id=1,
                    user_id=test_user.id,
                    status="pending",
                    requested_at=datetime.now() - timedelta(hours=1),
                )
            )
            session.commit()

        app, _ = _make_app(repo, user=test_user)
        client = TestClient(app)

        resp = client.post("/api/v1/collection/refresh-all-prices")
        assert resp.status_code == 200
        body = resp.json()
        assert body["data"]["card_count"] == 2
        assert body["data"]["skipped"] == 1

    def test_does_not_skip_old_pending_requests(self, test_user):
        repo = _make_repo_and_seed(card_count=2)

        # Pre-create an old pending request (>24h) for card_id=1
        with Session(repo.engine) as session:
            session.add(
                PriceUpdateRequestRow(
                    card_id=1,
                    user_id=test_user.id,
                    status="pending",
                    requested_at=datetime.now() - timedelta(hours=25),
                )
            )
            session.commit()

        app, _ = _make_app(repo, user=test_user)
        client = TestClient(app)

        resp = client.post("/api/v1/collection/refresh-all-prices")
        assert resp.status_code == 200
        assert resp.json()["data"]["card_count"] == 2
        assert resp.json()["data"]["skipped"] == 0

    def test_safety_cap_500(self, test_user):
        """Should cap at 500 cards even if collection is larger."""
        repo = _make_repo_and_seed(card_count=505)
        app, credit_svc = _make_app(repo, user=test_user)
        client = TestClient(app)

        resp = client.post("/api/v1/collection/refresh-all-prices")
        assert resp.status_code == 200
        body = resp.json()
        assert body["data"]["card_count"] == 500

        with Session(repo.engine) as session:
            rows = session.execute(select(PriceUpdateRequestRow)).scalars().all()
            assert len(rows) == 500

    def test_insufficient_credits(self, test_user):
        repo = _make_repo_and_seed(card_count=3)
        app, _ = _make_app(repo, user=test_user, credit_balance=0)
        client = TestClient(app)

        resp = client.post("/api/v1/collection/refresh-all-prices")
        assert resp.status_code == 402

    def test_deducts_credits(self, test_user):
        repo = _make_repo_and_seed(card_count=3)
        app, credit_svc = _make_app(repo, user=test_user)
        client = TestClient(app)

        resp = client.post("/api/v1/collection/refresh-all-prices")
        assert resp.status_code == 200

        credit_svc.deduct.assert_called_once_with(
            test_user.id, 3, "bulk_refresh", reference_id="collection"
        )

    def test_empty_collection(self, test_user):
        """Empty collection should return card_count=0 without error."""
        engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(engine)

        with Session(engine) as session:
            session.add(
                UserRow(
                    id=1,
                    email="t@t.com",
                    display_name="t",
                    auth_provider="email",
                    password_hash="x",
                )
            )
            session.commit()

        repo = Repository.__new__(Repository)
        repo.engine = engine
        app, credit_svc = _make_app(repo, user=test_user)
        client = TestClient(app)

        resp = client.post("/api/v1/collection/refresh-all-prices")
        assert resp.status_code == 200
        body = resp.json()
        assert body["data"]["card_count"] == 0
        assert body["data"]["total_cost"] == 0
        # Should not deduct credits for empty collection
        credit_svc.deduct.assert_not_called()

    def test_all_skipped_no_credit_deduction(self, test_user):
        """When all cards already have pending requests, no credits should be deducted."""
        repo = _make_repo_and_seed(card_count=2)

        # Pre-create pending requests for all cards
        with Session(repo.engine) as session:
            for cid in [1, 2]:
                session.add(
                    PriceUpdateRequestRow(
                        card_id=cid,
                        user_id=test_user.id,
                        status="pending",
                        requested_at=datetime.now(),
                    )
                )
            session.commit()

        app, credit_svc = _make_app(repo, user=test_user)
        client = TestClient(app)

        resp = client.post("/api/v1/collection/refresh-all-prices")
        assert resp.status_code == 200
        body = resp.json()
        assert body["data"]["card_count"] == 0
        assert body["data"]["skipped"] == 2
        credit_svc.deduct.assert_not_called()
