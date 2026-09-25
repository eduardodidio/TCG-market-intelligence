"""End-to-end integration test for F179 achievement Treasure rewards.

Exercises the real router + services + CLI on a temp SQLite DB, covering
unlock -> credit -> ledger -> backfill -> CLI (AC2, AC3, AC4, AC9).
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from time import sleep

import pytest
from click.testing import CliRunner
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from src.api.deps import get_current_user, get_db
from src.api.routers.achievements import router as achievements_router
from src.api.routers.credits import router as credits_router
from src.cli.achievement_rewards import backfill_achievement_rewards_cmd
from src.credits.service import CreditService
from src.database.models import AchievementRow, CreditTransactionRow, UserCollectionRow, UserRow
from src.database.repository import Repository
from src.domain.models import User
from src.services.achievement_rewards import ACHIEVEMENT_TIERS, REWARD_TIERS, get_reward
from src.services.achievements import (
    ACHIEVEMENT_DEFINITIONS,
    check_achievements_with_rewards,
    grant_set_master,
)


def _make_user(user_id: int) -> User:
    return User(
        id=user_id,
        email=f"user{user_id}@example.com",
        display_name=f"User {user_id}",
        auth_provider="email",
        preferred_language="en",
        is_active=True,
        is_admin=False,
    )


def _create_repo_user(repo: Repository, email: str) -> int:
    repo.create_user(email=email, display_name=email)
    with Session(repo.engine) as session:
        row = session.query(UserRow).filter_by(email=email).first()
        return row.id


def _build_app(repo: Repository, user: User) -> FastAPI:
    app = FastAPI()
    app.include_router(achievements_router, prefix="/api/v1")
    app.include_router(credits_router, prefix="/api/v1")
    app.dependency_overrides[get_db] = lambda: repo
    app.dependency_overrides[get_current_user] = lambda: user
    return app


def _ledger_rows(repo: Repository, user_id: int) -> list[CreditTransactionRow]:
    with Session(repo.engine) as session:
        rows = (
            session.query(CreditTransactionRow)
            .filter_by(user_id=user_id, reason="achievement_reward")
            .all()
        )
        session.expunge_all()
        return rows


def _ledger_count_by_key(repo: Repository, user_id: int, key: str) -> int:
    ref = f"achievement:{key}"
    with Session(repo.engine) as session:
        return (
            session.query(CreditTransactionRow)
            .filter_by(user_id=user_id, reason="achievement_reward", reference_id=ref)
            .count()
        )


@pytest.fixture()
def db_url(tmp_path):
    return f"sqlite:///{tmp_path / 'f179.db'}"


@pytest.fixture()
def repo(db_url):
    return Repository(db_url=db_url)


class TestJourneyUnlockToLedger:
    def test_add_card_check_balance_history(self, repo):
        user_id = _create_repo_user(repo, "journey@example.com")
        user = _make_user(user_id)
        app = _build_app(repo, user)
        client = TestClient(app)

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

        resp = client.post("/api/v1/achievements/check")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert "first_card" in data["newly_unlocked"]

        first_card_reward = next(r for r in data["rewards"] if r["key"] == "first_card")
        assert first_card_reward["amount"] == 50

        balance_resp = client.get("/api/v1/credits/balance")
        assert balance_resp.json()["data"]["balance"] >= 50

        history_resp = client.get("/api/v1/credits/history")
        reasons = [t["reason"] for t in history_resp.json()["data"]["transactions"]]
        assert "achievement_reward" in reasons


class TestSequentialIdempotency:
    def test_five_sequential_checks_one_ledger_row_per_key(self, repo):
        user_id = _create_repo_user(repo, "seq@example.com")
        user = _make_user(user_id)
        app = _build_app(repo, user)
        client = TestClient(app)

        for _ in range(5):
            resp = client.post("/api/v1/achievements/check")
            assert resp.status_code == 200

        with Session(repo.engine) as session:
            rows = (
                session.query(AchievementRow.achievement_key)
                .filter_by(user_id=user_id)
                .all()
            )
        unlocked_keys = {r[0] for r in rows}
        assert unlocked_keys  # early_adopter at minimum

        for key in unlocked_keys:
            assert _ledger_count_by_key(repo, user_id, key) == 1


class TestConcurrency:
    def test_concurrent_check_calls_credit_exactly_once(self, repo):
        user_id = _create_repo_user(repo, "concurrent@example.com")

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

        def run_check():
            for attempt in range(10):
                try:
                    return check_achievements_with_rewards(user_id, repo)
                except OperationalError:
                    if attempt == 9:
                        raise
                    sleep(0.05)
            return None

        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = [executor.submit(run_check) for _ in range(4)]
            results = [f.result() for f in futures]

        assert all(r is not None for r in results)

        with Session(repo.engine) as session:
            rows = (
                session.query(AchievementRow.achievement_key)
                .filter_by(user_id=user_id)
                .all()
            )
        unlocked_keys = {r[0] for r in rows}
        assert "first_card" in unlocked_keys

        for key in unlocked_keys:
            assert _ledger_count_by_key(repo, user_id, key) == 1

        expected_balance = sum(get_reward(key) for key in unlocked_keys)
        svc = CreditService(repo)
        assert svc.get_balance(user_id).balance == expected_balance


class TestLegacyBackfillCLI:
    def test_legacy_rows_dry_run_then_cli_then_check_backfilled_zero(self, repo, db_url):
        user_id = _create_repo_user(repo, "legacy@example.com")

        with Session(repo.engine) as session:
            session.add(AchievementRow(user_id=user_id, achievement_key="first_card"))
            session.add(AchievementRow(user_id=user_id, achievement_key="collector_10"))
            session.commit()

        runner = CliRunner()

        dry_run_result = runner.invoke(
            backfill_achievement_rewards_cmd, ["--db", db_url, "--dry-run"]
        )
        assert dry_run_result.exit_code == 0, dry_run_result.output
        assert _ledger_rows(repo, user_id) == []

        cli_result = runner.invoke(backfill_achievement_rewards_cmd, ["--db", db_url])
        assert cli_result.exit_code == 0, cli_result.output
        assert len(_ledger_rows(repo, user_id)) == 2

        user = _make_user(user_id)
        app = _build_app(repo, user)
        client = TestClient(app)
        resp = client.post("/api/v1/achievements/check")
        data = resp.json()["data"]
        assert data["backfilled"] == 0


class TestLegacyLazyBackfill:
    def test_legacy_rows_no_cli_check_backfills(self, repo):
        user_id = _create_repo_user(repo, "lazy@example.com")

        with Session(repo.engine) as session:
            session.add(AchievementRow(user_id=user_id, achievement_key="first_card"))
            session.add(AchievementRow(user_id=user_id, achievement_key="collector_10"))
            session.commit()

        user = _make_user(user_id)
        app = _build_app(repo, user)
        client = TestClient(app)
        resp = client.post("/api/v1/achievements/check")
        data = resp.json()["data"]

        expected = get_reward("first_card") + get_reward("collector_10")
        assert data["backfilled"] == expected


class TestBoundaryAllAchievements:
    def test_all_achievements_total_3400(self, repo):
        user_id = _create_repo_user(repo, "allach@example.com")

        keys = [d["key"] for d in ACHIEVEMENT_DEFINITIONS if d["key"] != "set_master"]
        with Session(repo.engine) as session:
            for key in keys:
                session.add(AchievementRow(user_id=user_id, achievement_key=key))
            session.commit()

        granted = grant_set_master(user_id, repo)
        assert granted is True

        user = _make_user(user_id)
        app = _build_app(repo, user)
        client = TestClient(app)
        client.post("/api/v1/achievements/check")

        svc = CreditService(repo)
        total = sum(REWARD_TIERS[tier] for tier in ACHIEVEMENT_TIERS.values())
        assert total == 3400
        assert svc.get_balance(user_id).balance == 3400


class TestDeductionInterplay:
    def test_deduct_after_reward_ledger_matches_balance(self, repo):
        user_id = _create_repo_user(repo, "deduct@example.com")

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

        user = _make_user(user_id)
        app = _build_app(repo, user)
        client = TestClient(app)
        client.post("/api/v1/achievements/check")

        svc = CreditService(repo)
        balance_before = svc.get_balance(user_id).balance
        assert balance_before > 0

        svc.deduct(user_id, cost=10, reason="test_deduction")

        with Session(repo.engine) as session:
            transactions = (
                session.query(CreditTransactionRow).filter_by(user_id=user_id).all()
            )
            ledger_sum = sum(t.amount for t in transactions)

        assert svc.get_balance(user_id).balance == balance_before - 10
        assert ledger_sum == svc.get_balance(user_id).balance
