from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from src.api.deps import get_db
from src.api.routers.market import router
from src.database.models import (
    CardRow,
    PriceObservationRow,
    SourceCardRow,
)
from src.database.repository import Repository


@pytest.fixture()
def repo(tmp_path):
    db_path = tmp_path / "test.db"
    return Repository(db_url=f"sqlite:///{db_path}")


@pytest.fixture()
def client(repo):
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_db] = lambda: repo
    return TestClient(app)


def _seed_movers_data(repo):
    """Seed cards with price changes for movers tests."""
    today = date.today()
    with Session(repo.engine) as session:
        # Card that went up: 10 -> 15 (+50%)
        c1 = CardRow(
            game="magic",
            name_en="Rising Star",
            set_code="SET1",
            collector_number="1",
        )
        # Card that went down: 20 -> 10 (-50%)
        c2 = CardRow(
            game="magic",
            name_en="Falling Stone",
            set_code="SET1",
            collector_number="2",
        )
        session.add_all([c1, c2])
        session.flush()

        sc1 = SourceCardRow(
            source="myp",
            external_id="rise1",
            card_id=c1.id,
            url="https://myp/rise1",
            name_en="Rising Star",
        )
        sc2 = SourceCardRow(
            source="myp",
            external_id="fall1",
            card_id=c2.id,
            url="https://myp/fall1",
            name_en="Falling Stone",
        )
        session.add_all([sc1, sc2])
        session.flush()

        # Price observations for Rising Star
        session.add_all(
            [
                PriceObservationRow(
                    source="myp",
                    external_id="rise1",
                    observed_at=today - timedelta(days=10),
                    median_price=Decimal("10.00"),
                    currency="BRL",
                ),
                PriceObservationRow(
                    source="myp",
                    external_id="rise1",
                    observed_at=today,
                    median_price=Decimal("15.00"),
                    currency="BRL",
                ),
            ]
        )

        # Price observations for Falling Stone
        session.add_all(
            [
                PriceObservationRow(
                    source="myp",
                    external_id="fall1",
                    observed_at=today - timedelta(days=10),
                    median_price=Decimal("20.00"),
                    currency="BRL",
                ),
                PriceObservationRow(
                    source="myp",
                    external_id="fall1",
                    observed_at=today,
                    median_price=Decimal("10.00"),
                    currency="BRL",
                ),
            ]
        )
        session.commit()


def _seed_stats_data(repo):
    """Seed data for market stats tests."""
    with Session(repo.engine) as session:
        c1 = CardRow(
            game="magic",
            name_en="Card A",
            set_code="S1",
            collector_number="1",
        )
        c2 = CardRow(
            game="pokemon",
            name_en="Card B",
            set_code="S2",
            collector_number="1",
        )
        session.add_all([c1, c2])
        session.flush()

        session.add_all(
            [
                PriceObservationRow(
                    source="myp",
                    external_id="a1",
                    observed_at=date(2026, 8, 1),
                    median_price=Decimal("10.00"),
                    currency="BRL",
                ),
                PriceObservationRow(
                    source="myp",
                    external_id="a1",
                    observed_at=date(2026, 8, 10),
                    median_price=Decimal("20.00"),
                    currency="BRL",
                ),
                PriceObservationRow(
                    source="myp",
                    external_id="b1",
                    observed_at=date(2026, 8, 5),
                    median_price=Decimal("30.00"),
                    currency="BRL",
                ),
            ]
        )
        session.commit()


class TestGetMovers:
    def test_identifies_gainers_and_losers(self, client, repo):
        _seed_movers_data(repo)
        resp = client.get("/market/movers?period=30d")
        assert resp.status_code == 200
        data = resp.json()["data"]
        gainers = data["gainers"]
        losers = data["losers"]
        assert len(gainers) >= 1
        assert len(losers) >= 1
        # Rising Star should be top gainer
        gainer_names = [g["name_en"] for g in gainers]
        assert "Rising Star" in gainer_names
        # Falling Stone should be top loser
        loser_names = [lo["name_en"] for lo in losers]
        assert "Falling Stone" in loser_names

    def test_movers_change_pct(self, client, repo):
        _seed_movers_data(repo)
        resp = client.get("/market/movers?period=30d")
        data = resp.json()["data"]
        gainer = next(g for g in data["gainers"] if g["name_en"] == "Rising Star")
        assert float(gainer["change_pct"]) == pytest.approx(50.0)
        loser = next(lo for lo in data["losers"] if lo["name_en"] == "Falling Stone")
        assert float(loser["change_pct"]) == pytest.approx(-50.0)

    def test_movers_7d_period(self, client, repo):
        _seed_movers_data(repo)
        resp = client.get("/market/movers?period=7d")
        assert resp.status_code == 200

    def test_movers_90d_period(self, client, repo):
        _seed_movers_data(repo)
        resp = client.get("/market/movers?period=90d")
        assert resp.status_code == 200

    def test_invalid_period(self, client):
        resp = client.get("/market/movers?period=999d")
        assert resp.status_code == 422

    def test_custom_limit(self, client, repo):
        _seed_movers_data(repo)
        resp = client.get("/market/movers?period=30d&limit=1")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert len(data["gainers"]) <= 1
        assert len(data["losers"]) <= 1

    def test_response_envelope(self, client, repo):
        _seed_movers_data(repo)
        resp = client.get("/market/movers?period=30d")
        body = resp.json()
        assert "data" in body
        assert "meta" in body


class TestGetStats:
    def test_stats_aggregation(self, client, repo):
        _seed_stats_data(repo)
        resp = client.get("/market/stats")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["total_cards"] == 2
        assert data["total_observations"] == 3
        assert data["avg_price"] is not None
        assert float(data["avg_price"]) == pytest.approx(20.0)
        assert data["date_range_start"] == "2026-08-01"
        assert data["date_range_end"] == "2026-08-10"

    def test_stats_with_game_filter(self, client, repo):
        _seed_stats_data(repo)
        resp = client.get("/market/stats?game=magic")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["total_cards"] == 1

    def test_stats_empty_database(self, client):
        resp = client.get("/market/stats")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["total_cards"] == 0
        assert data["total_observations"] == 0
        assert data["avg_price"] is None
        assert data["date_range_start"] is None
        assert data["date_range_end"] is None

    def test_response_envelope(self, client, repo):
        _seed_stats_data(repo)
        resp = client.get("/market/stats")
        body = resp.json()
        assert "data" in body
        assert "meta" in body
        assert "request_id" in body["meta"]
