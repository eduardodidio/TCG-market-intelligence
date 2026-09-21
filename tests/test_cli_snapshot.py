"""Tests for CLI daily-snapshot and backfill-snapshots commands (F168-T02/T03)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from click.testing import CliRunner

from src.cli.main import cli


class TestDailySnapshotCommand:
    def test_happy_path_prints_count(self):
        """daily-snapshot calls run_daily_snapshot and prints the count."""
        runner = CliRunner()

        mock_repo = MagicMock()
        with (
            patch("src.collectors.price_snapshot.run_daily_snapshot", return_value=42) as mock_snap,
            patch("src.database.repository.Repository", return_value=mock_repo),
        ):
            result = runner.invoke(cli, ["daily-snapshot", "--db", "sqlite:///test.db"])

        assert result.exit_code == 0
        mock_snap.assert_called_once_with(mock_repo)
        assert "42 new observations recorded" in result.output

    def test_zero_observations(self):
        """daily-snapshot handles zero new observations gracefully."""
        runner = CliRunner()

        with (
            patch("src.collectors.price_snapshot.run_daily_snapshot", return_value=0),
            patch("src.database.repository.Repository"),
        ):
            result = runner.invoke(cli, ["daily-snapshot", "--db", "sqlite:///test.db"])

        assert result.exit_code == 0
        assert "0 new observations recorded" in result.output

    def test_db_option_uses_resolve_db(self):
        """--db option uses _resolve_db callback (auto-detect when None)."""
        runner = CliRunner()

        with (
            patch("src.collectors.price_snapshot.run_daily_snapshot", return_value=10),
            patch("src.database.repository.Repository") as mock_repo_cls,
            patch("src.config.get_db_url", return_value="sqlite:///auto.db"),
        ):
            result = runner.invoke(cli, ["daily-snapshot"])

        assert result.exit_code == 0
        # When --db is not provided, _resolve_db calls get_db_url()
        mock_repo_cls.assert_called_once_with(db_url="sqlite:///auto.db")

    def test_shows_in_help(self):
        """daily-snapshot appears in top-level CLI help."""
        runner = CliRunner()
        result = runner.invoke(cli, ["--help"])

        assert result.exit_code == 0
        assert "daily-snapshot" in result.output

    def test_command_help(self):
        """daily-snapshot --help shows description."""
        runner = CliRunner()
        result = runner.invoke(cli, ["daily-snapshot", "--help"])

        assert result.exit_code == 0
        assert "--db" in result.output
        assert "Record daily price snapshot" in result.output


class TestBackfillSnapshotsCommand:
    def test_happy_path_prints_count(self):
        """backfill-snapshots calls backfill_snapshots and prints the count."""
        runner = CliRunner()

        mock_repo = MagicMock()
        with (
            patch("src.collectors.price_snapshot.backfill_snapshots", return_value=15) as mock_bf,
            patch("src.database.repository.Repository", return_value=mock_repo),
        ):
            result = runner.invoke(cli, ["backfill-snapshots", "--db", "sqlite:///test.db"])

        assert result.exit_code == 0
        mock_bf.assert_called_once_with(mock_repo, days=1)
        assert "15 observations created" in result.output

    def test_zero_observations(self):
        """backfill-snapshots handles zero gracefully."""
        runner = CliRunner()

        with (
            patch("src.collectors.price_snapshot.backfill_snapshots", return_value=0),
            patch("src.database.repository.Repository"),
        ):
            result = runner.invoke(cli, ["backfill-snapshots", "--db", "sqlite:///test.db"])

        assert result.exit_code == 0
        assert "0 observations created" in result.output

    def test_days_option(self):
        """--days option is passed through to backfill_snapshots."""
        runner = CliRunner()

        mock_repo = MagicMock()
        with (
            patch("src.collectors.price_snapshot.backfill_snapshots", return_value=30) as mock_bf,
            patch("src.database.repository.Repository", return_value=mock_repo),
        ):
            result = runner.invoke(
                cli, ["backfill-snapshots", "--db", "sqlite:///test.db", "--days", "10"]
            )

        assert result.exit_code == 0
        mock_bf.assert_called_once_with(mock_repo, days=10)
        assert "30 observations created" in result.output

    def test_shows_in_help(self):
        """backfill-snapshots appears in top-level CLI help."""
        runner = CliRunner()
        result = runner.invoke(cli, ["--help"])

        assert result.exit_code == 0
        assert "backfill-snapshots" in result.output

    def test_command_help(self):
        """backfill-snapshots --help shows description and options."""
        runner = CliRunner()
        result = runner.invoke(cli, ["backfill-snapshots", "--help"])

        assert result.exit_code == 0
        assert "--db" in result.output
        assert "--days" in result.output
        assert "Backfill daily snapshots" in result.output
