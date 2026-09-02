"""Tests for exchange rate fallback logic (F99-T07)."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy.orm import Session

from src.database.models import ExchangeRateRow
from src.database.repository import Repository
from src.services.currency import CurrencyConverter


@pytest.fixture()
def repo(tmp_path):
    db_path = tmp_path / "test_rate.db"
    db_url = f"sqlite:///{db_path}"
    return Repository(db_url=db_url)


def _seed_rate(repo, rate_date: date, rate: Decimal = Decimal("5.50")):
    with Session(repo.engine) as session:
        session.add(
            ExchangeRateRow(
                rate_date=rate_date,
                from_currency="USD",
                to_currency="BRL",
                rate=rate,
                source="test",
            )
        )
        session.commit()


class TestGetClosestRateFallback:
    def test_exact_date_match(self, repo):
        _seed_rate(repo, date(2026, 1, 15))
        row = repo.get_closest_rate(date(2026, 1, 15))
        assert row is not None
        assert row.rate_date == date(2026, 1, 15)

    def test_rate_2_days_before(self, repo):
        _seed_rate(repo, date(2026, 1, 13))
        row = repo.get_closest_rate(date(2026, 1, 15))
        assert row is not None
        assert row.rate_date == date(2026, 1, 13)

    def test_rate_8_days_before_returns_none(self, repo):
        _seed_rate(repo, date(2026, 1, 7))
        row = repo.get_closest_rate(date(2026, 1, 15))
        assert row is None

    def test_no_rate_before_but_3_days_after(self, repo):
        _seed_rate(repo, date(2026, 1, 18))
        row = repo.get_closest_rate(date(2026, 1, 15))
        assert row is not None
        assert row.rate_date == date(2026, 1, 18)

    def test_no_rate_before_10_days_after_returns_none(self, repo):
        _seed_rate(repo, date(2026, 1, 25))
        row = repo.get_closest_rate(date(2026, 1, 15))
        assert row is None

    def test_empty_table_returns_none(self, repo):
        row = repo.get_closest_rate(date(2026, 1, 15))
        assert row is None

    def test_custom_max_gap_days(self, repo):
        _seed_rate(repo, date(2026, 1, 1))
        # Default gap (7) should miss a 10-day gap
        row = repo.get_closest_rate(date(2026, 1, 11))
        assert row is None
        # With max_gap_days=15, it should find it
        row = repo.get_closest_rate(date(2026, 1, 11), max_gap_days=15)
        assert row is not None

    def test_prefers_before_over_after(self, repo):
        """When rates exist both before and after, prefer the one before."""
        _seed_rate(repo, date(2026, 1, 13), Decimal("5.00"))
        _seed_rate(repo, date(2026, 1, 17), Decimal("6.00"))
        row = repo.get_closest_rate(date(2026, 1, 15))
        assert row is not None
        assert row.rate_date == date(2026, 1, 13)
        assert row.rate == Decimal("5.00")


class TestCurrencyConverterFallback:
    def test_convert_with_rate_available(self, repo):
        _seed_rate(repo, date(2026, 1, 15), Decimal("5.00"))
        converter = CurrencyConverter(repo)
        result = converter.convert(Decimal("100.00"), date(2026, 1, 15), "USD")
        assert result == Decimal("20.00")

    def test_convert_fallback_to_brl_when_no_rate(self, repo):
        converter = CurrencyConverter(repo)
        result = converter.convert(
            Decimal("100.00"), date(2026, 1, 15), "USD", fallback_to_brl=True
        )
        # Should return BRL value as-is since no rate available
        assert result == Decimal("100.00")

    def test_convert_returns_none_when_no_rate_and_no_fallback(self, repo):
        converter = CurrencyConverter(repo)
        result = converter.convert(
            Decimal("100.00"), date(2026, 1, 15), "USD", fallback_to_brl=False
        )
        assert result is None

    def test_convert_brl_unchanged(self, repo):
        converter = CurrencyConverter(repo)
        result = converter.convert(Decimal("100.00"), date(2026, 1, 15), "BRL")
        assert result == Decimal("100.00")

    def test_convert_none_value(self, repo):
        converter = CurrencyConverter(repo)
        result = converter.convert(None, date(2026, 1, 15), "USD")
        assert result is None

    def test_caches_fallback_result(self, repo):
        _seed_rate(repo, date(2026, 1, 13), Decimal("5.00"))
        converter = CurrencyConverter(repo)
        # First call populates cache
        converter.convert(Decimal("100.00"), date(2026, 1, 15), "USD")
        # Second call should use cache
        result = converter.convert(Decimal("50.00"), date(2026, 1, 15), "USD")
        assert result == Decimal("10.00")  # 50 / 5.00
