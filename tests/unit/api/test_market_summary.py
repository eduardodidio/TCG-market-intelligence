"""Tests for the market summary + volatile endpoints (F40-T05)."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from unittest.mock import MagicMock

from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.api.deps import get_currency_converter_dep, get_db, get_market_data_service
from src.api.routers.market import (
    _endpoint_cache,
    get_trending_service,
    router,
)
from src.api.schemas.market_data import MarketSummary
from src.api.schemas.trending import TrendingCardEntry, TrendingResponse
from src.database.repository import Repository
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
    """Create a fresh FastAPI app with the market router and mocked deps."""
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


def _mock_market_summary(
    *,
    total_cards: int = 100,
    total_observations: int = 500,
    avg_price: Decimal | None = Decimal("12.50"),
    currency: str = "BRL",
) -> MarketSummary:
    return MarketSummary(
        total_cards=total_cards,
        total_observations=total_observations,
        avg_price=avg_price,
        date_range_start=None,
        date_range_end=None,
        currency=currency,
        computed_at=datetime(2026, 8, 22, 12, 0),
    )


def _mock_movers_tuples(
    gainers: list[tuple] | None = None,
    losers: list[tuple] | None = None,
) -> tuple[list[tuple], list[tuple]]:
    """Return (gainers_raw, losers_raw) tuples as the repo would."""
    if gainers is None:
        gainers = [
            (1, "Lightning Bolt", "Raio", "lea", Decimal("10.0"), Decimal("15.0"), Decimal("50.0")),
            (2, "Counterspell", "Anular", "lea", Decimal("5.0"), Decimal("7.0"), Decimal("40.0")),
        ]
    if losers is None:
        losers = [
            (
                3,
                "Dark Ritual",
                "Ritual Sombrio",
                "lea",
                Decimal("8.0"),
                Decimal("6.0"),
                Decimal("-25.0"),
            ),
        ]
    return (gainers, losers)


def _mock_trending_entry(**overrides) -> TrendingCardEntry:
    defaults = dict(
        card_id=1,
        name_en="Lightning Bolt",
        name_pt="Raio",
        set_code="lea",
        collector_number="161",
        image_url=None,
        price_start=10.0,
        price_end=15.0,
        change_pct=50.0,
        change_abs=5.0,
        consistency=0.9,
        composite_score=75.0,
        observation_count=5,
        currency="BRL",
    )
    defaults.update(overrides)
    return TrendingCardEntry(**defaults)


def _mock_trending_response(
    direction: str = "up",
    cards: list[TrendingCardEntry] | None = None,
) -> TrendingResponse:
    if cards is None:
        cards = [_mock_trending_entry()]
    return TrendingResponse(
        cards=cards,
        period="30d",
        direction=direction,
        computed_at=datetime(2026, 8, 22, 12, 0),
        cached=False,
    )


def _setup_summary_app(
    *,
    movers: tuple[list, list] | None = None,
    market_summary: MarketSummary | None = None,
    currency: str = "BRL",
) -> TestClient:
    """Create a test client pre-configured for /market/summary tests."""
    _endpoint_cache.clear()

    repo_mock = MagicMock(spec=Repository)
    repo_mock.get_movers.return_value = movers or _mock_movers_tuples()

    service_mock = MagicMock(spec=MarketDataService)
    service_mock.get_market_summary.return_value = market_summary or _mock_market_summary(
        currency=currency
    )

    app = _make_app(market_service=service_mock, repo=repo_mock)
    return TestClient(app)


# ===========================================================================
# GET /market/summary
# ===========================================================================


class TestGetSummary:
    """Tests for the GET /market/summary endpoint."""

    def setup_method(self) -> None:
        _endpoint_cache.clear()

    def test_returns_200_with_correct_schema(self) -> None:
        client = _setup_summary_app()
        resp = client.get("/api/v1/market/summary")
        assert resp.status_code == 200

        data = resp.json()["data"]
        assert "total_cards_tracked" in data
        assert "total_observations" in data
        assert "avg_price" in data
        assert "avg_price_change_pct" in data
        assert "gainers_count" in data
        assert "losers_count" in data
        assert "unchanged_count" in data
        assert "market_direction" in data
        assert "period" in data
        assert "currency" in data
        assert "computed_at" in data

    def test_default_period_is_30d(self) -> None:
        client = _setup_summary_app()
        resp = client.get("/api/v1/market/summary")
        data = resp.json()["data"]
        assert data["period"] == "30d"

    def test_valid_periods(self) -> None:
        for period in ("7d", "30d", "90d"):
            _endpoint_cache.clear()
            client = _setup_summary_app()
            resp = client.get(f"/api/v1/market/summary?period={period}")
            assert resp.status_code == 200
            assert resp.json()["data"]["period"] == period

    def test_invalid_period_returns_422(self) -> None:
        client = _setup_summary_app()
        resp = client.get("/api/v1/market/summary?period=999d")
        assert resp.status_code == 422

    def test_invalid_period_bad_string_returns_422(self) -> None:
        client = _setup_summary_app()
        resp = client.get("/api/v1/market/summary?period=invalid")
        assert resp.status_code == 422

    def test_currency_brl_default(self) -> None:
        client = _setup_summary_app()
        resp = client.get("/api/v1/market/summary")
        data = resp.json()["data"]
        assert data["currency"] == "BRL"

    def test_currency_usd(self) -> None:
        client = _setup_summary_app(currency="USD")
        resp = client.get("/api/v1/market/summary?currency=USD")
        data = resp.json()["data"]
        assert data["currency"] == "USD"

    def test_currency_pila(self) -> None:
        client = _setup_summary_app(currency="PILA")
        resp = client.get("/api/v1/market/summary?currency=PILA")
        data = resp.json()["data"]
        assert data["currency"] == "PILA"

    def test_invalid_currency_returns_422(self) -> None:
        client = _setup_summary_app()
        resp = client.get("/api/v1/market/summary?currency=INVALID")
        assert resp.status_code == 422

    def test_direction_up_when_gainers_more(self) -> None:
        movers = _mock_movers_tuples(
            gainers=[
                (1, "A", "A", "lea", Decimal("10"), Decimal("15"), Decimal("50")),
                (2, "B", "B", "lea", Decimal("5"), Decimal("7"), Decimal("40")),
            ],
            losers=[
                (3, "C", "C", "lea", Decimal("8"), Decimal("6"), Decimal("-25")),
            ],
        )
        client = _setup_summary_app(movers=movers)
        resp = client.get("/api/v1/market/summary")
        data = resp.json()["data"]
        assert data["market_direction"] == "up"
        assert data["gainers_count"] == 2
        assert data["losers_count"] == 1

    def test_direction_down_when_losers_more(self) -> None:
        movers = _mock_movers_tuples(
            gainers=[
                (1, "A", "A", "lea", Decimal("10"), Decimal("15"), Decimal("50")),
            ],
            losers=[
                (2, "B", "B", "lea", Decimal("8"), Decimal("6"), Decimal("-25")),
                (3, "C", "C", "lea", Decimal("7"), Decimal("5"), Decimal("-30")),
            ],
        )
        client = _setup_summary_app(movers=movers)
        resp = client.get("/api/v1/market/summary")
        data = resp.json()["data"]
        assert data["market_direction"] == "down"
        assert data["losers_count"] == 2

    def test_direction_flat_when_equal(self) -> None:
        movers = _mock_movers_tuples(
            gainers=[
                (1, "A", "A", "lea", Decimal("10"), Decimal("15"), Decimal("50")),
            ],
            losers=[
                (2, "B", "B", "lea", Decimal("8"), Decimal("6"), Decimal("-25")),
            ],
        )
        client = _setup_summary_app(movers=movers)
        resp = client.get("/api/v1/market/summary")
        data = resp.json()["data"]
        assert data["market_direction"] == "flat"

    def test_empty_movers_returns_zeros(self) -> None:
        movers = ([], [])
        client = _setup_summary_app(movers=movers)
        resp = client.get("/api/v1/market/summary")
        data = resp.json()["data"]
        assert data["gainers_count"] == 0
        assert data["losers_count"] == 0
        assert data["unchanged_count"] == 0
        assert data["avg_price_change_pct"] is None
        assert data["market_direction"] == "flat"

    def test_avg_price_null_gracefully(self) -> None:
        summary = _mock_market_summary(avg_price=None)
        _endpoint_cache.clear()
        repo_mock = MagicMock(spec=Repository)
        repo_mock.get_movers.return_value = ([], [])
        service_mock = MagicMock(spec=MarketDataService)
        service_mock.get_market_summary.return_value = summary
        app = _make_app(market_service=service_mock, repo=repo_mock)
        client = TestClient(app)
        resp = client.get("/api/v1/market/summary")
        assert resp.status_code == 200
        assert resp.json()["data"]["avg_price"] is None

    def test_unchanged_count(self) -> None:
        """Cards with exactly 0% change are counted as unchanged."""
        movers = _mock_movers_tuples(
            gainers=[
                (1, "A", "A", "lea", Decimal("10"), Decimal("10"), Decimal("0")),
            ],
            losers=[],
        )
        client = _setup_summary_app(movers=movers)
        resp = client.get("/api/v1/market/summary")
        data = resp.json()["data"]
        assert data["unchanged_count"] == 1
        assert data["gainers_count"] == 0
        assert data["losers_count"] == 0

    def test_avg_price_change_pct_computed(self) -> None:
        movers = _mock_movers_tuples(
            gainers=[
                (1, "A", "A", "lea", Decimal("10"), Decimal("15"), Decimal("50")),
            ],
            losers=[
                (2, "B", "B", "lea", Decimal("8"), Decimal("6"), Decimal("-25")),
            ],
        )
        client = _setup_summary_app(movers=movers)
        resp = client.get("/api/v1/market/summary")
        data = resp.json()["data"]
        # avg of 50 and -25 = 12.5
        assert data["avg_price_change_pct"] == 12.5

    def test_cache_returns_cached_value(self) -> None:
        """Second request should return cached data without hitting service again."""
        repo_mock = MagicMock(spec=Repository)
        repo_mock.get_movers.return_value = _mock_movers_tuples()

        service_mock = MagicMock(spec=MarketDataService)
        service_mock.get_market_summary.return_value = _mock_market_summary()

        app = _make_app(market_service=service_mock, repo=repo_mock)
        client = TestClient(app)

        # First request populates cache
        resp1 = client.get("/api/v1/market/summary")
        assert resp1.status_code == 200

        # Second request should use cache
        resp2 = client.get("/api/v1/market/summary")
        assert resp2.status_code == 200

        # Service called only once (second request used cache)
        assert service_mock.get_market_summary.call_count == 1


# ===========================================================================
# GET /market/volatile
# ===========================================================================


class TestGetVolatile:
    """Tests for the GET /market/volatile endpoint."""

    def setup_method(self) -> None:
        _endpoint_cache.clear()

    def test_returns_200(self) -> None:
        trending_svc = MagicMock(spec=TrendingService)
        trending_svc.get_trending.return_value = _mock_trending_response("up")

        converter = MagicMock(spec=CurrencyConverter)
        repo = MagicMock(spec=Repository)

        app = _make_app(trending_service=trending_svc, converter=converter, repo=repo)
        client = TestClient(app)
        resp = client.get("/api/v1/market/volatile")
        assert resp.status_code == 200

    def test_returns_valid_trending_response_schema(self) -> None:
        trending_svc = MagicMock(spec=TrendingService)
        trending_svc.get_trending.return_value = _mock_trending_response("up")

        converter = MagicMock(spec=CurrencyConverter)
        repo = MagicMock(spec=Repository)

        app = _make_app(trending_service=trending_svc, converter=converter, repo=repo)
        client = TestClient(app)
        resp = client.get("/api/v1/market/volatile")
        data = resp.json()["data"]

        assert "cards" in data
        assert "period" in data
        assert "direction" in data
        assert data["direction"] == "volatile"
        assert "computed_at" in data
        assert "cached" in data

    def test_cards_ranked_by_volatility(self) -> None:
        """Cards should be sorted by |change_pct| * (1 - consistency)."""
        # Card A: |50| * (1 - 0.9) = 5
        # Card B: |30| * (1 - 0.2) = 24  <-- higher volatility
        card_a = _mock_trending_entry(card_id=1, change_pct=50.0, consistency=0.9)
        card_b = _mock_trending_entry(card_id=2, change_pct=30.0, consistency=0.2)

        trending_svc = MagicMock(spec=TrendingService)
        trending_svc.get_trending.side_effect = [
            _mock_trending_response("up", cards=[card_a, card_b]),
            _mock_trending_response("down", cards=[]),
        ]

        converter = MagicMock(spec=CurrencyConverter)
        repo = MagicMock(spec=Repository)

        app = _make_app(trending_service=trending_svc, converter=converter, repo=repo)
        client = TestClient(app)
        resp = client.get("/api/v1/market/volatile")
        cards = resp.json()["data"]["cards"]

        assert len(cards) == 2
        assert cards[0]["card_id"] == 2  # card_b has higher volatility
        assert cards[1]["card_id"] == 1

    def test_limit_parameter_respected(self) -> None:
        cards = [
            _mock_trending_entry(card_id=i, change_pct=float(i * 10), consistency=0.1)
            for i in range(1, 6)
        ]
        trending_svc = MagicMock(spec=TrendingService)
        trending_svc.get_trending.side_effect = [
            _mock_trending_response("up", cards=cards),
            _mock_trending_response("down", cards=[]),
        ]

        converter = MagicMock(spec=CurrencyConverter)
        repo = MagicMock(spec=Repository)

        app = _make_app(trending_service=trending_svc, converter=converter, repo=repo)
        client = TestClient(app)
        resp = client.get("/api/v1/market/volatile?limit=3")
        result_cards = resp.json()["data"]["cards"]
        assert len(result_cards) <= 3

    def test_invalid_period_returns_422(self) -> None:
        trending_svc = MagicMock(spec=TrendingService)
        converter = MagicMock(spec=CurrencyConverter)
        repo = MagicMock(spec=Repository)

        app = _make_app(trending_service=trending_svc, converter=converter, repo=repo)
        client = TestClient(app)
        resp = client.get("/api/v1/market/volatile?period=999d")
        assert resp.status_code == 422

    def test_valid_periods(self) -> None:
        for period in ("7d", "30d", "90d"):
            _endpoint_cache.clear()
            trending_svc = MagicMock(spec=TrendingService)
            trending_svc.get_trending.return_value = _mock_trending_response("up")
            converter = MagicMock(spec=CurrencyConverter)
            repo = MagicMock(spec=Repository)

            app = _make_app(trending_service=trending_svc, converter=converter, repo=repo)
            client = TestClient(app)
            resp = client.get(f"/api/v1/market/volatile?period={period}")
            assert resp.status_code == 200
            assert resp.json()["data"]["period"] == period

    def test_empty_result_returns_empty_list(self) -> None:
        trending_svc = MagicMock(spec=TrendingService)
        trending_svc.get_trending.return_value = _mock_trending_response("up", cards=[])

        converter = MagicMock(spec=CurrencyConverter)
        repo = MagicMock(spec=Repository)

        app = _make_app(trending_service=trending_svc, converter=converter, repo=repo)
        client = TestClient(app)
        resp = client.get("/api/v1/market/volatile")
        assert resp.status_code == 200
        assert resp.json()["data"]["cards"] == []

    def test_currency_param(self) -> None:
        trending_svc = MagicMock(spec=TrendingService)
        trending_svc.get_trending.return_value = _mock_trending_response("up")

        converter = MagicMock(spec=CurrencyConverter)
        repo = MagicMock(spec=Repository)

        app = _make_app(trending_service=trending_svc, converter=converter, repo=repo)
        client = TestClient(app)

        for curr in ("BRL", "USD", "PILA"):
            _endpoint_cache.clear()
            resp = client.get(f"/api/v1/market/volatile?currency={curr}")
            assert resp.status_code == 200

    def test_fallback_on_trending_service_error(self) -> None:
        """When TrendingService raises, the endpoint falls back to repo.get_movers."""
        trending_svc = MagicMock(spec=TrendingService)
        trending_svc.get_trending.side_effect = Exception("service down")

        converter = MagicMock(spec=CurrencyConverter)
        repo = MagicMock(spec=Repository)
        repo.get_movers.return_value = _mock_movers_tuples()

        app = _make_app(trending_service=trending_svc, converter=converter, repo=repo)
        client = TestClient(app)
        resp = client.get("/api/v1/market/volatile")
        assert resp.status_code == 200

        data = resp.json()["data"]
        assert len(data["cards"]) > 0
        repo.get_movers.assert_called_once()

    def test_deduplicates_cards(self) -> None:
        """Cards appearing in both gainers and losers are deduped."""
        card = _mock_trending_entry(card_id=1, change_pct=50.0)

        trending_svc = MagicMock(spec=TrendingService)
        trending_svc.get_trending.side_effect = [
            _mock_trending_response("up", cards=[card]),
            _mock_trending_response("down", cards=[card]),  # same card_id
        ]

        converter = MagicMock(spec=CurrencyConverter)
        repo = MagicMock(spec=Repository)

        app = _make_app(trending_service=trending_svc, converter=converter, repo=repo)
        client = TestClient(app)
        resp = client.get("/api/v1/market/volatile")
        cards = resp.json()["data"]["cards"]
        assert len(cards) == 1
