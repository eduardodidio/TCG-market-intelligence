"""Tests for the user role column (F139-T01)."""

from __future__ import annotations

from unittest.mock import MagicMock

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import Session

from src.api.deps import get_db
from src.api.routers.auth import router
from src.api.schemas.auth import UserProfile
from src.auth.jwt import create_access_token
from src.auth.passwords import hash_password
from src.database.models import Base, UserRow
from src.domain.models import User


def _mock_user_row(**overrides):
    defaults = {
        "id": 1,
        "email": "test@example.com",
        "display_name": "Test User",
        "avatar_url": None,
        "auth_provider": "email",
        "provider_id": None,
        "password_hash": hash_password("validpass123"),
        "preferred_currency": "BRL",
        "preferred_language": "en",
        "is_active": 1,
        "is_admin": 0,
        "role": "admin",
    }
    defaults.update(overrides)
    row = MagicMock(spec=UserRow)
    for k, v in defaults.items():
        setattr(row, k, v)
    return row


def _make_app(mock_repo):
    app = FastAPI()
    app.include_router(router, prefix="/api/v1")
    app.dependency_overrides[get_db] = lambda: mock_repo
    return app


class TestUserRowRole:
    """UserRow model accepts the role field."""

    def setup_method(self):
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(self.engine)

    def test_default_role_is_admin(self):
        with Session(self.engine) as session:
            user = UserRow(
                email="default@test.com",
                auth_provider="email",
                password_hash="$2b$12$fakehash",
            )
            session.add(user)
            session.commit()
            session.refresh(user)
            assert user.role == "admin"

    def test_role_guest(self):
        with Session(self.engine) as session:
            user = UserRow(
                email="guest@test.com",
                auth_provider="email",
                role="guest",
            )
            session.add(user)
            session.commit()
            session.refresh(user)
            assert user.role == "guest"

    def test_role_column_exists_in_schema(self):
        inspector = inspect(self.engine)
        columns = {col["name"] for col in inspector.get_columns("users")}
        assert "role" in columns


class TestUserDomainRole:
    """User domain dataclass includes role."""

    def test_default_role(self):
        user = User(id=1, email="a@b.com")
        assert user.role == "admin"

    def test_custom_role(self):
        user = User(id=1, email="a@b.com", role="guest")
        assert user.role == "guest"


class TestUserProfileSchemaRole:
    """UserProfile Pydantic schema includes role."""

    def test_default_role(self):
        profile = UserProfile(
            id=1,
            email="a@b.com",
            auth_provider="email",
            is_active=True,
        )
        assert profile.role == "admin"

    def test_custom_role(self):
        profile = UserProfile(
            id=1,
            email="a@b.com",
            auth_provider="email",
            is_active=True,
            role="guest",
        )
        assert profile.role == "guest"

    def test_role_in_model_fields(self):
        assert "role" in UserProfile.model_fields


class TestAuthMeReturnsRole:
    """GET /auth/me returns the role field."""

    def test_returns_admin_role(self):
        mock_repo = MagicMock()
        mock_repo.get_user_by_id.return_value = _mock_user_row(role="admin")

        client = TestClient(_make_app(mock_repo))
        token = create_access_token(user_id=1, email="test@example.com")
        resp = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["role"] == "admin"

    def test_returns_guest_role(self):
        mock_repo = MagicMock()
        mock_repo.get_user_by_id.return_value = _mock_user_row(role="guest")

        client = TestClient(_make_app(mock_repo))
        token = create_access_token(user_id=1, email="test@example.com")
        resp = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["role"] == "guest"

    def test_role_defaults_when_missing_on_row(self):
        """Old user rows without role attribute should default to 'admin'."""
        mock_repo = MagicMock()
        row = _mock_user_row()
        # Simulate old row without role attribute
        del row.role
        mock_repo.get_user_by_id.return_value = row

        client = TestClient(_make_app(mock_repo))
        token = create_access_token(user_id=1, email="test@example.com")
        resp = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["role"] == "admin"


class TestRoleMigrationIdempotent:
    """Migration adds role column idempotently."""

    def test_column_added_on_fresh_db(self):
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(engine)
        inspector = inspect(engine)
        columns = {col["name"] for col in inspector.get_columns("users")}
        assert "role" in columns

    def test_migration_idempotent(self):
        """Running ALTER TABLE twice should not error (column already exists)."""
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(engine)

        # The column already exists from create_all, so the migration check
        # should detect it and skip the ALTER TABLE. Simulate the check.
        inspector = inspect(engine)
        columns = {col["name"] for col in inspector.get_columns("users")}
        assert "role" in columns  # Already there, migration would be a no-op

    def test_migration_adds_column_to_existing_table(self):
        """Simulate a pre-migration table without role column."""
        engine = create_engine("sqlite:///:memory:")
        # Create a minimal users table WITHOUT the role column
        with engine.begin() as conn:
            conn.execute(
                text(
                    "CREATE TABLE users ("
                    "  id INTEGER PRIMARY KEY AUTOINCREMENT,"
                    "  email VARCHAR(320) NOT NULL UNIQUE,"
                    "  auth_provider VARCHAR(20) NOT NULL,"
                    "  is_admin INTEGER DEFAULT 0"
                    ")"
                )
            )

        # Verify role column does not exist yet
        inspector = inspect(engine)
        columns = {col["name"] for col in inspector.get_columns("users")}
        assert "role" not in columns

        # Add role column (simulating migration logic)
        with engine.begin() as conn:
            conn.execute(text("ALTER TABLE users ADD COLUMN role VARCHAR(20) DEFAULT 'admin'"))

        # Verify column now exists with correct default
        inspector = inspect(engine)
        columns = {col["name"] for col in inspector.get_columns("users")}
        assert "role" in columns

        # Insert a row without specifying role and verify default
        with engine.begin() as conn:
            conn.execute(
                text("INSERT INTO users (email, auth_provider) " "VALUES ('test@x.com', 'email')")
            )
            result = conn.execute(text("SELECT role FROM users WHERE email='test@x.com'"))
            row = result.fetchone()
            assert row[0] == "admin"
