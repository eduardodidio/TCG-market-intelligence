"""Tests for has_acquisition_price filter on collection list endpoint (F136-T01)."""

from __future__ import annotations

from datetime import datetime
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
        "name_pt": "Raio",
        "set_name_en": "Dominaria Remastered",
        "set_name_pt": None,
        "notes": None,
        "quantity": 1,
        "quality": "NM",
        "language": "EN",
        "rarity": "R",
        "color": "R",
        "extras": None,
        "acquisition_price": None,
        "acquired_at": None,
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


class TestHasAcquisitionPriceFilter:
    """GET /collection?has_acquisition_price= filter tests."""

    def test_filter_true_returns_only_priced(self) -> None:
        """has_acquisition_price=true returns only entries with acquisition_price."""
        row = _make_row(id=1, acquisition_price=Decimal("5.00"))
        mock_repo = MagicMock()
        mock_repo.list_collection.return_value = [row]
        mock_repo.count_collection.return_value = 1
        mock_repo.get_latest_prices_batch.return_value = {}

        client = TestClient(_make_app(mock_repo))
        resp = client.get("/collection?has_acquisition_price=true")

        assert resp.status_code == 200
        mock_repo.list_collection.assert_called_once()
        call_kwargs = mock_repo.list_collection.call_args[1]
        assert call_kwargs["has_acquisition_price"] is True

    def test_filter_false_returns_only_unpriced(self) -> None:
        """has_acquisition_price=false returns only entries without acquisition_price."""
        row = _make_row(id=2, acquisition_price=None)
        mock_repo = MagicMock()
        mock_repo.list_collection.return_value = [row]
        mock_repo.count_collection.return_value = 1
        mock_repo.get_latest_prices_batch.return_value = {}

        client = TestClient(_make_app(mock_repo))
        resp = client.get("/collection?has_acquisition_price=false")

        assert resp.status_code == 200
        call_kwargs = mock_repo.list_collection.call_args[1]
        assert call_kwargs["has_acquisition_price"] is False

    def test_no_filter_returns_all(self) -> None:
        """No has_acquisition_price param returns all entries (backward compat)."""
        mock_repo = MagicMock()
        mock_repo.list_collection.return_value = []
        mock_repo.count_collection.return_value = 0
        mock_repo.get_latest_prices_batch.return_value = {}

        client = TestClient(_make_app(mock_repo))
        resp = client.get("/collection")

        assert resp.status_code == 200
        call_kwargs = mock_repo.list_collection.call_args[1]
        assert call_kwargs["has_acquisition_price"] is None

    def test_filter_combined_with_name_search(self) -> None:
        """Filter works alongside name search."""
        mock_repo = MagicMock()
        mock_repo.list_collection.return_value = []
        mock_repo.count_collection.return_value = 0
        mock_repo.get_latest_prices_batch.return_value = {}

        client = TestClient(_make_app(mock_repo))
        resp = client.get("/collection?name=bolt&has_acquisition_price=true")

        assert resp.status_code == 200
        call_kwargs = mock_repo.list_collection.call_args[1]
        assert call_kwargs["name_search"] == "bolt"
        assert call_kwargs["has_acquisition_price"] is True

    def test_filter_combined_with_set(self) -> None:
        """Filter works alongside set filter."""
        mock_repo = MagicMock()
        mock_repo.list_collection.return_value = []
        mock_repo.count_collection.return_value = 0
        mock_repo.get_latest_prices_batch.return_value = {}

        client = TestClient(_make_app(mock_repo))
        resp = client.get("/collection?set=DMR&has_acquisition_price=false")

        assert resp.status_code == 200
        call_kwargs = mock_repo.list_collection.call_args[1]
        assert call_kwargs["set_code"] == "DMR"
        assert call_kwargs["has_acquisition_price"] is False

    def test_total_reflects_filtered_count(self) -> None:
        """Pagination total matches filtered count."""
        row = _make_row(id=1, acquisition_price=Decimal("3.00"))
        mock_repo = MagicMock()
        mock_repo.list_collection.return_value = [row]
        mock_repo.count_collection.return_value = 1
        mock_repo.get_latest_prices_batch.return_value = {}

        client = TestClient(_make_app(mock_repo))
        resp = client.get("/collection?has_acquisition_price=true")

        assert resp.status_code == 200
        data = resp.json()
        assert data["meta"]["total"] == 1
        # count_collection should also receive the filter
        count_kwargs = mock_repo.count_collection.call_args[1]
        assert count_kwargs["has_acquisition_price"] is True

    def test_filter_false_with_price_sort(self) -> None:
        """has_acquisition_price=false with sort_by=price works."""
        mock_repo = MagicMock()
        mock_repo.list_collection.return_value = []
        mock_repo.count_collection.return_value = 0
        mock_repo.get_latest_prices_batch.return_value = {}

        client = TestClient(_make_app(mock_repo))
        resp = client.get("/collection?has_acquisition_price=false&sort_by=price&sort_dir=desc")

        assert resp.status_code == 200
        call_kwargs = mock_repo.list_collection.call_args[1]
        assert call_kwargs["has_acquisition_price"] is False
        assert call_kwargs["sort_by"] == "price"
