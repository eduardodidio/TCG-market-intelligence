"""Tests for achievement reward tiers and idempotent crediting (F179-T02)."""

from __future__ import annotations

import pytest
from sqlalchemy.orm import Session

from src.database.models import AchievementRow, CreditBalanceRow, CreditTransactionRow, UserRow
from src.database.repository import Repository
from src.services.achievement_rewards import (
    ACHIEVEMENT_REWARD_REASON,
    ACHIEVEMENT_TIERS,
    REWARD_TIERS,
    backfill_all_rewards,
    backfill_user_rewards_in_session,
    credit_reward_in_session,
    credited_keys,
    get_reward,
    get_tier,
    reference_id_for,
)
from src.services.achievements import ACHIEVEMENT_DEFINITIONS


@pytest.fixture()
def repo(tmp_path):
    db_path = tmp_path / "test_achievement_rewards.db"
    return Repository(db_url=f"sqlite:///{db_path}")


def _create_user(repo, email):
    repo.create_user(email=email, display_name=email)
    with Session(repo.engine) as session:
        user = session.query(UserRow).filter_by(email=email).first()
        return user.id


@pytest.fixture()
def user_id(repo):
    return _create_user(repo, "test@example.com")


@pytest.fixture()
def _two_users(repo):
    return _create_user(repo, "u1@example.com"), _create_user(repo, "u2@example.com")


class TestTiers:
    def test_reward_tiers_values(self):
        assert REWARD_TIERS == {
            "common": 50,
            "uncommon": 100,
            "rare": 250,
            "mythic": 500,
            "legendary": 1000,
        }

    def test_every_definition_has_a_tier(self):
        for defn in ACHIEVEMENT_DEFINITIONS:
            key = defn["key"]
            assert key in ACHIEVEMENT_TIERS, f"{key} missing from ACHIEVEMENT_TIERS"
            assert ACHIEVEMENT_TIERS[key] in REWARD_TIERS

    def test_get_tier_known(self):
        assert get_tier("first_card") == "common"
        assert get_tier("set_master") == "legendary"

    def test_get_tier_unknown(self):
        assert get_tier("nonexistent") is None

    def test_get_reward_known(self):
        assert get_reward("first_card") == 50
        assert get_reward("collector_50") == 250
        assert get_reward("set_master") == 1000

    def test_get_reward_unknown(self):
        assert get_reward("nonexistent") == 0

    def test_reference_id_for(self):
        assert reference_id_for("first_card") == "achievement:first_card"

    def test_legendary_boundary(self):
        assert REWARD_TIERS["legendary"] == 1000

    def test_all_achievements_total(self):
        total = sum(get_reward(k) for k in ACHIEVEMENT_TIERS)
        assert total == 3400


class TestCreditRewardInSession:
    def test_first_card_credits_fifty(self, repo, user_id):
        with Session(repo.engine) as session:
            amount = credit_reward_in_session(session, user_id, "first_card")
            session.commit()

        assert amount == 50

        with Session(repo.engine) as session:
            bal = session.query(CreditBalanceRow).filter_by(user_id=user_id).one()
            assert bal.balance == 50

            tx = session.query(CreditTransactionRow).filter_by(user_id=user_id).one()
            assert tx.reason == ACHIEVEMENT_REWARD_REASON
            assert tx.reference_id == "achievement:first_card"
            assert tx.amount == 50

    def test_credits_once_second_call_returns_zero(self, repo, user_id):
        with Session(repo.engine) as session:
            credit_reward_in_session(session, user_id, "first_card")
            session.commit()

        with Session(repo.engine) as session:
            amount = credit_reward_in_session(session, user_id, "first_card")
            session.commit()

        assert amount == 0

        with Session(repo.engine) as session:
            bal = session.query(CreditBalanceRow).filter_by(user_id=user_id).one()
            assert bal.balance == 50

            rows = session.query(CreditTransactionRow).filter_by(user_id=user_id).all()
            assert len(rows) == 1

    def test_existing_balance_is_added_to(self, repo, user_id):
        with Session(repo.engine) as session:
            session.add(CreditBalanceRow(user_id=user_id, balance=7))
            session.commit()

        with Session(repo.engine) as session:
            amount = credit_reward_in_session(session, user_id, "collector_50")
            session.commit()

        assert amount == 250

        with Session(repo.engine) as session:
            bal = session.query(CreditBalanceRow).filter_by(user_id=user_id).one()
            assert bal.balance == 257

    def test_unknown_key_credits_nothing(self, repo, user_id):
        with Session(repo.engine) as session:
            amount = credit_reward_in_session(session, user_id, "nonexistent")
            session.commit()

        assert amount == 0

        with Session(repo.engine) as session:
            assert session.query(CreditBalanceRow).filter_by(user_id=user_id).first() is None
            assert session.query(CreditTransactionRow).filter_by(user_id=user_id).first() is None

    def test_creates_balance_row_when_missing(self, repo, user_id):
        with Session(repo.engine) as session:
            assert session.query(CreditBalanceRow).filter_by(user_id=user_id).first() is None

        with Session(repo.engine) as session:
            credit_reward_in_session(session, user_id, "first_card")
            session.commit()

        with Session(repo.engine) as session:
            assert session.query(CreditBalanceRow).filter_by(user_id=user_id).first() is not None

    def test_pre_existing_ledger_row_blocks_credit(self, repo, user_id):
        with Session(repo.engine) as session:
            session.add(
                CreditTransactionRow(
                    user_id=user_id,
                    amount=50,
                    reason=ACHIEVEMENT_REWARD_REASON,
                    reference_id="achievement:first_card",
                )
            )
            session.commit()

        with Session(repo.engine) as session:
            amount = credit_reward_in_session(session, user_id, "first_card")
            session.commit()

        assert amount == 0

    def test_other_reasons_same_reference_dont_block(self, repo, user_id):
        with Session(repo.engine) as session:
            session.add(
                CreditTransactionRow(
                    user_id=user_id,
                    amount=5,
                    reason="bonus_claim",
                    reference_id="achievement:first_card",
                )
            )
            session.commit()

        with Session(repo.engine) as session:
            amount = credit_reward_in_session(session, user_id, "first_card")
            session.commit()

        assert amount == 50


class TestCreditedKeys:
    def test_returns_credited_keys(self, repo, user_id):
        with Session(repo.engine) as session:
            credit_reward_in_session(session, user_id, "first_card")
            credit_reward_in_session(session, user_id, "collector_50")
            session.commit()

        with Session(repo.engine) as session:
            keys = credited_keys(session, user_id)

        assert keys == {"first_card", "collector_50"}

    def test_empty_when_none_credited(self, repo, user_id):
        with Session(repo.engine) as session:
            keys = credited_keys(session, user_id)
        assert keys == set()


class TestBackfillUserRewardsInSession:
    def test_backfills_every_unlocked_achievement_once(self, repo, user_id):
        with Session(repo.engine) as session:
            for key in ACHIEVEMENT_TIERS:
                session.add(AchievementRow(user_id=user_id, achievement_key=key))
            session.commit()

        with Session(repo.engine) as session:
            total = backfill_user_rewards_in_session(session, user_id)
            session.commit()

        assert total == 3400

        with Session(repo.engine) as session:
            bal = session.query(CreditBalanceRow).filter_by(user_id=user_id).one()
            assert bal.balance == 3400

            rows = session.query(CreditTransactionRow).filter_by(user_id=user_id).all()
            assert len(rows) == len(ACHIEVEMENT_TIERS)

    def test_rerun_credits_nothing(self, repo, user_id):
        with Session(repo.engine) as session:
            session.add(AchievementRow(user_id=user_id, achievement_key="first_card"))
            session.commit()

        with Session(repo.engine) as session:
            backfill_user_rewards_in_session(session, user_id)
            session.commit()

        with Session(repo.engine) as session:
            total = backfill_user_rewards_in_session(session, user_id)
            session.commit()

        assert total == 0


class TestBackfillAllRewards:
    def test_backfills_all_users(self, repo, _two_users):
        u1, u2 = _two_users
        with Session(repo.engine) as session:
            session.add(AchievementRow(user_id=u1, achievement_key="first_card"))
            session.add(AchievementRow(user_id=u2, achievement_key="collector_50"))
            session.commit()

        result = backfill_all_rewards(repo)

        assert result["users"] == 2
        assert result["credited_users"] == 2
        assert result["credited_rows"] == 2
        assert result["total_tokens"] == 300
        assert result["errors"] == 0

    def test_rerun_returns_zeros(self, repo, _two_users):
        u1, u2 = _two_users
        with Session(repo.engine) as session:
            session.add(AchievementRow(user_id=u1, achievement_key="first_card"))
            session.add(AchievementRow(user_id=u2, achievement_key="collector_50"))
            session.commit()

        backfill_all_rewards(repo)
        result = backfill_all_rewards(repo)

        assert result["credited_users"] == 0
        assert result["credited_rows"] == 0
        assert result["total_tokens"] == 0
        assert result["errors"] == 0

    def test_only_credits_already_credited_user_skipped(self, repo, _two_users):
        u1, u2 = _two_users
        with Session(repo.engine) as session:
            session.add(AchievementRow(user_id=u1, achievement_key="first_card"))
            session.add(AchievementRow(user_id=u2, achievement_key="collector_50"))
            session.commit()

        with Session(repo.engine) as session:
            credit_reward_in_session(session, u1, "first_card")
            session.commit()

        result = backfill_all_rewards(repo)

        assert result["credited_users"] == 1
        assert result["credited_rows"] == 1
        assert result["total_tokens"] == 250

    def test_user_id_filter_only_touches_that_user(self, repo, _two_users):
        u1, u2 = _two_users
        with Session(repo.engine) as session:
            session.add(AchievementRow(user_id=u1, achievement_key="first_card"))
            session.add(AchievementRow(user_id=u2, achievement_key="collector_50"))
            session.commit()

        result = backfill_all_rewards(repo, user_id=u1)

        assert result["users"] == 1
        assert result["credited_users"] == 1
        assert result["total_tokens"] == 50

        with Session(repo.engine) as session:
            bal_u2 = session.query(CreditBalanceRow).filter_by(user_id=u2).first()
            assert bal_u2 is None

    def test_dry_run_does_not_write(self, repo, user_id):
        with Session(repo.engine) as session:
            session.add(AchievementRow(user_id=user_id, achievement_key="first_card"))
            session.commit()

        result = backfill_all_rewards(repo, dry_run=True)

        assert result["credited_rows"] == 1
        assert result["total_tokens"] == 50

        with Session(repo.engine) as session:
            assert session.query(CreditBalanceRow).filter_by(user_id=user_id).first() is None
            assert session.query(CreditTransactionRow).filter_by(user_id=user_id).first() is None

    def test_per_user_error_counted_others_processed(self, repo, _two_users, monkeypatch):
        u1, u2 = _two_users
        with Session(repo.engine) as session:
            session.add(AchievementRow(user_id=u1, achievement_key="first_card"))
            session.add(AchievementRow(user_id=u2, achievement_key="collector_50"))
            session.commit()

        import src.services.achievement_rewards as rewards_module

        original = rewards_module.credit_reward_in_session

        def _boom(session, uid, key):
            if uid == u1:
                raise RuntimeError("boom")
            return original(session, uid, key)

        monkeypatch.setattr(rewards_module, "credit_reward_in_session", _boom)

        result = backfill_all_rewards(repo)

        assert result["errors"] == 1
        assert result["credited_users"] == 1
        assert result["credited_rows"] == 1
        assert result["total_tokens"] == 250
