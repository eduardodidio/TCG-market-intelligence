"""Tests for trending API collection_only parameter -- F90-T03."""

from __future__ import annotations

from datetime import datetime
from unittest.mock import MagicMock

from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.api.deps import get_optional_user
from src.api.routers.market import get_trending_service, router
from src.api.schemas.trending import TrendingCardEntry, TrendingResponse
from src.domain.models import User
from src.services.trending import TrendingService


def _make_app(
    service_mock: TrendingService | None = None,
    user: User | None = None,
) -> FastAPI:
    test_app = FastAPI()
    test_app.include_router(router, prefix="/api/v1")

    if service_mock:
        test_app.dependency_overrides[get_trending_service] = lambda: service_mock
    test_app.dependency_overrides[get_optional_user] = lambda: user
    return test_app


def _mock_response(direction: str = "up") -> TrendingResponse:
    return TrendingResponse(
        cards=[
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
        ],
        period="30d",
        direction=direction,
        computed_at=datetime(2026, 8, 29, 12, 0),
        cached=False,
    )


def _user(uid: int = 42) -> User:
    return User(id=uid, email="test@example.com")


class TestCollectionOnlyGainers:
    def test_collection_only_with_auth_passes_user_id(self) -> None:
        service = MagicMock(spec=TrendingService)
        service.get_trending.return_value = _mock_response("up")
        user = _user(42)

        app = _make_app(service, user)
        client = TestClient(app)
        resp = client.get("/api/v1/market/trending/gainers?collection_only=true")
        assert resp.status_code == 200

        call_kwargs = service.get_trending.call_args
        assert call_kwargs.kwargs.get("user_id") == 42

    def test_collection_only_without_auth_ignores_flag(self) -> None:
        service = MagicMock(spec=TrendingService)
        service.get_trending.return_value = _mock_response("up")

        app = _make_app(service, user=None)
        client = TestClient(app)
        resp = client.get("/api/v1/market/trending/gainers?collection_only=true")
        assert resp.status_code == 200

        call_kwargs = service.get_trending.call_args
        assert call_kwargs.kwargs.get("user_id") is None

    def test_no_collection_only_with_auth_no_user_id(self) -> None:
        service = MagicMock(spec=TrendingService)
        service.get_trending.return_value = _mock_response("up")
        user = _user(42)

        app = _make_app(service, user)
        client = TestClient(app)
        resp = client.get("/api/v1/market/trending/gainers")
        assert resp.status_code == 200

        call_kwargs = service.get_trending.call_args
        assert call_kwargs.kwargs.get("user_id") is None

    def test_collection_only_false_with_auth_no_user_id(self) -> None:
        service = MagicMock(spec=TrendingService)
        service.get_trending.return_value = _mock_response("up")
        user = _user(42)

        app = _make_app(service, user)
        client = TestClient(app)
        resp = client.get("/api/v1/market/trending/gainers?collection_only=false")
        assert resp.status_code == 200

        call_kwargs = service.get_trending.call_args
        assert call_kwargs.kwargs.get("user_id") is None


class TestCollectionOnlyLosers:
    def test_collection_only_with_auth_passes_user_id(self) -> None:
        service = MagicMock(spec=TrendingService)
        service.get_trending.return_value = _mock_response("down")
        user = _user(42)

        app = _make_app(service, user)
        client = TestClient(app)
        resp = client.get("/api/v1/market/trending/losers?collection_only=true")
        assert resp.status_code == 200

        call_kwargs = service.get_trending.call_args
        assert call_kwargs.kwargs.get("user_id") == 42

    def test_collection_only_without_auth_returns_global(self) -> None:
        service = MagicMock(spec=TrendingService)
        service.get_trending.return_value = _mock_response("down")

        app = _make_app(service, user=None)
        client = TestClient(app)
        resp = client.get("/api/v1/market/trending/losers?collection_only=true")
        assert resp.status_code == 200

        call_kwargs = service.get_trending.call_args
        assert call_kwargs.kwargs.get("user_id") is None
