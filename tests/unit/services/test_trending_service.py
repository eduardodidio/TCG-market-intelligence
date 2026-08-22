"""Tests for TrendingService -- F36."""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import MagicMock

from src.api.schemas.trending import TrendingResponse
from src.services.trending import TrendingService


def _mock_repo():
    repo = MagicMock()
    # Return sample price data: two cards
    repo.get_trending_price_data.return_value = {
        1: [
            (date(2026, 8, 10), Decimal("10")),
            (date(2026, 8, 15), Decimal("12")),
            (date(2026, 8, 20), Decimal("15")),
        ],
        2: [
            (date(2026, 8, 10), Decimal("20")),
            (date(2026, 8, 15), Decimal("18")),
            (date(2026, 8, 20), Decimal("16")),
        ],
    }
    repo.get_card_info_batch.return_value = {
        1: ("Lightning Bolt", "Raio", "lea", "161"),
        2: ("Dark Ritual", "Ritual Sombrio", "lea", "116"),
    }
    return repo


def _mock_converter():
    converter = MagicMock()
    converter.get_display_rate.return_value = None
    converter.convert.side_effect = lambda v, d, c: v
    return converter


class TestTrendingService:
    def test_returns_trending_response(self) -> None:
        service = TrendingService(_mock_repo())
        result = service.get_trending("up", 30, 20, _mock_converter(), "BRL")
        assert isinstance(result, TrendingResponse)
        assert result.direction == "up"

    def test_calls_repo_methods(self) -> None:
        repo = _mock_repo()
        service = TrendingService(repo)
        service.get_trending("up", 30, 20, _mock_converter(), "BRL")
        repo.get_trending_price_data.assert_called_once_with(30)
        repo.get_card_info_batch.assert_called_once()

    def test_cache_hit_returns_cached(self) -> None:
        repo = _mock_repo()
        service = TrendingService(repo)
        converter = _mock_converter()

        # First call
        r1 = service.get_trending("up", 30, 20, converter, "BRL")
        assert r1.cached is False

        # Second call - should be cached
        r2 = service.get_trending("up", 30, 20, converter, "BRL")
        assert r2.cached is True
        # Repo should only be called once
        assert repo.get_trending_price_data.call_count == 1

    def test_cache_miss_after_ttl(self) -> None:
        repo = _mock_repo()
        service = TrendingService(repo)
        service._cache_ttl = timedelta(seconds=0)  # Expire immediately
        converter = _mock_converter()

        service.get_trending("up", 30, 20, converter, "BRL")
        service.get_trending("up", 30, 20, converter, "BRL")
        assert repo.get_trending_price_data.call_count == 2

    def test_invalidate_cache(self) -> None:
        repo = _mock_repo()
        service = TrendingService(repo)
        converter = _mock_converter()

        service.get_trending("up", 30, 20, converter, "BRL")
        service.invalidate_cache()
        service.get_trending("up", 30, 20, converter, "BRL")
        assert repo.get_trending_price_data.call_count == 2

    def test_empty_database(self) -> None:
        repo = MagicMock()
        repo.get_trending_price_data.return_value = {}
        repo.get_card_info_batch.return_value = {}

        service = TrendingService(repo)
        result = service.get_trending("up", 30, 20, _mock_converter(), "BRL")
        assert result.cards == []
        assert result.direction == "up"

    def test_gainers_returns_uptrending(self) -> None:
        service = TrendingService(_mock_repo())
        result = service.get_trending("up", 30, 20, _mock_converter(), "BRL")
        for card in result.cards:
            assert card.change_pct > 0

    def test_losers_returns_downtrending(self) -> None:
        service = TrendingService(_mock_repo())
        result = service.get_trending("down", 30, 20, _mock_converter(), "BRL")
        for card in result.cards:
            assert card.change_pct < 0

    def test_cards_have_image_urls(self) -> None:
        service = TrendingService(_mock_repo())
        result = service.get_trending("up", 30, 20, _mock_converter(), "BRL")
        for card in result.cards:
            if card.set_code and card.collector_number:
                assert card.image_url is not None
                assert "scryfall" in card.image_url

    def test_different_cache_keys_for_different_params(self) -> None:
        repo = _mock_repo()
        service = TrendingService(repo)
        converter = _mock_converter()

        service.get_trending("up", 30, 20, converter, "BRL")
        service.get_trending("up", 7, 20, converter, "BRL")
        assert repo.get_trending_price_data.call_count == 2
