"""Tests for TrendingService collection-only filtering -- F90-T03."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from unittest.mock import MagicMock

from src.api.schemas.trending import TrendingResponse
from src.services.trending import TrendingService


def _mock_repo():
    repo = MagicMock()
    # Global price data: 3 cards
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
        3: [
            (date(2026, 8, 10), Decimal("5")),
            (date(2026, 8, 15), Decimal("8")),
            (date(2026, 8, 20), Decimal("11")),
        ],
    }
    # User-scoped price data: only card 1
    repo.get_trending_price_data_for_user.return_value = {
        1: [
            (date(2026, 8, 10), Decimal("10")),
            (date(2026, 8, 15), Decimal("12")),
            (date(2026, 8, 20), Decimal("15")),
        ],
    }
    repo.get_card_info_batch.return_value = {
        1: ("Lightning Bolt", "Raio", "lea", "161"),
        2: ("Dark Ritual", "Ritual Sombrio", "lea", "116"),
        3: ("Counterspell", "Contramágica", "lea", "54"),
    }
    return repo


def _mock_converter():
    converter = MagicMock()
    converter.get_display_rate.return_value = None
    converter.convert.side_effect = lambda v, d, c: v
    return converter


class TestTrendingServiceCollectionOnly:
    def test_calls_global_method_when_no_user_id(self) -> None:
        repo = _mock_repo()
        service = TrendingService(repo)
        service.get_trending("up", 30, 20, _mock_converter(), "BRL")
        repo.get_trending_price_data.assert_called_once_with(30)
        repo.get_trending_price_data_for_user.assert_not_called()

    def test_calls_user_method_when_user_id_provided(self) -> None:
        repo = _mock_repo()
        service = TrendingService(repo)
        service.get_trending("up", 30, 20, _mock_converter(), "BRL", user_id=42)
        repo.get_trending_price_data_for_user.assert_called_once_with(42, 30)
        repo.get_trending_price_data.assert_not_called()

    def test_user_scoped_returns_only_collection_cards(self) -> None:
        repo = _mock_repo()
        service = TrendingService(repo)
        result = service.get_trending("up", 30, 20, _mock_converter(), "BRL", user_id=42)
        assert isinstance(result, TrendingResponse)
        # Only card 1 is in the user's collection
        card_ids = [c.card_id for c in result.cards]
        assert 1 in card_ids
        assert 2 not in card_ids
        assert 3 not in card_ids

    def test_cache_key_isolation_user_vs_global(self) -> None:
        repo = _mock_repo()
        service = TrendingService(repo)
        converter = _mock_converter()

        # Call global
        r1 = service.get_trending("up", 30, 20, converter, "BRL")
        assert r1.cached is False

        # Call user-scoped -- should NOT hit cache
        r2 = service.get_trending("up", 30, 20, converter, "BRL", user_id=42)
        assert r2.cached is False

        # Both methods should have been called
        repo.get_trending_price_data.assert_called_once()
        repo.get_trending_price_data_for_user.assert_called_once()

    def test_cache_key_isolation_different_users(self) -> None:
        repo = _mock_repo()
        service = TrendingService(repo)
        converter = _mock_converter()

        service.get_trending("up", 30, 20, converter, "BRL", user_id=1)
        service.get_trending("up", 30, 20, converter, "BRL", user_id=2)
        # Should be called twice (different users = different cache keys)
        assert repo.get_trending_price_data_for_user.call_count == 2

    def test_cache_hit_for_same_user(self) -> None:
        repo = _mock_repo()
        service = TrendingService(repo)
        converter = _mock_converter()

        r1 = service.get_trending("up", 30, 20, converter, "BRL", user_id=42)
        assert r1.cached is False
        r2 = service.get_trending("up", 30, 20, converter, "BRL", user_id=42)
        assert r2.cached is True
        assert repo.get_trending_price_data_for_user.call_count == 1

    def test_invalidate_cache_clears_user_scoped(self) -> None:
        repo = _mock_repo()
        service = TrendingService(repo)
        converter = _mock_converter()

        service.get_trending("up", 30, 20, converter, "BRL", user_id=42)
        service.invalidate_cache()
        service.get_trending("up", 30, 20, converter, "BRL", user_id=42)
        assert repo.get_trending_price_data_for_user.call_count == 2
