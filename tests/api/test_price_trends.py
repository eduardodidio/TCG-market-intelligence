"""Tests for GET /cards/price-trends endpoint (F104-T01)."""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from src.api.deps import get_db
from src.api.routers.cards import router
from src.database.models import CardRow, PriceObservationRow, SourceCardRow
from src.database.repository import Repository


@pytest.fixture()
def trends_app(tmp_path):
    """Create a test app with cards and price observations."""
    db_path = tmp_path / "trends.db"
    repo = Repository(db_url=f"sqlite:///{db_path}")

    today = date.today()
    with Session(repo.engine) as session:
        c1 = CardRow(game="magic", name_en="Card A", set_code="SET", collector_number="1")
        c2 = CardRow(game="magic", name_en="Card B", set_code="SET", collector_number="2")
        c3 = CardRow(game="magic", name_en="Card C", set_code="SET", collector_number="3")
        session.add_all([c1, c2, c3])
        session.flush()

        sc1 = SourceCardRow(
            source="liga",
            external_id="ext_a",
            card_id=c1.id,
            url="https://example.com/a",
        )
        sc2 = SourceCardRow(
            source="liga",
            external_id="ext_b",
            card_id=c2.id,
            url="https://example.com/b",
        )
        session.add_all([sc1, sc2])
        session.flush()

        # Card A: 3 observations over 5 days (rising)
        for i, price in enumerate([10.0, 12.0, 15.0]):
            session.add(
                PriceObservationRow(
                    source="liga",
                    external_id="ext_a",
                    observed_at=today - timedelta(days=5 - i * 2),
                    median_price=Decimal(str(price)),
                    currency="BRL",
                )
            )

        # Card B: 2 observations (falling)
        for i, price in enumerate([20.0, 16.0]):
            session.add(
                PriceObservationRow(
                    source="liga",
                    external_id="ext_b",
                    observed_at=today - timedelta(days=3 - i * 2),
                    median_price=Decimal(str(price)),
                    currency="BRL",
                )
            )

        # Card C: no source cards, no observations
        session.commit()

        ids = {"c1": c1.id, "c2": c2.id, "c3": c3.id}

    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_db] = lambda: repo
    client = TestClient(app)
    return client, ids


class TestPriceTrendsEndpoint:
    def test_returns_correct_shape(self, trends_app):
        client, ids = trends_app
        resp = client.get(f"/cards/price-trends?card_ids={ids['c1']},{ids['c2']}")
        assert resp.status_code == 200
        body = resp.json()
        assert "data" in body
        trends = body["data"]["trends"]
        assert str(ids["c1"]) in trends
        assert str(ids["c2"]) in trends
        assert "prices" in trends[str(ids["c1"])]
        assert "change_pct" in trends[str(ids["c1"])]

    def test_positive_change_pct(self, trends_app):
        client, ids = trends_app
        resp = client.get(f"/cards/price-trends?card_ids={ids['c1']}")
        trends = resp.json()["data"]["trends"]
        entry = trends[str(ids["c1"])]
        assert entry["change_pct"] > 0
        assert entry["prices"] == [10.0, 12.0, 15.0]

    def test_negative_change_pct(self, trends_app):
        client, ids = trends_app
        resp = client.get(f"/cards/price-trends?card_ids={ids['c2']}")
        trends = resp.json()["data"]["trends"]
        entry = trends[str(ids["c2"])]
        assert entry["change_pct"] < 0
        assert entry["prices"] == [20.0, 16.0]

    def test_no_observations_returns_empty(self, trends_app):
        client, ids = trends_app
        resp = client.get(f"/cards/price-trends?card_ids={ids['c3']}")
        trends = resp.json()["data"]["trends"]
        entry = trends[str(ids["c3"])]
        assert entry["prices"] == []
        assert entry["change_pct"] is None

    def test_max_50_card_ids(self, trends_app):
        client, _ = trends_app
        ids_str = ",".join(str(i) for i in range(51))
        resp = client.get(f"/cards/price-trends?card_ids={ids_str}")
        assert resp.status_code == 400

    def test_49_card_ids_ok(self, trends_app):
        client, _ = trends_app
        ids_str = ",".join(str(i) for i in range(49))
        resp = client.get(f"/cards/price-trends?card_ids={ids_str}")
        assert resp.status_code == 200

    def test_days_parameter(self, trends_app):
        client, ids = trends_app
        resp = client.get(f"/cards/price-trends?card_ids={ids['c1']}&days=1")
        assert resp.status_code == 200

    def test_invalid_card_ids(self, trends_app):
        client, _ = trends_app
        resp = client.get("/cards/price-trends?card_ids=abc,def")
        assert resp.status_code == 400

    def test_empty_card_ids(self, trends_app):
        client, _ = trends_app
        resp = client.get("/cards/price-trends?card_ids=")
        assert resp.status_code == 200
        trends = resp.json()["data"]["trends"]
        assert trends == {}
