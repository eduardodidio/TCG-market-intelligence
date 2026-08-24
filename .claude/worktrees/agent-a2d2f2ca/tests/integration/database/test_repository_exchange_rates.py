"""Integration tests for exchange rate repository methods (T04)."""

from datetime import date, timedelta
from decimal import Decimal

import pytest

from src.database.repository import Repository
from src.domain.models import ExchangeRate


@pytest.fixture()
def repo(tmp_path):
    db_path = tmp_path / "test.db"
    return Repository(db_url=f"sqlite:///{db_path}")


class TestUpsertExchangeRate:
    def test_insert_new_rate(self, repo):
        rate = ExchangeRate(rate_date=date(2026, 8, 20), rate=Decimal("5.25"))
        repo.upsert_exchange_rate(rate)

        row = repo.get_exchange_rate(date(2026, 8, 20))
        assert row is not None
        assert row.rate == Decimal("5.25")
        assert row.from_currency == "USD"
        assert row.to_currency == "BRL"

    def test_update_existing_rate(self, repo):
        rate1 = ExchangeRate(rate_date=date(2026, 8, 20), rate=Decimal("5.25"))
        repo.upsert_exchange_rate(rate1)

        rate2 = ExchangeRate(rate_date=date(2026, 8, 20), rate=Decimal("5.30"))
        repo.upsert_exchange_rate(rate2)

        row = repo.get_exchange_rate(date(2026, 8, 20))
        assert row is not None
        assert row.rate == Decimal("5.30")


class TestGetExchangeRate:
    def test_returns_none_for_missing_date(self, repo):
        assert repo.get_exchange_rate(date(2026, 8, 20)) is None

    def test_returns_exact_date(self, repo):
        repo.upsert_exchange_rate(ExchangeRate(rate_date=date(2026, 8, 20), rate=Decimal("5.25")))
        row = repo.get_exchange_rate(date(2026, 8, 20))
        assert row is not None
        assert row.rate_date == date(2026, 8, 20)


class TestGetClosestRate:
    def test_returns_none_when_no_rates(self, repo):
        assert repo.get_closest_rate(date(2026, 8, 20)) is None

    def test_returns_exact_date(self, repo):
        repo.upsert_exchange_rate(ExchangeRate(rate_date=date(2026, 8, 20), rate=Decimal("5.25")))
        row = repo.get_closest_rate(date(2026, 8, 20))
        assert row is not None
        assert row.rate_date == date(2026, 8, 20)

    def test_returns_most_recent_before_target(self, repo):
        repo.upsert_exchange_rate(ExchangeRate(rate_date=date(2026, 8, 18), rate=Decimal("5.20")))
        repo.upsert_exchange_rate(ExchangeRate(rate_date=date(2026, 8, 20), rate=Decimal("5.25")))
        # Asking for Aug 19 (weekend) should get Aug 18
        row = repo.get_closest_rate(date(2026, 8, 19))
        assert row is not None
        assert row.rate_date == date(2026, 8, 18)
        assert row.rate == Decimal("5.20")

    def test_ignores_future_dates(self, repo):
        repo.upsert_exchange_rate(ExchangeRate(rate_date=date(2026, 8, 22), rate=Decimal("5.30")))
        # Asking for Aug 20, the Aug 22 rate should NOT be returned
        assert repo.get_closest_rate(date(2026, 8, 20)) is None


class TestGetLatestRate:
    def test_returns_none_when_empty(self, repo):
        assert repo.get_latest_rate() is None

    def test_returns_most_recent(self, repo):
        repo.upsert_exchange_rate(ExchangeRate(rate_date=date(2026, 8, 18), rate=Decimal("5.20")))
        repo.upsert_exchange_rate(ExchangeRate(rate_date=date(2026, 8, 20), rate=Decimal("5.25")))
        row = repo.get_latest_rate()
        assert row is not None
        assert row.rate_date == date(2026, 8, 20)


class TestGetRateHistory:
    def test_returns_empty_when_no_data(self, repo):
        assert repo.get_rate_history(days=30) == []

    def test_returns_rates_within_window(self, repo):
        today = date.today()
        repo.upsert_exchange_rate(ExchangeRate(rate_date=today, rate=Decimal("5.25")))
        repo.upsert_exchange_rate(
            ExchangeRate(rate_date=today - timedelta(days=10), rate=Decimal("5.20"))
        )
        repo.upsert_exchange_rate(
            ExchangeRate(rate_date=today - timedelta(days=60), rate=Decimal("5.10"))
        )

        result = repo.get_rate_history(days=30)
        assert len(result) == 2
        # Ordered by rate_date desc
        assert result[0].rate_date == today

    def test_respects_days_parameter(self, repo):
        today = date.today()
        repo.upsert_exchange_rate(
            ExchangeRate(rate_date=today - timedelta(days=5), rate=Decimal("5.25"))
        )
        assert len(repo.get_rate_history(days=3)) == 0
        assert len(repo.get_rate_history(days=10)) == 1


class TestBulkUpsertRates:
    def test_inserts_multiple_rates(self, repo):
        rates = [
            ExchangeRate(rate_date=date(2026, 8, 18), rate=Decimal("5.20")),
            ExchangeRate(rate_date=date(2026, 8, 19), rate=Decimal("5.22")),
            ExchangeRate(rate_date=date(2026, 8, 20), rate=Decimal("5.25")),
        ]
        repo.bulk_upsert_rates(rates)

        assert repo.get_exchange_rate(date(2026, 8, 18)) is not None
        assert repo.get_exchange_rate(date(2026, 8, 19)) is not None
        assert repo.get_exchange_rate(date(2026, 8, 20)) is not None

    def test_empty_list_is_noop(self, repo):
        repo.bulk_upsert_rates([])
        assert repo.get_latest_rate() is None
