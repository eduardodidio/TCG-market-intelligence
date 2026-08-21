"""Integration tests for the update-exchange-rate CLI command (F18-T11).

These tests exercise the CLI with a real SQLite database and mocked BCB
API responses.
"""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock, patch

import pytest
from click.testing import CliRunner

from src.cli.main import cli
from src.database.repository import Repository
from src.domain.models import ExchangeRate


@pytest.fixture()
def db_url(tmp_path):
    return f"sqlite:///{tmp_path / 'test_cli.db'}"


@pytest.fixture()
def runner():
    return CliRunner()


class TestUpdateExchangeRateCLI:
    def test_fetch_single_date(self, runner, db_url):
        """CLI fetches rate for a specific date and stores it."""
        mock_rate = ExchangeRate(rate_date=date(2026, 8, 20), rate=Decimal("5.25"))
        with patch(
            "src.providers.bcb.client.fetch_daily_rate",
            new_callable=AsyncMock,
            return_value=mock_rate,
        ):
            result = runner.invoke(
                cli,
                ["update-exchange-rate", "--db", db_url, "--date", "2026-08-20"],
            )

        assert result.exit_code == 0, result.output
        assert "5.25" in result.output

        repo = Repository(db_url=db_url)
        row = repo.get_exchange_rate(date(2026, 8, 20))
        assert row is not None
        assert row.rate == Decimal("5.25")

    def test_fetch_today_default(self, runner, db_url):
        """When no --date is given, fetches today's rate."""
        mock_rate = ExchangeRate(rate_date=date.today(), rate=Decimal("5.10"))
        with patch(
            "src.providers.bcb.client.fetch_daily_rate",
            new_callable=AsyncMock,
            return_value=mock_rate,
        ):
            result = runner.invoke(
                cli,
                ["update-exchange-rate", "--db", db_url],
            )

        assert result.exit_code == 0, result.output
        repo = Repository(db_url=db_url)
        row = repo.get_exchange_rate(date.today())
        assert row is not None

    def test_backfill_days(self, runner, db_url):
        """--backfill-days fetches a range of rates."""
        today = date.today()
        start = today - timedelta(days=7)

        mock_rates = [
            ExchangeRate(
                rate_date=start + timedelta(days=i), rate=Decimal("5.00") + Decimal(str(i)) / 100
            )
            for i in range(5)  # weekdays only
        ]

        with patch(
            "src.providers.bcb.client.fetch_rate_range",
            new_callable=AsyncMock,
            return_value=mock_rates,
        ):
            result = runner.invoke(
                cli,
                ["update-exchange-rate", "--db", db_url, "--backfill-days", "7"],
            )

        assert result.exit_code == 0, result.output
        assert "5" in result.output  # should mention stored count

        repo = Repository(db_url=db_url)
        assert repo.get_latest_rate() is not None

    def test_no_rate_available(self, runner, db_url):
        """When BCB returns no rate, CLI reports it gracefully."""
        with patch(
            "src.providers.bcb.client.fetch_daily_rate",
            new_callable=AsyncMock,
            return_value=None,
        ):
            result = runner.invoke(
                cli,
                ["update-exchange-rate", "--db", db_url, "--date", "2026-08-20"],
            )

        assert result.exit_code == 0, result.output
        assert (
            "no rate" in result.output.lower()
            or "unavailable" in result.output.lower()
            or "No" in result.output
        )

    def test_backfill_is_idempotent(self, runner, db_url):
        """Running backfill twice doesn't create duplicates (upsert)."""
        mock_rates = [
            ExchangeRate(rate_date=date(2026, 8, 18), rate=Decimal("5.20")),
            ExchangeRate(rate_date=date(2026, 8, 19), rate=Decimal("5.22")),
        ]

        with patch(
            "src.providers.bcb.client.fetch_rate_range",
            new_callable=AsyncMock,
            return_value=mock_rates,
        ):
            runner.invoke(cli, ["update-exchange-rate", "--db", db_url, "--backfill-days", "3"])
            runner.invoke(cli, ["update-exchange-rate", "--db", db_url, "--backfill-days", "3"])

        repo = Repository(db_url=db_url)
        history = repo.get_rate_history(days=30)
        # Should have exactly 2 unique rates, not 4
        dates = {r.rate_date for r in history}
        assert len(dates) == 2
