"""Tests for achievement service (F109-T01)."""

from __future__ import annotations

from datetime import datetime

import pytest
from sqlalchemy.orm import Session

from src.database.models import (
    CreditTransactionRow,
    DeckRow,
    ScanRunRow,
    UserCollectionRow,
)
from src.database.repository import Repository
from src.services.achievements import (
    ACHIEVEMENT_DEFINITIONS,
    check_achievements,
    get_definition,
    get_user_achievements,
    grant_set_master,
)


@pytest.fixture()
def repo(tmp_path):
    db_path = tmp_path / "test_achievements.db"
    db_url = f"sqlite:///{db_path}"
    return Repository(db_url=db_url)


@pytest.fixture()
def user_id(repo):
    """Create a test user and return user id."""
    repo.create_user(email="test@example.com", display_name="Test User")
    with Session(repo.engine) as session:
        from src.database.models import UserRow

        user = session.query(UserRow).filter_by(email="test@example.com").first()
        return user.id


class TestGetDefinition:
    def test_known_key(self):
        defn = get_definition("first_card")
        assert defn is not None
        assert defn["key"] == "first_card"
        assert defn["icon"] == "card"

    def test_unknown_key(self):
        assert get_definition("nonexistent") is None


class TestCheckAchievements:
    def test_no_achievements_for_new_user(self, repo, user_id):
        # A brand new user with no activity except early_adopter (created before cutoff)
        newly = check_achievements(user_id, repo)
        # Should get early_adopter since test user is created "now" which is before 2027
        assert "early_adopter" in newly

    def test_first_card_achievement(self, repo, user_id):
        # Clear early adopter first
        check_achievements(user_id, repo)

        # Add a card to collection
        with Session(repo.engine) as session:
            session.add(
                UserCollectionRow(
                    user_id=str(user_id),
                    set_code="2ed",
                    collector_number="157",
                    name_en="Lightning Bolt",
                )
            )
            session.commit()

        newly = check_achievements(user_id, repo)
        assert "first_card" in newly

    def test_idempotent_check(self, repo, user_id):
        # Add a card
        with Session(repo.engine) as session:
            session.add(
                UserCollectionRow(
                    user_id=str(user_id),
                    set_code="2ed",
                    collector_number="157",
                    name_en="Lightning Bolt",
                )
            )
            session.commit()

        first_check = check_achievements(user_id, repo)
        assert "first_card" in first_check

        # Second check should return empty (already unlocked)
        second_check = check_achievements(user_id, repo)
        assert "first_card" not in second_check

    def test_deck_builder_achievement(self, repo, user_id):
        check_achievements(user_id, repo)  # clear early_adopter

        with Session(repo.engine) as session:
            session.add(DeckRow(user_id=str(user_id), name="Test Deck"))
            session.commit()

        newly = check_achievements(user_id, repo)
        assert "deck_builder" in newly

    def test_scanner_achievement(self, repo, user_id):
        check_achievements(user_id, repo)  # clear early_adopter

        with Session(repo.engine) as session:
            session.add(
                ScanRunRow(
                    scan_type="collection",
                    status="completed",
                    started_at=datetime.now(),
                    finished_at=datetime.now(),
                )
            )
            session.commit()

        newly = check_achievements(user_id, repo)
        assert "scanner" in newly

    def test_collector_milestones(self, repo, user_id):
        check_achievements(user_id, repo)  # clear early_adopter

        # Add 10 cards
        with Session(repo.engine) as session:
            for i in range(10):
                session.add(
                    UserCollectionRow(
                        user_id=str(user_id),
                        set_code="2ed",
                        collector_number=str(i),
                        name_en=f"Card {i}",
                    )
                )
            session.commit()

        newly = check_achievements(user_id, repo)
        assert "first_card" in newly
        assert "collector_10" in newly
        assert "collector_50" not in newly

    def test_treasure_hunter_achievement(self, repo, user_id):
        check_achievements(user_id, repo)  # clear early_adopter

        with Session(repo.engine) as session:
            for i in range(5):
                session.add(
                    CreditTransactionRow(
                        user_id=user_id,
                        amount=5,
                        reason="bonus",
                    )
                )
            session.commit()

        newly = check_achievements(user_id, repo)
        assert "treasure_hunter" in newly


class TestGrantSetMaster:
    def test_grant_set_master(self, repo, user_id):
        result = grant_set_master(user_id, repo)
        assert result is True

        # Second call should return False (already granted)
        result2 = grant_set_master(user_id, repo)
        assert result2 is False


class TestGetUserAchievements:
    def test_returns_all_definitions(self, repo, user_id):
        achievements = get_user_achievements(user_id, repo)
        assert len(achievements) == len(ACHIEVEMENT_DEFINITIONS)

    def test_shows_unlocked_status(self, repo, user_id):
        # Trigger check to get early_adopter
        check_achievements(user_id, repo)

        achievements = get_user_achievements(user_id, repo)
        by_key = {a["key"]: a for a in achievements}

        assert by_key["early_adopter"]["unlocked"] is True
        assert by_key["early_adopter"]["unlocked_at"] is not None
        assert by_key["first_card"]["unlocked"] is False
        assert by_key["first_card"]["unlocked_at"] is None
