"""F124-T03: acquisition_price / acquired_at surfaced in list + detail endpoints."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from unittest.mock import MagicMock

from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.api.deps import get_currency_converter_dep, get_db, require_auth_or_api_key
from src.api.routers.collection import router
from src.database.models import CardRow, UserCollectionRow

_TEST_USER_ID = "eduardo"


def _make_collection_row(**overrides) -> MagicMock:
    defaults = {
        "id": 1,
        "user_id": _TEST_USER_ID,
        "card_id": None,
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
        "acquisition_price": None,
        "acquired_at": None,
        "created_at": datetime(2026, 1, 1),
    }
    defaults.update(overrides)
    row = MagicMock(spec=UserCollectionRow)
    for k, v in defaults.items():
        setattr(row, k, v)
    return row


def _make_card_row(**overrides) -> MagicMock:
    defaults = {
        "id": 42,
        "name": "Raio",
        "name_en": "Lightning Bolt",
        "set_code": "DMR",
    }
    defaults.update(overrides)
    row = MagicMock(spec=CardRow)
    for k, v in defaults.items():
        setattr(row, k, v)
    return row


def _make_app(mock_repo: MagicMock, user_id: str = _TEST_USER_ID) -> FastAPI:
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_db] = lambda: mock_repo
    app.dependency_overrides[require_auth_or_api_key] = lambda: user_id
    mock_converter = MagicMock()
    mock_converter.convert.return_value = None
    app.dependency_overrides[get_currency_converter_dep] = lambda: mock_converter
    return app


class TestListCollectionAcquisitionFields:
    """GET /collection — acquisition_price / acquired_at."""

    def test_entry_with_acquisition_price_and_date(self) -> None:
        mock_repo = MagicMock()
        mock_repo.list_collection.return_value = [
            _make_collection_row(
                acquisition_price=Decimal("12.50"),
                acquired_at=date(2026, 9, 1),
            )
        ]
        mock_repo.count_collection.return_value = 1
        mock_repo.get_latest_prices_batch.return_value = {}

        client = TestClient(_make_app(mock_repo))
        resp = client.get("/collection")
        assert resp.status_code == 200
        data = resp.json()["data"][0]
        assert data["acquisition_price"] == 12.5
        assert data["acquired_at"] == "2026-09-01"

    def test_entry_without_acquisition_price_is_null(self) -> None:
        mock_repo = MagicMock()
        mock_repo.list_collection.return_value = [
            _make_collection_row(acquisition_price=None, acquired_at=None)
        ]
        mock_repo.count_collection.return_value = 1
        mock_repo.get_latest_prices_batch.return_value = {}

        client = TestClient(_make_app(mock_repo))
        resp = client.get("/collection")
        assert resp.status_code == 200
        data = resp.json()["data"][0]
        assert data["acquisition_price"] is None
        assert data["acquired_at"] is None


class TestCollectionDetailAcquisitionFields:
    """GET /collection/{id} — acquisition_price / acquired_at."""

    def test_entry_with_acquisition_price_and_date(self) -> None:
        mock_repo = MagicMock()
        mock_repo.get_collection_entry.return_value = _make_collection_row(
            card_id=42,
            acquisition_price=Decimal("12.50"),
            acquired_at=date(2026, 9, 1),
        )
        mock_repo.get_card_by_id.return_value = _make_card_row()
        mock_repo.get_source_cards_for_card.return_value = []
        mock_repo.get_latest_prices_batch.return_value = {}
        mock_repo.get_price_series.return_value = []

        client = TestClient(_make_app(mock_repo))
        resp = client.get("/collection/1")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["acquisition_price"] == 12.5
        assert data["acquired_at"] == "2026-09-01"

    def test_entry_without_acquisition_price_is_null(self) -> None:
        mock_repo = MagicMock()
        mock_repo.get_collection_entry.return_value = _make_collection_row(
            card_id=None,
            acquisition_price=None,
            acquired_at=None,
        )

        client = TestClient(_make_app(mock_repo))
        resp = client.get("/collection/1")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["acquisition_price"] is None
        assert data["acquired_at"] is None
