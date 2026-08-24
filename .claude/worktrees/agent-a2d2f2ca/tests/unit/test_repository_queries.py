"""Tests for repository price series query methods."""

from datetime import date, timedelta
from decimal import Decimal

import pytest

from src.database.repository import Repository
from src.domain.models import HistoricalPrice


@pytest.fixture
def repo(tmp_path):
    db_path = tmp_path / "test.db"
    return Repository(f"sqlite:///{db_path}")


def _make_price(external_id: str, observed_at: date, median: str = "100.00") -> HistoricalPrice:
    return HistoricalPrice(
        source="myp",
        external_id=external_id,
        observed_at=observed_at,
        median_price=Decimal(median),
        currency="BRL",
    )


class TestGetPriceSeries:
    def test_returns_ordered_by_date_asc(self, repo):
        prices = [
            _make_price("111", date(2026, 8, 10), "90.00"),
            _make_price("111", date(2026, 8, 1), "100.00"),
            _make_price("111", date(2026, 8, 5), "95.00"),
        ]
        repo.insert_price_observations(prices)

        result = repo.get_price_series("myp", "111")
        assert len(result) == 3
        assert result[0].observed_at == date(2026, 8, 1)
        assert result[1].observed_at == date(2026, 8, 5)
        assert result[2].observed_at == date(2026, 8, 10)

    def test_returns_historical_price_objects(self, repo):
        repo.insert_price_observations([_make_price("111", date(2026, 8, 1))])
        result = repo.get_price_series("myp", "111")
        assert len(result) == 1
        assert isinstance(result[0], HistoricalPrice)
        assert result[0].source == "myp"
        assert result[0].external_id == "111"
        assert result[0].median_price == Decimal("100.00")

    def test_filters_by_days(self, repo):
        today = date.today()
        prices = [
            _make_price("111", today - timedelta(days=30), "80.00"),
            _make_price("111", today - timedelta(days=5), "90.00"),
            _make_price("111", today - timedelta(days=1), "100.00"),
        ]
        repo.insert_price_observations(prices)

        result = repo.get_price_series("myp", "111", days=7)
        assert len(result) == 2
        assert result[0].median_price == Decimal("90.00")
        assert result[1].median_price == Decimal("100.00")

    def test_days_zero_returns_only_today(self, repo):
        today = date.today()
        prices = [
            _make_price("111", today - timedelta(days=1), "90.00"),
            _make_price("111", today, "100.00"),
        ]
        repo.insert_price_observations(prices)

        result = repo.get_price_series("myp", "111", days=0)
        assert len(result) == 1
        assert result[0].observed_at == today

    def test_nonexistent_card_returns_empty(self, repo):
        result = repo.get_price_series("myp", "nonexistent")
        assert result == []

    def test_single_observation(self, repo):
        repo.insert_price_observations([_make_price("111", date(2026, 8, 1))])
        result = repo.get_price_series("myp", "111")
        assert len(result) == 1

    def test_filters_by_source_and_external_id(self, repo):
        prices = [
            _make_price("111", date(2026, 8, 1)),
            _make_price("222", date(2026, 8, 1)),
        ]
        repo.insert_price_observations(prices)

        result = repo.get_price_series("myp", "111")
        assert len(result) == 1
        assert result[0].external_id == "111"


class TestGetCardsWithObservations:
    def test_returns_cards_with_counts(self, repo):
        prices = [
            _make_price("111", date(2026, 8, 1)),
            _make_price("111", date(2026, 8, 2)),
            _make_price("111", date(2026, 8, 3)),
            _make_price("222", date(2026, 8, 1)),
        ]
        repo.insert_price_observations(prices)

        result = repo.get_cards_with_observations("myp")
        assert len(result) == 2
        # Ordered by external_id
        assert result[0] == ("111", 3)
        assert result[1] == ("222", 1)

    def test_empty_source_returns_empty(self, repo):
        result = repo.get_cards_with_observations("myp")
        assert result == []

    def test_filters_by_source(self, repo):
        prices = [_make_price("111", date(2026, 8, 1))]
        repo.insert_price_observations(prices)

        result = repo.get_cards_with_observations("other_source")
        assert result == []
