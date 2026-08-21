"""Tests for CurrencyConverter service (T05)."""

from datetime import date
from decimal import Decimal
from unittest.mock import MagicMock

import pytest

from src.services.currency import CurrencyConverter


@pytest.fixture()
def mock_repo():
    return MagicMock()


@pytest.fixture()
def converter(mock_repo):
    return CurrencyConverter(mock_repo)


class TestConvert:
    def test_brl_returns_value_unchanged(self, converter):
        result = converter.convert(Decimal("100.00"), date(2026, 8, 20), "BRL")
        assert result == Decimal("100.00")

    def test_none_value_returns_none_for_brl(self, converter):
        result = converter.convert(None, date(2026, 8, 20), "BRL")
        assert result is None

    def test_none_value_returns_none_for_usd(self, converter):
        result = converter.convert(None, date(2026, 8, 20), "USD")
        assert result is None

    def test_converts_brl_to_usd(self, converter, mock_repo):
        rate_row = MagicMock()
        rate_row.rate = Decimal("5.00")
        mock_repo.get_closest_rate.return_value = rate_row

        result = converter.convert(Decimal("100.00"), date(2026, 8, 20), "USD")
        assert result == Decimal("20.00")

    def test_converts_with_rounding(self, converter, mock_repo):
        rate_row = MagicMock()
        rate_row.rate = Decimal("5.25")
        mock_repo.get_closest_rate.return_value = rate_row

        result = converter.convert(Decimal("100.00"), date(2026, 8, 20), "USD")
        assert result == Decimal("19.05")

    def test_returns_none_when_no_rate(self, converter, mock_repo):
        mock_repo.get_closest_rate.return_value = None
        result = converter.convert(Decimal("100.00"), date(2026, 8, 20), "USD")
        assert result is None

    def test_accepts_float_value(self, converter, mock_repo):
        rate_row = MagicMock()
        rate_row.rate = Decimal("5.00")
        mock_repo.get_closest_rate.return_value = rate_row

        result = converter.convert(50.0, date(2026, 8, 20), "USD")
        assert result == Decimal("10.00")

    def test_caches_rate_per_date(self, converter, mock_repo):
        rate_row = MagicMock()
        rate_row.rate = Decimal("5.00")
        mock_repo.get_closest_rate.return_value = rate_row

        converter.convert(Decimal("100.00"), date(2026, 8, 20), "USD")
        converter.convert(Decimal("200.00"), date(2026, 8, 20), "USD")

        # Should only call get_closest_rate once due to caching
        assert mock_repo.get_closest_rate.call_count == 1

    def test_different_dates_are_cached_separately(self, converter, mock_repo):
        rate_row1 = MagicMock()
        rate_row1.rate = Decimal("5.00")
        rate_row2 = MagicMock()
        rate_row2.rate = Decimal("5.25")
        mock_repo.get_closest_rate.side_effect = [rate_row1, rate_row2]

        result1 = converter.convert(Decimal("100.00"), date(2026, 8, 19), "USD")
        result2 = converter.convert(Decimal("100.00"), date(2026, 8, 20), "USD")

        assert result1 == Decimal("20.00")
        assert result2 == Decimal("19.05")
        assert mock_repo.get_closest_rate.call_count == 2

    def test_zero_value_returns_zero(self, converter, mock_repo):
        rate_row = MagicMock()
        rate_row.rate = Decimal("5.00")
        mock_repo.get_closest_rate.return_value = rate_row

        result = converter.convert(Decimal("0"), date(2026, 8, 20), "USD")
        assert result == Decimal("0.00")


class TestGetDisplayRate:
    def test_returns_rate(self, converter, mock_repo):
        rate_row = MagicMock()
        rate_row.rate = Decimal("5.25")
        mock_repo.get_closest_rate.return_value = rate_row

        result = converter.get_display_rate(date(2026, 8, 20))
        assert result == Decimal("5.25")

    def test_returns_none_when_no_rate(self, converter, mock_repo):
        mock_repo.get_closest_rate.return_value = None
        result = converter.get_display_rate(date(2026, 8, 20))
        assert result is None

    def test_uses_today_by_default(self, converter, mock_repo):
        rate_row = MagicMock()
        rate_row.rate = Decimal("5.25")
        mock_repo.get_closest_rate.return_value = rate_row

        converter.get_display_rate()
        mock_repo.get_closest_rate.assert_called_once_with(date.today())
