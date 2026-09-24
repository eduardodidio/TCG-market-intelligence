"""Tests for F177-T07: grouped banlist router, owned_only, /banlist/status."""

from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from src.api.deps import get_db, get_optional_user
from src.api.routers.banlist import router
from src.database.models import Base, CardLegalityRow, CardRow, UserCollectionRow
from src.database.repository import Repository
from src.domain.models import User


def _make_repo() -> Repository:
    repo = Repository.__new__(Repository)
    repo.engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(repo.engine)
    return repo


def _add_card(session, name_en, set_code="lea", collector_number="1"):
    card = CardRow(
        game="magic",
        name_en=name_en,
        set_code=set_code,
        collector_number=collector_number,
    )
    session.add(card)
    session.flush()
    return card.id


def _add_legality(session, card_id, format_, status):
    session.add(CardLegalityRow(card_id=card_id, format=format_, status=status))


def _make_app(repo: Repository, user: User | None = None) -> FastAPI:
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_db] = lambda: repo
    app.dependency_overrides[get_optional_user] = lambda: user
    app.state.repo = repo
    return app


class TestListBanlistGroupedRouter:
    def test_returns_grouped_entries_with_new_fields(self):
        repo = _make_repo()
        with Session(repo.engine) as session:
            id1 = _add_card(session, "Balance", set_code="lea")
            id2 = _add_card(session, "Balance", set_code="4ed")
            _add_legality(session, id1, "commander", "banned")
            _add_legality(session, id2, "commander", "banned")
            session.commit()

        app = _make_app(repo)
        client = TestClient(app)
        resp = client.get("/banlist?format=commander")
        assert resp.status_code == 200
        body = resp.json()
        data = body["data"]
        assert len(data) == 1
        assert data[0]["printings"] == 2
        assert data[0]["owned"] is False
        assert data[0]["owned_quantity"] == 0
        assert body["meta"]["total"] == 1

    def test_owned_only_with_auth_returns_only_owned(self):
        repo = _make_repo()
        with Session(repo.engine) as session:
            owned_id = _add_card(session, "Channel", set_code="lea")
            other_id = _add_card(session, "Balance", set_code="4ed")
            _add_legality(session, owned_id, "vintage", "banned")
            _add_legality(session, other_id, "vintage", "banned")
            session.add(
                UserCollectionRow(
                    user_id="1",
                    card_id=owned_id,
                    set_code="lea",
                    collector_number="1",
                    name_en="Channel",
                    quantity=2,
                )
            )
            session.commit()

        user = User(id=1, email="u1@test.com", display_name="U1")
        app = _make_app(repo, user=user)
        client = TestClient(app)
        resp = client.get("/banlist?format=vintage&owned_only=true")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert len(data) == 1
        assert data[0]["name_en"] == "Channel"
        assert data[0]["owned_quantity"] == 2

    def test_owned_only_without_auth_returns_401(self):
        repo = _make_repo()
        app = _make_app(repo, user=None)
        client = TestClient(app)
        resp = client.get("/banlist?format=vintage&owned_only=true")
        assert resp.status_code == 401
        body = resp.json()
        assert "error" in body or "detail" in body

    def test_anonymous_owned_false_for_all(self):
        repo = _make_repo()
        with Session(repo.engine) as session:
            cid = _add_card(session, "Channel")
            _add_legality(session, cid, "vintage", "banned")
            session.add(
                UserCollectionRow(
                    user_id="other",
                    card_id=cid,
                    set_code="lea",
                    collector_number="1",
                    name_en="Channel",
                    quantity=1,
                )
            )
            session.commit()

        app = _make_app(repo, user=None)
        client = TestClient(app)
        resp = client.get("/banlist?format=vintage")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert all(e["owned"] is False for e in data)

    def test_invalid_status_returns_422(self):
        repo = _make_repo()
        app = _make_app(repo)
        client = TestClient(app)
        resp = client.get("/banlist?format=vintage&status=legal")
        assert resp.status_code == 422

    @pytest.mark.parametrize("limit", [0, 501])
    def test_invalid_limit_returns_422(self, limit):
        repo = _make_repo()
        app = _make_app(repo)
        client = TestClient(app)
        resp = client.get(f"/banlist?format=vintage&limit={limit}")
        assert resp.status_code == 422

    def test_limit_500_accepted(self):
        repo = _make_repo()
        app = _make_app(repo)
        client = TestClient(app)
        resp = client.get("/banlist?format=vintage&limit=500")
        assert resp.status_code == 200

    def test_search_and_owned_only_combined(self):
        repo = _make_repo()
        with Session(repo.engine) as session:
            owned_id = _add_card(session, "Channel", set_code="lea")
            other_id = _add_card(session, "Balance", set_code="4ed")
            _add_legality(session, owned_id, "vintage", "banned")
            _add_legality(session, other_id, "vintage", "banned")
            session.add(
                UserCollectionRow(
                    user_id="1",
                    card_id=owned_id,
                    set_code="lea",
                    collector_number="1",
                    name_en="Channel",
                    quantity=1,
                )
            )
            session.commit()

        user = User(id=1, email="u1@test.com", display_name="U1")
        app = _make_app(repo, user=user)
        client = TestClient(app)
        resp = client.get("/banlist?format=vintage&owned_only=true&search=channel")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert len(data) == 1
        assert data[0]["name_en"] == "Channel"

        resp2 = client.get("/banlist?format=vintage&owned_only=true&search=balance")
        assert resp2.json()["data"] == []

    def test_empty_db_returns_empty_list_and_zero_total(self):
        repo = _make_repo()
        app = _make_app(repo)
        client = TestClient(app)
        resp = client.get("/banlist?format=vintage")
        assert resp.status_code == 200
        body = resp.json()
        assert body["data"] == []
        assert body["meta"]["total"] == 0

    def test_offset_beyond_total_returns_empty_but_preserves_total(self):
        repo = _make_repo()
        with Session(repo.engine) as session:
            cid = _add_card(session, "Channel")
            _add_legality(session, cid, "vintage", "banned")
            session.commit()

        app = _make_app(repo)
        client = TestClient(app)
        resp = client.get("/banlist?format=vintage&offset=10")
        assert resp.status_code == 200
        body = resp.json()
        assert body["data"] == []
        assert body["meta"]["total"] == 1


class TestBanlistStatusEndpoint:
    def test_works_anonymously_with_empty_db(self):
        repo = _make_repo()
        app = _make_app(repo, user=None)
        client = TestClient(app)
        resp = client.get("/banlist/status")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["last_synced_at"] is None
        assert data["legalities_count"] == 0
        assert data["banned_count"] == 0
        assert data["restricted_count"] == 0
        assert data["history_count"] == 0
        assert data["formats"] == 0

    def test_returns_counts(self):
        repo = _make_repo()
        with Session(repo.engine) as session:
            id1 = _add_card(session, "A")
            id2 = _add_card(session, "B", set_code="4ed")
            _add_legality(session, id1, "vintage", "banned")
            _add_legality(session, id2, "legacy", "restricted")
            session.commit()

        app = _make_app(repo)
        client = TestClient(app)
        resp = client.get("/banlist/status")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["legalities_count"] == 2
        assert data["banned_count"] == 1
        assert data["restricted_count"] == 1
        assert data["formats"] == 2
