"""Tests for F185-T02: Market endpoint sanity filters.

Verifies that /market/movers, /market/summary, and /market/volatile endpoints
respect the R$0.50 floor and +/-1000% cap filters applied by repo.get_movers().

These tests mock repo.get_movers() to return pre-filtered data (simulating the
T01 fix) and verify the endpoints propagate those filters correctly.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from unittest.mock import MagicMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.api.deps import get_currency_converter_dep, get_db, get_market_data_service
from src.api.routers.market import (
    _endpoint_cache,
    get_trending_service,
    router,
)
from src.api.schemas.market_data import MarketSummary, MoversResult
from src.api.schemas.trending import TrendingCardEntry, TrendingResponse
from src.database.repository import Repository
from src.services.aggregate_cache import AggregateCache
from src.services.currency import CurrencyConverter
from src.services.market_data import MarketDataService
from src.services.trending import TrendingService

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_app(
    *,
    market_service: MarketDataService | None = None,
    trending_service: TrendingService | None = None,
    repo: Repository | None = None,
    converter: CurrencyConverter | None = None,
) -> FastAPI:
    app = FastAPI()
    app.include_router(router, prefix="/api/v1")

    if market_service is not None:
        app.dependency_overrides[get_market_data_service] = lambda: market_service
    if trending_service is not None:
        app.dependency_overrides[get_trending_service] = lambda: trending_service
    if repo is not None:
        app.dependency_overrides[get_db] = lambda: repo
    if converter is not None:
        app.dependency_overrides[get_currency_converter_dep] = lambda: converter

    return app


def _mock_converter() -> CurrencyConverter:
    converter = MagicMock(spec=CurrencyConverter)
    converter.convert.side_effect = lambda v, d, c: (Decimal(str(v)) if v is not None else None)
    converter.get_display_rate.return_value = None
    return converter


def _mock_market_summary() -> MarketSummary:
    return MarketSummary(
        total_cards=100,
        total_observations=500,
        avg_price=Decimal("12.50"),
        date_range_start=None,
        date_range_end=None,
        currency="BRL",
        computed_at=datetime(2026, 9, 29, 12, 0),
    )


def _make_mover_tuple(
    card_id: int,
    name: str,
    price_start: str,
    price_end: str,
    change_pct: str,
) -> tuple:
    """Build a raw mover tuple as returned by repo.get_movers()."""
    return (
        card_id,
        name,
        name,
        "lea",
        Decimal(price_start),
        Decimal(price_end),
        Decimal(change_pct),
    )


def _trending_entry(**overrides) -> TrendingCardEntry:
    defaults = dict(
        card_id=1,
        name_en="Card A",
        name_pt="Carta A",
        set_code="lea",
        collector_number="1",
        image_url=None,
        price_start=10.0,
        price_end=15.0,
        change_pct=50.0,
        change_abs=5.0,
        consistency=0.5,
        composite_score=25.0,
        observation_count=5,
        currency="BRL",
    )
    defaults.update(overrides)
    return TrendingCardEntry(**defaults)


# ===========================================================================
# /market/movers — service delegates to repo.get_movers()
# ===========================================================================


class TestMoversEndpointFilters:
    """Verify /market/movers returns only filtered data from the service layer."""

    def setup_method(self) -> None:
        _endpoint_cache.clear()

    def test_service_delegates_to_repo_get_movers(self) -> None:
        """MarketDataService.get_top_movers() calls repo.get_movers() which
        applies the R$0.50 floor and 1000% cap (T01). Verify delegation."""
        mock_repo = MagicMock(spec=Repository)
        converter = _mock_converter()

        # Simulate T01-filtered data: only cards with price_start >= 0.50
        # and abs(change_pct) <= 1000
        mock_repo.get_movers.return_value = (
            [_make_mover_tuple(1, "Bolt", "5.00", "7.50", "50.00")],
            [_make_mover_tuple(2, "Ritual", "8.00", "6.00", "-25.00")],
        )

        cache = AggregateCache(default_ttl=0)  # no caching
        service = MarketDataService(mock_repo, converter, cache)
        result = service.get_top_movers(period="30d", limit=10, currency="BRL")

        assert isinstance(result, MoversResult)
        mock_repo.get_movers.assert_called_once_with(days=30, limit=10)
        assert len(result.gainers) == 1
        assert len(result.losers) == 1
        assert result.gainers[0].change_pct == Decimal("50.00")
        assert result.losers[0].change_pct == Decimal("-25.00")

    def test_movers_endpoint_no_extreme_percentages(self) -> None:
        """After T01 fix, no mover should have abs(change_pct) > 1000."""
        mock_repo = MagicMock(spec=Repository)
        converter = _mock_converter()

        # Only normal movers survive T01 filter
        mock_repo.get_movers.return_value = (
            [
                _make_mover_tuple(1, "Bolt", "5.00", "7.50", "50.00"),
                _make_mover_tuple(2, "Sol Ring", "100.00", "200.00", "100.00"),
            ],
            [
                _make_mover_tuple(3, "Ritual", "8.00", "6.00", "-25.00"),
            ],
        )

        cache = AggregateCache(default_ttl=0)
        service = MarketDataService(mock_repo, converter, cache)

        app = _make_app(market_service=service)
        client = TestClient(app)
        resp = client.get("/api/v1/market/movers?period=30d")

        assert resp.status_code == 200
        data = resp.json()["data"]

        for g in data["gainers"]:
            assert (
                abs(float(g["change_pct"])) <= 1000
            ), f"Gainer {g['name_en']} has change_pct={g['change_pct']} > 1000"
        for lo in data["losers"]:
            assert (
                abs(float(lo["change_pct"])) <= 1000
            ), f"Loser {lo['name_en']} has change_pct={lo['change_pct']} > 1000"

    def test_movers_endpoint_no_penny_cards(self) -> None:
        """After T01 fix, all movers should have price_start >= 0.50."""
        mock_repo = MagicMock(spec=Repository)
        converter = _mock_converter()

        # Repo only returns cards with price_start >= 0.50
        mock_repo.get_movers.return_value = (
            [_make_mover_tuple(1, "Bolt", "0.50", "1.00", "100.00")],
            [_make_mover_tuple(2, "Sol Ring", "5.00", "3.00", "-40.00")],
        )

        cache = AggregateCache(default_ttl=0)
        service = MarketDataService(mock_repo, converter, cache)

        app = _make_app(market_service=service)
        client = TestClient(app)
        resp = client.get("/api/v1/market/movers?period=30d")

        assert resp.status_code == 200
        data = resp.json()["data"]

        for g in data["gainers"]:
            assert float(str(g["price_start"])) >= 0.50
        for lo in data["losers"]:
            assert float(str(lo["price_start"])) >= 0.50


# ===========================================================================
# /market/summary — calls repo.get_movers() directly
# ===========================================================================


class TestSummaryEndpointFilters:
    """Verify /market/summary computes averages from filtered movers only."""

    def setup_method(self) -> None:
        _endpoint_cache.clear()

    def test_summary_avg_excludes_extreme_outliers(self) -> None:
        """avg_price_change_pct should reflect only filtered movers.

        If repo.get_movers() returned unfiltered data with a 49900% outlier,
        the average would be wildly inflated. After T01, such outliers are
        excluded at the repo level, so the summary avg stays reasonable.
        """
        # Simulate T01-filtered movers (no outliers)
        gainers = [
            _make_mover_tuple(1, "Bolt", "5.00", "7.50", "50.00"),
            _make_mover_tuple(2, "Ring", "10.00", "12.00", "20.00"),
        ]
        losers = [
            _make_mover_tuple(3, "Ritual", "8.00", "6.00", "-25.00"),
        ]

        repo_mock = MagicMock(spec=Repository)
        repo_mock.get_movers.return_value = (gainers, losers)

        service_mock = MagicMock(spec=MarketDataService)
        service_mock.get_market_summary.return_value = _mock_market_summary()

        app = _make_app(market_service=service_mock, repo=repo_mock)
        client = TestClient(app)
        resp = client.get("/api/v1/market/summary")

        data = resp.json()["data"]
        avg = data["avg_price_change_pct"]

        # avg of (50, 20, -25) = 15.0
        assert avg is not None
        assert avg == pytest.approx(15.0, abs=0.01)
        # Sanity: avg should be within a reasonable range (not inflated)
        assert abs(avg) < 1000

    def test_summary_counts_from_filtered_data(self) -> None:
        """Gainers/losers counts should reflect filtered movers."""
        gainers = [
            _make_mover_tuple(1, "Bolt", "5.00", "7.50", "50.00"),
        ]
        losers = [
            _make_mover_tuple(2, "Ritual", "8.00", "6.00", "-25.00"),
            _make_mover_tuple(3, "Dark", "3.00", "2.00", "-33.33"),
        ]

        repo_mock = MagicMock(spec=Repository)
        repo_mock.get_movers.return_value = (gainers, losers)

        service_mock = MagicMock(spec=MarketDataService)
        service_mock.get_market_summary.return_value = _mock_market_summary()

        app = _make_app(market_service=service_mock, repo=repo_mock)
        client = TestClient(app)
        resp = client.get("/api/v1/market/summary")

        data = resp.json()["data"]
        assert data["gainers_count"] == 1
        assert data["losers_count"] == 2
        assert data["market_direction"] == "down"

    def test_summary_uses_repo_get_movers_with_limit_9999(self) -> None:
        """The summary endpoint requests all movers (limit=9999) for aggregation."""
        repo_mock = MagicMock(spec=Repository)
        repo_mock.get_movers.return_value = ([], [])

        service_mock = MagicMock(spec=MarketDataService)
        service_mock.get_market_summary.return_value = _mock_market_summary()

        app = _make_app(market_service=service_mock, repo=repo_mock)
        client = TestClient(app)
        client.get("/api/v1/market/summary?period=30d")

        repo_mock.get_movers.assert_called_once_with(days=30, limit=9999)

    def test_summary_no_penny_card_inflation(self) -> None:
        """With T01 filter, penny cards that produced 49900% changes are gone.

        This test verifies the summary endpoint does not produce an inflated
        avg_change when fed only filtered data.
        """
        # All cards have price_start >= 0.50 and abs(change_pct) <= 1000
        gainers = [
            _make_mover_tuple(1, "A", "1.00", "2.00", "100.00"),
            _make_mover_tuple(2, "B", "5.00", "10.00", "100.00"),
            _make_mover_tuple(3, "C", "0.50", "1.00", "100.00"),
        ]
        losers = []

        repo_mock = MagicMock(spec=Repository)
        repo_mock.get_movers.return_value = (gainers, losers)

        service_mock = MagicMock(spec=MarketDataService)
        service_mock.get_market_summary.return_value = _mock_market_summary()

        app = _make_app(market_service=service_mock, repo=repo_mock)
        client = TestClient(app)
        resp = client.get("/api/v1/market/summary")

        data = resp.json()["data"]
        # All have 100% change, so avg should be exactly 100.0
        assert data["avg_price_change_pct"] == pytest.approx(100.0, abs=0.01)


# ===========================================================================
# /market/volatile — primary path uses TrendingService, fallback uses repo
# ===========================================================================


class TestVolatileEndpointFilters:
    """Verify /market/volatile excludes penny-card noise and extreme outliers."""

    def setup_method(self) -> None:
        _endpoint_cache.clear()

    def test_volatile_primary_path_excludes_penny_cards(self) -> None:
        """TrendingService already applies min_price=1.00 via rank_trending,
        so penny cards are excluded from the primary path."""
        # All cards have reasonable prices (TrendingService already filtered)
        cards = [
            _trending_entry(
                card_id=1,
                price_start=5.0,
                price_end=10.0,
                change_pct=100.0,
                consistency=0.3,
            ),
            _trending_entry(
                card_id=2,
                price_start=2.0,
                price_end=3.0,
                change_pct=50.0,
                consistency=0.2,
            ),
        ]

        trending_svc = MagicMock(spec=TrendingService)
        trending_svc.get_trending.side_effect = [
            TrendingResponse(
                cards=cards,
                period="30d",
                direction="up",
                computed_at=datetime.now(),
                cached=False,
            ),
            TrendingResponse(
                cards=[],
                period="30d",
                direction="down",
                computed_at=datetime.now(),
                cached=False,
            ),
        ]

        converter = MagicMock(spec=CurrencyConverter)
        repo = MagicMock(spec=Repository)

        app = _make_app(trending_service=trending_svc, converter=converter, repo=repo)
        client = TestClient(app)
        resp = client.get("/api/v1/market/volatile")

        assert resp.status_code == 200
        result_cards = resp.json()["data"]["cards"]
        for c in result_cards:
            assert (
                c["price_start"] >= 0.50
            ), f"Card {c['name_en']} has price_start={c['price_start']} < 0.50"

    def test_volatile_fallback_uses_filtered_repo_data(self) -> None:
        """When TrendingService fails, volatile falls back to repo.get_movers()
        which now applies T01 filters. Verify the fallback produces clean data."""
        trending_svc = MagicMock(spec=TrendingService)
        trending_svc.get_trending.side_effect = Exception("service down")

        converter = MagicMock(spec=CurrencyConverter)
        repo = MagicMock(spec=Repository)

        # Simulated T01-filtered output from repo.get_movers()
        repo.get_movers.return_value = (
            [
                _make_mover_tuple(1, "Bolt", "5.00", "7.50", "50.00"),
                _make_mover_tuple(2, "Ring", "10.00", "15.00", "50.00"),
            ],
            [
                _make_mover_tuple(3, "Ritual", "8.00", "6.00", "-25.00"),
            ],
        )

        app = _make_app(trending_service=trending_svc, converter=converter, repo=repo)
        client = TestClient(app)
        resp = client.get("/api/v1/market/volatile")

        assert resp.status_code == 200
        result_cards = resp.json()["data"]["cards"]

        assert len(result_cards) == 3
        for c in result_cards:
            assert (
                abs(c["change_pct"]) <= 1000
            ), f"Card {c['name_en']} has change_pct={c['change_pct']} exceeding cap"
            assert (
                c["price_start"] >= 0.50
            ), f"Card {c['name_en']} has penny price_start={c['price_start']}"

    def test_volatile_fallback_sorted_by_abs_change(self) -> None:
        """Fallback path sorts by abs(change_pct) descending."""
        trending_svc = MagicMock(spec=TrendingService)
        trending_svc.get_trending.side_effect = Exception("service down")

        converter = MagicMock(spec=CurrencyConverter)
        repo = MagicMock(spec=Repository)

        repo.get_movers.return_value = (
            [
                _make_mover_tuple(1, "Small", "5.00", "5.50", "10.00"),
                _make_mover_tuple(2, "Big", "5.00", "10.00", "100.00"),
            ],
            [
                _make_mover_tuple(3, "Drop", "8.00", "4.00", "-50.00"),
            ],
        )

        app = _make_app(trending_service=trending_svc, converter=converter, repo=repo)
        client = TestClient(app)
        resp = client.get("/api/v1/market/volatile")

        result_cards = resp.json()["data"]["cards"]
        # Sorted by abs(change_pct): 100, -50, 10
        assert result_cards[0]["card_id"] == 2  # 100%
        assert result_cards[1]["card_id"] == 3  # -50%
        assert result_cards[2]["card_id"] == 1  # 10%

    def test_volatile_fallback_calls_repo_with_limit_9999(self) -> None:
        """Fallback requests all movers for proper volatility ranking."""
        trending_svc = MagicMock(spec=TrendingService)
        trending_svc.get_trending.side_effect = Exception("service down")

        converter = MagicMock(spec=CurrencyConverter)
        repo = MagicMock(spec=Repository)
        repo.get_movers.return_value = ([], [])

        app = _make_app(trending_service=trending_svc, converter=converter, repo=repo)
        client = TestClient(app)
        client.get("/api/v1/market/volatile?period=30d")

        repo.get_movers.assert_called_once_with(days=30, limit=9999)


# ===========================================================================
# Service layer delegation
# ===========================================================================


class TestServiceLayerDelegation:
    """Verify MarketDataService delegates to repo.get_movers() without bypass."""

    def test_get_top_movers_calls_repo_get_movers(self) -> None:
        """The service method must call repo.get_movers(), not a custom query."""
        mock_repo = MagicMock(spec=Repository)
        converter = _mock_converter()
        cache = AggregateCache(default_ttl=0)

        mock_repo.get_movers.return_value = (
            [_make_mover_tuple(1, "Bolt", "5.00", "7.50", "50.00")],
            [],
        )

        service = MarketDataService(mock_repo, converter, cache)
        service.get_top_movers(period="7d", limit=5, currency="BRL")

        mock_repo.get_movers.assert_called_once_with(days=7, limit=5)

    def test_get_top_movers_respects_period_map(self) -> None:
        """Different period strings map to correct day counts."""
        mock_repo = MagicMock(spec=Repository)
        converter = _mock_converter()

        period_expectations = {"7d": 7, "30d": 30, "90d": 90}

        for period_str, expected_days in period_expectations.items():
            mock_repo.reset_mock()
            cache = AggregateCache(default_ttl=0)
            mock_repo.get_movers.return_value = ([], [])

            service = MarketDataService(mock_repo, converter, cache)
            service.get_top_movers(period=period_str, limit=10)

            mock_repo.get_movers.assert_called_once_with(days=expected_days, limit=10)

    def test_get_top_movers_handles_repo_exception(self) -> None:
        """If repo.get_movers() raises, service returns empty result."""
        mock_repo = MagicMock(spec=Repository)
        converter = _mock_converter()
        cache = AggregateCache(default_ttl=0)

        mock_repo.get_movers.side_effect = Exception("DB timeout")

        service = MarketDataService(mock_repo, converter, cache)
        result = service.get_top_movers(period="30d", limit=10)

        assert isinstance(result, MoversResult)
        assert result.gainers == []
        assert result.losers == []
