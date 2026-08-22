"""Tests for schedule management CLI commands (F37-T06).

Uses Click's CliRunner for testing.
"""

from __future__ import annotations

from click.testing import CliRunner

from src.cli.main import cli
from src.database.repository import Repository


def _get_db_url(tmp_path):
    return f"sqlite:///{tmp_path / 'test.db'}"


class TestScheduleList:
    """schedule-list command tests."""

    def test_list_with_schedules(self, tmp_path) -> None:
        db_url = _get_db_url(tmp_path)
        repo = Repository(db_url=db_url)
        repo.create_scheduled_scan(
            user_id="1",
            name="Daily Collection",
            cron_expression="0 6 * * *",
            scan_type="collection",
        )

        runner = CliRunner()
        result = runner.invoke(cli, ["schedule-list", "--db", db_url])
        assert result.exit_code == 0
        assert "Daily Collection" in result.output
        assert "0 6 * * *" in result.output

    def test_list_empty(self, tmp_path) -> None:
        db_url = _get_db_url(tmp_path)
        Repository(db_url=db_url)  # init DB

        runner = CliRunner()
        result = runner.invoke(cli, ["schedule-list", "--db", db_url])
        assert result.exit_code == 0
        assert "No schedules found" in result.output

    def test_list_with_status_filter(self, tmp_path) -> None:
        db_url = _get_db_url(tmp_path)
        repo = Repository(db_url=db_url)
        repo.create_scheduled_scan(
            user_id="1",
            name="Active One",
            cron_expression="0 6 * * *",
            scan_type="collection",
        )
        id2 = repo.create_scheduled_scan(
            user_id="1",
            name="Paused One",
            cron_expression="0 12 * * *",
            scan_type="collection",
        )
        repo.update_scheduled_scan(id2, status="paused")

        runner = CliRunner()
        result = runner.invoke(cli, ["schedule-list", "--db", db_url, "--status", "paused"])
        assert result.exit_code == 0
        assert "Paused One" in result.output
        assert "Active One" not in result.output


class TestScheduleAdd:
    """schedule-add command tests."""

    def test_add_happy_path(self, tmp_path) -> None:
        db_url = _get_db_url(tmp_path)
        Repository(db_url=db_url)

        runner = CliRunner()
        result = runner.invoke(
            cli,
            [
                "schedule-add",
                "--db",
                db_url,
                "--name",
                "Daily Scan",
                "--cron",
                "0 6 * * *",
            ],
        )
        assert result.exit_code == 0
        assert "Schedule created" in result.output
        assert "Daily Scan" in result.output

    def test_add_invalid_cron(self, tmp_path) -> None:
        db_url = _get_db_url(tmp_path)
        Repository(db_url=db_url)

        runner = CliRunner()
        result = runner.invoke(
            cli,
            [
                "schedule-add",
                "--db",
                db_url,
                "--name",
                "Bad",
                "--cron",
                "not a cron",
            ],
        )
        assert result.exit_code == 1
        assert "Error" in (result.output + (result.stderr or ""))

    def test_add_sub_hour_cron(self, tmp_path) -> None:
        db_url = _get_db_url(tmp_path)
        Repository(db_url=db_url)

        runner = CliRunner()
        result = runner.invoke(
            cli,
            [
                "schedule-add",
                "--db",
                db_url,
                "--name",
                "TooFast",
                "--cron",
                "*/5 * * * *",
            ],
        )
        assert result.exit_code == 1


class TestScheduleRemove:
    """schedule-remove command tests."""

    def test_remove_existing(self, tmp_path) -> None:
        db_url = _get_db_url(tmp_path)
        repo = Repository(db_url=db_url)
        schedule_id = repo.create_scheduled_scan(
            user_id="1",
            name="To Delete",
            cron_expression="0 6 * * *",
            scan_type="collection",
        )

        runner = CliRunner()
        result = runner.invoke(cli, ["schedule-remove", "--db", db_url, str(schedule_id)])
        assert result.exit_code == 0
        assert "deleted" in result.output

    def test_remove_nonexistent(self, tmp_path) -> None:
        db_url = _get_db_url(tmp_path)
        Repository(db_url=db_url)

        runner = CliRunner()
        result = runner.invoke(cli, ["schedule-remove", "--db", db_url, "99999"])
        assert result.exit_code == 1
        assert "not found" in (result.output + (result.stderr or ""))
