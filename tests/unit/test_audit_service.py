"""Tests for AuditService (F100-T02)."""

from __future__ import annotations

import json
from datetime import datetime, timedelta
from unittest.mock import MagicMock

import pytest

from src.database.repository import Repository
from src.domain.models import User
from src.services.audit import AuditService


def _make_admin(user_id: int = 1) -> User:
    return User(
        id=user_id,
        email="admin@example.com",
        display_name="Admin",
        auth_provider="email",
        is_active=True,
        is_admin=True,
    )


@pytest.fixture()
def repo(tmp_path):
    db_path = tmp_path / "test_audit_svc.db"
    return Repository(db_url=f"sqlite:///{db_path}")


@pytest.fixture()
def audit(repo):
    return AuditService(repo)


@pytest.fixture()
def admin():
    return _make_admin()


class TestLogAudit:
    def test_inserts_and_lists(self, repo):
        """log_audit inserts a row, list_audit_logs returns it."""
        row_id = repo.log_audit(
            actor_id=1,
            actor_email="admin@test.com",
            action="user_create",
            target_type="user",
            target_id="42",
            details={"email": "new@test.com"},
            ip_address="10.0.0.1",
        )
        assert row_id > 0

        logs, total = repo.list_audit_logs()
        assert total == 1
        assert logs[0]["action"] == "user_create"
        assert logs[0]["actor_email"] == "admin@test.com"
        assert logs[0]["target_id"] == "42"
        assert logs[0]["ip_address"] == "10.0.0.1"
        # details_json should be a valid JSON string
        details = json.loads(logs[0]["details_json"])
        assert details["email"] == "new@test.com"

    def test_filter_by_action(self, repo):
        """list_audit_logs filters by action type."""
        repo.log_audit(1, "a@test.com", "user_create")
        repo.log_audit(1, "a@test.com", "credit_adjust")
        repo.log_audit(1, "a@test.com", "user_create")

        logs, total = repo.list_audit_logs(action="user_create")
        assert total == 2
        assert all(entry["action"] == "user_create" for entry in logs)

    def test_filter_by_actor_id(self, repo):
        """list_audit_logs filters by actor_id."""
        repo.log_audit(1, "a@test.com", "user_create")
        repo.log_audit(2, "b@test.com", "user_create")

        logs, total = repo.list_audit_logs(actor_id=2)
        assert total == 1
        assert logs[0]["actor_email"] == "b@test.com"

    def test_filter_by_date_range(self, repo):
        """list_audit_logs filters by date range."""
        # Insert entries (timestamps will all be "now" but we can test the filter accepts them)
        repo.log_audit(1, "a@test.com", "user_create")

        now = datetime.now()
        logs, total = repo.list_audit_logs(
            date_from=now - timedelta(minutes=5),
            date_to=now + timedelta(minutes=5),
        )
        assert total == 1

        # Date range that excludes the entry
        logs, total = repo.list_audit_logs(
            date_from=now + timedelta(hours=1),
        )
        assert total == 0

    def test_pagination(self, repo):
        """list_audit_logs respects limit and offset."""
        for i in range(5):
            repo.log_audit(1, "a@test.com", f"action_{i}")

        logs, total = repo.list_audit_logs(limit=2, offset=0)
        assert total == 5
        assert len(logs) == 2

        logs2, _ = repo.list_audit_logs(limit=2, offset=2)
        assert len(logs2) == 2
        # Should be different entries
        assert logs[0]["id"] != logs2[0]["id"]

    def test_ordered_by_timestamp_desc(self, repo):
        """list_audit_logs returns newest first."""
        repo.log_audit(1, "a@test.com", "first")
        repo.log_audit(1, "a@test.com", "second")

        logs, _ = repo.list_audit_logs()
        assert logs[0]["action"] == "second"
        assert logs[1]["action"] == "first"


class TestAuditService:
    def test_log_calls_repo(self, audit, admin, repo):
        """AuditService.log() inserts via repo."""
        audit.log(
            actor=admin,
            action="user_create",
            target_type="user",
            target_id=42,
            details={"email": "test@test.com"},
            ip_address="127.0.0.1",
        )
        logs, total = repo.list_audit_logs()
        assert total == 1
        assert logs[0]["action"] == "user_create"
        assert logs[0]["target_id"] == "42"  # converted to string

    def test_log_swallows_exceptions(self):
        """AuditService.log() never raises, even on repo failure."""
        mock_repo = MagicMock()
        mock_repo.log_audit.side_effect = RuntimeError("DB error")
        svc = AuditService(mock_repo)
        admin = _make_admin()

        # Should not raise
        svc.log(actor=admin, action="test_action")

    def test_log_serializes_details(self, audit, admin, repo):
        """details dict is serialized to JSON in the stored row."""
        audit.log(
            actor=admin,
            action="credit_adjust",
            details={"amount": 100, "reason": "test"},
        )
        logs, _ = repo.list_audit_logs()
        parsed = json.loads(logs[0]["details_json"])
        assert parsed["amount"] == 100
        assert parsed["reason"] == "test"

    def test_log_with_none_details(self, audit, admin, repo):
        """details=None results in null details_json."""
        audit.log(actor=admin, action="db_backup")
        logs, _ = repo.list_audit_logs()
        assert logs[0]["details_json"] is None
