"""Tests for portfolio-summary cards_without_acquisition field (F136-T02)."""

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
        "quantity": 2,
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


class TestPortfolioSummaryCardsWithoutAcquisition:
    """GET /collection/portfolio-summary — cards_without_acquisition field."""

    def test_includes_cards_without_acquisition_field(self) -> None:
        mock_repo = MagicMock()
        mock_repo.get_portfolio_invested_total.return_value = (Decimal("10.00"), 1)
        mock_repo.count_entries_without_acquisition.return_value = 3
        entry = _make_row(card_id=42, acquisition_price=Decimal("5.00"))
        mock_repo.get_collection_entries_with_acquisition.return_value = [entry]
        mock_repo.get_latest_prices_batch.return_value = {42: _make_obs()}

        client = TestClient(_make_app(mock_repo))
        resp = client.get("/collection/portfolio-summary")

        assert resp.status_code == 200
        data = resp.json()["data"]
        assert "cards_without_acquisition" in data
        assert data["cards_without_acquisition"] == 3

    def test_correct_count_mix_of_with_and_without(self) -> None:
        mock_repo = MagicMock()
        mock_repo.get_portfolio_invested_total.return_value = (Decimal("20.00"), 2)
        mock_repo.count_entries_without_acquisition.return_value = 5

        entries = [
            _make_row(id=1, card_id=42, acquisition_price=Decimal("10.00")),
            _make_row(id=2, card_id=43, acquisition_price=Decimal("10.00")),
        ]
        mock_repo.get_collection_entries_with_acquisition.return_value = entries
        mock_repo.get_latest_prices_batch.return_value = {
            42: _make_obs(median_price=Decimal("15.00")),
            43: _make_obs(median_price=Decimal("12.00")),
        }

        client = TestClient(_make_app(mock_repo))
        resp = client.get("/collection/portfolio-summary")
        data = resp.json()["data"]

        assert data["invested_card_count"] == 2
        assert data["cards_without_acquisition"] == 5

    def test_unpriced_card_count_populated(self) -> None:
        """Entries with acquisition but no market price counted as unpriced."""
        mock_repo = MagicMock()
        mock_repo.get_portfolio_invested_total.return_value = (Decimal("10.00"), 2)
        mock_repo.count_entries_without_acquisition.return_value = 0

        entries = [
            _make_row(id=1, card_id=42, acquisition_price=Decimal("5.00")),
            _make_row(id=2, card_id=43, acquisition_price=Decimal("5.00")),
        ]
        mock_repo.get_collection_entries_with_acquisition.return_value = entries
        # Only card_id=42 has a price; card_id=43 has no obs
        mock_repo.get_latest_prices_batch.return_value = {
            42: _make_obs(median_price=Decimal("8.00")),
        }

        client = TestClient(_make_app(mock_repo))
        resp = client.get("/collection/portfolio-summary")
        data = resp.json()["data"]

        assert data["unpriced_card_count"] == 1

    def test_all_cards_have_acquisition(self) -> None:
        mock_repo = MagicMock()
        mock_repo.get_portfolio_invested_total.return_value = (Decimal("10.00"), 2)
        mock_repo.count_entries_without_acquisition.return_value = 0
        entries = [
            _make_row(id=1, card_id=42, acquisition_price=Decimal("5.00")),
            _make_row(id=2, card_id=43, acquisition_price=Decimal("5.00")),
        ]
        mock_repo.get_collection_entries_with_acquisition.return_value = entries
        mock_repo.get_latest_prices_batch.return_value = {
            42: _make_obs(),
            43: _make_obs(),
        }

        client = TestClient(_make_app(mock_repo))
        resp = client.get("/collection/portfolio-summary")
        data = resp.json()["data"]

        assert data["cards_without_acquisition"] == 0

    def test_no_cards_have_acquisition(self) -> None:
        mock_repo = MagicMock()
        mock_repo.get_portfolio_invested_total.return_value = (Decimal("0"), 0)
        mock_repo.count_entries_without_acquisition.return_value = 5

        client = TestClient(_make_app(mock_repo))
        resp = client.get("/collection/portfolio-summary")
        data = resp.json()["data"]

        assert data["invested_card_count"] == 0
        assert data["cards_without_acquisition"] == 5
