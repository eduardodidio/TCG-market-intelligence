"""Tests for F213-T06: Banlist API — owned filter, status endpoint, manual sync.

Covers:
- owned_only filter with mock collection (returns subset)
- owned_only without auth returns 401
- status endpoint returns correct schema
- sync endpoint requires admin (403 for non-admin)
- pagination with owned_only
"""

from __future__ import annotations

from datetime import datetime

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from src.api.deps import get_db, get_optional_user, require_admin
from src.api.routers.banlist import router
from src.database.models import (
    Base,
    CardLegalityRow,
    CardRow,
    LegalityHistoryRow,
    UserCollectionRow,
)
from src.database.repository import Repository
from src.domain.models import User

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_repo() -> Repository:
    """Create an in-memory Repository with all tables."""
    repo = Repository.__new__(Repository)
    repo.engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(repo.engine)
    return repo


def _add_card(session: Session, name_en: str, set_code: str = "lea", cn: str = "1") -> int:
    card = CardRow(game="magic", name_en=name_en, set_code=set_code, collector_number=cn)
    session.add(card)
    session.flush()
    return card.id


def _add_legality(session: Session, card_id: int, fmt: str, status: str) -> None:
    session.add(CardLegalityRow(card_id=card_id, format=fmt, status=status))


def _add_history(session: Session, card_id: int, fmt: str, new_status: str) -> None:
    session.add(
        LegalityHistoryRow(
            card_id=card_id,
            format=fmt,
            new_status=new_status,
            changed_at=datetime.now(),
            source="scryfall_sync",
        )
    )


def _add_collection(
    session: Session, user_id: str, card_id: int, name_en: str, qty: int = 1
) -> None:
    session.add(
        UserCollectionRow(
            user_id=user_id,
            card_id=card_id,
            set_code="lea",
            collector_number="1",
            name_en=name_en,
            quantity=qty,
        )
    )


def _make_app(
    repo: Repository,
    user: User | None = None,
    admin_override: User | None = None,
) -> FastAPI:
    """Build a minimal FastAPI app with the banlist router.

    Parameters
    ----------
    repo : Repository to inject
    user : User returned by get_optional_user (None = anonymous)
    admin_override : If set, require_admin returns this user.
                     If None, require_admin is NOT overridden (will check real auth).
    """
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_db] = lambda: repo
    app.dependency_overrides[get_optional_user] = lambda: user
    if admin_override is not None:
        app.dependency_overrides[require_admin] = lambda: admin_override
    app.state.repo = repo
    return app


ADMIN_USER = User(id=1, email="admin@test.com", display_name="Admin", is_admin=True)
REGULAR_USER = User(id=2, email="user@test.com", display_name="User", is_admin=False)


# ---------------------------------------------------------------------------
# GET /banlist — owned_only filter
# ---------------------------------------------------------------------------


class TestOwnedOnlyFilter:
    """owned_only=true filters to cards the user owns."""

    def test_owned_only_returns_only_owned_cards(self):
        repo = _make_repo()
        with Session(repo.engine) as s:
            id_owned = _add_card(s, "Channel", set_code="lea", cn="1")
            id_other = _add_card(s, "Balance", set_code="lea", cn="2")
            _add_legality(s, id_owned, "vintage", "banned")
            _add_legality(s, id_other, "vintage", "banned")
            _add_collection(s, "1", id_owned, "Channel", qty=3)
            s.commit()

        user = User(id=1, email="u@test.com", display_name="U")
        app = _make_app(repo, user=user)
        client = TestClient(app)

        resp = client.get("/banlist?format=vintage&owned_only=true")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert len(data) == 1
        assert data[0]["name_en"] == "Channel"
        assert data[0]["owned"] is True
        assert data[0]["owned_quantity"] == 3

    def test_owned_only_false_returns_all(self):
        repo = _make_repo()
        with Session(repo.engine) as s:
            id1 = _add_card(s, "Channel", cn="1")
            id2 = _add_card(s, "Balance", set_code="lea", cn="2")
            _add_legality(s, id1, "vintage", "banned")
            _add_legality(s, id2, "vintage", "restricted")
            _add_collection(s, "1", id1, "Channel")
            s.commit()

        user = User(id=1, email="u@test.com", display_name="U")
        app = _make_app(repo, user=user)
        client = TestClient(app)

        resp = client.get("/banlist?format=vintage&owned_only=false")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert len(data) == 2

    def test_owned_only_without_auth_returns_401(self):
        repo = _make_repo()
        app = _make_app(repo, user=None)
        client = TestClient(app)

        resp = client.get("/banlist?format=vintage&owned_only=true")
        assert resp.status_code == 401

    def test_owned_only_no_matches_returns_empty(self):
        """User owns no banned cards -> empty list."""
        repo = _make_repo()
        with Session(repo.engine) as s:
            cid = _add_card(s, "Balance")
            _add_legality(s, cid, "vintage", "banned")
            s.commit()

        user = User(id=1, email="u@test.com", display_name="U")
        app = _make_app(repo, user=user)
        client = TestClient(app)

        resp = client.get("/banlist?format=vintage&owned_only=true")
        assert resp.status_code == 200
        assert resp.json()["data"] == []
        assert resp.json()["meta"]["total"] == 0


# ---------------------------------------------------------------------------
# GET /banlist — pagination with owned_only
# ---------------------------------------------------------------------------


class TestPaginationWithOwnedOnly:
    """Pagination (limit/offset) works correctly with owned_only."""

    def _seed(self, repo: Repository, count: int = 5) -> User:
        with Session(repo.engine) as s:
            for i in range(count):
                cid = _add_card(s, f"Card{i}", set_code="lea", cn=str(i))
                _add_legality(s, cid, "vintage", "banned")
                _add_collection(s, "1", cid, f"Card{i}")
            s.commit()
        return User(id=1, email="u@test.com", display_name="U")

    def test_limit_respects_owned_only(self):
        repo = _make_repo()
        user = self._seed(repo, count=5)
        app = _make_app(repo, user=user)
        client = TestClient(app)

        resp = client.get("/banlist?format=vintage&owned_only=true&limit=2")
        assert resp.status_code == 200
        body = resp.json()
        assert len(body["data"]) == 2
        assert body["meta"]["total"] == 5

    def test_offset_respects_owned_only(self):
        repo = _make_repo()
        user = self._seed(repo, count=5)
        app = _make_app(repo, user=user)
        client = TestClient(app)

        resp = client.get("/banlist?format=vintage&owned_only=true&limit=2&offset=3")
        assert resp.status_code == 200
        body = resp.json()
        assert len(body["data"]) == 2
        assert body["meta"]["total"] == 5

    def test_offset_beyond_total_returns_empty(self):
        repo = _make_repo()
        user = self._seed(repo, count=3)
        app = _make_app(repo, user=user)
        client = TestClient(app)

        resp = client.get("/banlist?format=vintage&owned_only=true&offset=10")
        assert resp.status_code == 200
        body = resp.json()
        assert body["data"] == []
        assert body["meta"]["total"] == 3


# ---------------------------------------------------------------------------
# GET /banlist/status
# ---------------------------------------------------------------------------


class TestBanlistStatus:
    """The /banlist/status endpoint returns correct schema and counts."""

    def test_status_empty_db(self):
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

    def test_status_with_data(self):
        repo = _make_repo()
        with Session(repo.engine) as s:
            id1 = _add_card(s, "Channel", cn="1")
            id2 = _add_card(s, "Balance", set_code="lea", cn="2")
            id3 = _add_card(s, "Black Lotus", set_code="lea", cn="3")
            _add_legality(s, id1, "vintage", "banned")
            _add_legality(s, id2, "vintage", "restricted")
            _add_legality(s, id3, "legacy", "banned")
            _add_history(s, id1, "vintage", "banned")
            _add_history(s, id3, "legacy", "banned")
            s.commit()

        app = _make_app(repo, user=None)
        client = TestClient(app)

        resp = client.get("/banlist/status")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["legalities_count"] == 3
        assert data["banned_count"] == 2
        assert data["restricted_count"] == 1
        assert data["history_count"] == 2
        assert data["formats"] == 2

    def test_status_is_public_no_auth_needed(self):
        """Endpoint works without any user authentication."""
        repo = _make_repo()
        app = _make_app(repo, user=None)
        client = TestClient(app)

        resp = client.get("/banlist/status")
        assert resp.status_code == 200

    def test_status_schema_keys(self):
        """Verify all expected keys are present in the response."""
        repo = _make_repo()
        app = _make_app(repo, user=None)
        client = TestClient(app)

        resp = client.get("/banlist/status")
        data = resp.json()["data"]
        expected_keys = {
            "last_synced_at",
            "legalities_count",
            "banned_count",
            "restricted_count",
            "history_count",
            "formats",
        }
        assert expected_keys == set(data.keys())


# ---------------------------------------------------------------------------
# POST /banlist/sync — admin-only
# ---------------------------------------------------------------------------


class TestSyncEndpoint:
    """The /banlist/sync endpoint requires admin role."""

    def test_sync_as_admin_starts_job(self):
        repo = _make_repo()
        app = _make_app(repo, user=ADMIN_USER, admin_override=ADMIN_USER)
        client = TestClient(app)

        resp = client.post("/banlist/sync", json={"bulk": True})
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["status"] == "running"
        assert "job_id" in data
        assert data["message"] == "Banlist sync started"

    def test_sync_without_auth_returns_401(self):
        """No auth at all -> 401."""
        repo = _make_repo()
        # Do NOT override require_admin so it tries to authenticate
        app = FastAPI()
        app.include_router(router)
        app.dependency_overrides[get_db] = lambda: repo
        client = TestClient(app)

        resp = client.post("/banlist/sync", json={"bulk": True})
        assert resp.status_code == 401

    def test_sync_as_non_admin_returns_403(self):
        """Authenticated non-admin user -> 403."""
        from src.api.deps import get_current_user

        repo = _make_repo()
        app = FastAPI()
        app.include_router(router)
        app.dependency_overrides[get_db] = lambda: repo

        # Override get_current_user to return a non-admin user.
        # require_admin depends on get_current_user and checks is_admin.
        app.dependency_overrides[get_current_user] = lambda: REGULAR_USER
        client = TestClient(app)

        resp = client.post("/banlist/sync", json={"bulk": True})
        assert resp.status_code == 403

    def test_sync_with_limit(self):
        repo = _make_repo()
        app = _make_app(repo, user=ADMIN_USER, admin_override=ADMIN_USER)
        client = TestClient(app)

        resp = client.post("/banlist/sync", json={"bulk": False, "limit": 100})
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["status"] == "running"
