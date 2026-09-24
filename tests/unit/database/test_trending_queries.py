"""Tests for F175-T03: market-wide trending price series (union of source_cards + direct)."""

from __future__ import annotations

from datetime import date, datetime, timedelta
from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from src.database.models import Base, CardRow, PriceObservationRow, SourceCardRow
from src.database.trending_queries import load_market_trending_prices, parse_direct_card_id


@pytest.fixture()
def _sqlite_engine_with_prices():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return engine


def _seed_card(session: Session, card_id: int) -> None:
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


def _seed_source_card(session: Session, card_id: int, source: str, external_id: str) -> None:
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


def _seed_obs(
    session: Session, source: str, external_id: str, observed_at: date, median_price
) -> None:
    session.add(
        PriceObservationRow(
            source=source,
            external_id=external_id,
            observed_at=observed_at,
            median_price=median_price,
        )
    )


class TestParseDirectCardId:
    def test_liga_pattern(self):
        assert parse_direct_card_id("liga_42") == 42

    def test_liga_foil_is_excluded(self):
        assert parse_direct_card_id("liga_42_foil") is None

    def test_manual_pattern(self):
        assert parse_direct_card_id("manual_42") == 42

    def test_liga_catalog_is_not_a_card_id(self):
        assert parse_direct_card_id("liga_catalog_mh3_12") is None

    def test_liga_non_numeric_suffix_is_rejected(self):
        assert parse_direct_card_id("liga_abc") is None

    def test_manual_with_no_id_is_rejected(self):
        assert parse_direct_card_id("manual_") is None


class TestLoadMarketTrendingPrices:
    def test_liga_only_card_rising_over_5_days(self, _sqlite_engine_with_prices):
        engine = _sqlite_engine_with_prices
        today = date.today()
        with Session(engine) as session:
            _seed_card(session, 42)
            for i in range(5):
                _seed_obs(
                    session,
                    "liga",
                    "liga_42",
                    today - timedelta(days=4 - i),
                    Decimal(f"{10 + i}.00"),
                )
            session.commit()

        result = load_market_trending_prices(engine, period_days=30)

        assert 42 in result
        assert len(result[42]) == 5
        prices = [p for _, p in result[42]]
        assert prices == sorted(prices)
        dates = [d for d, _ in result[42]]
        assert dates == sorted(dates)

    def test_source_cards_and_liga_merge_for_same_card(self, _sqlite_engine_with_prices):
        engine = _sqlite_engine_with_prices
        today = date.today()
        with Session(engine) as session:
            _seed_card(session, 7)
            _seed_source_card(session, 7, "myp", "myp_7")
            _seed_obs(session, "myp", "myp_7", today - timedelta(days=2), Decimal("5.00"))
            _seed_obs(session, "liga", "liga_7", today - timedelta(days=1), Decimal("6.00"))
            session.commit()

        result = load_market_trending_prices(engine, period_days=30)

        assert len(result[7]) == 2

    def test_same_day_dedup_keeps_highest(self, _sqlite_engine_with_prices):
        engine = _sqlite_engine_with_prices
        today = date.today()
        with Session(engine) as session:
            _seed_card(session, 42)
            _seed_obs(session, "liga", "liga_42", today, Decimal("10.00"))
            _seed_obs(session, "manual", "manual_42", today, Decimal("12.00"))
            session.commit()

        result = load_market_trending_prices(engine, period_days=30)

        assert result[42] == [(today, Decimal("12.00"))]

    def test_foil_observations_do_not_mix_into_series(self, _sqlite_engine_with_prices):
        engine = _sqlite_engine_with_prices
        today = date.today()
        with Session(engine) as session:
            _seed_card(session, 42)
            _seed_obs(session, "liga", "liga_42", today, Decimal("10.00"))
            _seed_obs(session, "liga", "liga_42_foil", today, Decimal("25.00"))
            _seed_obs(session, "liga", "liga_42_foil", today - timedelta(days=1), Decimal("30.00"))
            session.commit()

        result = load_market_trending_prices(engine, period_days=30)

        assert result[42] == [(today, Decimal("10.00"))]

    def test_liga_catalog_and_malformed_ids_are_ignored(self, _sqlite_engine_with_prices):
        engine = _sqlite_engine_with_prices
        today = date.today()
        with Session(engine) as session:
            _seed_obs(session, "liga", "liga_catalog_mh3_12", today, Decimal("10.00"))
            _seed_obs(session, "liga", "liga_abc", today, Decimal("10.00"))
            _seed_obs(session, "manual", "manual_", today, Decimal("10.00"))
            session.commit()

        result = load_market_trending_prices(engine, period_days=30)

        assert result == {}

    def test_observation_exactly_on_cutoff_is_included(self, _sqlite_engine_with_prices):
        engine = _sqlite_engine_with_prices
        cutoff = date.today() - timedelta(days=30)
        with Session(engine) as session:
            _seed_card(session, 42)
            _seed_obs(session, "liga", "liga_42", cutoff, Decimal("10.00"))
            session.commit()

        result = load_market_trending_prices(engine, period_days=30)

        assert result == {42: [(cutoff, Decimal("10.00"))]}

    def test_observation_before_cutoff_is_excluded(self, _sqlite_engine_with_prices):
        engine = _sqlite_engine_with_prices
        before_cutoff = date.today() - timedelta(days=31)
        with Session(engine) as session:
            _seed_card(session, 42)
            _seed_obs(session, "liga", "liga_42", before_cutoff, Decimal("10.00"))
            session.commit()

        result = load_market_trending_prices(engine, period_days=30)

        assert result == {}

    def test_null_median_price_is_ignored(self, _sqlite_engine_with_prices):
        engine = _sqlite_engine_with_prices
        today = date.today()
        with Session(engine) as session:
            _seed_card(session, 42)
            _seed_obs(session, "liga", "liga_42", today, None)
            session.commit()

        result = load_market_trending_prices(engine, period_days=30)

        assert result == {}

    def test_empty_db_returns_empty_dict(self, _sqlite_engine_with_prices):
        result = load_market_trending_prices(_sqlite_engine_with_prices, period_days=30)
        assert result == {}
