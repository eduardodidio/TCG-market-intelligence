"""Tests for price observation insertion validation (F185-T03).

Ensures that records with median_price <= 0 are rejected before reaching the DB,
while None and positive values are accepted normally.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from src.database.repository import Repository
from src.domain.models import HistoricalPrice


@pytest.fixture
def repo(tmp_path):
    db_path = tmp_path / "test.db"
    return Repository(f"sqlite:///{db_path}")


def _make_price(
    external_id: str = "card1",
    observed_at: date = date(2026, 1, 1),
    median_price: Decimal | None = Decimal("10.00"),
    **kwargs,
) -> HistoricalPrice:
    return HistoricalPrice(
        source="myp",
        external_id=external_id,
        observed_at=observed_at,
        median_price=median_price,
        currency="BRL",
        **kwargs,
    )


class TestPriceValidation:
    """Validation: insert_price_observations rejects median_price <= 0."""

    def test_zero_price_skipped(self, repo):
        prices = [_make_price(median_price=Decimal("0"))]
        count = repo.insert_price_observations(prices)
        assert count == 0

    def test_negative_price_skipped(self, repo):
        prices = [_make_price(median_price=Decimal("-5.00"))]
        count = repo.insert_price_observations(prices)
        assert count == 0

    def test_none_price_allowed(self, repo):
        prices = [_make_price(median_price=None)]
        count = repo.insert_price_observations(prices)
        assert count == 1

    def test_valid_price_inserted(self, repo):
        prices = [_make_price(median_price=Decimal("10.50"))]
        count = repo.insert_price_observations(prices)
        assert count == 1

    def test_mixed_batch(self, repo):
        """2 invalid + 3 valid = only 3 inserted."""
        prices = [
            _make_price(external_id="bad1", median_price=Decimal("0")),
            _make_price(external_id="bad2", median_price=Decimal("-3.00")),
            _make_price(
                external_id="ok1",
                observed_at=date(2026, 1, 1),
                median_price=Decimal("5.00"),
            ),
            _make_price(
                external_id="ok2",
                observed_at=date(2026, 1, 2),
                median_price=Decimal("15.00"),
            ),
            _make_price(
                external_id="ok3",
                observed_at=date(2026, 1, 3),
                median_price=None,
            ),
        ]
        count = repo.insert_price_observations(prices)
        assert count == 3

    def test_structlog_warning_emitted(self, repo):
        """Verify structlog warning is emitted for skipped records."""
        from unittest.mock import MagicMock, patch

        mock_logger = MagicMock()
        with patch("src.database.repository.logger", mock_logger):
            prices = [_make_price(median_price=Decimal("0"))]
            repo.insert_price_observations(prices)

        mock_logger.warning.assert_called_once_with(
            "skipping_invalid_price",
            external_id="card1",
            median_price=0.0,
        )

    def test_all_invalid_returns_zero(self, repo):
        """When all records are invalid, returns 0."""
        prices = [
            _make_price(external_id="a", median_price=Decimal("0")),
            _make_price(external_id="b", median_price=Decimal("-1")),
            _make_price(external_id="c", median_price=Decimal("-100")),
        ]
        count = repo.insert_price_observations(prices)
        assert count == 0

    def test_tcg_price_not_filtered(self, repo):
        """Records with zero tcg_price but valid median_price are NOT filtered."""
        prices = [
            _make_price(
                median_price=Decimal("10.00"),
                tcg_price=Decimal("0"),
            ),
        ]
        count = repo.insert_price_observations(prices)
        assert count == 1

    def test_last_sold_price_not_filtered(self, repo):
        """Records with zero last_sold_price but valid median_price are NOT filtered."""
        prices = [
            _make_price(
                median_price=Decimal("10.00"),
                last_sold_price=Decimal("0"),
            ),
        ]
        count = repo.insert_price_observations(prices)
        assert count == 1
