"""Tests for the trending API endpoints (F36)."""

from __future__ import annotations

from datetime import datetime
from unittest.mock import MagicMock

from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.api.routers.market import get_trending_service, router
from src.api.schemas.trending import TrendingCardEntry, TrendingResponse
from src.services.trending import TrendingService


def _make_app(service_mock: TrendingService | None = None) -> FastAPI:
    """Create a fresh FastAPI app with the market router."""
    test_app = FastAPI()
    test_app.include_router(router, prefix="/api/v1")

    if service_mock:
        test_app.dependency_overrides[get_trending_service] = lambda: service_mock
    return test_app


def _mock_trending_response(
    direction: str = "up",
    cards: list[TrendingCardEntry] | None = None,
) -> TrendingResponse:
    if cards is None:
        cards = [
            TrendingCardEntry(
                card_id=1,
                name_en="Lightning Bolt",
                name_pt="Raio",
                set_code="lea",
                collector_number="161",
                image_url="https://api.scryfall.com/cards/lea/161?format=image&version=normal",
                price_start=10.0,
                price_end=15.0,
                change_pct=50.0,
                change_abs=5.0,
                consistency=0.9,
                composite_score=75.0,
                observation_count=5,
                currency="BRL",
            )
        ]
    return TrendingResponse(
        cards=cards,
        period="30d",
        direction=direction,
        computed_at=datetime(2026, 8, 22, 12, 0),
        cached=False,
    )


class TestGetTrendingGainers:
    def test_returns_200(self) -> None:
        service = MagicMock(spec=TrendingService)
        service.get_trending.return_value = _mock_trending_response("up")

        app = _make_app(service)
        client = TestClient(app)
        resp = client.get("/api/v1/market/trending/gainers")
        assert resp.status_code == 200

        data = resp.json()["data"]
        assert data["direction"] == "up"
        assert len(data["cards"]) == 1
        assert data["cards"][0]["name_en"] == "Lightning Bolt"

    def test_default_period_30d(self) -> None:
        service = MagicMock(spec=TrendingService)
        service.get_trending.return_value = _mock_trending_response("up")

        app = _make_app(service)
        client = TestClient(app)
        client.get("/api/v1/market/trending/gainers")

        service.get_trending.assert_called_once()
        call_args = service.get_trending.call_args
        assert call_args[0][1] == 30  # period_days

    def test_invalid_period_returns_422(self) -> None:
        service = MagicMock(spec=TrendingService)
        app = _make_app(service)
        client = TestClient(app)
        resp = client.get("/api/v1/market/trending/gainers?period=999d")
        assert resp.status_code == 422

    def test_limit_param(self) -> None:
        service = MagicMock(spec=TrendingService)
        service.get_trending.return_value = _mock_trending_response("up")

        app = _make_app(service)
        client = TestClient(app)
        client.get("/api/v1/market/trending/gainers?limit=5")

        call_args = service.get_trending.call_args
        assert call_args[0][2] == 5  # limit

    def test_currency_param(self) -> None:
        service = MagicMock(spec=TrendingService)
        service.get_trending.return_value = _mock_trending_response("up")

        app = _make_app(service)
        client = TestClient(app)
        client.get("/api/v1/market/trending/gainers?currency=USD")

        call_args = service.get_trending.call_args
        assert call_args[0][4] == "USD"  # currency


class TestGetTrendingLosers:
    def test_returns_200_down_direction(self) -> None:
        service = MagicMock(spec=TrendingService)
        service.get_trending.return_value = _mock_trending_response("down")

        app = _make_app(service)
        client = TestClient(app)
        resp = client.get("/api/v1/market/trending/losers")
        assert resp.status_code == 200

        data = resp.json()["data"]
        assert data["direction"] == "down"

    def test_invalid_period_returns_422(self) -> None:
        service = MagicMock(spec=TrendingService)
        app = _make_app(service)
        client = TestClient(app)
        resp = client.get("/api/v1/market/trending/losers?period=bad")
        assert resp.status_code == 422

    def test_empty_cards_list(self) -> None:
        service = MagicMock(spec=TrendingService)
        service.get_trending.return_value = _mock_trending_response("down", cards=[])

        app = _make_app(service)
        client = TestClient(app)
        resp = client.get("/api/v1/market/trending/losers")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["cards"] == []
