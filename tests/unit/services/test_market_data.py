"""Tests for MarketDataService (F44-T03)."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from unittest.mock import MagicMock

import pytest

from src.api.schemas.market_data import MoversResult
from src.services.aggregate_cache import AggregateCache
from src.services.market_data import PERIOD_MAP, MarketDataService


@pytest.fixture()
def mock_repo():
    return MagicMock()


@pytest.fixture()
def mock_converter():
    converter = MagicMock()
    # Default: BRL passthrough
    converter.convert.side_effect = lambda v, d, c: (
        Decimal(str(v)) if v is not None and c in ("BRL", "PILA") else v
    )
    converter.get_display_rate.return_value = None  # No USD rate by default
    return converter


@pytest.fixture()
def service(mock_repo, mock_converter):
    cache = AggregateCache(default_ttl=300)
    return MarketDataService(mock_repo, mock_converter, cache)


class TestGetLatestPrice:
    def test_cache_miss_fetches_from_repo(self, service, mock_repo):
        obs = MagicMock()
        obs.median_price = Decimal("15.00")
        obs.observed_at = date(2026, 8, 20)
        mock_repo.get_latest_prices_batch.return_value = {1: obs}

        result = service.get_latest_price(1, "BRL")

        assert result is not None
        assert result.card_id == 1
        assert result.latest_price == Decimal("15.00")
        mock_repo.get_latest_prices_batch.assert_called_once_with([1])

    def test_cache_hit_skips_repo(self, service, mock_repo):
        obs = MagicMock()
        obs.median_price = Decimal("10.00")
        obs.observed_at = date(2026, 8, 20)
        mock_repo.get_latest_prices_batch.return_value = {1: obs}

        # First call populates cache
        service.get_latest_price(1, "BRL")
        # Second call should use cache
        service.get_latest_price(1, "BRL")

        # Repo should only be called once
        mock_repo.get_latest_prices_batch.assert_called_once()

    def test_returns_none_when_no_data(self, service, mock_repo):
        mock_repo.get_latest_prices_batch.return_value = {}
        result = service.get_latest_price(99, "BRL")
        assert result is None

    def test_applies_currency_conversion(self, service, mock_repo, mock_converter):
        obs = MagicMock()
        obs.median_price = Decimal("50.00")
        obs.observed_at = date(2026, 8, 20)
        mock_repo.get_latest_prices_batch.return_value = {1: obs}

        # Set up converter to actually convert
        def _convert(v, d, c):
            if v is None:
                return None
            return Decimal(str(v)) / Decimal("5") if c == "USD" else Decimal(str(v))

        mock_converter.convert.side_effect = _convert
        mock_converter.get_display_rate.return_value = Decimal("5.00")

        result = service.get_latest_price(1, "USD")
        assert result is not None
        assert result.currency == "USD"
        assert result.latest_price == Decimal("10")


class TestGetCardsWithPrices:
    def test_batch_partial_cache(self, service, mock_repo):
        obs1 = MagicMock()
        obs1.median_price = Decimal("10.00")
        obs1.observed_at = date(2026, 8, 20)
        obs2 = MagicMock()
        obs2.median_price = Decimal("20.00")
        obs2.observed_at = date(2026, 8, 20)

        # First call caches card 1
        mock_repo.get_latest_prices_batch.return_value = {1: obs1}
        service.get_latest_price(1, "BRL")

        # Batch call for cards 1 and 2 -- card 1 should be cached
        mock_repo.get_latest_prices_batch.return_value = {2: obs2}
        result = service.get_cards_with_prices([1, 2], "BRL")

        assert 1 in result
        assert 2 in result
        # Second batch call should only fetch card 2
        mock_repo.get_latest_prices_batch.assert_called_with([2])


class TestGetTopMovers:
    def test_caches_result(self, service, mock_repo):
        mock_repo.get_movers.return_value = (
            [(1, "Card A", None, "SET", Decimal("10"), Decimal("15"), Decimal("50"))],
            [(2, "Card B", None, "SET", Decimal("20"), Decimal("10"), Decimal("-50"))],
        )

        result1 = service.get_top_movers("30d", 10, "BRL")
        result2 = service.get_top_movers("30d", 10, "BRL")

        # Repo called only once
        mock_repo.get_movers.assert_called_once()
        assert len(result1.gainers) == 1
        assert len(result2.losers) == 1

    def test_currency_fallback(self, service, mock_repo, mock_converter):
        """When no exchange rate, falls back to BRL."""
        mock_converter.get_display_rate.return_value = None
        mock_repo.get_movers.return_value = (
            [(1, "Card A", None, "SET", Decimal("10"), Decimal("15"), Decimal("50"))],
            [],
        )

        result = service.get_top_movers("30d", 10, "USD")
        assert result.currency == "BRL"

    def test_movers_result_structure(self, service, mock_repo):
        mock_repo.get_movers.return_value = ([], [])
        result = service.get_top_movers("7d", 5, "BRL")
        assert isinstance(result, MoversResult)
        assert result.period == "7d"
        assert result.computed_at is not None


class TestGetMarketSummary:
    def test_caches_result(self, service, mock_repo):
        mock_repo.get_market_stats.return_value = {
            "total_cards": 100,
            "total_observations": 500,
            "avg_price": 15.5,
            "date_range_start": date(2026, 1, 1),
            "date_range_end": date(2026, 8, 20),
        }

        result1 = service.get_market_summary("BRL")
        result2 = service.get_market_summary("BRL")

        mock_repo.get_market_stats.assert_called_once()
        assert result1.total_cards == 100
        assert result2.total_observations == 500

    def test_summary_with_none_avg_price(self, service, mock_repo):
        mock_repo.get_market_stats.return_value = {
            "total_cards": 0,
            "total_observations": 0,
            "avg_price": None,
            "date_range_start": None,
            "date_range_end": None,
        }
        result = service.get_market_summary("BRL")
        assert result.avg_price is None
        assert result.total_cards == 0

    def test_game_filter_uses_different_cache_key(self, service, mock_repo):
        mock_repo.get_market_stats.return_value = {
            "total_cards": 50,
            "total_observations": 100,
            "avg_price": 10.0,
            "date_range_start": date(2026, 1, 1),
            "date_range_end": date(2026, 8, 20),
        }
        service.get_market_summary("BRL", game="magic")
        service.get_market_summary("BRL", game="pokemon")
        # Should be called twice -- different cache keys
        assert mock_repo.get_market_stats.call_count == 2


class TestInvalidateCards:
    def test_clears_card_and_global_caches(self, service, mock_repo):
        # Populate caches
        obs = MagicMock()
        obs.median_price = Decimal("10.00")
        obs.observed_at = date(2026, 8, 20)
        mock_repo.get_latest_prices_batch.return_value = {1: obs}
        mock_repo.get_movers.return_value = ([], [])
        mock_repo.get_market_stats.return_value = {
            "total_cards": 1,
            "total_observations": 1,
            "avg_price": 10.0,
            "date_range_start": date(2026, 1, 1),
            "date_range_end": date(2026, 8, 20),
        }

        service.get_latest_price(1, "BRL")
        service.get_top_movers("30d", 10, "BRL")
        service.get_market_summary("BRL")

        # Invalidate
        service.invalidate_cards([1])

        # Verify caches are cleared
        assert service._cache.get("latest_price:1") is None
        assert service._cache.get("movers:30d:10") is None
        assert service._cache.get("market_summary:all") is None


class TestPeriodMap:
    def test_contains_all_periods(self):
        expected = {"24h", "7d", "30d", "90d", "180d", "1y", "3y"}
        assert set(PERIOD_MAP.keys()) == expected

    def test_values_are_positive_ints(self):
        for key, val in PERIOD_MAP.items():
            assert isinstance(val, int)
            assert val > 0
