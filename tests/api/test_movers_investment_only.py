"""Tests for movers investment_only filter (F136-T02)."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from unittest.mock import MagicMock

from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.api.deps import get_currency_converter_dep, get_db, require_auth_or_api_key
from src.api.routers.collection import router
from src.database.models import UserCollectionRow

_TEST_USER_ID = "eduardo"


def _make_row(**overrides) -> MagicMock:
    defaults = {
        "id": 1,
        "user_id": _TEST_USER_ID,
        "card_id": 42,
        "set_code": "DMR",
        "collector_number": "123",
        "name_en": "Lightning Bolt",
        "name_pt": None,
        "quantity": 1,
        "quality": "NM",
        "language": "EN",
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


def _make_app(mock_repo: MagicMock) -> FastAPI:
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_db] = lambda: mock_repo
    app.dependency_overrides[require_auth_or_api_key] = lambda: _TEST_USER_ID
    mock_converter = MagicMock()
    mock_converter.convert.return_value = None
    app.dependency_overrides[get_currency_converter_dep] = lambda: mock_converter
    return app


class TestMoversInvestmentOnly:
    """GET /collection/movers?investment_only= tests."""

    def test_investment_only_true_filters_to_acquisition_cards(self) -> None:
        """Only cards with acquisition_price appear in movers."""
        mock_repo = MagicMock()
        # card 42 has acquisition, card 99 does not
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
        # Card 42 should be a gainer, card 99 should be excluded
        gainer_ids = [g["card_id"] for g in data["gainers"]]
        assert 42 in gainer_ids
        assert 99 not in gainer_ids

    def test_investment_only_false_returns_all(self) -> None:
        """Default behavior: all cards with price data."""
        mock_repo = MagicMock()
        mock_repo.get_trending_price_data_for_user.return_value = {
            42: [(date(2026, 9, 1), Decimal("5.00")), (date(2026, 9, 7), Decimal("10.00"))],
            99: [(date(2026, 9, 1), Decimal("3.00")), (date(2026, 9, 7), Decimal("6.00"))],
        }
        mock_repo.get_card_info_with_image_batch.return_value = {
            42: ("Lightning Bolt", "DMR", "123", None),
            99: ("Counterspell", "MH2", "12", None),
        }

        client = TestClient(_make_app(mock_repo))
        resp = client.get("/collection/movers?investment_only=false")

        assert resp.status_code == 200
        data = resp.json()["data"]
        gainer_ids = [g["card_id"] for g in data["gainers"]]
        assert 42 in gainer_ids
        assert 99 in gainer_ids

    def test_no_param_returns_all_backward_compat(self) -> None:
        """No investment_only param = all cards (backward compatible)."""
        mock_repo = MagicMock()
        mock_repo.get_trending_price_data_for_user.return_value = {
            42: [(date(2026, 9, 1), Decimal("5.00")), (date(2026, 9, 7), Decimal("10.00"))],
        }
        mock_repo.get_card_info_with_image_batch.return_value = {
            42: ("Lightning Bolt", "DMR", "123", None),
        }

        client = TestClient(_make_app(mock_repo))
        resp = client.get("/collection/movers")

        assert resp.status_code == 200
        # Should NOT call get_collection_entries_with_acquisition
        mock_repo.get_collection_entries_with_acquisition.assert_not_called()

    def test_investment_only_no_investment_cards_empty(self) -> None:
        """investment_only=true with no investment cards returns empty."""
        mock_repo = MagicMock()
        mock_repo.get_trending_price_data_for_user.return_value = {
            42: [(date(2026, 9, 1), Decimal("5.00")), (date(2026, 9, 7), Decimal("10.00"))],
        }
        mock_repo.get_collection_entries_with_acquisition.return_value = []

        client = TestClient(_make_app(mock_repo))
        resp = client.get("/collection/movers?investment_only=true")

        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["gainers"] == []
        assert data["losers"] == []
