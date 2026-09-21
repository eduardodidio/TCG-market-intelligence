"""Tests for trending/movers error resilience (F165-T04).

Verifies that TrendingService and market router endpoints gracefully handle
database errors, returning empty results instead of 500s.
"""

from __future__ import annotations

from unittest.mock import MagicMock

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.exc import InternalError, OperationalError

from src.api.deps import get_currency_converter_dep, get_db, get_optional_user
from src.api.routers.market import get_trending_service, router
from src.api.schemas.trending import TrendingResponse
from src.services.currency import CurrencyConverter
from src.services.trending import TrendingService

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _mock_converter() -> MagicMock:
    conv = MagicMock(spec=CurrencyConverter)
    conv.convert.return_value = None
    conv.get_display_rate.return_value = None
    return conv


def _make_service(mock_repo: MagicMock | None = None) -> TrendingService:
    repo = mock_repo or MagicMock()
    return TrendingService(repo)


def _make_app(
    *,
    mock_repo: MagicMock | None = None,
    mock_trending: TrendingService | None = None,
    user_id: str | None = None,
) -> FastAPI:
    """Build a minimal FastAPI app with the market router and overrides."""
    app = FastAPI()
    app.include_router(router)

    repo = mock_repo or MagicMock()
    converter = _mock_converter()

    app.dependency_overrides[get_db] = lambda: repo
    app.dependency_overrides[get_currency_converter_dep] = lambda: converter

    if mock_trending is not None:
        app.dependency_overrides[get_trending_service] = lambda: mock_trending

    if user_id is not None:
        from src.domain.models import User

        fake_user = MagicMock(spec=User)
        fake_user.id = int(user_id)
        app.dependency_overrides[get_optional_user] = lambda: fake_user
    else:
        app.dependency_overrides[get_optional_user] = lambda: None

    return app


# =========================================================================
# Group 1: TrendingService unit tests (mock repo)
# =========================================================================


class TestTrendingServiceErrorResilience:
    """TrendingService.get_trending catches DB/runtime errors gracefully."""

    def test_trending_service_catches_operational_error(self) -> None:
        mock_repo = MagicMock()
        mock_repo.get_trending_price_data.side_effect = OperationalError("timeout", {}, None)
        mock_repo.get_card_info_batch.return_value = {}

        service = _make_service(mock_repo)
        converter = _mock_converter()

        result = service.get_trending("up", 30, 10, converter, "BRL")

        assert isinstance(result, TrendingResponse)
        assert result.cards == []

    def test_trending_service_catches_internal_error(self) -> None:
        mock_repo = MagicMock()
        mock_repo.get_trending_price_data.side_effect = InternalError("timeout", {}, None)
        mock_repo.get_card_info_batch.return_value = {}

        service = _make_service(mock_repo)
        converter = _mock_converter()

        result = service.get_trending("up", 30, 10, converter, "BRL")

        assert isinstance(result, TrendingResponse)
        assert result.cards == []

    def test_trending_service_catches_generic_exception(self) -> None:
        mock_repo = MagicMock()
        mock_repo.get_trending_price_data.side_effect = RuntimeError("connection reset")
        mock_repo.get_card_info_batch.return_value = {}

        service = _make_service(mock_repo)
        converter = _mock_converter()

        result = service.get_trending("up", 30, 10, converter, "BRL")

        assert isinstance(result, TrendingResponse)
        assert result.cards == []

    def test_trending_service_catches_user_query_exception(self) -> None:
        mock_repo = MagicMock()
        mock_repo.get_trending_price_data_for_user.side_effect = Exception("timeout")
        mock_repo.get_card_info_batch.return_value = {}

        service = _make_service(mock_repo)
        converter = _mock_converter()

        result = service.get_trending("up", 30, 10, converter, "BRL", user_id=1)

        assert isinstance(result, TrendingResponse)
        assert result.cards == []


# =========================================================================
# Group 2: Market router integration tests (TestClient + mocked service)
# =========================================================================


class TestMarketRouterErrorResilience:
    """Market router endpoints return 200 with empty data on service errors."""

    def test_trending_gainers_returns_200_on_service_error(self) -> None:
        mock_trending = MagicMock(spec=TrendingService)
        mock_trending.get_trending.side_effect = RuntimeError("db gone")

        app = _make_app(mock_trending=mock_trending)
        client = TestClient(app)

        resp = client.get("/market/trending/gainers?period=30d&currency=BRL")

        assert resp.status_code == 200
        body = resp.json()
        assert body["data"]["cards"] == []

    def test_trending_losers_returns_200_on_service_error(self) -> None:
        mock_trending = MagicMock(spec=TrendingService)
        mock_trending.get_trending.side_effect = RuntimeError("db gone")

        app = _make_app(mock_trending=mock_trending)
        client = TestClient(app)

        resp = client.get("/market/trending/losers?period=30d&currency=BRL")

        assert resp.status_code == 200
        body = resp.json()
        assert body["data"]["cards"] == []

    def test_trending_gainers_collection_only_returns_200_on_error(self) -> None:
        mock_trending = MagicMock(spec=TrendingService)
        mock_trending.get_trending.side_effect = RuntimeError("db gone")

        app = _make_app(mock_trending=mock_trending, user_id="1")
        client = TestClient(app)

        resp = client.get("/market/trending/gainers?period=30d&currency=BRL&collection_only=true")

        assert resp.status_code == 200
        body = resp.json()
        assert body["data"]["cards"] == []

    def test_volatile_returns_200_on_total_failure(self) -> None:
        mock_trending = MagicMock(spec=TrendingService)
        mock_trending.get_trending.side_effect = RuntimeError("db gone")

        mock_repo = MagicMock()
        mock_repo.get_movers.side_effect = RuntimeError("also broken")

        app = _make_app(mock_repo=mock_repo, mock_trending=mock_trending)
        client = TestClient(app)

        resp = client.get("/market/volatile?period=30d&currency=BRL")

        assert resp.status_code == 200
        body = resp.json()
        assert body["data"]["cards"] == []
