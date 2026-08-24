"""Integration tests for market router with MarketDataService (F44-T07)."""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from src.api.deps import get_currency_converter_dep, get_db, get_market_data_service
from src.api.routers.market import router
from src.database.models import (
    CardRow,
    PriceObservationRow,
    SourceCardRow,
)
from src.database.repository import Repository
from src.services.currency import CurrencyConverter
from src.services.market_data import MarketDataService


@pytest.fixture()
def repo(tmp_path):
    db_path = tmp_path / "test.db"
    return Repository(db_url=f"sqlite:///{db_path}")


def _make_client(repo, cache_ttl=300):
    """Create a TestClient with MarketDataService wired."""
    from src.services.aggregate_cache import AggregateCache

    app = FastAPI()
    app.include_router(router)

    converter = CurrencyConverter(repo)
    cache = AggregateCache(default_ttl=cache_ttl)
    service = MarketDataService(repo, converter, cache)

    app.dependency_overrides[get_market_data_service] = lambda: service
    app.dependency_overrides[get_db] = lambda: repo
    app.dependency_overrides[get_currency_converter_dep] = lambda: converter

    return TestClient(app), service


@pytest.fixture()
def client(repo):
    client, _ = _make_client(repo)
    return client


def _seed_movers(repo):
    today = date.today()
    with Session(repo.engine) as session:
        c1 = CardRow(game="magic", name_en="Gainer", set_code="S1", collector_number="1")
        c2 = CardRow(game="magic", name_en="Loser", set_code="S1", collector_number="2")
        session.add_all([c1, c2])
        session.flush()
        sc1 = SourceCardRow(
            source="myp", external_id="g1", card_id=c1.id, url="u1", name_en="Gainer"
        )
        sc2 = SourceCardRow(
            source="myp", external_id="l1", card_id=c2.id, url="u2", name_en="Loser"
        )
        session.add_all([sc1, sc2])
        session.flush()
        session.add_all(
            [
                PriceObservationRow(
                    source="myp",
                    external_id="g1",
                    observed_at=today - timedelta(days=10),
                    median_price=Decimal("10.00"),
                    currency="BRL",
                ),
                PriceObservationRow(
                    source="myp",
                    external_id="g1",
                    observed_at=today,
                    median_price=Decimal("20.00"),
                    currency="BRL",
                ),
                PriceObservationRow(
                    source="myp",
                    external_id="l1",
                    observed_at=today - timedelta(days=10),
                    median_price=Decimal("20.00"),
                    currency="BRL",
                ),
                PriceObservationRow(
                    source="myp",
                    external_id="l1",
                    observed_at=today,
                    median_price=Decimal("10.00"),
                    currency="BRL",
                ),
            ]
        )
        session.commit()


def _seed_stats(repo):
    with Session(repo.engine) as session:
        c1 = CardRow(game="magic", name_en="A", set_code="S1", collector_number="1")
        session.add(c1)
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
            ]
        )
        session.commit()


class TestMoversViaService:
    def test_returns_same_shape_as_before(self, client, repo):
        _seed_movers(repo)
        resp = client.get("/market/movers?period=30d")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert "gainers" in data
        assert "losers" in data
        for g in data["gainers"]:
            assert "card_id" in g
            assert "name_en" in g
            assert "price_start" in g
            assert "price_end" in g
            assert "change_pct" in g
            assert "currency" in g

    def test_movers_uses_cache_on_second_call(self, repo):
        _seed_movers(repo)
        client, service = _make_client(repo)

        resp1 = client.get("/market/movers?period=30d")
        assert resp1.status_code == 200

        # Cache should be populated
        stats = service._cache.stats()
        assert stats["size"] >= 1

        resp2 = client.get("/market/movers?period=30d")
        assert resp2.status_code == 200

        # Should have cache hits
        stats2 = service._cache.stats()
        assert stats2["hits"] >= 1


class TestStatsViaService:
    def test_returns_same_shape_as_before(self, client, repo):
        _seed_stats(repo)
        resp = client.get("/market/stats")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert "total_cards" in data
        assert "total_observations" in data
        assert "avg_price" in data
        assert "currency" in data

    def test_stats_uses_cache_on_second_call(self, repo):
        _seed_stats(repo)
        client, service = _make_client(repo)

        client.get("/market/stats")
        stats1 = service._cache.stats()

        client.get("/market/stats")
        stats2 = service._cache.stats()

        assert stats2["hits"] > stats1["hits"]


class TestCacheInvalidation:
    def test_invalidation_refreshes_data(self, repo):
        _seed_movers(repo)
        client, service = _make_client(repo)

        # First call populates cache
        resp1 = client.get("/market/movers?period=30d")
        assert resp1.status_code == 200

        # Invalidate
        service.invalidate_cards([1, 2])

        # Cache should be cleared
        assert service._cache.get("movers:30d:10") is None


class TestCurrencyFallback:
    def test_fallback_when_no_exchange_rate(self, client, repo):
        _seed_movers(repo)
        resp = client.get("/market/movers?period=30d&currency=USD")
        assert resp.status_code == 200
        data = resp.json()["data"]
        for g in data["gainers"]:
            assert g["currency"] == "BRL"
