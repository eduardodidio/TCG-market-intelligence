"""Tests for TrendingService cache-on-failure behavior -- F175-T04."""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import MagicMock

from sqlalchemy.exc import OperationalError

from src.services.trending import TrendingService


def _mock_repo_raising():
    repo = MagicMock()
    repo.get_trending_price_data.side_effect = OperationalError("timeout", {}, None)
    repo.get_card_info_batch.return_value = {}
    return repo


def _mock_repo_empty():
    repo = MagicMock()
    repo.get_trending_price_data.return_value = {}
    repo.get_card_info_batch.return_value = {}
    return repo


def _mock_repo_with_cards():
    repo = MagicMock()
    repo.get_trending_price_data.return_value = {
        1: [
            (date(2026, 8, 10), Decimal("10")),
            (date(2026, 8, 15), Decimal("12")),
            (date(2026, 8, 20), Decimal("15")),
        ],
    }
    repo.get_card_info_batch.return_value = {
        1: ("Lightning Bolt", "Raio", "lea", "161"),
    }
    return repo


def _mock_converter():
    converter = MagicMock()
    converter.get_display_rate.return_value = None
    converter.convert.side_effect = lambda v, d, c: v
    return converter


class TestTrendingServiceDoesNotCacheFailures:
    def test_repo_exception_not_cached_second_call_hits_repo_again(self) -> None:
        repo = _mock_repo_raising()
        service = TrendingService(repo)
        converter = _mock_converter()

        r1 = service.get_trending("up", 30, 20, converter, "BRL")
        assert r1.cards == []

        r2 = service.get_trending("up", 30, 20, converter, "BRL")
        assert r2.cards == []

        assert repo.get_trending_price_data.call_count == 2

    def test_error_then_success_recovers(self) -> None:
        repo = MagicMock()
        repo.get_trending_price_data.side_effect = [
            OperationalError("timeout", {}, None),
            {
                1: [
                    (date(2026, 8, 10), Decimal("10")),
                    (date(2026, 8, 15), Decimal("12")),
                    (date(2026, 8, 20), Decimal("15")),
                ],
            },
        ]
        repo.get_card_info_batch.return_value = {
            1: ("Lightning Bolt", "Raio", "lea", "161"),
        }
        service = TrendingService(repo)
        converter = _mock_converter()

        r1 = service.get_trending("up", 30, 20, converter, "BRL")
        assert r1.cards == []

        r2 = service.get_trending("up", 30, 20, converter, "BRL")
        assert len(r2.cards) == 1
        assert repo.get_trending_price_data.call_count == 2


class TestTrendingServiceEmptyResultShortTTL:
    def test_legitimate_empty_result_is_cached(self) -> None:
        repo = _mock_repo_empty()
        service = TrendingService(repo)
        converter = _mock_converter()

        r1 = service.get_trending("up", 30, 20, converter, "BRL")
        assert r1.cards == []
        assert r1.cached is False

        r2 = service.get_trending("up", 30, 20, converter, "BRL")
        assert r2.cached is True
        assert repo.get_trending_price_data.call_count == 1

    def test_empty_result_recomputed_after_short_ttl(self) -> None:
        repo = _mock_repo_empty()
        service = TrendingService(repo)
        converter = _mock_converter()

        service.get_trending("up", 30, 20, converter, "BRL")

        cache_key = "up:30:all"
        cached_at, cached_response = service._cache[cache_key]
        service._cache[cache_key] = (
            cached_at - timedelta(minutes=2, seconds=1),
            cached_response,
        )

        service.get_trending("up", 30, 20, converter, "BRL")
        assert repo.get_trending_price_data.call_count == 2

    def test_empty_result_still_cached_just_under_two_minutes(self) -> None:
        repo = _mock_repo_empty()
        service = TrendingService(repo)
        converter = _mock_converter()

        service.get_trending("up", 30, 20, converter, "BRL")

        cache_key = "up:30:all"
        cached_at, cached_response = service._cache[cache_key]
        service._cache[cache_key] = (
            cached_at - timedelta(minutes=1, seconds=59),
            cached_response,
        )

        r2 = service.get_trending("up", 30, 20, converter, "BRL")
        assert r2.cached is True
        assert repo.get_trending_price_data.call_count == 1


class TestTrendingServiceNonEmptyResultLongTTL:
    def test_non_empty_result_cached_for_thirty_minutes(self) -> None:
        repo = _mock_repo_with_cards()
        service = TrendingService(repo)
        converter = _mock_converter()

        service.get_trending("up", 30, 20, converter, "BRL")

        cache_key = "up:30:all"
        cached_at, cached_response = service._cache[cache_key]
        service._cache[cache_key] = (
            cached_at - timedelta(minutes=29, seconds=59),
            cached_response,
        )

        r2 = service.get_trending("up", 30, 20, converter, "BRL")
        assert r2.cached is True
        assert repo.get_trending_price_data.call_count == 1

    def test_non_empty_result_expires_after_thirty_minutes(self) -> None:
        repo = _mock_repo_with_cards()
        service = TrendingService(repo)
        converter = _mock_converter()

        service.get_trending("up", 30, 20, converter, "BRL")

        cache_key = "up:30:all"
        cached_at, cached_response = service._cache[cache_key]
        service._cache[cache_key] = (
            cached_at - timedelta(minutes=30, seconds=1),
            cached_response,
        )

        service.get_trending("up", 30, 20, converter, "BRL")
        assert repo.get_trending_price_data.call_count == 2


class TestTrendingServiceCacheIsolationAcrossScopes:
    def test_failure_in_all_scope_does_not_affect_user_scope(self) -> None:
        repo = MagicMock()
        repo.get_trending_price_data.side_effect = OperationalError("timeout", {}, None)
        repo.get_trending_price_data_for_user.return_value = {
            1: [
                (date(2026, 8, 10), Decimal("10")),
                (date(2026, 8, 15), Decimal("12")),
                (date(2026, 8, 20), Decimal("15")),
            ],
        }
        repo.get_card_info_batch.return_value = {
            1: ("Lightning Bolt", "Raio", "lea", "161"),
        }
        service = TrendingService(repo)
        converter = _mock_converter()

        r_all = service.get_trending("up", 30, 20, converter, "BRL")
        assert r_all.cards == []

        r_user = service.get_trending("up", 30, 20, converter, "BRL", user_id=42)
        assert len(r_user.cards) == 1
        assert r_user.cached is False

        r_user_again = service.get_trending("up", 30, 20, converter, "BRL", user_id=42)
        assert r_user_again.cached is True
        assert repo.get_trending_price_data_for_user.call_count == 1

    def test_failure_in_user_scope_does_not_affect_all_scope(self) -> None:
        repo = MagicMock()
        repo.get_trending_price_data_for_user.side_effect = OperationalError(
            "timeout", {}, None
        )
        repo.get_trending_price_data.return_value = {
            1: [
                (date(2026, 8, 10), Decimal("10")),
                (date(2026, 8, 15), Decimal("12")),
                (date(2026, 8, 20), Decimal("15")),
            ],
        }
        repo.get_card_info_batch.return_value = {
            1: ("Lightning Bolt", "Raio", "lea", "161"),
        }
        service = TrendingService(repo)
        converter = _mock_converter()

        r_user = service.get_trending("up", 30, 20, converter, "BRL", user_id=42)
        assert r_user.cards == []

        r_all = service.get_trending("up", 30, 20, converter, "BRL")
        assert len(r_all.cards) == 1
        assert r_all.cached is False

        r_all_again = service.get_trending("up", 30, 20, converter, "BRL")
        assert r_all_again.cached is True
        assert repo.get_trending_price_data.call_count == 1
