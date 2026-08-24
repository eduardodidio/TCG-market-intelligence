"""Tests for User CRUD methods in Repository."""

from __future__ import annotations

import pytest

from src.database.repository import Repository


@pytest.fixture()
def repo():
    return Repository(db_url="sqlite:///:memory:")


class TestCreateUser:
    def test_creates_user_with_email(self, repo):
        user = repo.create_user(email="test@example.com", auth_provider="email")
        assert user.id is not None
        assert user.email == "test@example.com"
        assert user.auth_provider == "email"
        assert user.is_active == 1

    def test_creates_user_with_all_fields(self, repo):
        user = repo.create_user(
            email="full@test.com",
            display_name="Full User",
            auth_provider="google",
            provider_id="google-123",
            password_hash="$2b$12$hash",
        )
        assert user.display_name == "Full User"
        assert user.auth_provider == "google"
        assert user.provider_id == "google-123"
        assert user.password_hash == "$2b$12$hash"

    def test_duplicate_email_raises(self, repo):
        repo.create_user(email="dup@test.com")
        with pytest.raises(Exception):
            repo.create_user(email="dup@test.com")


class TestGetUserById:
    def test_returns_existing_user(self, repo):
        created = repo.create_user(email="get@test.com")
        found = repo.get_user_by_id(created.id)
        assert found is not None
        assert found.email == "get@test.com"

    def test_returns_none_for_missing(self, repo):
        assert repo.get_user_by_id(999) is None


class TestGetUserByEmail:
    def test_returns_user(self, repo):
        repo.create_user(email="find@test.com")
        found = repo.get_user_by_email("find@test.com")
        assert found is not None
        assert found.email == "find@test.com"

    def test_returns_none_for_missing(self, repo):
        assert repo.get_user_by_email("nope@test.com") is None


class TestGetUserByProvider:
    def test_returns_user(self, repo):
        repo.create_user(
            email="oauth@test.com",
            auth_provider="google",
            provider_id="g-456",
        )
        found = repo.get_user_by_provider("google", "g-456")
        assert found is not None
        assert found.email == "oauth@test.com"

    def test_returns_none_for_missing(self, repo):
        assert repo.get_user_by_provider("google", "nonexistent") is None


class TestUpdateUser:
    def test_updates_display_name(self, repo):
        user = repo.create_user(email="upd@test.com", display_name="Old")
        updated = repo.update_user(user.id, display_name="New")
        assert updated is not None
        assert updated.display_name == "New"

    def test_returns_none_for_missing_user(self, repo):
        assert repo.update_user(999, display_name="X") is None

    def test_ignores_unknown_fields(self, repo):
        user = repo.create_user(email="ign@test.com")
        updated = repo.update_user(user.id, nonexistent_field="value")
        assert updated is not None  # No error, just ignored


class TestMigrateCollectionUser:
    def test_migrates_entries(self, repo):
        # Create some collection entries for old user
        from sqlalchemy.orm import Session

        from src.database.models import UserCollectionRow

        with Session(repo.engine) as session:
            for i in range(3):
                session.add(
                    UserCollectionRow(
                        user_id="old_user",
                        set_code="DMR",
                        collector_number=str(i),
                        name_en=f"Card {i}",
                    )
                )
            session.commit()

        count = repo.migrate_collection_user("old_user", "new_user")
        assert count == 3

        # Verify migration
        entries = repo.list_collection(user_id="new_user")
        assert len(entries) == 3

        old_entries = repo.list_collection(user_id="old_user")
        assert len(old_entries) == 0

    def test_no_entries_returns_zero(self, repo):
        count = repo.migrate_collection_user("nobody", "someone")
        assert count == 0
