"""Tests for batch parse and batch add endpoints."""

from __future__ import annotations

from unittest.mock import MagicMock

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from src.api.deps import get_db, require_auth_or_api_key
from src.api.routers.collection import router
from src.database.models import Base, CardRow, UserCollectionRow

_TEST_USER_ID = "test-user-42"


def _create_app(repo_override=None, user_id: str = _TEST_USER_ID) -> FastAPI:
    """Build a minimal FastAPI app with the collection router."""
    app = FastAPI()
    app.include_router(router, prefix="/api/v1")

    if repo_override is not None:
        app.dependency_overrides[get_db] = lambda: repo_override

    app.dependency_overrides[require_auth_or_api_key] = lambda: user_id
    return app


def _create_test_db():
    """Create an in-memory SQLite engine with all tables.

    Uses StaticPool so all connections share the same in-memory database.
    Enables SAVEPOINTs by emitting BEGIN on connect.
    """
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(engine, "connect")
    def _set_sqlite_pragma(dbapi_connection, connection_record):
        # Enable foreign keys
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(engine)
    return engine


class TestBatchParse:
    """POST /api/v1/collection/batch/parse — preview only, no DB."""

    def test_parse_simple_text(self) -> None:
        app = _create_app()
        client = TestClient(app)

        resp = client.post(
            "/api/v1/collection/batch/parse",
            json={"text": "2 Lightning Bolt\nCounterspell"},
        )
        assert resp.status_code == 200
        data = resp.json()["data"]
        entries = data["entries"]
        assert len(entries) == 2
        assert entries[0]["name"] == "Lightning Bolt"
        assert entries[0]["quantity"] == 2
        assert entries[1]["name"] == "Counterspell"
        assert entries[1]["quantity"] == 1

    def test_parse_full_format(self) -> None:
        app = _create_app()
        client = TestClient(app)

        resp = client.post(
            "/api/v1/collection/batch/parse",
            json={"text": "2x Lightning Bolt [m15] NM EN Foil"},
        )
        assert resp.status_code == 200
        entries = resp.json()["data"]["entries"]
        assert len(entries) == 1
        e = entries[0]
        assert e["quantity"] == 2
        assert e["name"] == "Lightning Bolt"
        assert e["set_code"] == "m15"
        assert e["quality"] == "NM"
        assert e["language"] == "EN"
        assert e["extras"] == "Foil"
        assert e["error"] is None

    def test_parse_skips_comments_and_blanks(self) -> None:
        app = _create_app()
        client = TestClient(app)

        text = "# header\n\n2 Lightning Bolt\n# comment\nCounterspell"
        resp = client.post(
            "/api/v1/collection/batch/parse",
            json={"text": text},
        )
        assert resp.status_code == 200
        entries = resp.json()["data"]["entries"]
        assert len(entries) == 2

    def test_parse_returns_errors_for_invalid_lines(self) -> None:
        app = _create_app()
        client = TestClient(app)

        resp = client.post(
            "/api/v1/collection/batch/parse",
            json={"text": "2 [m15]"},
        )
        assert resp.status_code == 200
        entries = resp.json()["data"]["entries"]
        assert len(entries) == 1
        assert entries[0]["error"] == "No card name found"

    def test_parse_no_db_writes(self) -> None:
        """Parse endpoint must not touch the database."""
        app = _create_app()
        client = TestClient(app)

        resp = client.post(
            "/api/v1/collection/batch/parse",
            json={"text": "Lightning Bolt"},
        )
        assert resp.status_code == 200
        # No DB dependency is even injected for parse


class TestBatchAdd:
    """POST /api/v1/collection/batch — add entries to collection."""

    def test_add_three_entries(self) -> None:
        engine = _create_test_db()
        repo = MagicMock()
        repo.engine = engine

        app = _create_app(repo_override=repo)
        client = TestClient(app)

        resp = client.post(
            "/api/v1/collection/batch",
            json={
                "entries": [
                    {"name_en": "Lightning Bolt"},
                    {"name_en": "Counterspell"},
                    {"name_en": "Swords to Plowshares"},
                ]
            },
        )
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["added"] == 3
        assert data["errors"] == []

        # Verify rows exist in DB
        with Session(engine) as session:
            rows = session.query(UserCollectionRow).all()
            assert len(rows) == 3
            names = {r.name_en for r in rows}
            assert names == {"Lightning Bolt", "Counterspell", "Swords to Plowshares"}
            # All should have user_id set
            assert all(r.user_id == _TEST_USER_ID for r in rows)

    def test_auto_links_existing_card(self) -> None:
        engine = _create_test_db()

        # Pre-create a CardRow
        with Session(engine) as session:
            card = CardRow(
                game="magic",
                name_en="Lightning Bolt",
                set_code="m15",
                collector_number="155",
            )
            session.add(card)
            session.commit()
            card_id = card.id

        repo = MagicMock()
        repo.engine = engine

        app = _create_app(repo_override=repo)
        client = TestClient(app)

        resp = client.post(
            "/api/v1/collection/batch",
            json={
                "entries": [
                    {
                        "name_en": "Lightning Bolt",
                        "set_code": "m15",
                        "collector_number": "155",
                    }
                ]
            },
        )
        assert resp.status_code == 200
        assert resp.json()["data"]["added"] == 1

        # Verify it linked to the existing card
        with Session(engine) as session:
            row = session.query(UserCollectionRow).first()
            assert row.card_id == card_id

    def test_auto_creates_card_when_no_match(self) -> None:
        engine = _create_test_db()
        repo = MagicMock()
        repo.engine = engine

        app = _create_app(repo_override=repo)
        client = TestClient(app)

        resp = client.post(
            "/api/v1/collection/batch",
            json={
                "entries": [
                    {"name_en": "Some Rare Card", "set_code": "abc", "collector_number": "999"}
                ]
            },
        )
        assert resp.status_code == 200
        assert resp.json()["data"]["added"] == 1

        # A new CardRow should have been created
        with Session(engine) as session:
            card = session.query(CardRow).filter_by(name_en="Some Rare Card").first()
            assert card is not None
            assert card.game == "magic"
            assert card.set_code == "abc"

            row = session.query(UserCollectionRow).first()
            assert row.card_id == card.id

    def test_401_without_auth(self) -> None:
        from fastapi import HTTPException

        def deny_auth():
            raise HTTPException(status_code=401, detail="Not authenticated")

        app = FastAPI()
        app.include_router(router, prefix="/api/v1")
        app.dependency_overrides[require_auth_or_api_key] = deny_auth
        client = TestClient(app, raise_server_exceptions=False)
        resp = client.post(
            "/api/v1/collection/batch",
            json={"entries": [{"name_en": "Test"}]},
        )
        assert resp.status_code == 401

    def test_max_500_entries_validation(self) -> None:
        app = _create_app()
        client = TestClient(app)

        entries = [{"name_en": f"Card {i}"} for i in range(501)]
        resp = client.post(
            "/api/v1/collection/batch",
            json={"entries": entries},
        )
        assert resp.status_code == 422

    def test_empty_entries_validation(self) -> None:
        app = _create_app()
        client = TestClient(app)

        resp = client.post(
            "/api/v1/collection/batch",
            json={"entries": []},
        )
        assert resp.status_code == 422

    def test_partial_errors(self) -> None:
        """Some valid + some causing DB errors: valid ones succeed."""
        engine = _create_test_db()

        # Create a card that will cause a unique constraint violation
        # if we try to create another with same (game, set_code, collector_number)
        with Session(engine) as session:
            card = CardRow(
                game="magic",
                name_en="Existing Card",
                set_code="abc",
                collector_number="1",
            )
            session.add(card)
            session.commit()

        repo = MagicMock()
        repo.engine = engine

        app = _create_app(repo_override=repo)
        client = TestClient(app)

        # Both entries should succeed (one links, one creates)
        resp = client.post(
            "/api/v1/collection/batch",
            json={
                "entries": [
                    {"name_en": "Lightning Bolt"},
                    {"name_en": "Counterspell"},
                ]
            },
        )
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["added"] == 2

    def test_add_with_quality_and_language(self) -> None:
        engine = _create_test_db()
        repo = MagicMock()
        repo.engine = engine

        app = _create_app(repo_override=repo)
        client = TestClient(app)

        resp = client.post(
            "/api/v1/collection/batch",
            json={
                "entries": [
                    {
                        "name_en": "Lightning Bolt",
                        "quality": "NM",
                        "language": "EN",
                        "extras": "Foil",
                        "quantity": 3,
                    }
                ]
            },
        )
        assert resp.status_code == 200

        with Session(engine) as session:
            row = session.query(UserCollectionRow).first()
            assert row.quality == "NM"
            assert row.language == "EN"
            assert row.extras == "Foil"
            assert row.quantity == 3

    def test_invalid_quality_rejected(self) -> None:
        app = _create_app()
        client = TestClient(app)

        resp = client.post(
            "/api/v1/collection/batch",
            json={"entries": [{"name_en": "Test", "quality": "INVALID"}]},
        )
        assert resp.status_code == 422

    def test_invalid_language_rejected(self) -> None:
        app = _create_app()
        client = TestClient(app)

        resp = client.post(
            "/api/v1/collection/batch",
            json={"entries": [{"name_en": "Test", "language": "XX"}]},
        )
        assert resp.status_code == 422
