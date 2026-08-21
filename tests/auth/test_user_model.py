"""Tests for UserRow database model."""

from __future__ import annotations

from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import Session

from src.database.models import Base, UserRow


class TestUserRow:
    def setup_method(self):
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(self.engine)

    def test_table_exists(self):
        inspector = inspect(self.engine)
        tables = inspector.get_table_names()
        assert "users" in tables

    def test_create_user(self):
        with Session(self.engine) as session:
            user = UserRow(
                email="test@example.com",
                auth_provider="email",
                display_name="Test",
                password_hash="$2b$12$fakehash",
            )
            session.add(user)
            session.commit()
            session.refresh(user)

            assert user.id is not None
            assert user.email == "test@example.com"
            assert user.auth_provider == "email"
            assert user.is_active == 1
            assert user.created_at is not None

    def test_email_unique_constraint(self):
        import sqlalchemy

        with Session(self.engine) as session:
            u1 = UserRow(email="dup@test.com", auth_provider="email")
            session.add(u1)
            session.commit()

        with Session(self.engine) as session:
            u2 = UserRow(email="dup@test.com", auth_provider="google")
            session.add(u2)
            try:
                session.commit()
                assert False, "Should have raised IntegrityError"
            except sqlalchemy.exc.IntegrityError:
                session.rollback()

    def test_nullable_fields(self):
        with Session(self.engine) as session:
            user = UserRow(email="minimal@test.com", auth_provider="email")
            session.add(user)
            session.commit()
            session.refresh(user)

            assert user.display_name is None
            assert user.avatar_url is None
            assert user.provider_id is None
            assert user.password_hash is None

    def test_indexes_exist(self):
        inspector = inspect(self.engine)
        indexes = inspector.get_indexes("users")
        index_names = [idx["name"] for idx in indexes]
        assert "ix_users_email" in index_names
        assert "ix_users_provider" in index_names
