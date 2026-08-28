"""Tests for GET /collection/valuation endpoint (F80-T03)."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from unittest.mock import MagicMock

from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.api.deps import get_currency_converter_dep, get_db, require_auth_or_api_key
from src.api.routers.collection import router
from src.database.models import PortfolioSnapshotRow
from src.services.currency import CurrencyConverter


def _make_snapshot(**overrides) -> MagicMock:
    defaults = {
        "id": 1,
        "user_id": "1",
        "snapshot_date": date(2026, 8, 27),
        "total_value_brl": Decimal("1234.56"),
        "priced_card_count": 300,
        "total_card_count": 349,
    }
    defaults.update(overrides)
    row = MagicMock(spec=PortfolioSnapshotRow)
    for k, v in defaults.items():
        setattr(row, k, v)
    return row


def _make_app(mock_repo, user_id="1", converter=None):
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_db] = lambda: mock_repo
    app.dependency_overrides[require_auth_or_api_key] = lambda: user_id
    if converter:
        app.dependency_overrides[get_currency_converter_dep] = lambda: converter
    return app


class TestValuationEndpoint:
    def test_empty_snapshots(self):
        mock_repo = MagicMock()
        mock_repo.get_portfolio_snapshots.return_value = []
        app = _make_app(mock_repo)
        client = TestClient(app)

        resp = client.get("/collection/valuation")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["current_value"] is None
        assert data["change_pct"] is None
        assert data["snapshots"] == []

    def test_single_snapshot_no_change(self):
        snap = _make_snapshot()
        mock_repo = MagicMock()
        mock_repo.get_portfolio_snapshots.return_value = [snap]
        app = _make_app(mock_repo)
        client = TestClient(app)

        resp = client.get("/collection/valuation")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["current_value"] == 1234.56
        assert data["previous_value"] is None
        assert data["change_pct"] is None
        assert len(data["snapshots"]) == 1

    def test_two_snapshots_positive_change(self):
        snap_latest = _make_snapshot(
            id=2,
            snapshot_date=date(2026, 8, 27),
            total_value_brl=Decimal("1300.00"),
        )
        snap_prev = _make_snapshot(
            id=1,
            snapshot_date=date(2026, 8, 26),
            total_value_brl=Decimal("1000.00"),
        )
        mock_repo = MagicMock()
        mock_repo.get_portfolio_snapshots.return_value = [snap_latest, snap_prev]
        app = _make_app(mock_repo)
        client = TestClient(app)

        resp = client.get("/collection/valuation")
        data = resp.json()["data"]
        assert data["current_value"] == 1300.0
        assert data["previous_value"] == 1000.0
        assert data["change_pct"] == 30.0
        assert data["change_abs"] == 300.0

    def test_negative_change(self):
        snap_latest = _make_snapshot(
            id=2,
            snapshot_date=date(2026, 8, 27),
            total_value_brl=Decimal("900.00"),
        )
        snap_prev = _make_snapshot(
            id=1,
            snapshot_date=date(2026, 8, 26),
            total_value_brl=Decimal("1000.00"),
        )
        mock_repo = MagicMock()
        mock_repo.get_portfolio_snapshots.return_value = [snap_latest, snap_prev]
        app = _make_app(mock_repo)
        client = TestClient(app)

        resp = client.get("/collection/valuation")
        data = resp.json()["data"]
        assert data["change_pct"] == -10.0
        assert data["change_abs"] == -100.0

    def test_days_param_forwarded_to_repo(self):
        mock_repo = MagicMock()
        mock_repo.get_portfolio_snapshots.return_value = []
        app = _make_app(mock_repo)
        client = TestClient(app)

        client.get("/collection/valuation?days=7")
        mock_repo.get_portfolio_snapshots.assert_called_once_with("1", days=7)

    def test_currency_param_in_response(self):
        mock_repo = MagicMock()
        mock_repo.get_portfolio_snapshots.return_value = []
        app = _make_app(mock_repo)
        client = TestClient(app)

        resp = client.get("/collection/valuation?currency=USD")
        data = resp.json()["data"]
        assert data["currency"] == "USD"

    def test_currency_conversion_applied(self):
        snap = _make_snapshot(total_value_brl=Decimal("1000.00"))
        mock_repo = MagicMock()
        mock_repo.get_portfolio_snapshots.return_value = [snap]

        converter = MagicMock(spec=CurrencyConverter)
        converter.convert.return_value = Decimal("200.00")

        app = _make_app(mock_repo, converter=converter)
        client = TestClient(app)

        resp = client.get("/collection/valuation?currency=USD")
        data = resp.json()["data"]
        assert data["current_value"] == 200.0
        assert data["currency"] == "USD"

    def test_snapshots_include_date_and_counts(self):
        snap = _make_snapshot(
            snapshot_date=date(2026, 8, 27),
            total_value_brl=Decimal("500.00"),
            priced_card_count=100,
            total_card_count=200,
        )
        mock_repo = MagicMock()
        mock_repo.get_portfolio_snapshots.return_value = [snap]
        app = _make_app(mock_repo)
        client = TestClient(app)

        resp = client.get("/collection/valuation")
        snapshots = resp.json()["data"]["snapshots"]
        assert len(snapshots) == 1
        assert snapshots[0]["date"] == "2026-08-27"
        assert snapshots[0]["priced_count"] == 100
        assert snapshots[0]["total_count"] == 200
