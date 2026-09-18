"""Tests for movers investment_only filter (F136-T02, updated for F152-T02 CTE optimization)."""

from __future__ import annotations

from unittest.mock import MagicMock

from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.api.deps import get_currency_converter_dep, get_db, require_auth_or_api_key
from src.api.routers.collection import router

_TEST_USER_ID = "42"


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

    def test_investment_only_true_passed_to_optimized_method(self) -> None:
        """investment_only=true is forwarded to the repository method."""
        mock_repo = MagicMock()
        mock_repo.get_collection_movers_optimized.return_value = (
            [(42, "Lightning Bolt", "DMR", "123", None, 5.0, 10.0, 5.0, 100.0)],
            [],
        )

        client = TestClient(_make_app(mock_repo))
        resp = client.get("/collection/movers?investment_only=true")

        assert resp.status_code == 200
        mock_repo.get_collection_movers_optimized.assert_called_once_with(
            42,
            7,
            5,
            True,
        )
        data = resp.json()["data"]
        gainer_ids = [g["card_id"] for g in data["gainers"]]
        assert 42 in gainer_ids

    def test_investment_only_false_returns_all(self) -> None:
        """Default behavior: investment_only=False passed to repo."""
        mock_repo = MagicMock()
        mock_repo.get_collection_movers_optimized.return_value = (
            [
                (42, "Lightning Bolt", "DMR", "123", None, 5.0, 10.0, 5.0, 100.0),
                (99, "Counterspell", "MH2", "12", None, 3.0, 6.0, 3.0, 100.0),
            ],
            [],
        )

        client = TestClient(_make_app(mock_repo))
        resp = client.get("/collection/movers?investment_only=false")

        assert resp.status_code == 200
        mock_repo.get_collection_movers_optimized.assert_called_once_with(
            42,
            7,
            5,
            False,
        )
        data = resp.json()["data"]
        gainer_ids = [g["card_id"] for g in data["gainers"]]
        assert 42 in gainer_ids
        assert 99 in gainer_ids

    def test_no_param_returns_all_backward_compat(self) -> None:
        """No investment_only param = False (backward compatible)."""
        mock_repo = MagicMock()
        mock_repo.get_collection_movers_optimized.return_value = (
            [(42, "Lightning Bolt", "DMR", "123", None, 5.0, 10.0, 5.0, 100.0)],
            [],
        )

        client = TestClient(_make_app(mock_repo))
        resp = client.get("/collection/movers")

        assert resp.status_code == 200
        mock_repo.get_collection_movers_optimized.assert_called_once_with(
            42,
            7,
            5,
            False,
        )

    def test_investment_only_no_investment_cards_empty(self) -> None:
        """investment_only=true with no investment cards returns empty."""
        mock_repo = MagicMock()
        mock_repo.get_collection_movers_optimized.return_value = ([], [])

        client = TestClient(_make_app(mock_repo))
        resp = client.get("/collection/movers?investment_only=true")

        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["gainers"] == []
        assert data["losers"] == []
