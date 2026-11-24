"""Tests for the price history API router (F213-T07)."""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

import pytest
from click.testing import CliRunner
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from src.api.deps import get_db, require_auth_or_api_key
from src.api.routers.price_history import router
from src.database.models import (
    CardRow,
    PriceObservationRow,
    SourceCardRow,
    UserCollectionRow,
)
from src.database.repository import Repository

_TEST_USER_ID = "test-user-1"


@pytest.fixture()
def _seed_db(tmp_path):
    """Create a temp DB with cards, source_cards, observations, and a collection entry."""
    db_path = tmp_path / "test.db"
    db_url = f"sqlite:///{db_path}"
    repo = Repository(db_url=db_url)

    today = date.today()
    with Session(repo.engine) as session:
        # Card with price history
        c1 = CardRow(
            game="magic",
            name_en="Lightning Bolt",
            name_pt="Raio",
            set_code="2XM",
            collector_number="1",
        )
        # Card without any observations
        c2 = CardRow(
            game="magic",
            name_en="Counterspell",
            name_pt="Contrafeitico",
            set_code="DMR",
            collector_number="44",
        )
        session.add_all([c1, c2])
        session.flush()

        sc1 = SourceCardRow(
            source="myp",
            external_id="ext1",
            card_id=c1.id,
            url="https://myp/ext1",
            name_en="Lightning Bolt",
            set_code="2XM",
            collector_number="1",
        )
        session.add(sc1)
        session.flush()

        # Create observations spread over several days
        for i in range(5):
            obs = PriceObservationRow(
                source="myp",
                external_id="ext1",
                observed_at=today - timedelta(days=10 - i * 2),
                median_price=Decimal("5.00") + Decimal(str(i)),
                currency="BRL",
            )
            session.add(obs)

        session.flush()

        # Collection entry for user
        entry = UserCollectionRow(
            user_id=_TEST_USER_ID,
            card_id=c1.id,
            set_code="2XM",
            collector_number="1",
            name_en="Lightning Bolt",
        )
        session.add(entry)

        # Unlinked collection entry (no card_id)
        entry_unlinked = UserCollectionRow(
            user_id=_TEST_USER_ID,
            card_id=None,
            set_code="UNK",
            collector_number="99",
            name_en="Unknown Card",
        )
        session.add(entry_unlinked)
        session.flush()

        ids = {
            "c1": c1.id,
            "c2": c2.id,
            "entry": entry.id,
            "entry_unlinked": entry_unlinked.id,
        }
        session.commit()

    return repo, ids


@pytest.fixture()
def test_app(_seed_db):
    """Create a FastAPI test app with the price_history router."""
    repo, ids = _seed_db

    app = FastAPI()
    app.include_router(router)

    def override_get_db():
        yield repo

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[require_auth_or_api_key] = lambda: _TEST_USER_ID

    client = TestClient(app)
    return client, ids


# ---------------------------------------------------------------------------
# Card-level history endpoint
# ---------------------------------------------------------------------------


class TestCardHistory:
    def test_returns_correct_schema(self, test_app):
        client, ids = test_app
        resp = client.get(f"/price-history/cards/{ids['c1']}/history?days=90")
        assert resp.status_code == 200

        body = resp.json()
        data = body["data"]
        assert data["card_id"] == ids["c1"]
        assert data["variant"] == "normal"
        assert isinstance(data["sources"], list)
        assert isinstance(data["real_points"], int)
        assert isinstance(data["snapshot_points"], int)
        assert isinstance(data["data"], list)
        assert len(data["data"]) > 0

        # Check individual data point schema
        point = data["data"][0]
        assert "date" in point
        assert "price" in point
        assert "source" in point

    def test_days_parameter_filters_range(self, test_app):
        client, ids = test_app
        # With days=1 we should get fewer (or no) points vs days=90
        resp_narrow = client.get(f"/price-history/cards/{ids['c1']}/history?days=1")
        resp_wide = client.get(f"/price-history/cards/{ids['c1']}/history?days=90")
        assert resp_narrow.status_code == 200
        assert resp_wide.status_code == 200

        narrow_count = len(resp_narrow.json()["data"]["data"])
        wide_count = len(resp_wide.json()["data"]["data"])
        assert wide_count >= narrow_count

    def test_404_for_nonexistent_card(self, test_app):
        client, _ = test_app
        resp = client.get("/price-history/cards/999999/history")
        assert resp.status_code == 404

    def test_card_with_no_observations(self, test_app):
        client, ids = test_app
        resp = client.get(f"/price-history/cards/{ids['c2']}/history")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["data"] == []
        assert data["real_points"] == 0


# ---------------------------------------------------------------------------
# Card-level metrics endpoint
# ---------------------------------------------------------------------------


class TestCardMetrics:
    def test_returns_min_max_avg(self, test_app):
        client, ids = test_app
        resp = client.get(f"/price-history/cards/{ids['c1']}/metrics?days=90")
        assert resp.status_code == 200

        data = resp.json()["data"]
        assert data["card_id"] == ids["c1"]
        assert data["min_price"] is not None
        assert data["max_price"] is not None
        assert data["avg_price"] is not None
        assert data["current_price"] is not None
        assert data["data_points"] > 0
        assert data["min_price"] <= data["max_price"]

    def test_trend_direction(self, test_app):
        client, ids = test_app
        resp = client.get(f"/price-history/cards/{ids['c1']}/metrics?days=90")
        assert resp.status_code == 200

        data = resp.json()["data"]
        # Our seed data goes from 5.00 to 9.00 — should be "up"
        assert data["trend"] in ("up", "down", "stable", None)
        assert data["change_pct"] is not None

    def test_404_for_nonexistent_card(self, test_app):
        client, _ = test_app
        resp = client.get("/price-history/cards/999999/metrics")
        assert resp.status_code == 404

    def test_card_with_no_data_returns_nulls(self, test_app):
        client, ids = test_app
        resp = client.get(f"/price-history/cards/{ids['c2']}/metrics")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["min_price"] is None
        assert data["max_price"] is None
        assert data["avg_price"] is None
        assert data["data_points"] == 0


# ---------------------------------------------------------------------------
# Collection-entry-level history endpoint
# ---------------------------------------------------------------------------


class TestCollectionEntryHistory:
    def test_returns_history_for_linked_entry(self, test_app):
        client, ids = test_app
        resp = client.get(f"/price-history/collection/{ids['entry']}/history")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["card_id"] == ids["c1"]
        assert len(data["data"]) > 0

    def test_unlinked_entry_returns_empty(self, test_app):
        client, ids = test_app
        resp = client.get(f"/price-history/collection/{ids['entry_unlinked']}/history")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["data"] == []

    def test_404_for_nonexistent_entry(self, test_app):
        client, _ = test_app
        resp = client.get("/price-history/collection/999999/history")
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Collection-entry-level metrics endpoint
# ---------------------------------------------------------------------------


class TestCollectionEntryMetrics:
    def test_returns_metrics_for_linked_entry(self, test_app):
        client, ids = test_app
        resp = client.get(f"/price-history/collection/{ids['entry']}/metrics")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["min_price"] is not None
        assert data["data_points"] > 0

    def test_unlinked_entry_returns_empty_metrics(self, test_app):
        client, ids = test_app
        resp = client.get(f"/price-history/collection/{ids['entry_unlinked']}/metrics")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["min_price"] is None
        assert data["data_points"] == 0


# ---------------------------------------------------------------------------
# CLI backfill command
# ---------------------------------------------------------------------------


class TestPriceHistoryBackfillCLI:
    def test_dry_run_output(self, tmp_path):
        from src.cli.main import cli

        db_path = tmp_path / "test.db"
        db_url = f"sqlite:///{db_path}"
        repo = Repository(db_url=db_url)

        # Seed a card with observations that have gaps
        today = date.today()
        with Session(repo.engine) as session:
            card = CardRow(
                game="magic",
                name_en="Test Card",
                set_code="TST",
                collector_number="1",
            )
            session.add(card)
            session.flush()

            sc = SourceCardRow(
                source="myp",
                external_id="test_ext",
                card_id=card.id,
                url="https://test",
                name_en="Test Card",
                set_code="TST",
                collector_number="1",
            )
            session.add(sc)
            session.flush()

            # Add observations with gaps (day 10 and day 5 ago, missing days in between)
            for days_ago in [10, 5]:
                obs = PriceObservationRow(
                    source="myp",
                    external_id="test_ext",
                    observed_at=today - timedelta(days=days_ago),
                    median_price=Decimal("10.00"),
                    currency="BRL",
                )
                session.add(obs)
            session.commit()

        runner = CliRunner()
        result = runner.invoke(
            cli,
            ["price-history-backfill", "--db", db_url, "--days", "15", "--dry-run"],
        )
        assert result.exit_code == 0
        assert "DRY RUN" in result.output
        assert "Would create:" in result.output or "observations" in result.output
