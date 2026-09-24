"""Tests for achievement service (F109-T01)."""

from __future__ import annotations

from datetime import datetime

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from src.database.models import (
    CreditBalanceRow,
    CreditTransactionRow,
    DeckRow,
    ScanRunRow,
    UserCollectionRow,
)
from src.database.repository import Repository
from src.services.achievement_rewards import ACHIEVEMENT_TIERS
from src.services.achievements import (
    ACHIEVEMENT_DEFINITIONS,
    check_achievements,
    check_achievements_with_rewards,
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

    def test_reward_fields_present(self, repo, user_id):
        check_achievements(user_id, repo)

        achievements = get_user_achievements(user_id, repo)
        by_key = {a["key"]: a for a in achievements}

        for key, tier in ACHIEVEMENT_TIERS.items():
            assert by_key[key]["tier"] == tier
            assert by_key[key]["reward"] > 0

    def test_reward_credited_only_for_credited_keys(self, repo, user_id):
        check_achievements(user_id, repo)  # unlocks + credits early_adopter

        achievements = get_user_achievements(user_id, repo)
        by_key = {a["key"]: a for a in achievements}

        assert by_key["early_adopter"]["reward_credited"] is True
        assert by_key["first_card"]["reward_credited"] is False


class TestCheckAchievementsWithRewards:
    def test_credits_reward_on_unlock(self, repo, user_id):
        result = check_achievements_with_rewards(user_id, repo)

        assert "early_adopter" in result["newly_unlocked"]
        reward = next(r for r in result["rewards"] if r["key"] == "early_adopter")
        assert reward["amount"] == 100
        assert reward["tier"] == "uncommon"
        assert result["total_reward"] >= 100

        with Session(repo.engine) as session:
            bal = session.execute(
                select(CreditTransactionRow).where(
                    CreditTransactionRow.user_id == user_id,
                    CreditTransactionRow.reason == "achievement_reward",
                    CreditTransactionRow.reference_id == "achievement:early_adopter",
                )
            ).scalars().all()
            assert len(bal) == 1

            balance_row = session.execute(
                select(CreditBalanceRow).where(CreditBalanceRow.user_id == user_id)
            ).scalar_one()
            assert balance_row.balance == result["total_reward"]

    def test_second_check_no_new_rewards(self, repo, user_id):
        check_achievements_with_rewards(user_id, repo)
        result = check_achievements_with_rewards(user_id, repo)

        assert result["newly_unlocked"] == []
        assert result["total_reward"] == 0
        assert result["rewards"] == []

        with Session(repo.engine) as session:
            balance_row = session.execute(
                select(CreditBalanceRow).where(CreditBalanceRow.user_id == user_id)
            ).scalar_one()
            first_balance = balance_row.balance

        result2 = check_achievements_with_rewards(user_id, repo)
        assert result2["total_reward"] == 0

        with Session(repo.engine) as session:
            balance_row = session.execute(
                select(CreditBalanceRow).where(CreditBalanceRow.user_id == user_id)
            ).scalar_one()
            assert balance_row.balance == first_balance

    def test_lazy_backfill_credits_pre_existing_achievement(self, repo, user_id):
        # Simulate an achievement unlocked before this feature (no ledger row).
        from src.database.models import AchievementRow

        with Session(repo.engine) as session:
            session.add(
                AchievementRow(
                    user_id=user_id,
                    achievement_key="set_master",
                    unlocked_at=datetime.now(),
                )
            )
            session.commit()

        result = check_achievements_with_rewards(user_id, repo)

        # set_master (1000) plus early_adopter unlocked now (100).
        assert result["backfilled"] == 1000

        with Session(repo.engine) as session:
            tx = session.execute(
                select(CreditTransactionRow).where(
                    CreditTransactionRow.user_id == user_id,
                    CreditTransactionRow.reference_id == "achievement:set_master",
                )
            ).scalars().all()
            assert len(tx) == 1
            assert tx[0].amount == 1000

    def test_unknown_legacy_key_ignored(self, repo, user_id):
        # A legacy AchievementRow whose key is no longer in ACHIEVEMENT_TIERS
        # must be skipped by backfill (reward 0) without raising.
        from src.database.models import AchievementRow

        with Session(repo.engine) as session:
            session.add(
                AchievementRow(
                    user_id=user_id,
                    achievement_key="retired_achievement",
                    unlocked_at=datetime.now(),
                )
            )
            session.commit()

        result = check_achievements_with_rewards(user_id, repo)

        with Session(repo.engine) as session:
            tx = session.execute(
                select(CreditTransactionRow).where(
                    CreditTransactionRow.user_id == user_id,
                    CreditTransactionRow.reference_id == "achievement:retired_achievement",
                )
            ).scalars().all()
            assert tx == []

        assert result is not None

    def test_backfill_runs_even_without_new_unlocks(self, repo, user_id):
        check_achievements_with_rewards(user_id, repo)  # unlocks + credits early_adopter

        from src.database.models import AchievementRow

        with Session(repo.engine) as session:
            session.add(
                AchievementRow(
                    user_id=user_id,
                    achievement_key="set_master",
                    unlocked_at=datetime.now(),
                )
            )
            session.commit()

        result = check_achievements_with_rewards(user_id, repo)
        assert result["newly_unlocked"] == []
        assert result["backfilled"] == 1000


class TestGrantSetMasterRewards:
    def test_grant_set_master_credits_once(self, repo, user_id):
        result = grant_set_master(user_id, repo)
        assert result is True

        result2 = grant_set_master(user_id, repo)
        assert result2 is False

        with Session(repo.engine) as session:
            tx = session.execute(
                select(CreditTransactionRow).where(
                    CreditTransactionRow.user_id == user_id,
                    CreditTransactionRow.reference_id == "achievement:set_master",
                )
            ).scalars().all()
            assert len(tx) == 1
            assert tx[0].amount == 1000


class TestTreasureHunterBugFix:
    def test_bonus_claim_reason_unlocks_treasure_hunter(self, repo, user_id):
        check_achievements(user_id, repo)  # clear early_adopter

        with Session(repo.engine) as session:
            for _ in range(5):
                session.add(
                    CreditTransactionRow(user_id=user_id, amount=5, reason="bonus_claim")
                )
            session.commit()

        newly = check_achievements(user_id, repo)
        assert "treasure_hunter" in newly

    def test_four_bonus_claims_do_not_unlock(self, repo, user_id):
        check_achievements(user_id, repo)  # clear early_adopter

        with Session(repo.engine) as session:
            for _ in range(4):
                session.add(
                    CreditTransactionRow(user_id=user_id, amount=5, reason="bonus_claim")
                )
            session.commit()

        newly = check_achievements(user_id, repo)
        assert "treasure_hunter" not in newly

    def test_achievement_reward_transactions_not_counted(self, repo, user_id):
        check_achievements(user_id, repo)  # clear early_adopter (credits a reward tx)

        with Session(repo.engine) as session:
            for _ in range(5):
                session.add(
                    CreditTransactionRow(
                        user_id=user_id,
                        amount=100,
                        reason="achievement_reward",
                        reference_id="achievement:something",
                    )
                )
            session.commit()

        newly = check_achievements(user_id, repo)
        assert "treasure_hunter" not in newly
