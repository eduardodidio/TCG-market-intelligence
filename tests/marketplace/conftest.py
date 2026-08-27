"""Shared fixtures for marketplace tests."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from src.api.app import create_app
from src.database.models import UserCollectionRow, UserRow
from src.database.repository import Repository
from src.domain.models import User


@pytest.fixture()
def integration_repo(tmp_path):
    db_path = tmp_path / "test_mkt_integration.db"
    db_url = f"sqlite:///{db_path}"
    return Repository(db_url=db_url)


def create_db_user(
    repo: Repository,
    user_id: int,
    email: str,
    *,
    is_admin: bool = False,
    credits: int = 100,
) -> User:
    """Create a user in the DB with optional credits."""
    with Session(repo.engine) as session:
        user = UserRow(
            id=user_id,
            email=email,
            auth_provider="email",
            password_hash="fakehash",
            is_admin=int(is_admin),
        )
        session.add(user)
        session.commit()

    if credits > 0:
        repo.ensure_credit_balance(user_id)
        repo.update_credit_balance(user_id, delta=credits, reason="test_grant")

    return User(
        id=user_id,
        email=email,
        display_name=None,
        auth_provider="email",
        is_admin=is_admin,
    )


def create_collection_entry(
    repo: Repository,
    user_id: int,
    name_en: str = "Lightning Bolt",
    set_code: str = "lea",
    collector_number: str = "161",
) -> int:
    """Create a collection entry, returns entry_id."""
    with Session(repo.engine) as session:
        entry = UserCollectionRow(
            user_id=str(user_id),
            name_en=name_en,
            set_code=set_code,
            collector_number=collector_number,
            rarity="C",
        )
        session.add(entry)
        session.commit()
        session.refresh(entry)
        return entry.id


def make_client_for_user(repo: Repository, user: User) -> TestClient:
    """Create a TestClient authenticated as the given user."""
    app = create_app()

    def override_db():
        yield repo

    def override_user():
        return user

    def override_optional_user():
        return user

    from src.api.deps import get_current_user, get_db, get_optional_user

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_current_user] = override_user
    app.dependency_overrides[get_optional_user] = override_optional_user

    return TestClient(app)
