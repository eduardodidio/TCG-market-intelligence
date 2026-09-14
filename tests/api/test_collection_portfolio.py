"""Tests for portfolio investment tracking endpoints (F105)."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from unittest.mock import MagicMock

from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.api.deps import get_currency_converter_dep, get_db, require_auth_or_api_key
from src.api.routers.collection import router
from src.database.models import PortfolioSnapshotRow, PriceObservationRow, UserCollectionRow

_TEST_USER_ID = "eduardo"


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


def _make_price_obs(**overrides) -> MagicMock:
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


def _make_app(mock_repo: MagicMock, user_id: str = _TEST_USER_ID) -> FastAPI:
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_db] = lambda: mock_repo
    app.dependency_overrides[require_auth_or_api_key] = lambda: user_id
    mock_converter = MagicMock()
    mock_converter.convert.return_value = None
    app.dependency_overrides[get_currency_converter_dep] = lambda: mock_converter
    return app


class TestPatchAcquisitionFields:
    """PATCH /collection/{entry_id} — acquisition_price and acquired_at."""

    def test_update_acquisition_price(self) -> None:
        mock_repo = MagicMock()
        updated_row = _make_collection_row(acquisition_price=Decimal("12.50"))
        mock_repo.update_collection_entry.return_value = updated_row

        client = TestClient(_make_app(mock_repo))
        resp = client.patch("/collection/1", json={"acquisition_price": 12.50})
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["acquisition_price"] == 12.50

    def test_update_acquired_at(self) -> None:
        mock_repo = MagicMock()
        updated_row = _make_collection_row(acquired_at=date(2026, 3, 15))
        mock_repo.update_collection_entry.return_value = updated_row

        client = TestClient(_make_app(mock_repo))
        resp = client.patch("/collection/1", json={"acquired_at": "2026-03-15"})
        assert resp.status_code == 200
        # acquired_at should be in the response
        call_updates = mock_repo.update_collection_entry.call_args[0][2]
        assert call_updates["acquired_at"] == date(2026, 3, 15)

    def test_update_both_acquisition_fields(self) -> None:
        mock_repo = MagicMock()
        updated_row = _make_collection_row(
            acquisition_price=Decimal("25.00"),
            acquired_at=date(2026, 6, 1),
        )
        mock_repo.update_collection_entry.return_value = updated_row

        client = TestClient(_make_app(mock_repo))
        resp = client.patch(
            "/collection/1",
            json={"acquisition_price": 25.00, "acquired_at": "2026-06-01"},
        )
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["acquisition_price"] == 25.00

    def test_negative_acquisition_price_rejected(self) -> None:
        mock_repo = MagicMock()
        client = TestClient(_make_app(mock_repo))
        resp = client.patch("/collection/1", json={"acquisition_price": -5.00})
        assert resp.status_code == 422

    def test_zero_acquisition_price_rejected(self) -> None:
        mock_repo = MagicMock()
        client = TestClient(_make_app(mock_repo))
        resp = client.patch("/collection/1", json={"acquisition_price": 0})
        assert resp.status_code == 422

    def test_invalid_acquired_at_rejected(self) -> None:
        mock_repo = MagicMock()
        client = TestClient(_make_app(mock_repo))
        resp = client.patch("/collection/1", json={"acquired_at": "not-a-date"})
        assert resp.status_code == 422


class TestPortfolioSummary:
    """GET /collection/portfolio-summary.

    F124 semantics: total_invested counts all entries with a paid price;
    total_pnl / total_pnl_pct only consider the subset that also has a
    current price (unpriced entries are excluded, not treated as a 100%
    loss); foil entries are valued with the foil price observation.
    """

    def test_empty_portfolio(self) -> None:
        mock_repo = MagicMock()
        mock_repo.get_portfolio_invested_total.return_value = (Decimal("0"), 0)

        client = TestClient(_make_app(mock_repo))
        resp = client.get("/collection/portfolio-summary")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["total_invested"] == 0.0
        assert data["total_current_value"] == 0.0
        assert data["total_pnl"] == 0.0
        assert data["total_pnl_pct"] is None
        assert data["invested_card_count"] == 0
        assert data["unpriced_card_count"] == 0

    def test_portfolio_with_entries(self) -> None:
        mock_repo = MagicMock()
        mock_repo.get_portfolio_invested_total.return_value = (Decimal("10.00"), 1)

        entry = _make_collection_row(
            acquisition_price=Decimal("5.00"),
            quantity=2,
            card_id=42,
        )
        mock_repo.get_collection_entries_with_acquisition.return_value = [entry]
        mock_repo.get_latest_prices_batch.return_value = {
            42: _make_price_obs(median_price=Decimal("8.50")),
        }

        client = TestClient(_make_app(mock_repo))
        resp = client.get("/collection/portfolio-summary")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["total_invested"] == 10.00
        # current value = 8.50 * 2 = 17.00
        assert data["total_current_value"] == 17.00
        # pnl = 17.00 - 10.00 = 7.00
        assert data["total_pnl"] == 7.00
        assert data["total_pnl_pct"] == 70.0
        assert data["invested_card_count"] == 1
        assert data["unpriced_card_count"] == 0

    def test_mix_of_priced_and_unpriced_entries(self) -> None:
        """Entry with paid price but no current price is excluded from P&L."""
        mock_repo = MagicMock()
        # invested total covers both entries: 2*10 + 1*20 = 40
        mock_repo.get_portfolio_invested_total.return_value = (Decimal("40.00"), 2)

        priced_entry = _make_collection_row(
            id=1,
            card_id=42,
            acquisition_price=Decimal("10.00"),
            quantity=2,
        )
        unpriced_entry = _make_collection_row(
            id=2,
            card_id=43,
            acquisition_price=Decimal("20.00"),
            quantity=1,
        )
        mock_repo.get_collection_entries_with_acquisition.return_value = [
            priced_entry,
            unpriced_entry,
        ]
        mock_repo.get_latest_prices_batch.return_value = {
            42: _make_price_obs(median_price=Decimal("15.00")),
            # card 43 has no price observation
        }

        client = TestClient(_make_app(mock_repo))
        resp = client.get("/collection/portfolio-summary")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["total_invested"] == 40.00
        # current value = 15 * 2 = 30 (unpriced entry contributes 0)
        assert data["total_current_value"] == 30.00
        # invested_priced = 10 * 2 = 20 (only the priced entry)
        # pnl = 30 - 20 = 10; pct = 10/20*100 = 50.0
        assert data["total_pnl"] == 10.00
        assert data["total_pnl_pct"] == 50.0
        assert data["unpriced_card_count"] == 1

    def test_all_entries_unpriced(self) -> None:
        mock_repo = MagicMock()
        mock_repo.get_portfolio_invested_total.return_value = (Decimal("20.00"), 1)

        entry = _make_collection_row(card_id=42, acquisition_price=Decimal("20.00"), quantity=1)
        mock_repo.get_collection_entries_with_acquisition.return_value = [entry]
        mock_repo.get_latest_prices_batch.return_value = {}

        client = TestClient(_make_app(mock_repo))
        resp = client.get("/collection/portfolio-summary")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["total_invested"] == 20.00
        assert data["total_current_value"] == 0.0
        assert data["total_pnl"] == 0.0
        assert data["total_pnl_pct"] is None
        assert data["unpriced_card_count"] == 1

    def test_entry_with_no_card_id_is_unpriced(self) -> None:
        mock_repo = MagicMock()
        mock_repo.get_portfolio_invested_total.return_value = (Decimal("20.00"), 1)

        entry = _make_collection_row(card_id=None, acquisition_price=Decimal("20.00"), quantity=1)
        mock_repo.get_collection_entries_with_acquisition.return_value = [entry]
        mock_repo.get_latest_prices_batch.return_value = {}

        client = TestClient(_make_app(mock_repo))
        resp = client.get("/collection/portfolio-summary")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["unpriced_card_count"] == 1
        assert data["total_pnl_pct"] is None

    def test_foil_entry_uses_foil_price(self) -> None:
        """Foil entry must be valued with the foil price observation, not the
        non-foil one, mirroring list_collection's foil-aware lookup."""
        mock_repo = MagicMock()
        mock_repo.get_portfolio_invested_total.return_value = (Decimal("10.00"), 2)

        foil_entry = _make_collection_row(
            id=1,
            card_id=42,
            extras="Foil",
            acquisition_price=Decimal("5.00"),
            quantity=1,
        )
        non_foil_entry = _make_collection_row(
            id=2,
            card_id=42,
            extras=None,
            acquisition_price=Decimal("5.00"),
            quantity=1,
        )
        mock_repo.get_collection_entries_with_acquisition.return_value = [
            foil_entry,
            non_foil_entry,
        ]

        def _fake_latest_prices_batch(card_ids, foil_card_ids=None):
            if foil_card_ids:
                return {42: _make_price_obs(median_price=Decimal("20.00"))}
            return {42: _make_price_obs(median_price=Decimal("8.00"))}

        mock_repo.get_latest_prices_batch.side_effect = _fake_latest_prices_batch

        client = TestClient(_make_app(mock_repo))
        resp = client.get("/collection/portfolio-summary")
        assert resp.status_code == 200
        data = resp.json()["data"]
        # foil entry: 20.00 * 1; non-foil entry: 8.00 * 1 => 28.00
        assert data["total_current_value"] == 28.00
        assert data["unpriced_card_count"] == 0


class TestPortfolioHistory:
    """GET /collection/portfolio-history."""

    def test_empty_history(self) -> None:
        mock_repo = MagicMock()
        mock_repo.get_portfolio_snapshots.return_value = []

        client = TestClient(_make_app(mock_repo))
        resp = client.get("/collection/portfolio-history")
        assert resp.status_code == 200
        assert resp.json()["data"] == []

    def test_history_returns_chronological(self) -> None:
        mock_repo = MagicMock()
        snap1 = MagicMock(spec=PortfolioSnapshotRow)
        snap1.snapshot_date = date(2026, 9, 1)
        snap1.total_value_brl = Decimal("100.00")
        snap2 = MagicMock(spec=PortfolioSnapshotRow)
        snap2.snapshot_date = date(2026, 9, 2)
        snap2.total_value_brl = Decimal("110.00")
        # Snapshots come from repo in DESC order
        mock_repo.get_portfolio_snapshots.return_value = [snap2, snap1]

        client = TestClient(_make_app(mock_repo))
        resp = client.get("/collection/portfolio-history?days=30")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert len(data) == 2
        # Should be in chronological order (ASC)
        assert data[0]["date"] == "2026-09-01"
        assert data[1]["date"] == "2026-09-02"
        assert data[0]["value"] == 100.00
        assert data[1]["value"] == 110.00


class TestExportPnlCsv:
    """GET /collection/export-pnl."""

    def test_empty_export(self) -> None:
        mock_repo = MagicMock()
        mock_repo.get_collection_entries_with_acquisition.return_value = []
        mock_repo.get_latest_prices_batch.return_value = {}

        client = TestClient(_make_app(mock_repo))
        resp = client.get("/collection/export-pnl")
        assert resp.status_code == 200
        assert resp.headers["content-type"].startswith("text/csv")
        assert "attachment" in resp.headers.get("content-disposition", "")
        lines = resp.text.strip().split("\n")
        assert len(lines) == 1  # header only

    def test_export_with_data(self) -> None:
        mock_repo = MagicMock()
        entry = _make_collection_row(
            name_en="Lightning Bolt",
            set_code="DMR",
            quantity=2,
            acquisition_price=Decimal("5.00"),
            acquired_at=date(2026, 1, 15),
            card_id=42,
        )
        mock_repo.get_collection_entries_with_acquisition.return_value = [entry]
        mock_repo.get_latest_prices_batch.return_value = {
            42: _make_price_obs(median_price=Decimal("8.50")),
        }

        client = TestClient(_make_app(mock_repo))
        resp = client.get("/collection/export-pnl")
        assert resp.status_code == 200
        lines = resp.text.strip().split("\n")
        assert len(lines) == 2  # header + 1 row
        # Check header
        assert "card_name" in lines[0]
        assert "pnl" in lines[0]
        # Check data row
        assert "Lightning Bolt" in lines[1]
        assert "DMR" in lines[1]
