"""Tests for the seed-users CLI command."""

from __future__ import annotations

from click.testing import CliRunner

from src.auth.passwords import verify_password
from src.cli.main import cli
from src.database.repository import Repository


class TestSeedUsers:
    def test_creates_both_users(self, tmp_path):
        db_path = tmp_path / "test_seed.db"
        db_url = f"sqlite:///{db_path}"

        runner = CliRunner()
        result = runner.invoke(cli, ["seed-users", "--db", db_url])
        assert result.exit_code == 0
        assert "Created: eduardo.didio" in result.output
        assert "Created: anderson.serafim" in result.output
        assert "Seed users done." in result.output

        # Verify users exist and passwords work
        repo = Repository(db_url=db_url)
        user1 = repo.get_user_by_email("eduardo.didio")
        assert user1 is not None
        assert user1.display_name == "Eduardo Didio"

        user2 = repo.get_user_by_email("anderson.serafim")
        assert user2 is not None
        assert user2.display_name == "Anderson Serafim"

        # Verify passwords
        assert verify_password("mudar@123", user1.password_hash)
        assert verify_password("mudar@123", user2.password_hash)

    def test_idempotent_second_run(self, tmp_path):
        db_path = tmp_path / "test_seed2.db"
        db_url = f"sqlite:///{db_path}"

        runner = CliRunner()
        # First run
        result1 = runner.invoke(cli, ["seed-users", "--db", db_url])
        assert result1.exit_code == 0
        assert "Created: eduardo.didio" in result1.output

        # Second run
        result2 = runner.invoke(cli, ["seed-users", "--db", db_url])
        assert result2.exit_code == 0
        assert "Skipped (exists): eduardo.didio" in result2.output
        assert "Skipped (exists): anderson.serafim" in result2.output
        assert "Created" not in result2.output
