from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from src.api.deps import get_db
from src.api.routers.sets import router
from src.database.models import CardRow
from src.database.repository import Repository


@pytest.fixture()
def repo(tmp_path):
    db_path = tmp_path / "test.db"
    return Repository(db_url=f"sqlite:///{db_path}")


@pytest.fixture()
def client(repo):
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_db] = lambda: repo
    return TestClient(app)


def _seed_cards(repo):
    """Seed cards in different sets."""
    with Session(repo.engine) as session:
        session.add_all(
            [
                CardRow(
                    game="magic",
                    name_en="Lightning Bolt",
                    set_code="2XM",
                    collector_number="1",
                ),
                CardRow(
                    game="magic",
                    name_en="Counterspell",
                    set_code="2XM",
                    collector_number="2",
                ),
                CardRow(
                    game="magic",
                    name_en="Sol Ring",
                    set_code="CMR",
                    collector_number="100",
                ),
                CardRow(
                    game="pokemon",
                    name_en="Pikachu",
                    set_code="SV1",
                    collector_number="25",
                ),
            ]
        )
        session.commit()


class TestListSets:
    def test_returns_all_sets(self, client, repo):
        _seed_cards(repo)
        resp = client.get("/sets")
        assert resp.status_code == 200
        body = resp.json()
        data = body["data"]
        assert len(data) == 3
        set_codes = [s["set_code"] for s in data]
        assert "2XM" in set_codes
        assert "CMR" in set_codes
        assert "SV1" in set_codes

    def test_card_counts(self, client, repo):
        _seed_cards(repo)
        resp = client.get("/sets")
        data = resp.json()["data"]
        twoxm = next(s for s in data if s["set_code"] == "2XM")
        assert twoxm["card_count"] == 2
        cmr = next(s for s in data if s["set_code"] == "CMR")
        assert cmr["card_count"] == 1

    def test_filter_by_game(self, client, repo):
        _seed_cards(repo)
        resp = client.get("/sets?game=pokemon")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert len(data) == 1
        assert data[0]["set_code"] == "SV1"
        assert data[0]["game"] == "pokemon"

    def test_empty_database(self, client):
        resp = client.get("/sets")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data == []

    def test_response_envelope(self, client, repo):
        _seed_cards(repo)
        resp = client.get("/sets")
        body = resp.json()
        assert "data" in body
        assert "meta" in body
        assert "request_id" in body["meta"]
