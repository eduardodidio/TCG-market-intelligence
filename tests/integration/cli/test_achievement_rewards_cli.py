"""Integration tests for the backfill-achievement-rewards CLI command (F179-T05)."""

from __future__ import annotations

from unittest.mock import patch

import pytest
from click.testing import CliRunner
from sqlalchemy.orm import Session

from src.cli.achievement_rewards import backfill_achievement_rewards_cmd
from src.database.models import AchievementRow, CreditBalanceRow, CreditTransactionRow, UserRow
from src.database.repository import Repository


@pytest.fixture()
def db_url(tmp_path):
    return f"sqlite:///{tmp_path / 'test_cli_achievements.db'}"


@pytest.fixture()
def repo(db_url):
    return Repository(db_url=db_url)


@pytest.fixture()
def runner():
    return CliRunner()


def _create_user(repo, email):
    repo.create_user(email=email, display_name=email)
    with Session(repo.engine) as session:
        user = session.query(UserRow).filter_by(email=email).first()
        return user.id


def _unlock(repo, user_id, key):
    with Session(repo.engine) as session:
        session.add(AchievementRow(user_id=user_id, achievement_key=key))
        session.commit()


def _balance(repo, user_id):
    with Session(repo.engine) as session:
        bal = (
            session.query(CreditBalanceRow)
            .filter_by(user_id=user_id)
            .first()
        )
        return bal.balance if bal else 0


def _tx_count(repo, user_id):
    with Session(repo.engine) as session:
        return (
            session.query(CreditTransactionRow)
            .filter_by(user_id=user_id, reason="achievement_reward")
            .count()
        )


class TestBackfillAchievementRewardsCLI:
    def test_happy_path_two_users(self, runner, repo, db_url):
        u1 = _create_user(repo, "u1@example.com")
        u2 = _create_user(repo, "u2@example.com")
        _unlock(repo, u1, "first_card")  # common = 50
        _unlock(repo, u2, "collector_50")  # rare = 250

        result = runner.invoke(
            backfill_achievement_rewards_cmd, ["--db", db_url]
        )

        assert result.exit_code == 0, result.output
        assert "2 users" in result.output
        assert "2 rewards" in result.output
        assert "300 Tesouros" in result.output
        assert "dry-run: no" in result.output
        assert _balance(repo, u1) == 50
        assert _balance(repo, u2) == 250

    def test_idempotent_second_run_zero(self, runner, repo, db_url):
        u1 = _create_user(repo, "u1@example.com")
        _unlock(repo, u1, "first_card")

        runner.invoke(backfill_achievement_rewards_cmd, ["--db", db_url])
        result = runner.invoke(backfill_achievement_rewards_cmd, ["--db", db_url])

        assert result.exit_code == 0, result.output
        assert "0 rewards" in result.output
        assert "0 Tesouros" in result.output
        assert _balance(repo, u1) == 50

    def test_dry_run_writes_nothing(self, runner, repo, db_url):
        u1 = _create_user(repo, "u1@example.com")
        _unlock(repo, u1, "first_card")

        result = runner.invoke(
            backfill_achievement_rewards_cmd, ["--db", db_url, "--dry-run"]
        )

        assert result.exit_code == 0, result.output
        assert "1 rewards" in result.output
        assert "50 Tesouros" in result.output
        assert "dry-run: yes" in result.output
        assert _balance(repo, u1) == 0
        assert _tx_count(repo, u1) == 0

    def test_user_id_restricts_scope(self, runner, repo, db_url):
        u1 = _create_user(repo, "u1@example.com")
        u2 = _create_user(repo, "u2@example.com")
        _unlock(repo, u1, "first_card")
        _unlock(repo, u2, "collector_50")

        result = runner.invoke(
            backfill_achievement_rewards_cmd, ["--db", db_url, "--user-id", str(u1)]
        )

        assert result.exit_code == 0, result.output
        assert "1 users" in result.output
        assert "1 rewards" in result.output
        assert "50 Tesouros" in result.output
        assert _balance(repo, u1) == 50
        assert _balance(repo, u2) == 0

    def test_user_id_without_achievements(self, runner, repo, db_url):
        u1 = _create_user(repo, "u1@example.com")

        result = runner.invoke(
            backfill_achievement_rewards_cmd, ["--db", db_url, "--user-id", str(u1)]
        )

        assert result.exit_code == 0, result.output
        assert "0 users" in result.output
        assert "0 rewards" in result.output

    def test_errors_exit_nonzero(self, runner, repo, db_url):
        with patch(
            "src.services.achievement_rewards.backfill_all_rewards",
            return_value={
                "users": 1,
                "credited_users": 0,
                "credited_rows": 0,
                "total_tokens": 0,
                "errors": 1,
            },
        ):
            result = runner.invoke(
                backfill_achievement_rewards_cmd, ["--db", db_url]
            )

        assert result.exit_code == 1, result.output
        assert "WARNING" in result.output

    def test_empty_db(self, runner, db_url):
        result = runner.invoke(backfill_achievement_rewards_cmd, ["--db", db_url])

        assert result.exit_code == 0, result.output
        assert "0 users" in result.output
