"""Tests for evaluation list (watchlist) CRUD endpoints."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from src.api.deps import get_current_user, get_db
from src.api.routers.evaluations import router
from src.database.models import Base, EvaluationEntryRow, UserCollectionRow
from src.database.repository import Repository
from src.domain.models import User

_TEST_USER = User(
    id=1,
    email="test@example.com",
    display_name="Test",
    is_active=True,
    is_admin=False,
)

_OTHER_USER = User(
    id=2,
    email="other@example.com",
    display_name="Other",
    is_active=True,
    is_admin=False,
)


def _create_test_db():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(engine, "connect")
    def _set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(engine)
    return engine


def _create_app(repo: Repository, user: User = _TEST_USER) -> FastAPI:
    app = FastAPI()
    app.include_router(router, prefix="/api/v1")
    app.dependency_overrides[get_db] = lambda: repo
    app.dependency_overrides[get_current_user] = lambda: user
    return app


def _make_repo() -> Repository:
    repo = Repository.__new__(Repository)
    repo.engine = _create_test_db()
    return repo


class TestCreateEvaluation:
    def test_create_success(self) -> None:
        repo = _make_repo()
        client = TestClient(_create_app(repo))

        resp = client.post(
            "/api/v1/evaluations",
            json={"card_name": "Lightning Bolt", "price_at_add": 5.50},
        )
        assert resp.status_code == 201
        data = resp.json()["data"]
        assert data["card_name"] == "Lightning Bolt"
        assert data["price_at_add"] == 5.50
        assert data["id"] is not None

    def test_create_with_set_code(self) -> None:
        repo = _make_repo()
        client = TestClient(_create_app(repo))

        resp = client.post(
            "/api/v1/evaluations",
            json={
                "card_name": "Lightning Bolt",
                "set_code": "m21",
                "collector_number": "152",
            },
        )
        assert resp.status_code == 201
        data = resp.json()["data"]
        assert data["set_code"] == "m21"
        assert data["collector_number"] == "152"
        assert data["image_url"] is not None
        assert "m21" in data["image_url"]

    def test_create_empty_name_rejected(self) -> None:
        repo = _make_repo()
        client = TestClient(_create_app(repo))

        resp = client.post("/api/v1/evaluations", json={"card_name": ""})
        assert resp.status_code == 422

    def test_limit_50(self) -> None:
        repo = _make_repo()
        client = TestClient(_create_app(repo))

        # Insert 50 entries directly
        with Session(repo.engine) as session:
            for i in range(50):
                session.add(
                    EvaluationEntryRow(
                        user_id=_TEST_USER.id,
                        card_name=f"Card {i}",
                    )
                )
            session.commit()

        resp = client.post(
            "/api/v1/evaluations",
            json={"card_name": "Card 51"},
        )
        assert resp.status_code == 400
        assert "limit" in resp.json()["detail"].lower()

    def test_limit_does_not_count_other_users(self) -> None:
        repo = _make_repo()

        # Other user has 50 entries
        with Session(repo.engine) as session:
            for i in range(50):
                session.add(
                    EvaluationEntryRow(
                        user_id=_OTHER_USER.id,
                        card_name=f"Other Card {i}",
                    )
                )
            session.commit()

        client = TestClient(_create_app(repo))
        resp = client.post(
            "/api/v1/evaluations",
            json={"card_name": "My Card"},
        )
        assert resp.status_code == 201


class TestListEvaluations:
    def test_list_empty(self) -> None:
        repo = _make_repo()
        client = TestClient(_create_app(repo))

        resp = client.get("/api/v1/evaluations")
        assert resp.status_code == 200
        assert resp.json()["data"] == []

    def test_list_own_entries(self) -> None:
        repo = _make_repo()

        with Session(repo.engine) as session:
            session.add(EvaluationEntryRow(user_id=_TEST_USER.id, card_name="Bolt"))
            session.add(EvaluationEntryRow(user_id=_OTHER_USER.id, card_name="Other"))
            session.commit()

        client = TestClient(_create_app(repo))
        resp = client.get("/api/v1/evaluations")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert len(data) == 1
        assert data[0]["card_name"] == "Bolt"


class TestDeleteEvaluation:
    def test_delete_success(self) -> None:
        repo = _make_repo()

        with Session(repo.engine) as session:
            entry = EvaluationEntryRow(user_id=_TEST_USER.id, card_name="Bolt")
            session.add(entry)
            session.commit()
            entry_id = entry.id

        client = TestClient(_create_app(repo))
        resp = client.delete(f"/api/v1/evaluations/{entry_id}")
        assert resp.status_code == 200
        assert resp.json()["data"]["deleted"] is True

        # Verify it's gone
        resp2 = client.get("/api/v1/evaluations")
        assert len(resp2.json()["data"]) == 0

    def test_delete_not_found(self) -> None:
        repo = _make_repo()
        client = TestClient(_create_app(repo))

        resp = client.delete("/api/v1/evaluations/999")
        assert resp.status_code == 404

    def test_delete_idor_blocked(self) -> None:
        repo = _make_repo()

        with Session(repo.engine) as session:
            entry = EvaluationEntryRow(user_id=_OTHER_USER.id, card_name="Other Bolt")
            session.add(entry)
            session.commit()
            entry_id = entry.id

        # Test user tries to delete other user's entry
        client = TestClient(_create_app(repo))
        resp = client.delete(f"/api/v1/evaluations/{entry_id}")
        assert resp.status_code == 404


class TestPromoteEvaluation:
    def test_promote_success(self) -> None:
        repo = _make_repo()

        with Session(repo.engine) as session:
            entry = EvaluationEntryRow(
                user_id=_TEST_USER.id,
                card_name="Lightning Bolt",
            )
            session.add(entry)
            session.commit()
            entry_id = entry.id

        client = TestClient(_create_app(repo))
        resp = client.post(f"/api/v1/evaluations/{entry_id}/promote")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["card_name"] == "Lightning Bolt"
        assert data["collection_entry_id"] > 0

        # Verify eval entry removed
        resp2 = client.get("/api/v1/evaluations")
        assert len(resp2.json()["data"]) == 0

        # Verify collection entry created
        with Session(repo.engine) as session:
            from sqlalchemy import select

            count = session.execute(
                select(UserCollectionRow).where(
                    UserCollectionRow.user_id == str(_TEST_USER.id),
                    UserCollectionRow.name_en == "Lightning Bolt",
                )
            ).scalar_one_or_none()
            assert count is not None

    def test_promote_not_found(self) -> None:
        repo = _make_repo()
        client = TestClient(_create_app(repo))

        resp = client.post("/api/v1/evaluations/999/promote")
        assert resp.status_code == 404

    def test_promote_idor_blocked(self) -> None:
        repo = _make_repo()

        with Session(repo.engine) as session:
            entry = EvaluationEntryRow(user_id=_OTHER_USER.id, card_name="Other Card")
            session.add(entry)
            session.commit()
            entry_id = entry.id

        client = TestClient(_create_app(repo))
        resp = client.post(f"/api/v1/evaluations/{entry_id}/promote")
        assert resp.status_code == 404
