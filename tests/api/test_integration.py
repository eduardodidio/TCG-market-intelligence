from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from src.api.app import create_app
from src.api.deps import get_db
from src.database.models import (
    CardRow,
    PriceObservationRow,
    SourceCardRow,
)
from src.database.repository import Repository


@pytest.fixture()
def test_db(tmp_path):
    db_url = f"sqlite:///{tmp_path}/integration_test.db"
    repo = Repository(db_url=db_url)
    return repo, db_url


@pytest.fixture()
def seeded_db(test_db):
    repo, db_url = test_db
    engine = repo.engine
    with Session(engine) as session:
        # Create cards
        card1 = CardRow(
            game="magic",
            name_en="Sol Ring",
            name_pt="Anel Solar",
            set_code="dmr",
            collector_number="001",
        )
        card2 = CardRow(
            game="magic",
            name_en="Lightning Bolt",
            name_pt="Raio",
            set_code="2xm",
            collector_number="125",
        )
        card3 = CardRow(
            game="pokemon",
            name_en="Pikachu",
            set_code="base",
            collector_number="025",
        )
        session.add_all([card1, card2, card3])
        session.flush()

        # Create source cards linked to canonical cards
        sc1 = SourceCardRow(
            source="myp",
            external_id="100",
            card_id=card1.id,
            url="https://mypcards.com/magic/produto/100/sol-ring",
            sku="magic_dmr_001",
            name_en="Sol Ring",
            set_code="dmr",
        )
        sc2 = SourceCardRow(
            source="myp",
            external_id="200",
            card_id=card2.id,
            url="https://mypcards.com/magic/produto/200/lightning-bolt",
            sku="magic_2xm_125",
            name_en="Lightning Bolt",
            set_code="2xm",
        )
        session.add_all([sc1, sc2])
        session.flush()

        # Create price observations
        today = date.today()
        for i in range(60):
            day = today - timedelta(days=60 - i)
            # Sol Ring: price goes from 10 to 20 (uptrend)
            price = Decimal("10.00") + Decimal(str(i * 10 / 60))
            session.add(
                PriceObservationRow(
                    source="myp",
                    external_id="100",
                    observed_at=day,
                    median_price=price.quantize(Decimal("0.01")),
                    currency="BRL",
                )
            )
            # Lightning Bolt: price goes from 30 to 15 (downtrend)
            price2 = Decimal("30.00") - Decimal(str(i * 15 / 60))
            session.add(
                PriceObservationRow(
                    source="myp",
                    external_id="200",
                    observed_at=day,
                    median_price=price2.quantize(Decimal("0.01")),
                    currency="BRL",
                )
            )
        session.commit()

    return repo, db_url


@pytest.fixture()
def client(seeded_db):
    repo, db_url = seeded_db
    app = create_app()

    def override_get_db():
        yield repo

    app.dependency_overrides[get_db] = override_get_db
    return TestClient(app)


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------


class TestHealthCheck:
    def test_health_returns_ok(self, client):
        resp = client.get("/health")
        assert resp.status_code == 200
        assert resp.json() == {"status": "ok"}


# ---------------------------------------------------------------------------
# Cards endpoints
# ---------------------------------------------------------------------------


class TestListCards:
    def test_returns_envelope(self, client):
        resp = client.get("/api/v1/cards")
        assert resp.status_code == 200
        body = resp.json()
        assert "data" in body
        assert "meta" in body
        assert "errors" in body
        assert "request_id" in body["meta"]

    def test_returns_all_cards(self, client):
        resp = client.get("/api/v1/cards")
        body = resp.json()
        assert len(body["data"]) == 3
        assert body["meta"]["total"] == 3

    def test_filter_by_game(self, client):
        resp = client.get("/api/v1/cards?game=magic")
        body = resp.json()
        assert len(body["data"]) == 2
        for card in body["data"]:
            assert card["game"] == "magic"

    def test_filter_by_set(self, client):
        resp = client.get("/api/v1/cards?set=dmr")
        body = resp.json()
        assert len(body["data"]) == 1
        assert body["data"][0]["set_code"] == "dmr"

    def test_filter_by_name(self, client):
        resp = client.get("/api/v1/cards?name=sol")
        body = resp.json()
        assert len(body["data"]) == 1
        assert body["data"][0]["name_en"] == "Sol Ring"

    def test_pagination_with_limit(self, client):
        resp = client.get("/api/v1/cards?limit=1")
        body = resp.json()
        assert len(body["data"]) == 1
        assert body["meta"]["cursor"] is not None
        assert body["meta"]["total"] == 3

    def test_pagination_follow_cursor(self, client):
        # First page
        resp1 = client.get("/api/v1/cards?limit=1")
        body1 = resp1.json()
        cursor = body1["meta"]["cursor"]
        first_id = body1["data"][0]["id"]

        # Second page
        resp2 = client.get(f"/api/v1/cards?limit=1&cursor={cursor}")
        body2 = resp2.json()
        assert len(body2["data"]) == 1
        assert body2["data"][0]["id"] != first_id

    def test_latest_price_included(self, client):
        resp = client.get("/api/v1/cards?set=dmr")
        body = resp.json()
        card = body["data"][0]
        # Sol Ring has price observations, latest_price should be set
        assert card["latest_price"] is not None


class TestGetCard:
    def test_card_detail(self, client):
        # Get list first to find a valid ID
        list_resp = client.get("/api/v1/cards?set=dmr")
        card_id = list_resp.json()["data"][0]["id"]

        resp = client.get(f"/api/v1/cards/{card_id}")
        body = resp.json()
        assert body["data"]["id"] == card_id
        assert body["data"]["name_en"] == "Sol Ring"
        assert "source_cards" in body["data"]
        assert len(body["data"]["source_cards"]) >= 1
        assert "request_id" in body["meta"]

    def test_card_not_found(self, client):
        resp = client.get("/api/v1/cards/99999")
        assert resp.status_code == 404
        body = resp.json()
        assert body["data"] is None
        assert len(body["errors"]) > 0


class TestGetHistory:
    def test_history_returns_observations(self, client):
        list_resp = client.get("/api/v1/cards?set=dmr")
        card_id = list_resp.json()["data"][0]["id"]

        resp = client.get(f"/api/v1/cards/{card_id}/history")
        body = resp.json()
        assert resp.status_code == 200
        assert len(body["data"]) > 0
        # Should be ordered by date
        dates = [obs["observed_at"] for obs in body["data"]]
        assert dates == sorted(dates)

    def test_history_period_30d(self, client):
        list_resp = client.get("/api/v1/cards?set=dmr")
        card_id = list_resp.json()["data"][0]["id"]

        resp = client.get(f"/api/v1/cards/{card_id}/history?period=30d")
        body = resp.json()
        assert resp.status_code == 200
        # 30d period should have fewer observations than default 90d
        cutoff = date.today() - timedelta(days=30)
        for obs in body["data"]:
            assert obs["observed_at"] >= cutoff.isoformat()

    def test_history_card_not_found(self, client):
        resp = client.get("/api/v1/cards/99999/history")
        assert resp.status_code == 404

    def test_history_envelope(self, client):
        list_resp = client.get("/api/v1/cards?set=dmr")
        card_id = list_resp.json()["data"][0]["id"]

        resp = client.get(f"/api/v1/cards/{card_id}/history")
        body = resp.json()
        assert "data" in body
        assert "meta" in body
        assert "errors" in body
        assert "request_id" in body["meta"]


# ---------------------------------------------------------------------------
# Sets endpoint
# ---------------------------------------------------------------------------


class TestListSets:
    def test_returns_sets_with_counts(self, client):
        resp = client.get("/api/v1/sets")
        body = resp.json()
        assert resp.status_code == 200
        assert len(body["data"]) >= 2  # dmr, 2xm, base
        set_codes = [s["set_code"] for s in body["data"]]
        assert "dmr" in set_codes
        assert "2xm" in set_codes

    def test_sets_have_card_count(self, client):
        resp = client.get("/api/v1/sets")
        body = resp.json()
        for s in body["data"]:
            assert "card_count" in s
            assert s["card_count"] >= 1

    def test_sets_envelope(self, client):
        resp = client.get("/api/v1/sets")
        body = resp.json()
        assert "data" in body
        assert "meta" in body
        assert "errors" in body
        assert "request_id" in body["meta"]


# ---------------------------------------------------------------------------
# Market endpoints
# ---------------------------------------------------------------------------


class TestMarketMovers:
    def test_movers_has_gainers_and_losers(self, client):
        resp = client.get("/api/v1/market/movers")
        body = resp.json()
        assert resp.status_code == 200
        assert "gainers" in body["data"]
        assert "losers" in body["data"]

    def test_movers_sol_ring_is_gainer(self, client):
        resp = client.get("/api/v1/market/movers")
        body = resp.json()
        gainers = body["data"]["gainers"]
        gainer_names = [g["name_en"] for g in gainers]
        # Sol Ring goes from 10 to 20 (uptrend)
        assert "Sol Ring" in gainer_names

    def test_movers_lightning_bolt_is_loser(self, client):
        resp = client.get("/api/v1/market/movers")
        body = resp.json()
        losers = body["data"]["losers"]
        loser_names = [lo["name_en"] for lo in losers]
        # Lightning Bolt goes from 30 to 15 (downtrend)
        assert "Lightning Bolt" in loser_names

    def test_movers_envelope(self, client):
        resp = client.get("/api/v1/market/movers")
        body = resp.json()
        assert "data" in body
        assert "meta" in body
        assert "errors" in body
        assert "request_id" in body["meta"]


class TestMarketStats:
    def test_stats_totals(self, client):
        resp = client.get("/api/v1/market/stats")
        body = resp.json()
        assert resp.status_code == 200
        assert body["data"]["total_cards"] == 3
        assert body["data"]["total_observations"] == 120

    def test_stats_has_date_range(self, client):
        resp = client.get("/api/v1/market/stats")
        body = resp.json()
        assert body["data"]["date_range_start"] is not None
        assert body["data"]["date_range_end"] is not None

    def test_stats_has_avg_price(self, client):
        resp = client.get("/api/v1/market/stats")
        body = resp.json()
        assert body["data"]["avg_price"] is not None

    def test_stats_envelope(self, client):
        resp = client.get("/api/v1/market/stats")
        body = resp.json()
        assert "data" in body
        assert "meta" in body
        assert "errors" in body
        assert "request_id" in body["meta"]


# ---------------------------------------------------------------------------
# Collect endpoints (mocked to avoid network calls)
# ---------------------------------------------------------------------------


class TestCollectBackfill:
    def test_backfill_returns_job(self, client):
        with patch("src.api.routers.collect.asyncio") as mock_asyncio:
            mock_asyncio.create_task = lambda coro: coro.close()
            resp = client.post(
                "/api/v1/collect/backfill",
                json={"set": "dmr"},
            )
        body = resp.json()
        assert resp.status_code == 200
        assert body["data"]["job_id"] is not None
        assert body["data"]["status"] == "started"
        assert "dmr" in body["data"]["message"]

    def test_backfill_envelope(self, client):
        with patch("src.api.routers.collect.asyncio") as mock_asyncio:
            mock_asyncio.create_task = lambda coro: coro.close()
            resp = client.post(
                "/api/v1/collect/backfill",
                json={"set": "dmr"},
            )
        body = resp.json()
        assert "data" in body
        assert "meta" in body
        assert "errors" in body
        assert "request_id" in body["meta"]


class TestCollectUpdate:
    def test_update_returns_job(self, client):
        with patch("src.api.routers.collect.asyncio") as mock_asyncio:
            mock_asyncio.create_task = lambda coro: coro.close()
            resp = client.post(
                "/api/v1/collect/update",
                json={},
            )
        body = resp.json()
        assert resp.status_code == 200
        assert body["data"]["job_id"] is not None
        assert body["data"]["status"] == "started"

    def test_update_envelope(self, client):
        with patch("src.api.routers.collect.asyncio") as mock_asyncio:
            mock_asyncio.create_task = lambda coro: coro.close()
            resp = client.post(
                "/api/v1/collect/update",
                json={},
            )
        body = resp.json()
        assert "data" in body
        assert "meta" in body
        assert "errors" in body
        assert "request_id" in body["meta"]


# ---------------------------------------------------------------------------
# Envelope structure validation
# ---------------------------------------------------------------------------


class TestEnvelopeConsistency:
    """Verify all endpoints return consistent envelope structure."""

    def test_all_get_endpoints_have_envelope(self, client):
        list_resp = client.get("/api/v1/cards")
        card_id = list_resp.json()["data"][0]["id"]

        endpoints = [
            "/api/v1/cards",
            f"/api/v1/cards/{card_id}",
            f"/api/v1/cards/{card_id}/history",
            "/api/v1/sets",
            "/api/v1/market/movers",
            "/api/v1/market/stats",
        ]

        for endpoint in endpoints:
            resp = client.get(endpoint)
            body = resp.json()
            assert "data" in body, f"{endpoint} missing 'data'"
            assert "meta" in body, f"{endpoint} missing 'meta'"
            assert "errors" in body, f"{endpoint} missing 'errors'"
            assert "request_id" in body["meta"], f"{endpoint} missing 'request_id'"

    def test_error_responses_have_envelope(self, client):
        resp = client.get("/api/v1/cards/99999")
        body = resp.json()
        assert "data" in body
        assert "meta" in body
        assert "errors" in body
        assert body["data"] is None
        assert len(body["errors"]) > 0

    def test_request_id_in_header(self, client):
        resp = client.get("/api/v1/cards")
        assert "x-request-id" in resp.headers
