"""Tests for portfolio component consistency (F136-T05).

Verifies:
1. cards_without_acquisition + invested_card_count = total collection count
2. export-pnl only includes cards with acquisition price (regression)
3. investment_only movers excludes cards without acquisition price
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from unittest.mock import MagicMock

from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.api.deps import get_currency_converter_dep, get_db, require_auth_or_api_key
from src.api.routers.collection import router
from src.database.models import PriceObservationRow, UserCollectionRow

_TEST_USER_ID = "eduardo"


def _make_row(**overrides) -> MagicMock:
    defaults = {
        "id": 1,
        "user_id": _TEST_USER_ID,
        "card_id": 42,
        "set_code": "DMR",
        "collector_number": "123",
        "name_en": "Lightning Bolt",
        "name_pt": "Raio",
        "set_name_en": "Dominaria Remastered",
        "quantity": 1,
        "quality": "NM",
        "language": "EN",
        "rarity": "R",
        "color": "R",
        "extras": None,
        "acquisition_price": Decimal("5.00"),
        "acquired_at": date(2026, 1, 15),
        "created_at": datetime(2026, 1, 1),
    }
    defaults.update(overrides)
    row = MagicMock(spec=UserCollectionRow)
    for k, v in defaults.items():
        setattr(row, k, v)
    return row


def _make_obs(**overrides) -> MagicMock:
    defaults = {
        "median_price": Decimal("8.50"),
        "tcg_price": None,
        "last_sold_price": None,
        "source": "liga",
        "observed_at": date(2026, 9, 1),
    }
    defaults.update(overrides)
    obs = MagicMock(spec=PriceObservationRow)
    for k, v in defaults.items():
        setattr(obs, k, v)
    return obs


def _make_app(mock_repo: MagicMock) -> FastAPI:
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_db] = lambda: mock_repo
    app.dependency_overrides[require_auth_or_api_key] = lambda: _TEST_USER_ID
    mock_converter = MagicMock()
    mock_converter.convert.return_value = None
    app.dependency_overrides[get_currency_converter_dep] = lambda: mock_converter
    return app


class TestPortfolioConsistency:
    """Verify cards_without_acquisition + invested_card_count = total."""

    def test_counts_sum_to_total(self) -> None:
        """cards_without_acquisition + invested_card_count should equal total collection."""
        mock_repo = MagicMock()
        # 3 cards with acquisition, 2 without = 5 total
        mock_repo.get_portfolio_invested_total.return_value = (Decimal("30.00"), 3)
        mock_repo.count_entries_without_acquisition.return_value = 2

        entries = [
            _make_row(id=1, card_id=42, acquisition_price=Decimal("10.00")),
            _make_row(id=2, card_id=43, acquisition_price=Decimal("10.00")),
            _make_row(id=3, card_id=44, acquisition_price=Decimal("10.00")),
        ]
        mock_repo.get_collection_entries_with_acquisition.return_value = entries
        mock_repo.get_latest_prices_batch.return_value = {
            42: _make_obs(),
            43: _make_obs(),
            44: _make_obs(),
        }

        client = TestClient(_make_app(mock_repo))
        resp = client.get("/collection/portfolio-summary")
        data = resp.json()["data"]

        # 3 invested + 2 without = 5 total
        assert data["invested_card_count"] + data["cards_without_acquisition"] == 5

    def test_export_pnl_only_acquisition_cards(self) -> None:
        """export-pnl endpoint only fetches entries with acquisition price."""
        mock_repo = MagicMock()
        entries = [
            _make_row(id=1, card_id=42, acquisition_price=Decimal("5.00")),
        ]
        mock_repo.get_collection_entries_with_acquisition.return_value = entries
        mock_repo.get_latest_prices_batch.return_value = {
            42: _make_obs(),
        }

        client = TestClient(_make_app(mock_repo))
        resp = client.get("/collection/export-pnl")

        assert resp.status_code == 200
        # Verify the repo method used is the acquisition-only one
        mock_repo.get_collection_entries_with_acquisition.assert_called_once_with(_TEST_USER_ID)

    def test_movers_investment_only_excludes_non_investment(self) -> None:
        """investment_only=true excludes cards without acquisition from movers."""
        mock_repo = MagicMock()
        mock_repo.get_trending_price_data_for_user.return_value = {
            42: [(date(2026, 9, 1), Decimal("5.00")), (date(2026, 9, 7), Decimal("10.00"))],
            99: [(date(2026, 9, 1), Decimal("3.00")), (date(2026, 9, 7), Decimal("6.00"))],
        }
        # Only card 42 has acquisition price
        entry = _make_row(card_id=42, acquisition_price=Decimal("5.00"))
        mock_repo.get_collection_entries_with_acquisition.return_value = [entry]
        mock_repo.get_card_info_with_image_batch.return_value = {
            42: ("Lightning Bolt", "DMR", "123", None),
        }

        client = TestClient(_make_app(mock_repo))
        resp = client.get("/collection/movers?investment_only=true")

        assert resp.status_code == 200
        data = resp.json()["data"]
        gainers = [g["card_id"] for g in data["gainers"]]
        losers = [x["card_id"] for x in data["losers"]]
        all_card_ids = gainers + losers
        assert 42 in all_card_ids
        assert 99 not in all_card_ids
