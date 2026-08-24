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
    ExchangeRateRow,
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


@pytest.fixture()
def client(repo):
    app = FastAPI()
    app.include_router(router)

    converter = CurrencyConverter(repo)
    service = MarketDataService(repo, converter)

    app.dependency_overrides[get_market_data_service] = lambda: service
    # Keep overrides for trending endpoints which still use get_db/converter
    app.dependency_overrides[get_db] = lambda: repo
    app.dependency_overrides[get_currency_converter_dep] = lambda: converter
    return TestClient(app)


def _seed_movers_data(repo):
    """Seed cards with price changes for movers tests."""
    today = date.today()
    with Session(repo.engine) as session:
        # Card that went up: 10 -> 15 (+50%)
        c1 = CardRow(
            game="magic",
            name_en="Rising Star",
            name_pt="Estrela Ascendente",
            set_code="SET1",
            collector_number="1",
        )
        # Card that went down: 20 -> 10 (-50%)
        c2 = CardRow(
            game="magic",
            name_en="Falling Stone",
            name_pt="Pedra Cadente",
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

    def test_movers_usd_no_rate_falls_back_to_brl(self, client, repo):
        """When currency=USD but no exchange rate exists, response falls back to BRL."""
        _seed_movers_data(repo)
        resp = client.get("/market/movers?period=30d&currency=USD")
        assert resp.status_code == 200
        data = resp.json()["data"]
        # Should fall back to BRL since no exchange rate is seeded
        for g in data["gainers"]:
            assert g["currency"] == "BRL"
            assert g["price_start"] is not None
            assert g["price_end"] is not None
        for lo in data["losers"]:
            assert lo["currency"] == "BRL"

    def test_movers_usd_with_rate_converts(self, client, repo):
        """When currency=USD and exchange rate exists, prices are converted."""
        _seed_movers_data(repo)
        # Seed an exchange rate
        with Session(repo.engine) as session:
            session.add(
                ExchangeRateRow(
                    rate_date=date.today(),
                    from_currency="USD",
                    to_currency="BRL",
                    rate=Decimal("5.00"),
                    source="bcb_ptax",
                )
            )
            session.commit()
        resp = client.get("/market/movers?period=30d&currency=USD")
        assert resp.status_code == 200
        data = resp.json()["data"]
        for g in data["gainers"]:
            assert g["currency"] == "USD"
        # Rising Star: price_start was 10 BRL -> 2.00 USD at rate 5.00
        gainer = next(g for g in data["gainers"] if g["name_en"] == "Rising Star")
        assert float(gainer["price_start"]) == pytest.approx(2.00)
        assert float(gainer["price_end"]) == pytest.approx(3.00)

    def test_movers_include_name_pt(self, client, repo):
        """Movers response includes name_pt field from CardRow."""
        _seed_movers_data(repo)
        resp = client.get("/market/movers?period=30d")
        assert resp.status_code == 200
        data = resp.json()["data"]
        gainer = next(g for g in data["gainers"] if g["name_en"] == "Rising Star")
        assert gainer["name_pt"] == "Estrela Ascendente"
        loser = next(lo for lo in data["losers"] if lo["name_en"] == "Falling Stone")
        assert loser["name_pt"] == "Pedra Cadente"

    def test_movers_brl_always_works(self, client, repo):
        """BRL currency never falls back, prices are always present."""
        _seed_movers_data(repo)
        resp = client.get("/market/movers?period=30d&currency=BRL")
        assert resp.status_code == 200
        data = resp.json()["data"]
        for g in data["gainers"]:
            assert g["currency"] == "BRL"
            assert g["price_start"] is not None


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

    def test_stats_usd_no_rate_falls_back_to_brl(self, client, repo):
        """When currency=USD but no exchange rate exists, response falls back to BRL."""
        _seed_stats_data(repo)
        resp = client.get("/market/stats?currency=USD")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["currency"] == "BRL"
        assert data["avg_price"] is not None

    def test_stats_usd_with_rate_converts(self, client, repo):
        """When currency=USD and exchange rate exists, avg_price is converted."""
        _seed_stats_data(repo)
        with Session(repo.engine) as session:
            session.add(
                ExchangeRateRow(
                    rate_date=date.today(),
                    from_currency="USD",
                    to_currency="BRL",
                    rate=Decimal("5.00"),
                    source="bcb_ptax",
                )
            )
            session.commit()
        resp = client.get("/market/stats?currency=USD")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["currency"] == "USD"
        # avg_price was 20.00 BRL -> 4.00 USD at rate 5.00
        assert float(data["avg_price"]) == pytest.approx(4.00)
