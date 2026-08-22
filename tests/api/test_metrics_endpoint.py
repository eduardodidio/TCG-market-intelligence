"""Tests for GET /collection/{entry_id}/metrics endpoint — F34."""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import MagicMock

from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.api.deps import get_currency_converter_dep, get_db, require_auth_or_api_key
from src.api.routers.collection import router
from src.database.models import PriceObservationRow, SourceCardRow, UserCollectionRow

_TEST_USER_ID = "eduardo"


def _make_collection_row(**overrides) -> MagicMock:
    defaults = {
        "id": 1,
        "user_id": "eduardo",
        "card_id": 42,
        "set_code": "DMR",
        "collector_number": "123",
        "name_en": "Lightning Bolt",
        "name_pt": "Raio",
        "set_name_en": "Dominaria Remastered",
        "quantity": 2,
        "quality": "NM",
        "language": "EN",
        "rarity": "R",
        "color": "R",
        "extras": None,
        "created_at": date(2026, 1, 1),
    }
    defaults.update(overrides)
    row = MagicMock(spec=UserCollectionRow)
    for k, v in defaults.items():
        setattr(row, k, v)
    return row


def _make_source_card(**overrides) -> MagicMock:
    defaults = {
        "id": 10,
        "source": "myp",
        "external_id": "99999",
        "card_id": 42,
        "sku": "magic_dmr_123",
        "url": "https://mypcards.com/magic/99999/lightning-bolt",
        "name_en": "Lightning Bolt",
        "name_pt": "Raio",
        "set_code": "DMR",
        "collector_number": "123",
    }
    defaults.update(overrides)
    sc = MagicMock(spec=SourceCardRow)
    for k, v in defaults.items():
        setattr(sc, k, v)
    return sc


def _make_price_obs(d: date, price: Decimal, **overrides) -> MagicMock:
    defaults = {
        "id": 100,
        "source": "myp",
        "external_id": "99999",
        "observed_at": d,
        "median_price": price,
        "tcg_price": None,
        "last_sold_price": None,
        "quantity_available": 5,
        "last_sold_meta": None,
        "currency": "BRL",
    }
    defaults.update(overrides)
    obs = MagicMock(spec=PriceObservationRow)
    for k, v in defaults.items():
        setattr(obs, k, v)
    return obs


def _make_converter():
    """Create a mock converter that passes BRL through unchanged."""
    converter = MagicMock()
    converter.convert.side_effect = lambda val, d, curr: (
        val
        if curr in ("BRL", "PILA")
        else ((val / Decimal("5.50")).quantize(Decimal("0.01")) if val is not None else None)
    )
    return converter


def _make_app(
    mock_repo: MagicMock,
    user_id: str = _TEST_USER_ID,
    converter=None,
) -> FastAPI:
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_db] = lambda: mock_repo
    app.dependency_overrides[require_auth_or_api_key] = lambda: user_id
    if converter:
        app.dependency_overrides[get_currency_converter_dep] = lambda: converter
    else:
        app.dependency_overrides[get_currency_converter_dep] = _make_converter
    return app


def _setup_with_prices(n_days: int = 30):
    """Setup mock repo with n_days of price data."""
    mock_repo = MagicMock()
    mock_repo.get_collection_entry.return_value = _make_collection_row()
    mock_repo.get_source_cards_for_card.return_value = [_make_source_card()]

    today = date.today()
    prices = [
        _make_price_obs(today - timedelta(days=n_days - i), Decimal("10") + Decimal(str(i)))
        for i in range(n_days)
    ]
    mock_repo.get_price_series.return_value = prices

    return mock_repo


class TestGetCardMetrics:
    def test_returns_200_with_valid_data(self) -> None:
        mock_repo = _setup_with_prices(30)
        app = _make_app(mock_repo)
        client = TestClient(app)

        resp = client.get("/collection/1/metrics?period=30d")
        assert resp.status_code == 200

        data = resp.json()["data"]
        assert data["entry_id"] == 1
        assert data["card_id"] == 42
        assert data["period"] == "30d"
        assert data["currency"] == "BRL"
        assert data["data_points"] == 30

    def test_contains_all_metric_fields(self) -> None:
        mock_repo = _setup_with_prices(60)
        app = _make_app(mock_repo)
        client = TestClient(app)

        resp = client.get("/collection/1/metrics?period=30d")
        data = resp.json()["data"]

        assert "moving_averages" in data
        assert "extremes" in data
        assert "volatility" in data
        assert "momentum" in data
        assert "performance" in data
        assert "period_comparison" in data

    def test_extremes_populated(self) -> None:
        mock_repo = _setup_with_prices(30)
        app = _make_app(mock_repo)
        client = TestClient(app)

        resp = client.get("/collection/1/metrics?period=30d")
        data = resp.json()["data"]

        assert data["extremes"] is not None
        assert "ath_price" in data["extremes"]
        assert "atl_price" in data["extremes"]
        assert "ath_date" in data["extremes"]
        assert "atl_date" in data["extremes"]

    def test_momentum_populated(self) -> None:
        mock_repo = _setup_with_prices(30)
        app = _make_app(mock_repo)
        client = TestClient(app)

        resp = client.get("/collection/1/metrics?period=30d")
        data = resp.json()["data"]

        assert data["momentum"] is not None
        assert "rate_of_change" in data["momentum"]
        assert "trend_direction" in data["momentum"]

    def test_null_fields_when_insufficient_data(self) -> None:
        mock_repo = MagicMock()
        mock_repo.get_collection_entry.return_value = _make_collection_row()
        mock_repo.get_source_cards_for_card.return_value = [_make_source_card()]

        today = date.today()
        # Only 1 price point
        mock_repo.get_price_series.return_value = [
            _make_price_obs(today, Decimal("10")),
        ]

        app = _make_app(mock_repo)
        client = TestClient(app)

        resp = client.get("/collection/1/metrics?period=30d")
        assert resp.status_code == 200

        data = resp.json()["data"]
        assert data["volatility"] is None
        assert data["momentum"] is None
        assert data["performance"] is None

    def test_404_for_nonexistent_entry(self) -> None:
        mock_repo = MagicMock()
        mock_repo.get_collection_entry.return_value = None

        app = _make_app(mock_repo)
        client = TestClient(app)

        resp = client.get("/collection/999/metrics")
        assert resp.status_code == 404

    def test_404_for_other_users_entry(self) -> None:
        mock_repo = MagicMock()
        mock_repo.get_collection_entry.return_value = _make_collection_row(user_id="other_user")

        app = _make_app(mock_repo)
        client = TestClient(app)

        resp = client.get("/collection/1/metrics")
        assert resp.status_code == 404

    def test_422_when_card_not_linked(self) -> None:
        mock_repo = MagicMock()
        mock_repo.get_collection_entry.return_value = _make_collection_row(card_id=None)

        app = _make_app(mock_repo)
        client = TestClient(app)

        resp = client.get("/collection/1/metrics")
        assert resp.status_code == 422

    def test_invalid_period_returns_422(self) -> None:
        mock_repo = _setup_with_prices(30)
        app = _make_app(mock_repo)
        client = TestClient(app)

        resp = client.get("/collection/1/metrics?period=invalid")
        assert resp.status_code == 422

    def test_different_periods(self) -> None:
        mock_repo = _setup_with_prices(60)
        app = _make_app(mock_repo)
        client = TestClient(app)

        resp_7d = client.get("/collection/1/metrics?period=7d")
        resp_90d = client.get("/collection/1/metrics?period=90d")

        assert resp_7d.status_code == 200
        assert resp_90d.status_code == 200

        data_7d = resp_7d.json()["data"]
        data_90d = resp_90d.json()["data"]
        assert data_7d["period"] == "7d"
        assert data_90d["period"] == "90d"

    def test_all_valid_periods(self) -> None:
        mock_repo = _setup_with_prices(30)
        app = _make_app(mock_repo)
        client = TestClient(app)

        for period in ("24h", "7d", "30d", "90d", "180d", "1y"):
            resp = client.get(f"/collection/1/metrics?period={period}")
            assert resp.status_code == 200, f"Period {period} failed"

    def test_empty_source_cards_returns_empty_metrics(self) -> None:
        mock_repo = MagicMock()
        mock_repo.get_collection_entry.return_value = _make_collection_row()
        mock_repo.get_source_cards_for_card.return_value = []

        app = _make_app(mock_repo)
        client = TestClient(app)

        resp = client.get("/collection/1/metrics?period=30d")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["data_points"] == 0

    def test_follows_api_response_envelope(self) -> None:
        mock_repo = _setup_with_prices(30)
        app = _make_app(mock_repo)
        client = TestClient(app)

        resp = client.get("/collection/1/metrics?period=30d")
        body = resp.json()
        assert "data" in body
        assert "meta" in body
        assert "errors" in body
