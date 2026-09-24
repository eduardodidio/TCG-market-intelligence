"""Integration tests for the daily snapshot pipeline (F168-T05).

Covers: snapshot creation, history API, backfill, idempotency,
admin endpoint auth, sparkline/price-trends integration, and empty DB.
"""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from src.api.deps import get_current_user, get_db
from src.api.routers.admin import router as admin_router
from src.api.routers.cards import router as cards_router
from src.collectors.price_snapshot import (
    BACKFILL_SOURCE,
    SNAPSHOT_SOURCE,
    backfill_snapshots,
    run_daily_snapshot,
)
from src.database.models import CardRow, PriceObservationRow, SourceCardRow
from src.database.repository import Repository
from src.domain.models import User

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_user(user_id: int = 1, is_admin: bool = False, email: str = "u@test.com") -> User:
    return User(
        id=user_id,
        email=email,
        display_name="Test User",
        auth_provider="email",
        is_active=True,
        is_admin=is_admin,
    )


def _seed_cards_with_prices(repo: Repository) -> dict[str, int]:
    """Create 3 cards with source_cards and price observations, plus 1 card with no prices.

    Returns dict mapping card label -> card_id.
    """
    today = date.today()
    with Session(repo.engine) as session:
        # Cards with prices
        c1 = CardRow(game="magic", name_en="Snapshot Card A", set_code="TST", collector_number="1")
        c2 = CardRow(game="magic", name_en="Snapshot Card B", set_code="TST", collector_number="2")
        c3 = CardRow(game="magic", name_en="Snapshot Card C", set_code="TST", collector_number="3")
        # Card with no prices
        c4 = CardRow(game="magic", name_en="No Price Card", set_code="TST", collector_number="4")
        session.add_all([c1, c2, c3, c4])
        session.flush()

        sc1 = SourceCardRow(
            source="liga", external_id="liga_snap_1", card_id=c1.id, url="https://example.com/1"
        )
        sc2 = SourceCardRow(
            source="liga", external_id="liga_snap_2", card_id=c2.id, url="https://example.com/2"
        )
        sc3 = SourceCardRow(
            source="liga", external_id="liga_snap_3", card_id=c3.id, url="https://example.com/3"
        )
        session.add_all([sc1, sc2, sc3])
        session.flush()

        # Price observations (liga source) for c1, c2, c3
        for ext_id, price in [("liga_snap_1", 10.0), ("liga_snap_2", 25.50), ("liga_snap_3", 5.0)]:
            session.add(
                PriceObservationRow(
                    source="liga",
                    external_id=ext_id,
                    observed_at=today - timedelta(days=1),
                    median_price=Decimal(str(price)),
                    currency="BRL",
                )
            )

        session.commit()
        return {"c1": c1.id, "c2": c2.id, "c3": c3.id, "c4": c4.id}


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def repo(tmp_path):
    db_path = tmp_path / "test_snapshot_pipeline.db"
    return Repository(db_url=f"sqlite:///{db_path}")


@pytest.fixture()
def seeded_repo(repo):
    """Repo with 3 priced cards + 1 unpriced card."""
    ids = _seed_cards_with_prices(repo)
    return repo, ids


@pytest.fixture()
def admin_user():
    return _make_user(user_id=1, is_admin=True, email="admin@snap.test")


@pytest.fixture()
def regular_user():
    return _make_user(user_id=2, is_admin=False, email="user@snap.test")


@pytest.fixture()
def full_app(seeded_repo, admin_user):
    """App with both cards and admin routers, authenticated as admin."""
    repo, ids = seeded_repo
    app = FastAPI()
    app.include_router(cards_router)
    app.include_router(admin_router, prefix="/api/v1")
    app.dependency_overrides[get_db] = lambda: repo
    app.dependency_overrides[get_current_user] = lambda: admin_user
    user_row = repo.create_user(email=admin_user.email, display_name=admin_user.display_name)
    repo.update_user(user_row.id, is_admin=1)
    return TestClient(app), repo, ids


# ---------------------------------------------------------------------------
# 1. Full pipeline: create cards -> snapshot -> query history -> verify
# ---------------------------------------------------------------------------


class TestFullPipeline:
    def test_snapshot_creates_observations_and_history_shows_them(self, seeded_repo):
        """Run daily snapshot, then verify observations appear in card history."""
        repo, ids = seeded_repo
        count = run_daily_snapshot(repo)

        # Should create 3 observations (one per priced card, card c4 has no price)
        assert count == 3

        # Verify observations exist in DB with correct source
        with Session(repo.engine) as session:
            snapshot_obs = (
                session.query(PriceObservationRow)
                .filter(PriceObservationRow.source == SNAPSHOT_SOURCE)
                .all()
            )
            assert len(snapshot_obs) == 3
            ext_ids = {o.external_id for o in snapshot_obs}
            assert ext_ids == {"liga_snap_1", "liga_snap_2", "liga_snap_3"}

            # All should be today's date
            for obs in snapshot_obs:
                assert obs.observed_at == date.today()

    def test_history_endpoint_returns_snapshot_data(self, full_app):
        """After snapshot, GET /cards/{id}/history includes daily_snapshot obs."""
        client, repo, ids = full_app
        run_daily_snapshot(repo)

        resp = client.get(f"/cards/{ids['c1']}/history?period=30d")
        assert resp.status_code == 200
        observations = resp.json()["data"]["observations"]
        # Should have at least 2 observations: 1 liga + 1 daily_snapshot
        assert len(observations) >= 2

    def test_unpriced_card_history_empty(self, full_app):
        """Card c4 has no source_cards, history should be empty."""
        client, repo, ids = full_app
        run_daily_snapshot(repo)

        resp = client.get(f"/cards/{ids['c4']}/history?period=30d")
        assert resp.status_code == 200
        observations = resp.json()["data"]["observations"]
        assert len(observations) == 0


# ---------------------------------------------------------------------------
# 2. Sparkline / price-trends integration
# ---------------------------------------------------------------------------


class TestSparklineIntegration:
    def test_price_trends_includes_snapshot_data(self, full_app):
        """Price-trends endpoint should return data from daily_snapshot source."""
        client, repo, ids = full_app

        # Add a daily_snapshot observation only (no liga obs for a new external_id)
        # But since get_price_series_batch uses source_cards external_ids,
        # the snapshot must use the same external_id. run_daily_snapshot does this.
        run_daily_snapshot(repo)

        resp = client.get(f"/cards/price-trends?card_ids={ids['c1']}")
        assert resp.status_code == 200
        trends = resp.json()["data"]["trends"]
        entry = trends[str(ids["c1"])]
        # Should have prices from both liga and daily_snapshot
        assert len(entry["prices"]) >= 2

    def test_card_with_only_snapshot_shows_in_trends(self, full_app):
        """A card whose only recent observation is daily_snapshot should appear in trends."""
        client, repo, ids = full_app

        # Remove the liga observation for c1 so only snapshot remains
        with Session(repo.engine) as session:
            session.query(PriceObservationRow).filter(
                PriceObservationRow.source == "liga",
                PriceObservationRow.external_id == "liga_snap_1",
            ).delete()
            session.commit()

        # Now create a snapshot — this should still find c1 via other cards' prices
        # But c1 has no liga obs left so get_all_latest_prices won't include it.
        # Instead, manually insert a snapshot observation for c1
        from src.domain.models import HistoricalPrice

        repo.insert_price_observations(
            [
                HistoricalPrice(
                    source=SNAPSHOT_SOURCE,
                    external_id="liga_snap_1",
                    observed_at=date.today(),
                    median_price=Decimal("10.00"),
                )
            ]
        )

        resp = client.get(f"/cards/price-trends?card_ids={ids['c1']}")
        assert resp.status_code == 200
        trends = resp.json()["data"]["trends"]
        entry = trends[str(ids["c1"])]
        assert len(entry["prices"]) >= 1
        assert entry["prices"][0] == 10.0


# ---------------------------------------------------------------------------
# 3. Admin endpoint auth
# ---------------------------------------------------------------------------


class TestAdminEndpointAuth:
    def test_admin_returns_200(self, full_app):
        """Admin user can trigger snapshot-prices."""
        client, repo, ids = full_app
        with patch("src.collectors.price_snapshot.run_daily_snapshot", return_value=3):
            resp = client.post("/api/v1/admin/jobs/snapshot-prices")
        assert resp.status_code == 200
        assert resp.json()["data"]["observations_created"] == 3

    def test_nonadmin_returns_403(self, seeded_repo, regular_user):
        """Non-admin user gets 403."""
        repo, ids = seeded_repo
        app = FastAPI()
        app.include_router(admin_router, prefix="/api/v1")
        app.dependency_overrides[get_db] = lambda: repo
        app.dependency_overrides[get_current_user] = lambda: regular_user
        repo.create_user(email=regular_user.email, display_name=regular_user.display_name)
        client = TestClient(app)

        resp = client.post("/api/v1/admin/jobs/snapshot-prices")
        assert resp.status_code == 403

    def test_noauth_returns_401(self, seeded_repo):
        """Unauthenticated request gets 401."""
        repo, ids = seeded_repo
        app = FastAPI()
        app.include_router(admin_router, prefix="/api/v1")
        app.dependency_overrides[get_db] = lambda: repo
        # No user override -> should raise 401
        client = TestClient(app)

        resp = client.post("/api/v1/admin/jobs/snapshot-prices")
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# 4. Backfill + snapshot
# ---------------------------------------------------------------------------


class TestBackfillAndSnapshot:
    # F176-T05: backfill forward-fills from real observations (seeded at D-1),
    # so a 3-day window only fills today, under BACKFILL_SOURCE.
    def test_backfill_creates_multi_day_observations(self, seeded_repo):
        """backfill_snapshots(days=3) fills only days after the first real obs."""
        repo, ids = seeded_repo
        count = backfill_snapshots(repo, days=3)
        assert count == 3  # 3 cards x 1 day (today); D-2 precedes the first real obs

        with Session(repo.engine) as session:
            snapshot_obs = (
                session.query(PriceObservationRow)
                .filter(PriceObservationRow.source == BACKFILL_SOURCE)
                .all()
            )
            assert len(snapshot_obs) == 3
            assert {o.observed_at for o in snapshot_obs} == {date.today()}

    def test_backfill_then_daily_snapshot(self, seeded_repo):
        """Backfill 3 days, then daily snapshot. Daily should be idempotent for today."""
        repo, ids = seeded_repo

        backfill_count = backfill_snapshots(repo, days=3)
        assert backfill_count == 3

        # Daily snapshot for today — backfill already covered today,
        # so this should create 0 new observations
        daily_count = run_daily_snapshot(repo)
        assert daily_count == 0

    def test_backfill_second_run_creates_zero(self, seeded_repo):
        """Backfill is idempotent: the second run finds no empty days."""
        repo, ids = seeded_repo

        count1 = backfill_snapshots(repo, days=2)
        assert count1 == 3  # 3 cards x today (D-1 has the real observation)

        count2 = backfill_snapshots(repo, days=2)
        assert count2 == 0


# ---------------------------------------------------------------------------
# 5. Idempotency
# ---------------------------------------------------------------------------


class TestIdempotency:
    def test_second_daily_snapshot_creates_zero(self, seeded_repo):
        """Running daily snapshot twice on the same day creates 0 on second run."""
        repo, ids = seeded_repo

        count1 = run_daily_snapshot(repo)
        assert count1 == 3

        count2 = run_daily_snapshot(repo)
        assert count2 == 0

    def test_idempotency_preserves_existing_data(self, seeded_repo):
        """Second run doesn't corrupt existing observations."""
        repo, ids = seeded_repo

        run_daily_snapshot(repo)
        run_daily_snapshot(repo)

        with Session(repo.engine) as session:
            total = (
                session.query(PriceObservationRow)
                .filter(PriceObservationRow.source == SNAPSHOT_SOURCE)
                .count()
            )
            assert total == 3  # Still exactly 3


# ---------------------------------------------------------------------------
# 6. Empty DB
# ---------------------------------------------------------------------------


class TestEmptyDB:
    def test_snapshot_empty_db_returns_zero(self, repo):
        """Snapshot on empty DB returns 0 and doesn't error."""
        count = run_daily_snapshot(repo)
        assert count == 0

    def test_backfill_empty_db_returns_zero(self, repo):
        """Backfill on empty DB returns 0 and doesn't error."""
        count = backfill_snapshots(repo, days=5)
        assert count == 0
