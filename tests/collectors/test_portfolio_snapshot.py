"""Tests for portfolio snapshot service (F80-T02)."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from unittest.mock import MagicMock

import pytest

from src.collectors.portfolio_snapshot import take_snapshot


@pytest.fixture()
def mock_repo():
    repo = MagicMock()
    repo.get_collection_total_value.return_value = Decimal("1234.56")
    repo.get_collection_summary.return_value = {
        "total_unique": 349,
        "total_cards": 500,
        "linked_count": 300,
        "priced_count": 280,
        "sets_count": 15,
    }
    return repo


class TestTakeSnapshot:
    def test_snapshot_returns_correct_data(self, mock_repo):
        result = take_snapshot("1", mock_repo)

        assert result["user_id"] == "1"
        assert result["date"] == date.today()
        assert result["value"] == Decimal("1234.56")
        assert result["priced_count"] == 280
        assert result["total_cards"] == 500

    def test_snapshot_calls_upsert(self, mock_repo):
        take_snapshot("1", mock_repo)

        mock_repo.upsert_portfolio_snapshot.assert_called_once_with(
            user_id="1",
            snapshot_date=date.today(),
            total_value_brl=Decimal("1234.56"),
            priced_card_count=280,
            total_card_count=500,
        )

    def test_snapshot_with_no_value(self, mock_repo):
        mock_repo.get_collection_total_value.return_value = None

        result = take_snapshot("1", mock_repo)

        assert result["value"] == Decimal("0")
        mock_repo.upsert_portfolio_snapshot.assert_called_once()
        call_kwargs = mock_repo.upsert_portfolio_snapshot.call_args[1]
        assert call_kwargs["total_value_brl"] == Decimal("0")

    def test_snapshot_with_zero_priced_cards(self, mock_repo):
        mock_repo.get_collection_summary.return_value = {
            "total_unique": 10,
            "total_cards": 10,
            "linked_count": 0,
            "priced_count": 0,
            "sets_count": 2,
        }
        mock_repo.get_collection_total_value.return_value = None

        result = take_snapshot("1", mock_repo)

        assert result["priced_count"] == 0
        assert result["total_cards"] == 10
        assert result["value"] == Decimal("0")
