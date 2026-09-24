"""Tests for the achievements API router (F109-T01)."""

from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from src.api.deps import get_current_user, get_db
from src.api.routers.achievements import router
from src.database.models import UserCollectionRow
from src.database.repository import Repository
from src.domain.models import User


def _make_user(user_id: int = 1, is_admin: bool = False, lang: str = "en") -> User:
    return User(
        id=user_id,
        email="test@example.com",
        display_name="Test User",
        auth_provider="email",
        preferred_language=lang,
        is_active=True,
        is_admin=is_admin,
    )


@pytest.fixture()
def repo(tmp_path):
    db_path = tmp_path / "test_achievements_api.db"
    db_url = f"sqlite:///{db_path}"
    return Repository(db_url=db_url)


@pytest.fixture()
def user():
    return _make_user()


@pytest.fixture()
def test_app(repo, user):
    app = FastAPI()
    app.include_router(router, prefix="/api/v1")
    app.dependency_overrides[get_db] = lambda: repo
    app.dependency_overrides[get_current_user] = lambda: user
    repo.create_user(email=user.email, display_name=user.display_name)
    return app


@pytest.fixture()
def client(test_app):
    return TestClient(test_app)


class TestListAchievements:
    def test_returns_all_achievements(self, client):
        resp = client.get("/api/v1/achievements")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert isinstance(data, list)
        assert len(data) == 11  # 11 achievement definitions

    def test_shows_unlocked_status(self, client):
        resp = client.get("/api/v1/achievements")
        data = resp.json()["data"]
        for a in data:
            assert "key" in a
            assert "title" in a
            assert "description" in a
            assert "icon" in a
            assert "unlocked" in a
            assert "unlocked_at" in a

    def test_english_titles(self, client):
        resp = client.get("/api/v1/achievements")
        data = resp.json()["data"]
        first_card = next(a for a in data if a["key"] == "first_card")
        assert first_card["title"] == "First Card"

    def test_portuguese_titles(self, repo):
        user_pt = _make_user(lang="pt-BR")
        app = FastAPI()
        app.include_router(router, prefix="/api/v1")
        app.dependency_overrides[get_db] = lambda: repo
        app.dependency_overrides[get_current_user] = lambda: user_pt
        client_pt = TestClient(app)

        resp = client_pt.get("/api/v1/achievements")
        data = resp.json()["data"]
        first_card = next(a for a in data if a["key"] == "first_card")
        assert first_card["title"] == "Primeira Carta"


class TestCheckAchievements:
    def test_check_returns_newly_unlocked(self, client):
        resp = client.post("/api/v1/achievements/check")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert "newly_unlocked" in data
        assert isinstance(data["newly_unlocked"], list)
        # Early adopter should be unlocked for new test user
        assert "early_adopter" in data["newly_unlocked"]

    def test_check_idempotent(self, client):
        # First check
        resp1 = client.post("/api/v1/achievements/check")
        assert len(resp1.json()["data"]["newly_unlocked"]) > 0

        # Second check — no new achievements
        resp2 = client.post("/api/v1/achievements/check")
        assert len(resp2.json()["data"]["newly_unlocked"]) == 0

    def test_check_after_adding_card(self, client, repo, user):
        # Clear initial achievements
        client.post("/api/v1/achievements/check")

        # Add a card
        with Session(repo.engine) as session:
            session.add(
                UserCollectionRow(
                    user_id=str(user.id),
                    set_code="2ed",
                    collector_number="157",
                    name_en="Lightning Bolt",
                )
            )
            session.commit()

        # Check again
        resp = client.post("/api/v1/achievements/check")
        assert "first_card" in resp.json()["data"]["newly_unlocked"]

    def test_check_returns_rewards_and_balance(self, client):
        resp = client.post("/api/v1/achievements/check")
        data = resp.json()["data"]

        assert "rewards" in data
        assert "total_reward" in data
        assert "backfilled" in data
        assert "balance" in data

        reward = next(r for r in data["rewards"] if r["key"] == "early_adopter")
        assert reward["amount"] == 100
        assert reward["tier"] == "uncommon"
        assert data["total_reward"] == 100
        assert data["balance"] == 100

    def test_check_ignores_unknown_legacy_achievement_key(self, client, repo, user):
        from src.database.models import AchievementRow

        with Session(repo.engine) as session:
            session.add(
                AchievementRow(user_id=user.id, achievement_key="retired_achievement")
            )
            session.commit()

        resp = client.post("/api/v1/achievements/check")
        assert resp.status_code == 200

    def test_second_check_no_reward_no_balance_change(self, client):
        resp1 = client.post("/api/v1/achievements/check")
        balance_after_first = resp1.json()["data"]["balance"]

        resp2 = client.post("/api/v1/achievements/check")
        data2 = resp2.json()["data"]

        assert data2["newly_unlocked"] == []
        assert data2["total_reward"] == 0
        assert data2["balance"] == balance_after_first


class TestListAchievementsRewardFields:
    def test_reward_fields_present_for_locked_and_unlocked(self, client):
        client.post("/api/v1/achievements/check")

        resp = client.get("/api/v1/achievements")
        data = resp.json()["data"]
        by_key = {a["key"]: a for a in data}

        assert by_key["early_adopter"]["reward_credited"] is True
        assert by_key["early_adopter"]["reward"] == 100
        assert by_key["early_adopter"]["tier"] == "uncommon"

        assert by_key["first_card"]["reward_credited"] is False
        assert by_key["first_card"]["reward"] == 50
        assert by_key["first_card"]["tier"] == "common"

    def test_reward_fields_present_pt_br(self, repo):
        user_pt = _make_user(lang="pt-BR")
        app = FastAPI()
        app.include_router(router, prefix="/api/v1")
        app.dependency_overrides[get_db] = lambda: repo
        app.dependency_overrides[get_current_user] = lambda: user_pt
        client_pt = TestClient(app)

        resp = client_pt.get("/api/v1/achievements")
        data = resp.json()["data"]
        first_card = next(a for a in data if a["key"] == "first_card")
        assert first_card["reward"] == 50
        assert first_card["tier"] == "common"
