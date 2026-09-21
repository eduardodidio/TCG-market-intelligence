"""Tests for GET /collection/movers endpoint (optimized CTE version)."""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import MagicMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from src.api.deps import get_db, require_auth_or_api_key
from src.api.routers.collection import router
from src.database.models import (
    Base,
    CardRow,
    PriceObservationRow,
    UserCollectionRow,
)
from src.database.repository import Repository

_TEST_USER_ID = "42"


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
    def test_empty_when_no_movers(self, client):
        tc, repo = client
        repo.get_collection_movers_optimized.return_value = ([], [])

        resp = tc.get("/collection/movers")
        assert resp.status_code == 200

        data = resp.json()["data"]
        assert data["gainers"] == []
        assert data["losers"] == []
        assert data["period_days"] == 7

    def test_gainers_returned_correctly(self, client):
        tc, repo = client
        # (card_id, card_name, set_code, collector_number, image_uri,
        #  price_start, price_end, change_abs, change_pct)
        repo.get_collection_movers_optimized.return_value = (
            [
                (3, "Card C", "SET3", "003", "http://img/3.jpg", 5.0, 10.0, 5.0, 100.0),
                (1, "Card A", "SET1", "001", "http://img/1.jpg", 10.0, 15.0, 5.0, 50.0),
                (2, "Card B", "SET2", "002", "http://img/2.jpg", 20.0, 24.0, 4.0, 20.0),
            ],
            [],
        )

        resp = tc.get("/collection/movers")
        assert resp.status_code == 200
        data = resp.json()["data"]

        gainers = data["gainers"]
        assert len(gainers) == 3
        assert gainers[0]["card_name"] == "Card C"
        assert gainers[0]["change_pct"] == 100.0
        assert gainers[0]["image_uri"] == "http://img/3.jpg"
        assert gainers[1]["card_name"] == "Card A"
        assert gainers[1]["change_pct"] == 50.0
        assert gainers[2]["card_name"] == "Card B"
        assert gainers[2]["change_pct"] == 20.0

    def test_losers_returned_correctly(self, client):
        tc, repo = client
        repo.get_collection_movers_optimized.return_value = (
            [],
            [
                (2, "Card B", "SET2", "002", None, 20.0, 10.0, -10.0, -50.0),
                (1, "Card A", "SET1", "001", None, 10.0, 8.0, -2.0, -20.0),
            ],
        )

        resp = tc.get("/collection/movers")
        assert resp.status_code == 200
        data = resp.json()["data"]

        assert data["gainers"] == []
        losers = data["losers"]
        assert len(losers) == 2
        assert losers[0]["card_name"] == "Card B"
        assert losers[0]["change_pct"] == -50.0
        assert losers[1]["card_name"] == "Card A"
        assert losers[1]["change_pct"] == -20.0

    def test_mixed_gainers_and_losers(self, client):
        tc, repo = client
        repo.get_collection_movers_optimized.return_value = (
            [(1, "Gainer Card", "SET1", "001", None, 10.0, 15.0, 5.0, 50.0)],
            [(2, "Loser Card", "SET2", "002", None, 20.0, 10.0, -10.0, -50.0)],
        )

        resp = tc.get("/collection/movers")
        assert resp.status_code == 200
        data = resp.json()["data"]

        assert len(data["gainers"]) == 1
        assert data["gainers"][0]["card_name"] == "Gainer Card"
        assert len(data["losers"]) == 1
        assert data["losers"][0]["card_name"] == "Loser Card"

    def test_custom_days_and_limit(self, client):
        tc, repo = client
        repo.get_collection_movers_optimized.return_value = ([], [])

        resp = tc.get("/collection/movers?days=30&limit=10")
        assert resp.status_code == 200

        data = resp.json()["data"]
        assert data["period_days"] == 30
        repo.get_collection_movers_optimized.assert_called_once_with(
            42,
            30,
            10,
            False,
        )

    def test_days_validation_max_90(self, client):
        tc, repo = client
        resp = tc.get("/collection/movers?days=100")
        assert resp.status_code == 422

    def test_limit_validation_max_100(self, client):
        tc, repo = client
        resp = tc.get("/collection/movers?limit=101")
        assert resp.status_code == 422

    def test_movers_limit_100_accepted(self, client):
        tc, repo = client
        repo.get_collection_movers_optimized.return_value = ([], [])

        resp = tc.get("/collection/movers?limit=100")
        assert resp.status_code == 200
        repo.get_collection_movers_optimized.assert_called_once_with(
            42,
            7,
            100,
            False,
        )

    def test_movers_limit_101_rejected(self, client):
        tc, repo = client
        resp = tc.get("/collection/movers?limit=101")
        assert resp.status_code == 422

    def test_investment_only_passed_to_repo(self, client):
        tc, repo = client
        repo.get_collection_movers_optimized.return_value = ([], [])

        resp = tc.get("/collection/movers?investment_only=true")
        assert resp.status_code == 200
        repo.get_collection_movers_optimized.assert_called_once_with(
            42,
            7,
            5,
            True,
        )

    def test_null_card_name_falls_back(self, client):
        tc, repo = client
        repo.get_collection_movers_optimized.return_value = (
            [(99, None, "SET1", "001", None, 10.0, 15.0, 5.0, 50.0)],
            [],
        )

        resp = tc.get("/collection/movers")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["gainers"][0]["card_name"] == "Card #99"


def _seed_card_with_prices(
    session: Session,
    card_id: int,
    name: str,
    price_start: Decimal,
    price_end: Decimal,
    days_ago: int = 5,
) -> None:
    card = CardRow(
        id=card_id,
        game="mtg",
        name_en=name,
        set_code="tst",
        collector_number=str(card_id).zfill(3),
    )
    session.add(card)
    session.flush()

    session.add(
        UserCollectionRow(
            user_id="1",
            card_id=card_id,
            set_code="tst",
            collector_number=str(card_id).zfill(3),
            name_en=name,
        )
    )

    today = date.today()
    ext_id = f"liga_{card_id}"
    session.add(
        PriceObservationRow(
            source="liga",
            external_id=ext_id,
            observed_at=today - timedelta(days=days_ago),
            median_price=price_start,
        )
    )
    session.add(
        PriceObservationRow(
            source="liga",
            external_id=ext_id,
            observed_at=today,
            median_price=price_end,
        )
    )
    session.flush()


@pytest.fixture()
def repo_db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    repo = Repository.__new__(Repository)
    repo.engine = engine
    return repo, engine


class TestMoversFilters:
    def test_movers_filters_low_price_start(self, repo_db):
        repo, engine = repo_db
        with Session(engine) as session:
            _seed_card_with_prices(session, 1, "Cheap Card", Decimal("0.10"), Decimal("1.00"))
            _seed_card_with_prices(session, 2, "Normal Card", Decimal("5.00"), Decimal("10.00"))
            session.commit()

        gainers, losers = repo.get_collection_movers_optimized(1, 7)
        all_names = [m[1] for m in gainers + losers]
        assert "Cheap Card" not in all_names
        assert "Normal Card" in all_names

    def test_movers_filters_extreme_percentage(self, repo_db):
        repo, engine = repo_db
        with Session(engine) as session:
            _seed_card_with_prices(session, 1, "Extreme Card", Decimal("0.50"), Decimal("100.00"))
            _seed_card_with_prices(session, 2, "Moderate Card", Decimal("5.00"), Decimal("10.00"))
            session.commit()

        gainers, losers = repo.get_collection_movers_optimized(1, 7)
        all_names = [m[1] for m in gainers + losers]
        assert "Extreme Card" not in all_names
        assert "Moderate Card" in all_names

    def test_movers_keeps_reasonable_changes(self, repo_db):
        repo, engine = repo_db
        with Session(engine) as session:
            _seed_card_with_prices(session, 1, "Gainer", Decimal("10.00"), Decimal("15.00"))
            _seed_card_with_prices(session, 2, "Loser", Decimal("20.00"), Decimal("12.00"))
            _seed_card_with_prices(session, 3, "Big Gainer", Decimal("1.00"), Decimal("10.00"))
            session.commit()

        gainers, losers = repo.get_collection_movers_optimized(1, 7)
        gainer_names = [m[1] for m in gainers]
        loser_names = [m[1] for m in losers]
        assert "Gainer" in gainer_names
        assert "Big Gainer" in gainer_names
        assert "Loser" in loser_names
