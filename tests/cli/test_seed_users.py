"""Tests for the seed-users CLI command."""

from __future__ import annotations

from click.testing import CliRunner
from sqlalchemy.orm import Session

from src.auth.passwords import verify_password
from src.cli.main import cli
from src.database.models import UserCollectionRow
from src.database.repository import Repository

ADMIN_EMAIL = "eduardorutkoskididio@gmail.com"
GUEST_EMAIL = "guest@tedhmarket.com.br"


class TestSeedUsers:
    def test_creates_seed_user_with_env_password(self, tmp_path, monkeypatch):
        db_path = tmp_path / "test_seed.db"
        db_url = f"sqlite:///{db_path}"

        monkeypatch.setenv("TCG_SEED_PASSWORD", "test-password-123")
        runner = CliRunner()
        result = runner.invoke(cli, ["seed-users", "--db", db_url])
        assert result.exit_code == 0
        assert "Created: eduardorutkoskididio@gmail.com" in result.output
        assert "Seed users done." in result.output

        # Verify user exists and password works
        repo = Repository(db_url=db_url)
        user1 = repo.get_user_by_email("eduardorutkoskididio@gmail.com")
        assert user1 is not None
        assert user1.display_name == "Eduardo Didio"

        # Verify password matches the env var
        assert verify_password("test-password-123", user1.password_hash)

    def test_uses_default_password_when_no_env(self, tmp_path, monkeypatch):
        db_path = tmp_path / "test_seed_default.db"
        db_url = f"sqlite:///{db_path}"

        monkeypatch.delenv("TCG_SEED_PASSWORD", raising=False)
        runner = CliRunner()
        result = runner.invoke(cli, ["seed-users", "--db", db_url])
        assert result.exit_code == 0

        # Verify default password mudar@123 works
        repo = Repository(db_url=db_url)
        user = repo.get_user_by_email("eduardorutkoskididio@gmail.com")
        assert user is not None
        assert verify_password("mudar@123", user.password_hash)

    def test_idempotent_second_run(self, tmp_path):
        db_path = tmp_path / "test_seed2.db"
        db_url = f"sqlite:///{db_path}"

        runner = CliRunner()
        # First run
        result1 = runner.invoke(cli, ["seed-users", "--db", db_url])
        assert result1.exit_code == 0
        assert "Created: eduardorutkoskididio@gmail.com" in result1.output

        # Second run
        result2 = runner.invoke(cli, ["seed-users", "--db", db_url])
        assert result2.exit_code == 0
        assert "Skipped (exists): eduardorutkoskididio@gmail.com" in result2.output
        assert "Created" not in result2.output

    def test_reassigns_orphaned_collection_entries(self, tmp_path):
        db_path = tmp_path / "test_seed_reassign.db"
        db_url = f"sqlite:///{db_path}"

        # Create repo and tables, insert orphaned collection entries
        repo = Repository(db_url=db_url)
        with Session(repo.engine) as session:
            session.add(
                UserCollectionRow(
                    user_id="old_user",
                    set_code="mh3",
                    collector_number="1",
                    name_en="Test Card",
                    quantity=1,
                )
            )
            session.add(
                UserCollectionRow(
                    user_id="another_old",
                    set_code="mh3",
                    collector_number="2",
                    name_en="Test Card 2",
                    quantity=2,
                )
            )
            session.commit()

        runner = CliRunner()
        result = runner.invoke(cli, ["seed-users", "--db", db_url])
        assert result.exit_code == 0
        assert "Reassigned 2 collection entries" in result.output

        # Verify entries now belong to the primary user
        primary = repo.get_user_by_email("eduardorutkoskididio@gmail.com")
        assert primary is not None
        primary_uid = str(primary.id)
        with Session(repo.engine) as session:
            entries = session.query(UserCollectionRow).all()
            for entry in entries:
                assert entry.user_id == primary_uid

    def test_no_reassignment_when_already_correct(self, tmp_path):
        db_path = tmp_path / "test_seed_no_reassign.db"
        db_url = f"sqlite:///{db_path}"

        runner = CliRunner()
        # First run creates users (no collection entries to reassign)
        result = runner.invoke(cli, ["seed-users", "--db", db_url])
        assert result.exit_code == 0
        assert "No collection entries needed reassignment" in result.output


class TestSeedGuestUser:
    """Tests for the guest user seeded via seed-users command."""

    def _run_seed(self, tmp_path, monkeypatch=None):
        db_path = tmp_path / "test_guest.db"
        db_url = f"sqlite:///{db_path}"
        if monkeypatch:
            monkeypatch.delenv("TCG_SEED_PASSWORD", raising=False)
        runner = CliRunner()
        result = runner.invoke(cli, ["seed-users", "--db", db_url])
        repo = Repository(db_url=db_url)
        return result, repo, db_url

    def test_guest_user_created_with_correct_fields(self, tmp_path, monkeypatch):
        result, repo, _ = self._run_seed(tmp_path, monkeypatch)
        assert result.exit_code == 0
        assert f"Created: {GUEST_EMAIL}" in result.output

        guest = repo.get_user_by_email(GUEST_EMAIL)
        assert guest is not None
        assert guest.display_name == "Guest"
        assert guest.role == "guest"
        assert guest.is_admin == 0

    def test_guest_password_is_hardcoded(self, tmp_path, monkeypatch):
        """Guest password should be 'mudar@12345', NOT the env var default."""
        monkeypatch.setenv("TCG_SEED_PASSWORD", "some-other-password")
        result, repo, _ = self._run_seed(tmp_path)
        assert result.exit_code == 0

        guest = repo.get_user_by_email(GUEST_EMAIL)
        assert guest is not None
        # Guest uses its own hardcoded password, not the env var
        assert verify_password("mudar@12345", guest.password_hash)
        assert not verify_password("some-other-password", guest.password_hash)

    def test_admin_password_uses_env_var(self, tmp_path, monkeypatch):
        """Admin should use the env var password, guest should not."""
        monkeypatch.setenv("TCG_SEED_PASSWORD", "admin-env-pass")
        result, repo, _ = self._run_seed(tmp_path)
        assert result.exit_code == 0

        admin = repo.get_user_by_email(ADMIN_EMAIL)
        assert admin is not None
        assert verify_password("admin-env-pass", admin.password_hash)

        guest = repo.get_user_by_email(GUEST_EMAIL)
        assert guest is not None
        assert verify_password("mudar@12345", guest.password_hash)

    def test_guest_gets_10000_credits(self, tmp_path, monkeypatch):
        result, repo, _ = self._run_seed(tmp_path, monkeypatch)
        assert result.exit_code == 0

        guest = repo.get_user_by_email(GUEST_EMAIL)
        assert guest is not None
        balance = repo.get_credit_balance(guest.id)
        assert balance is not None
        assert balance.balance == 10_000

    def test_admin_also_gets_10000_credits(self, tmp_path, monkeypatch):
        result, repo, _ = self._run_seed(tmp_path, monkeypatch)
        assert result.exit_code == 0

        admin = repo.get_user_by_email(ADMIN_EMAIL)
        assert admin is not None
        balance = repo.get_credit_balance(admin.id)
        assert balance is not None
        assert balance.balance == 10_000

    def test_idempotent_second_run_no_error(self, tmp_path, monkeypatch):
        result1, repo, db_url = self._run_seed(tmp_path, monkeypatch)
        assert result1.exit_code == 0
        assert f"Created: {GUEST_EMAIL}" in result1.output

        runner = CliRunner()
        result2 = runner.invoke(cli, ["seed-users", "--db", db_url])
        assert result2.exit_code == 0
        assert f"Skipped (exists): {GUEST_EMAIL}" in result2.output
        assert f"Created: {GUEST_EMAIL}" not in result2.output

    def test_idempotent_updates_role_if_changed(self, tmp_path, monkeypatch):
        """If guest role was manually changed, seed-users restores it."""
        result1, repo, db_url = self._run_seed(tmp_path, monkeypatch)
        assert result1.exit_code == 0

        # Manually change guest role to something wrong
        guest = repo.get_user_by_email(GUEST_EMAIL)
        repo.update_user(guest.id, role="admin", is_admin=1)

        # Re-run seed-users
        runner = CliRunner()
        result2 = runner.invoke(cli, ["seed-users", "--db", db_url])
        assert result2.exit_code == 0
        assert "Updated" in result2.output

        # Verify role restored
        guest_updated = repo.get_user_by_email(GUEST_EMAIL)
        assert guest_updated.role == "guest"
        assert guest_updated.is_admin == 0

    def test_collection_reassignment_targets_admin_not_guest(self, tmp_path, monkeypatch):
        """Collection entries should be reassigned to admin user, not guest."""
        db_path = tmp_path / "test_guest_reassign.db"
        db_url = f"sqlite:///{db_path}"
        if monkeypatch:
            monkeypatch.delenv("TCG_SEED_PASSWORD", raising=False)

        repo = Repository(db_url=db_url)
        with Session(repo.engine) as session:
            session.add(
                UserCollectionRow(
                    user_id="orphan_user",
                    set_code="mh3",
                    collector_number="99",
                    name_en="Orphan Card",
                    quantity=1,
                )
            )
            session.commit()

        runner = CliRunner()
        result = runner.invoke(cli, ["seed-users", "--db", db_url])
        assert result.exit_code == 0
        assert "Reassigned 1 collection entries" in result.output

        # Verify entries were reassigned to admin, not guest
        admin = repo.get_user_by_email(ADMIN_EMAIL)
        guest = repo.get_user_by_email(GUEST_EMAIL)
        assert admin is not None
        assert guest is not None
        admin_uid = str(admin.id)
        guest_uid = str(guest.id)

        with Session(repo.engine) as session:
            entries = session.query(UserCollectionRow).all()
            for entry in entries:
                assert entry.user_id == admin_uid
                assert entry.user_id != guest_uid

    def test_admin_has_correct_role_and_flag(self, tmp_path, monkeypatch):
        """Admin user should have role='admin' and is_admin=1."""
        result, repo, _ = self._run_seed(tmp_path, monkeypatch)
        assert result.exit_code == 0

        admin = repo.get_user_by_email(ADMIN_EMAIL)
        assert admin is not None
        assert admin.role == "admin"
        assert admin.is_admin == 1
