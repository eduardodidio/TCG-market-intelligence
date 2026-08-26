"""Tests for admin repository methods (F66-T01)."""

from __future__ import annotations

import pytest

from src.credits.service import CreditService
from src.database.repository import Repository


@pytest.fixture()
def repo(tmp_path):
    db_path = tmp_path / "test_repo_admin.db"
    db_url = f"sqlite:///{db_path}"
    return Repository(db_url=db_url)


class TestListUsersWithBalances:
    def test_returns_empty_for_no_users(self, repo):
        users, total = repo.list_users_with_balances()
        assert users == []
        assert total == 0

    def test_returns_users_with_zero_balance(self, repo):
        repo.create_user(email="a@example.com", display_name="A")
        users, total = repo.list_users_with_balances()
        assert total == 1
        assert len(users) == 1
        assert users[0]["email"] == "a@example.com"
        assert users[0]["credit_balance"] == 0

    def test_left_join_shows_credit_balance(self, repo):
        u1 = repo.create_user(email="a@example.com")
        repo.create_user(email="b@example.com")

        svc = CreditService(repo)
        svc.grant(u1.id, 50, "test")
        # u2 has no credit balance row

        users, total = repo.list_users_with_balances()
        assert total == 2

        by_email = {u["email"]: u for u in users}
        assert by_email["a@example.com"]["credit_balance"] == 50
        assert by_email["b@example.com"]["credit_balance"] == 0

    def test_pagination(self, repo):
        for i in range(10):
            repo.create_user(email=f"user{i}@example.com")

        users, total = repo.list_users_with_balances(limit=3, offset=0)
        assert total == 10
        assert len(users) == 3

        users2, _ = repo.list_users_with_balances(limit=3, offset=3)
        assert len(users2) == 3
        # No overlap
        ids1 = {u["id"] for u in users}
        ids2 = {u["id"] for u in users2}
        assert ids1.isdisjoint(ids2)

    def test_returns_correct_fields(self, repo):
        repo.create_user(email="test@example.com", display_name="Test")
        users, _ = repo.list_users_with_balances()
        u = users[0]
        assert "id" in u
        assert "email" in u
        assert "display_name" in u
        assert "is_admin" in u
        assert "is_active" in u
        assert "credit_balance" in u
        assert "created_at" in u

    def test_is_admin_bool_conversion(self, repo):
        u = repo.create_user(email="admin@example.com")
        repo.update_user(u.id, is_admin=1)

        users, _ = repo.list_users_with_balances()
        admin = next(usr for usr in users if usr["email"] == "admin@example.com")
        assert admin["is_admin"] is True


class TestGetAdminUserIds:
    def test_returns_empty_for_no_users(self, repo):
        result = repo.get_admin_user_ids()
        assert result == []

    def test_returns_empty_when_no_admins(self, repo):
        repo.create_user(email="user@example.com")
        result = repo.get_admin_user_ids()
        assert result == []

    def test_returns_admin_ids(self, repo):
        u1 = repo.create_user(email="admin@example.com")
        repo.create_user(email="user@example.com")
        repo.update_user(u1.id, is_admin=1)

        result = repo.get_admin_user_ids()
        assert result == [u1.id]

    def test_returns_multiple_admin_ids(self, repo):
        u1 = repo.create_user(email="admin1@example.com")
        u2 = repo.create_user(email="admin2@example.com")
        repo.create_user(email="user@example.com")
        repo.update_user(u1.id, is_admin=1)
        repo.update_user(u2.id, is_admin=1)

        result = repo.get_admin_user_ids()
        assert set(result) == {u1.id, u2.id}


class TestGetPlatformStats:
    def test_empty_database(self, repo):
        stats = repo.get_platform_stats()
        assert stats["total_users"] == 0
        assert stats["active_users"] == 0
        assert stats["admin_users"] == 0
        assert stats["total_credits_in_circulation"] == 0
        assert stats["total_credits_granted"] == 0
        assert stats["total_credits_spent"] == 0
        assert stats["total_collection_entries"] == 0
        assert stats["total_scans"] == 0

    def test_counts_users_correctly(self, repo):
        u1 = repo.create_user(email="a@example.com")
        repo.create_user(email="b@example.com")
        repo.update_user(u1.id, is_admin=1)

        stats = repo.get_platform_stats()
        assert stats["total_users"] == 2
        assert stats["active_users"] == 2
        assert stats["admin_users"] == 1

    def test_credit_aggregation(self, repo):
        u1 = repo.create_user(email="a@example.com")
        u2 = repo.create_user(email="b@example.com")

        svc = CreditService(repo)
        svc.grant(u1.id, 100, "seed")
        svc.grant(u2.id, 50, "seed")
        svc.deduct(u1.id, 20, "spend")

        stats = repo.get_platform_stats()
        assert stats["total_credits_in_circulation"] == 130  # 80 + 50
        assert stats["total_credits_granted"] == 150  # 100 + 50
        assert stats["total_credits_spent"] == 20

    def test_collection_and_scan_counts(self, repo):
        # These should be 0 if no entries exist
        stats = repo.get_platform_stats()
        assert stats["total_collection_entries"] == 0
        assert stats["total_scans"] == 0
