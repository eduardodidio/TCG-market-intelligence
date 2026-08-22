"""Tests for GET /collection/{entry_id}/history endpoint."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from unittest.mock import MagicMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.api.deps import get_currency_converter_dep, get_db, require_auth_or_api_key
from src.api.routers.collection import router
from src.database.models import PriceObservationRow, SourceCardRow, UserCollectionRow

_TEST_USER_ID = "test-user"


def _make_collection_row(**overrides) -> MagicMock:
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
    }
    defaults.update(overrides)
    row = MagicMock(spec=UserCollectionRow)
    for k, v in defaults.items():
        setattr(row, k, v)
    return row


def _make_source_card(**overrides) -> MagicMock:
    defaults = {
        "id": 10,
        "source": "myp",
        "external_id": "99999",
        "card_id": 42,
        "sku": "magic_dmr_123",
        "url": "https://mypcards.com/magic/99999/lightning-bolt",
        "name_en": "Lightning Bolt",
        "name_pt": "Raio",
        "set_code": "DMR",
        "collector_number": "123",
    }
    defaults.update(overrides)
    sc = MagicMock(spec=SourceCardRow)
    for k, v in defaults.items():
        setattr(sc, k, v)
    return sc


def _make_price_obs(
    day: int = 20,
    median: str = "8.50",
    tcg: str | None = "7.00",
    last_sold: str | None = "9.00",
    **overrides,
) -> MagicMock:
    defaults = {
        "id": 100 + day,
        "source": "myp",
        "external_id": "99999",
        "observed_at": date(2026, 8, day),
        "median_price": Decimal(median),
        "tcg_price": Decimal(tcg) if tcg else None,
        "last_sold_price": Decimal(last_sold) if last_sold else None,
        "quantity_available": 5,
        "last_sold_meta": None,
        "currency": "BRL",
    }
    defaults.update(overrides)
    obs = MagicMock(spec=PriceObservationRow)
    for k, v in defaults.items():
        setattr(obs, k, v)
    return obs


def _make_app(
    mock_repo: MagicMock,
    user_id: str = _TEST_USER_ID,
    converter: MagicMock | None = None,
) -> FastAPI:
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_db] = lambda: mock_repo
    app.dependency_overrides[require_auth_or_api_key] = lambda: user_id

    if converter is None:
        converter = MagicMock()
        converter.convert.side_effect = lambda price, d, curr: price
    app.dependency_overrides[get_currency_converter_dep] = lambda: converter

    return app


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestCollectionHistory:
    def test_requires_auth(self) -> None:
        """Endpoint requires auth; without override returns error."""
        mock_repo = MagicMock()
        app = FastAPI()
        app.include_router(router)
        app.dependency_overrides[get_db] = lambda: mock_repo
        converter = MagicMock()
        converter.convert.side_effect = lambda price, d, curr: price
        app.dependency_overrides[get_currency_converter_dep] = lambda: converter
        # No auth override — dependency will fail
        client = TestClient(app, raise_server_exceptions=False)
        resp = client.get("/collection/1/history")
        # Without auth, should get an error status (depends on how require_auth is wired)
        assert resp.status_code != 200

    def test_returns_404_for_other_user(self) -> None:
        mock_repo = MagicMock()
        mock_repo.get_collection_entry.return_value = _make_collection_row(
            user_id="other-user",
        )
        app = _make_app(mock_repo, user_id=_TEST_USER_ID)
        client = TestClient(app)

        resp = client.get("/collection/1/history")
        assert resp.status_code == 404

    def test_returns_observations(self) -> None:
        mock_repo = MagicMock()
        mock_repo.get_collection_entry.return_value = _make_collection_row()
        mock_repo.get_source_cards_for_card.return_value = [_make_source_card()]
        mock_repo.get_price_series.return_value = [
            _make_price_obs(day=18, median="10.00"),
            _make_price_obs(day=19, median="12.00"),
            _make_price_obs(day=20, median="15.00"),
        ]

        app = _make_app(mock_repo)
        client = TestClient(app)

        resp = client.get("/collection/1/history")
        assert resp.status_code == 200
        body = resp.json()
        data = body["data"]
        assert len(data["observations"]) == 3
        assert data["summary"] is not None
        assert data["summary"]["period"] == "30d"
        assert data["summary"]["data_points"] == 3

    def test_empty_for_unlinked(self) -> None:
        mock_repo = MagicMock()
        mock_repo.get_collection_entry.return_value = _make_collection_row(
            card_id=None,
        )

        app = _make_app(mock_repo)
        client = TestClient(app)

        resp = client.get("/collection/1/history")
        assert resp.status_code == 200
        body = resp.json()
        assert body["data"]["observations"] == []
        assert body["data"]["summary"] is None

    def test_applies_period_filter(self) -> None:
        mock_repo = MagicMock()
        mock_repo.get_collection_entry.return_value = _make_collection_row()
        mock_repo.get_source_cards_for_card.return_value = [_make_source_card()]
        mock_repo.get_price_series.return_value = []

        app = _make_app(mock_repo)
        client = TestClient(app)

        resp = client.get("/collection/1/history?period=7d")
        assert resp.status_code == 200

        # Verify get_price_series was called with days=7
        call_kwargs = mock_repo.get_price_series.call_args
        assert call_kwargs[1]["days"] == 7

    def test_applies_currency_conversion(self) -> None:
        mock_repo = MagicMock()
        mock_repo.get_collection_entry.return_value = _make_collection_row()
        mock_repo.get_source_cards_for_card.return_value = [_make_source_card()]
        mock_repo.get_price_series.return_value = [
            _make_price_obs(day=20, median="10.00"),
        ]

        converter = MagicMock()
        converter.convert.side_effect = lambda price, d, curr: (
            price / Decimal("5.00") if curr == "USD" and price else price
        )

        app = _make_app(mock_repo, converter=converter)
        client = TestClient(app)

        resp = client.get("/collection/1/history?currency=USD")
        assert resp.status_code == 200
        body = resp.json()
        obs = body["data"]["observations"][0]
        assert obs["currency"] == "USD"
        assert float(obs["median_price"]) == pytest.approx(2.0)

    def test_invalid_period(self) -> None:
        mock_repo = MagicMock()
        mock_repo.get_collection_entry.return_value = _make_collection_row()

        app = _make_app(mock_repo)
        client = TestClient(app)

        resp = client.get("/collection/1/history?period=3y")
        assert resp.status_code == 422

    def test_entry_not_found(self) -> None:
        mock_repo = MagicMock()
        mock_repo.get_collection_entry.return_value = None

        app = _make_app(mock_repo)
        client = TestClient(app)

        resp = client.get("/collection/1/history")
        assert resp.status_code == 404
