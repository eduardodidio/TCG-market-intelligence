"""Tests for the seed-users CLI command."""

from __future__ import annotations

from click.testing import CliRunner
from sqlalchemy.orm import Session

from src.auth.passwords import verify_password
from src.cli.main import cli
from src.database.models import UserCollectionRow
from src.database.repository import Repository


class TestSeedUsers:
    def test_creates_both_users(self, tmp_path):
        db_path = tmp_path / "test_seed.db"
        db_url = f"sqlite:///{db_path}"

        runner = CliRunner()
        result = runner.invoke(cli, ["seed-users", "--db", db_url])
        assert result.exit_code == 0
        assert "Created: eduardorutkoskididio@gmail.com" in result.output
        assert "Created: anderson.serafim" in result.output
        assert "Seed users done." in result.output

        # Verify users exist and passwords work
        repo = Repository(db_url=db_url)
        user1 = repo.get_user_by_email("eduardorutkoskididio@gmail.com")
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
        assert "Created: eduardorutkoskididio@gmail.com" in result1.output

        # Second run
        result2 = runner.invoke(cli, ["seed-users", "--db", db_url])
        assert result2.exit_code == 0
        assert "Skipped (exists): eduardorutkoskididio@gmail.com" in result2.output
        assert "Skipped (exists): anderson.serafim" in result2.output
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
