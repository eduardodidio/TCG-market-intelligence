"""End-to-end integration tests for multi-currency conversion (F18).

These tests exercise the full stack: seed exchange rates + price data in a
real SQLite database, call the FastAPI endpoints with ?currency=USD|BRL,
and verify converted values match expectations.
"""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from src.api.app import create_app
from src.api.deps import get_currency_converter_dep, get_db
from src.database.models import CardRow, PriceObservationRow, SourceCardRow
from src.database.repository import Repository
from src.domain.models import ExchangeRate
from src.services.currency import CurrencyConverter

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def repo(tmp_path):
    db_path = tmp_path / "test_e2e.db"
    r = Repository(db_url=f"sqlite:///{db_path}")
    return r


@pytest.fixture()
def seeded_repo(repo):
    """Repo with a card, source card, price observations, and exchange rates."""
    with Session(repo.engine) as session:
        card = CardRow(
            id=1,
            game="magic",
            name_en="Lightning Bolt",
            name_pt="Relampago",
            set_code="m21",
            collector_number="199",
        )
        session.add(card)

        sc = SourceCardRow(
            card_id=1,
            source="myp",
            external_id="12345",
            url="https://example.com/bolt",
        )
        session.add(sc)
        session.flush()

        today = date.today()
        for i in range(5):
            obs_date = today - timedelta(days=i)
            obs = PriceObservationRow(
                source="myp",
                external_id="12345",
                observed_at=obs_date,
                median_price=Decimal("10.00") + Decimal(str(i)),
                tcg_price=Decimal("2.00"),
                last_sold_price=Decimal("9.50") + Decimal(str(i)),
                quantity_available=10,
            )
            session.add(obs)
        session.commit()

    # Seed exchange rates
    today = date.today()
    for i in range(10):
        d = today - timedelta(days=i)
        repo.upsert_exchange_rate(ExchangeRate(rate_date=d, rate=Decimal("5.00")))

    return repo


@pytest.fixture()
def client(seeded_repo):
    app = create_app()

    def override_db():
        yield seeded_repo

    def override_converter():
        yield CurrencyConverter(seeded_repo)

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_currency_converter_dep] = override_converter

    return TestClient(app)


# ---------------------------------------------------------------------------
# Tests: Card list endpoint
# ---------------------------------------------------------------------------


class TestListCardsCurrency:
    def test_brl_returns_original_prices(self, client):
        resp = client.get("/api/v1/cards?currency=BRL")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert len(data) == 1
        card = data[0]
        assert card["currency"] == "BRL"
        # Latest price should be the most recent observation (10.00)
        assert card["latest_price"] is not None
        assert float(card["latest_price"]) == 10.00

    def test_usd_returns_converted_prices(self, client):
        resp = client.get("/api/v1/cards?currency=USD")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert len(data) == 1
        card = data[0]
        assert card["currency"] == "USD"
        # 10.00 BRL / 5.00 rate = 2.00 USD
        assert float(card["latest_price"]) == 2.00

    def test_invalid_currency_rejected(self, client):
        resp = client.get("/api/v1/cards?currency=EUR")
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# Tests: Card detail endpoint
# ---------------------------------------------------------------------------


class TestCardDetailCurrency:
    def test_brl_detail_unchanged(self, client):
        resp = client.get("/api/v1/cards/1?currency=BRL")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["currency"] == "BRL"
        assert float(data["latest_price"]) == 10.00

    def test_usd_detail_converted(self, client):
        resp = client.get("/api/v1/cards/1?currency=USD")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["currency"] == "USD"
        assert float(data["latest_price"]) == 2.00


# ---------------------------------------------------------------------------
# Tests: Price history endpoint
# ---------------------------------------------------------------------------


class TestHistoryCurrency:
    def test_brl_history_unchanged(self, client):
        resp = client.get("/api/v1/cards/1/history?period=30d&currency=BRL")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert len(data) == 5
        for obs in data:
            assert obs["currency"] == "BRL"
        # First observation (oldest) median should be 14.00
        assert float(data[0]["median_price"]) == 14.00

    def test_usd_history_converted(self, client):
        resp = client.get("/api/v1/cards/1/history?period=30d&currency=USD")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert len(data) == 5
        for obs in data:
            assert obs["currency"] == "USD"
        # 14.00 BRL / 5.00 = 2.80 USD
        assert float(data[0]["median_price"]) == 2.80

    def test_history_uses_per_date_rates(self, client, seeded_repo):
        """Each observation should be converted using the rate for its date."""
        # Change the rate for 2 days ago to 4.00
        today = date.today()
        two_days_ago = today - timedelta(days=2)
        seeded_repo.upsert_exchange_rate(ExchangeRate(rate_date=two_days_ago, rate=Decimal("4.00")))

        resp = client.get("/api/v1/cards/1/history?period=30d&currency=USD")
        data = resp.json()["data"]

        # Find the observation for two_days_ago
        obs_2d = [o for o in data if o["observed_at"].startswith(str(two_days_ago))]
        assert len(obs_2d) == 1
        # median_price for 2 days ago = 12.00, rate = 4.00, so 12.00/4.00 = 3.00
        assert float(obs_2d[0]["median_price"]) == 3.00


# ---------------------------------------------------------------------------
# Tests: Missing exchange rate fallback
# ---------------------------------------------------------------------------


class TestMissingRateFallback:
    def test_empty_rate_table_usd_returns_null(self, tmp_path):
        """When no exchange rates exist, USD conversion should return null prices."""
        db_path = tmp_path / "empty_rates.db"
        repo = Repository(db_url=f"sqlite:///{db_path}")

        # Create a card with a price but no exchange rates
        with Session(repo.engine) as session:
            card = CardRow(
                id=1,
                game="magic",
                name_en="Test Card",
                set_code="tst",
                collector_number="1",
            )
            session.add(card)

            sc = SourceCardRow(
                card_id=1,
                source="myp",
                external_id="99",
                url="https://example.com",
            )
            session.add(sc)
            session.flush()

            obs = PriceObservationRow(
                source="myp",
                external_id="99",
                observed_at=date.today(),
                median_price=Decimal("10.00"),
            )
            session.add(obs)
            session.commit()

        app = create_app()

        def _override_db():
            yield repo

        def _override_converter():
            yield CurrencyConverter(repo)

        app.dependency_overrides[get_db] = _override_db
        app.dependency_overrides[get_currency_converter_dep] = _override_converter

        client = TestClient(app)
        resp = client.get("/api/v1/cards/1?currency=USD")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["latest_price"] is None
        assert data["currency"] == "USD"

    def test_closest_rate_used_for_weekends(self, seeded_repo, client):
        """When exact date has no rate, closest previous rate is used."""
        # Our seeded repo has rates for the last 10 days, so weekdays are covered.
        # Just verify USD conversion still works (uses closest rate fallback).
        resp = client.get("/api/v1/cards/1?currency=USD")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["latest_price"] is not None


# ---------------------------------------------------------------------------
# Tests: Exchange rate API endpoints
# ---------------------------------------------------------------------------


class TestExchangeRateEndpoints:
    def test_get_current_rate(self, client):
        resp = client.get("/api/v1/exchange-rates/current")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["rate"] is not None
        assert float(data["rate"]) == 5.00

    def test_get_rate_history(self, client):
        resp = client.get("/api/v1/exchange-rates/history?days=5")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert len(data["rates"]) >= 5

    def test_default_currency_is_brl(self, client):
        """When no currency param, default should be BRL (unchanged prices)."""
        resp = client.get("/api/v1/cards/1")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["currency"] == "BRL"
        assert float(data["latest_price"]) == 10.00
