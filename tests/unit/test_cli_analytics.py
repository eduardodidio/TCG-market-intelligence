"""Tests for CLI analytics commands (analyze card, analyze list)."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from src.cli.main import cli
from src.domain.models import (
    CardAnalytics,
    HistoricalPrice,
    Momentum,
    MovingAverage,
    PriceExtremes,
    Volatility,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_prices(n: int = 10, external_id: str = "12345") -> list[HistoricalPrice]:
    """Build a list of HistoricalPrice with sequential dates."""
    base = date(2026, 1, 1)
    return [
        HistoricalPrice(
            source="myp",
            external_id=external_id,
            observed_at=date.fromordinal(base.toordinal() + i),
            median_price=Decimal("10.00") + Decimal(str(i)),
            tcg_price=Decimal("9.50") + Decimal(str(i)),
            currency="BRL",
        )
        for i in range(n)
    ]


def _make_analytics(external_id: str = "12345", source: str = "myp") -> CardAnalytics:
    """Build a full CardAnalytics for output formatting tests."""
    return CardAnalytics(
        external_id=external_id,
        source=source,
        moving_averages=[
            MovingAverage(period=7, value=Decimal("12.34"), price_field="median_price", calculated_at=date(2026, 1, 10)),
            MovingAverage(period=30, value=Decimal("11.89"), price_field="median_price", calculated_at=date(2026, 1, 10)),
        ],
        extremes=PriceExtremes(
            ath_price=Decimal("15.00"),
            ath_date=date(2026, 3, 15),
            atl_price=Decimal("8.50"),
            atl_date=date(2025, 11, 2),
            price_field="median_price",
        ),
        volatility=Volatility(
            period_days=30,
            std_dev=Decimal("1.23"),
            coefficient_of_variation=Decimal("0.103"),
            price_field="median_price",
        ),
        momentum=Momentum(
            period_days=7,
            rate_of_change=Decimal("5.2"),
            trend_direction="up",
            price_field="median_price",
        ),
        computed_at=datetime(2026, 1, 10, 12, 0, 0),
    )


# ---------------------------------------------------------------------------
# analyze card — happy path
# ---------------------------------------------------------------------------

class TestAnalyzeCard:
    def test_happy_path(self):
        """Full analytics output is printed when card has data."""
        runner = CliRunner()
        prices = _make_prices(n=30)
        analytics = _make_analytics()

        with patch("src.database.repository.Repository") as MockRepo, \
             patch("src.analytics.indicators.compute_card_analytics", return_value=analytics) as mock_compute:
            mock_repo = MagicMock()
            MockRepo.return_value = mock_repo
            mock_repo.get_price_series.return_value = prices

            result = runner.invoke(cli, ["analyze", "card", "12345"])

        assert result.exit_code == 0
        assert "=== Card Analytics: 12345 (myp) ===" in result.output
        assert "Price field: median_price" in result.output
        assert "Data points: 30" in result.output
        assert "MA(7)" in result.output
        assert "R$ 12.34" in result.output
        assert "MA(30)" in result.output
        assert "R$ 11.89" in result.output
        assert "ATH: R$ 15.00 (2026-03-15)" in result.output
        assert "ATL: R$ 8.50 (2025-11-02)" in result.output
        assert "Std Dev: R$ 1.23" in result.output
        assert "CoV:     10.3%" in result.output
        assert "RoC:   +5.2%" in result.output
        assert "Trend: up" in result.output

        MockRepo.assert_called_once_with(db_url="sqlite:///tcg_market.db")
        mock_repo.get_price_series.assert_called_once_with(source="myp", external_id="12345")
        mock_compute.assert_called_once_with(
            prices=prices,
            source="myp",
            external_id="12345",
            price_field="median_price",
        )

    def test_no_data(self):
        """Prints friendly message when card has no observations."""
        runner = CliRunner()

        with patch("src.database.repository.Repository") as MockRepo:
            mock_repo = MagicMock()
            MockRepo.return_value = mock_repo
            mock_repo.get_price_series.return_value = []

            result = runner.invoke(cli, ["analyze", "card", "99999"])

        assert result.exit_code == 0
        assert "No data found for card 99999" in result.output
        assert "source=myp" in result.output

    def test_custom_options(self):
        """Respects --db, --source, and --price-field options."""
        runner = CliRunner()
        prices = _make_prices(n=10)
        analytics = _make_analytics()

        with patch("src.database.repository.Repository") as MockRepo, \
             patch("src.analytics.indicators.compute_card_analytics", return_value=analytics):
            mock_repo = MagicMock()
            MockRepo.return_value = mock_repo
            mock_repo.get_price_series.return_value = prices

            result = runner.invoke(cli, [
                "analyze", "card",
                "--db", "sqlite:///custom.db",
                "--source", "tcgplayer",
                "--price-field", "tcg_price",
                "ABC123",
            ])

        assert result.exit_code == 0
        MockRepo.assert_called_once_with(db_url="sqlite:///custom.db")
        mock_repo.get_price_series.assert_called_once_with(source="tcgplayer", external_id="ABC123")
        assert "Price field: tcg_price" in result.output

    def test_negative_momentum(self):
        """Negative RoC is printed without + sign."""
        runner = CliRunner()
        prices = _make_prices(n=10)
        analytics = _make_analytics()
        analytics.momentum = Momentum(
            period_days=7,
            rate_of_change=Decimal("-3.8"),
            trend_direction="down",
            price_field="median_price",
        )

        with patch("src.database.repository.Repository") as MockRepo, \
             patch("src.analytics.indicators.compute_card_analytics", return_value=analytics):
            mock_repo = MagicMock()
            MockRepo.return_value = mock_repo
            mock_repo.get_price_series.return_value = prices

            result = runner.invoke(cli, ["analyze", "card", "12345"])

        assert result.exit_code == 0
        assert "RoC:   -3.8%" in result.output
        assert "Trend: down" in result.output

    def test_partial_analytics(self):
        """Sections are omitted when analytics fields are None."""
        runner = CliRunner()
        prices = _make_prices(n=5)
        analytics = CardAnalytics(
            external_id="12345",
            source="myp",
            moving_averages=[],
            extremes=None,
            volatility=None,
            momentum=None,
        )

        with patch("src.database.repository.Repository") as MockRepo, \
             patch("src.analytics.indicators.compute_card_analytics", return_value=analytics):
            mock_repo = MagicMock()
            MockRepo.return_value = mock_repo
            mock_repo.get_price_series.return_value = prices

            result = runner.invoke(cli, ["analyze", "card", "12345"])

        assert result.exit_code == 0
        assert "=== Card Analytics: 12345 (myp) ===" in result.output
        assert "Moving Averages:" not in result.output
        assert "Price Extremes:" not in result.output
        assert "Volatility" not in result.output
        assert "Momentum" not in result.output


# ---------------------------------------------------------------------------
# analyze list
# ---------------------------------------------------------------------------

class TestAnalyzeList:
    def test_happy_path(self):
        """Prints table of cards with observation counts."""
        runner = CliRunner()

        with patch("src.database.repository.Repository") as MockRepo:
            mock_repo = MagicMock()
            MockRepo.return_value = mock_repo
            mock_repo.get_cards_with_observations.return_value = [
                ("card_001", 277),
                ("card_002", 150),
            ]

            result = runner.invoke(cli, ["analyze", "list"])

        assert result.exit_code == 0
        assert "card_001" in result.output
        assert "277" in result.output
        assert "card_002" in result.output
        assert "150" in result.output
        assert "Total: 2 cards" in result.output
        MockRepo.assert_called_once_with(db_url="sqlite:///tcg_market.db")
        mock_repo.get_cards_with_observations.assert_called_once_with(source="myp")

    def test_no_cards(self):
        """Prints friendly message when no cards exist."""
        runner = CliRunner()

        with patch("src.database.repository.Repository") as MockRepo:
            mock_repo = MagicMock()
            MockRepo.return_value = mock_repo
            mock_repo.get_cards_with_observations.return_value = []

            result = runner.invoke(cli, ["analyze", "list"])

        assert result.exit_code == 0
        assert "No cards found" in result.output

    def test_custom_source(self):
        """Respects --source option."""
        runner = CliRunner()

        with patch("src.database.repository.Repository") as MockRepo:
            mock_repo = MagicMock()
            MockRepo.return_value = mock_repo
            mock_repo.get_cards_with_observations.return_value = [("x", 1)]

            result = runner.invoke(cli, ["analyze", "list", "--source", "tcgplayer"])

        mock_repo.get_cards_with_observations.assert_called_once_with(source="tcgplayer")
