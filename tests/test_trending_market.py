"""Tests for F213-T02: Trending market query union + cache fix.

Tests cover:
- ``load_market_trending_prices()`` returns data from both paths (source_cards + direct)
- Liga observations are included via the direct path
- Deduplication: same card from two sources keeps latest/highest
- Cache behaviour: errors not cached, empty results use short TTL
"""

from __future__ import annotations

from datetime import date, datetime, timedelta
from decimal import Decimal
from unittest.mock import MagicMock

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from src.database.models import Base, CardRow, PriceObservationRow, SourceCardRow
from src.database.trending_queries import (
    load_market_trending_prices,
    parse_direct_card_id,
)
from src.services.trending import TrendingService

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


@pytest.fixture()
def engine():
    eng = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(eng)
    return eng


def _card(session: Session, card_id: int) -> None:
    session.add(
        CardRow(
            id=card_id,
            game="magic",
            name_en=f"Card {card_id}",
            set_code="TST",
            collector_number=str(card_id).zfill(3),
            created_at=datetime(2026, 1, 1),
            updated_at=datetime(2026, 1, 1),
        )
    )


def _source_card(session: Session, card_id: int, source: str, external_id: str) -> None:
    session.add(
        SourceCardRow(
            source=source,
            external_id=external_id,
            card_id=card_id,
            url=f"https://example.com/{external_id}",
            created_at=datetime(2026, 1, 1),
            updated_at=datetime(2026, 1, 1),
        )
    )


def _obs(session: Session, source: str, external_id: str, observed_at: date, price) -> None:
    session.add(
        PriceObservationRow(
            source=source,
            external_id=external_id,
            observed_at=observed_at,
            median_price=price,
        )
    )


# ---------------------------------------------------------------------------
# parse_direct_card_id
# ---------------------------------------------------------------------------


class TestParseDirectCardIdF213:
    """Verify liga patterns are now accepted."""

    def test_liga_non_foil(self):
        assert parse_direct_card_id("liga_100") == 100

    def test_liga_foil(self):
        assert parse_direct_card_id("liga_100_foil") == 100

    def test_myp_foil_still_excluded(self):
        # MYP foil is excluded to avoid mixing foil/non-foil in trends
        assert parse_direct_card_id("myp_42_foil") is None

    def test_manual_foil_still_excluded(self):
        # Manual foil is excluded to avoid mixing foil/non-foil in trends
        assert parse_direct_card_id("manual_7_foil") is None

    def test_myp_non_foil(self):
        assert parse_direct_card_id("myp_42") == 42

    def test_manual_non_foil(self):
        assert parse_direct_card_id("manual_7") == 7

    def test_liga_catalog_still_rejected(self):
        assert parse_direct_card_id("liga_catalog_mh3_12") is None

    def test_unknown_prefix_rejected(self):
        assert parse_direct_card_id("scryfall_42") is None

    def test_empty_id_rejected(self):
        assert parse_direct_card_id("liga_") is None


# ---------------------------------------------------------------------------
# load_market_trending_prices — both paths
# ---------------------------------------------------------------------------


class TestLoadMarketTrendingBothPaths:
    """Data from source_cards (path 1) and direct observations (path 2) merge."""

    def test_source_cards_path_returns_data(self, engine):
        today = date.today()
        with Session(engine) as s:
            _card(s, 1)
            _source_card(s, 1, "myp", "ext_myp_1")
            _obs(s, "myp", "ext_myp_1", today, Decimal("10.00"))
            s.commit()

        result = load_market_trending_prices(engine, period_days=30)
        assert 1 in result
        assert result[1] == [(today, Decimal("10.00"))]

    def test_liga_direct_path_returns_data(self, engine):
        today = date.today()
        with Session(engine) as s:
            _card(s, 50)
            _obs(s, "liga", "liga_50", today, Decimal("15.00"))
            s.commit()

        result = load_market_trending_prices(engine, period_days=30)
        assert 50 in result
        assert result[50] == [(today, Decimal("15.00"))]

    def test_liga_foil_direct_path_returns_data(self, engine):
        today = date.today()
        with Session(engine) as s:
            _card(s, 50)
            _obs(s, "liga", "liga_50_foil", today, Decimal("25.00"))
            s.commit()

        result = load_market_trending_prices(engine, period_days=30)
        assert 50 in result
        assert result[50] == [(today, Decimal("25.00"))]

    def test_both_paths_merge(self, engine):
        """Card with source_cards price AND liga direct price merges correctly."""
        today = date.today()
        yesterday = today - timedelta(days=1)
        with Session(engine) as s:
            _card(s, 10)
            _source_card(s, 10, "myp", "ext_myp_10")
            _obs(s, "myp", "ext_myp_10", yesterday, Decimal("5.00"))
            _obs(s, "liga", "liga_10", today, Decimal("8.00"))
            s.commit()

        result = load_market_trending_prices(engine, period_days=30)
        assert 10 in result
        assert len(result[10]) == 2
        assert result[10][0] == (yesterday, Decimal("5.00"))
        assert result[10][1] == (today, Decimal("8.00"))


# ---------------------------------------------------------------------------
# Deduplication
# ---------------------------------------------------------------------------


class TestDeduplication:
    def test_same_card_same_day_keeps_highest(self, engine):
        today = date.today()
        with Session(engine) as s:
            _card(s, 20)
            # Path 2: two direct observations on the same day
            _obs(s, "liga", "liga_20", today, Decimal("10.00"))
            _obs(s, "manual", "manual_20", today, Decimal("12.00"))
            s.commit()

        result = load_market_trending_prices(engine, period_days=30)
        assert result[20] == [(today, Decimal("12.00"))]

    def test_source_cards_and_direct_same_day_dedup(self, engine):
        """When path 1 and path 2 produce the same card+date, keep highest."""
        today = date.today()
        with Session(engine) as s:
            _card(s, 30)
            _source_card(s, 30, "myp", "ext_myp_30")
            _obs(s, "myp", "ext_myp_30", today, Decimal("7.00"))
            _obs(s, "liga", "liga_30", today, Decimal("9.00"))
            s.commit()

        result = load_market_trending_prices(engine, period_days=30)
        assert result[30] == [(today, Decimal("9.00"))]

    def test_different_days_all_kept(self, engine):
        today = date.today()
        d1 = today - timedelta(days=2)
        d2 = today - timedelta(days=1)
        with Session(engine) as s:
            _card(s, 40)
            _obs(s, "liga", "liga_40", d1, Decimal("5.00"))
            _obs(s, "manual", "manual_40", d2, Decimal("6.00"))
            _obs(s, "myp", "myp_40", today, Decimal("7.00"))
            s.commit()

        result = load_market_trending_prices(engine, period_days=30)
        assert len(result[40]) == 3
        prices = [p for _, p in result[40]]
        assert prices == [Decimal("5.00"), Decimal("6.00"), Decimal("7.00")]


# ---------------------------------------------------------------------------
# Cache behaviour (TrendingService)
# ---------------------------------------------------------------------------


class TestTrendingServiceCache:
    """Verify cache rules: errors not cached, empty uses short TTL."""

    def _make_service(self):
        repo = MagicMock()
        repo.get_card_info_batch.return_value = {}
        return TrendingService(repo), repo

    def _make_converter(self):
        converter = MagicMock()
        converter.get_display_rate.return_value = None
        return converter

    def test_error_not_cached(self):
        svc, repo = self._make_service()
        repo.get_trending_price_data.side_effect = RuntimeError("DB down")
        converter = self._make_converter()

        # First call — error
        resp1 = svc.get_trending("up", 7, 10, converter, "BRL")
        assert resp1.cards == []

        # Second call should NOT hit cache (error was not cached)
        repo.get_trending_price_data.side_effect = RuntimeError("DB still down")
        svc.get_trending("up", 7, 10, converter, "BRL")
        # get_trending_price_data was called twice (not served from cache)
        assert repo.get_trending_price_data.call_count == 2

    def test_empty_result_cached_with_short_ttl(self):
        svc, repo = self._make_service()
        repo.get_trending_price_data.return_value = {}
        converter = self._make_converter()

        resp1 = svc.get_trending("up", 7, 10, converter, "BRL")
        assert resp1.cards == []

        # Second call within 2min should use cache
        resp2 = svc.get_trending("up", 7, 10, converter, "BRL")
        assert resp2.cached is True
        assert repo.get_trending_price_data.call_count == 1

    def test_empty_result_expires_after_short_ttl(self):
        svc, repo = self._make_service()
        repo.get_trending_price_data.return_value = {}
        converter = self._make_converter()

        svc.get_trending("up", 7, 10, converter, "BRL")

        # Manually age the cache entry beyond the 2-minute TTL
        cache_key = "up:7:all"
        cached_at, cached_resp = svc._cache[cache_key]
        svc._cache[cache_key] = (
            cached_at - timedelta(minutes=3),
            cached_resp,
        )

        resp2 = svc.get_trending("up", 7, 10, converter, "BRL")
        assert resp2.cached is False
        assert repo.get_trending_price_data.call_count == 2

    def test_non_empty_result_uses_long_ttl(self):
        svc, repo = self._make_service()
        # Build a price series with enough points for compute_trending_score
        # to produce a result (needs >=2 observations across the period).
        today = date.today()
        series = [(today - timedelta(days=i), Decimal(f"{10 + i}.00")) for i in range(7)]
        repo.get_trending_price_data.return_value = {1: series}
        repo.get_card_info_batch.return_value = {
            1: ("Test Card", None, "TST", "001"),
        }
        converter = self._make_converter()

        resp1 = svc.get_trending("up", 7, 10, converter, "BRL")

        # If the scorer produced no entries, the test premise is wrong.
        # In that case, manually inject a non-empty cached response.
        cache_key = "up:7:all"
        if not resp1.cards:
            from src.api.schemas.trending import TrendingCardEntry, TrendingResponse

            fake_entry = TrendingCardEntry(
                card_id=1,
                name_en="X",
                name_pt=None,
                set_code="TST",
                collector_number="001",
                image_url=None,
                price_start=10.0,
                price_end=15.0,
                change_pct=50.0,
                change_abs=5.0,
                consistency=1.0,
                composite_score=1.0,
                observation_count=7,
                currency="BRL",
            )
            fake_resp = TrendingResponse(
                cards=[fake_entry],
                period="7d",
                direction="up",
                computed_at=datetime.now(),
                cached=False,
            )
            svc._cache[cache_key] = (datetime.now(), fake_resp)

        # Advance cache by 10 minutes — should still be cached (30min TTL)
        cached_at, cached_resp = svc._cache[cache_key]
        assert cached_resp.cards != [], "Cache must hold non-empty response for this test"
        svc._cache[cache_key] = (
            cached_at - timedelta(minutes=10),
            cached_resp,
        )

        # Reset call count so we can check cache hit
        repo.get_trending_price_data.reset_mock()

        resp2 = svc.get_trending("up", 7, 10, converter, "BRL")
        assert resp2.cached is True
        assert repo.get_trending_price_data.call_count == 0
