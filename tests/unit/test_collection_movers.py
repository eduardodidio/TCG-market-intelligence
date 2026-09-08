"""Tests for GET /collection/movers endpoint."""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import MagicMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.api.deps import get_db, require_auth_or_api_key
from src.api.routers.collection import router

_TEST_USER_ID = "test-user"


@pytest.fixture()
def client():
    app = FastAPI()
    app.include_router(router)

    mock_repo = MagicMock()

    app.dependency_overrides[get_db] = lambda: mock_repo
    app.dependency_overrides[require_auth_or_api_key] = lambda: _TEST_USER_ID

    yield TestClient(app), mock_repo

    app.dependency_overrides.clear()


class TestCollectionMovers:
    def test_empty_when_no_trending_data(self, client):
        tc, repo = client
        repo.get_trending_price_data_for_user.return_value = {}

        resp = tc.get("/collection/movers")
        assert resp.status_code == 200

        data = resp.json()["data"]
        assert data["gainers"] == []
        assert data["losers"] == []
        assert data["period_days"] == 7

    def test_empty_when_only_single_data_points(self, client):
        tc, repo = client
        today = date.today()
        repo.get_trending_price_data_for_user.return_value = {
            1: [(today, Decimal("10.00"))],
            2: [(today, Decimal("20.00"))],
        }

        resp = tc.get("/collection/movers")
        assert resp.status_code == 200

        data = resp.json()["data"]
        assert data["gainers"] == []
        assert data["losers"] == []

    def test_gainers_sorted_by_pct_desc(self, client):
        tc, repo = client
        today = date.today()
        yesterday = today - timedelta(days=1)

        repo.get_trending_price_data_for_user.return_value = {
            1: [(yesterday, Decimal("10.00")), (today, Decimal("15.00"))],  # +50%
            2: [(yesterday, Decimal("20.00")), (today, Decimal("24.00"))],  # +20%
            3: [(yesterday, Decimal("5.00")), (today, Decimal("10.00"))],  # +100%
        }
        # (name_en, set_code, collector_number, image_uri)
        repo.get_card_info_with_image_batch.return_value = {
            1: ("Card A", "SET1", "001", "http://img/1.jpg"),
            2: ("Card B", "SET2", "002", "http://img/2.jpg"),
            3: ("Card C", "SET3", "003", "http://img/3.jpg"),
        }

        resp = tc.get("/collection/movers")
        assert resp.status_code == 200
        data = resp.json()["data"]

        gainers = data["gainers"]
        assert len(gainers) == 3
        # Sorted by % change desc: 100%, 50%, 20%
        assert gainers[0]["card_name"] == "Card C"
        assert gainers[0]["change_pct"] == 100.0
        assert gainers[0]["image_uri"] == "http://img/3.jpg"
        assert gainers[1]["card_name"] == "Card A"
        assert gainers[1]["change_pct"] == 50.0
        assert gainers[2]["card_name"] == "Card B"
        assert gainers[2]["change_pct"] == 20.0

    def test_losers_sorted_by_pct_asc(self, client):
        tc, repo = client
        today = date.today()
        yesterday = today - timedelta(days=1)

        repo.get_trending_price_data_for_user.return_value = {
            1: [(yesterday, Decimal("10.00")), (today, Decimal("8.00"))],  # -20%
            2: [(yesterday, Decimal("20.00")), (today, Decimal("10.00"))],  # -50%
        }
        repo.get_card_info_with_image_batch.return_value = {
            1: ("Card A", "SET1", "001", None),
            2: ("Card B", "SET2", "002", None),
        }

        resp = tc.get("/collection/movers")
        assert resp.status_code == 200
        data = resp.json()["data"]

        assert data["gainers"] == []
        losers = data["losers"]
        assert len(losers) == 2
        # Sorted by % change asc: -50%, -20%
        assert losers[0]["card_name"] == "Card B"
        assert losers[0]["change_pct"] == -50.0
        assert losers[1]["card_name"] == "Card A"
        assert losers[1]["change_pct"] == -20.0

    def test_mixed_gainers_and_losers(self, client):
        tc, repo = client
        today = date.today()
        yesterday = today - timedelta(days=1)

        repo.get_trending_price_data_for_user.return_value = {
            1: [(yesterday, Decimal("10.00")), (today, Decimal("15.00"))],  # +50%
            2: [(yesterday, Decimal("20.00")), (today, Decimal("10.00"))],  # -50%
            3: [(yesterday, Decimal("5.00")), (today, Decimal("5.00"))],  # 0% (neither)
        }
        repo.get_card_info_with_image_batch.return_value = {
            1: ("Gainer Card", "SET1", "001", None),
            2: ("Loser Card", "SET2", "002", None),
        }

        resp = tc.get("/collection/movers")
        assert resp.status_code == 200
        data = resp.json()["data"]

        assert len(data["gainers"]) == 1
        assert data["gainers"][0]["card_name"] == "Gainer Card"
        assert len(data["losers"]) == 1
        assert data["losers"][0]["card_name"] == "Loser Card"

    def test_custom_days_and_limit(self, client):
        tc, repo = client
        repo.get_trending_price_data_for_user.return_value = {}

        resp = tc.get("/collection/movers?days=30&limit=10")
        assert resp.status_code == 200

        data = resp.json()["data"]
        assert data["period_days"] == 30
        repo.get_trending_price_data_for_user.assert_called_once_with(_TEST_USER_ID, 30)

    def test_days_validation_max_90(self, client):
        tc, repo = client
        resp = tc.get("/collection/movers?days=100")
        assert resp.status_code == 422

    def test_limit_validation_max_20(self, client):
        tc, repo = client
        resp = tc.get("/collection/movers?limit=25")
        assert resp.status_code == 422

    def test_limit_caps_results(self, client):
        tc, repo = client
        today = date.today()
        yesterday = today - timedelta(days=1)

        # Create 10 gainers
        trending = {}
        card_info = {}
        for i in range(1, 11):
            trending[i] = [
                (yesterday, Decimal("10.00")),
                (today, Decimal(str(10 + i))),
            ]
            # (name_en, set_code, collector_number, image_uri)
            card_info[i] = (f"Card {i}", "SET", str(i), None)

        repo.get_trending_price_data_for_user.return_value = trending
        repo.get_card_info_with_image_batch.return_value = card_info

        resp = tc.get("/collection/movers?limit=3")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert len(data["gainers"]) == 3

    def test_zero_start_price_excluded(self, client):
        tc, repo = client
        today = date.today()
        yesterday = today - timedelta(days=1)

        repo.get_trending_price_data_for_user.return_value = {
            1: [(yesterday, Decimal("0.00")), (today, Decimal("10.00"))],
        }

        resp = tc.get("/collection/movers")
        assert resp.status_code == 200

        data = resp.json()["data"]
        assert data["gainers"] == []
        assert data["losers"] == []
