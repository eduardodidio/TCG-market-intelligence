"""Tests for CLI daily-snapshot and backfill-snapshots commands (F168-T02/T03, F176-T11)."""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path
from unittest.mock import MagicMock, patch

from click.testing import CliRunner
from sqlalchemy.orm import Session

from src.cli.main import cli
from src.database.models import PriceObservationRow
from src.database.repository import Repository


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
        mock_bf.assert_called_once_with(mock_repo, days=1, dry_run=False)
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
        mock_bf.assert_called_once_with(mock_repo, days=10, dry_run=False)
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

    def test_help_shows_dry_run(self):
        """backfill-snapshots --help shows the --dry-run flag."""
        runner = CliRunner()
        result = runner.invoke(cli, ["backfill-snapshots", "--help"])

        assert result.exit_code == 0
        assert "--dry-run" in result.output

    def test_dry_run_does_not_write(self, tmp_path):
        """--dry-run reports the count but writes nothing to the database."""
        db_url = f"sqlite:///{tmp_path}/t.db"
        runner = CliRunner()

        repo = Repository(db_url=db_url)
        today = date.today()
        with Session(repo.engine) as session:
            session.add(
                PriceObservationRow(
                    source="liga",
                    external_id="liga_1",
                    observed_at=today - timedelta(days=3),
                    median_price=Decimal("10.00"),
                )
            )
            session.commit()

        result = runner.invoke(
            cli, ["backfill-snapshots", "--db", db_url, "--days", "5", "--dry-run"]
        )

        assert result.exit_code == 0
        assert "Backfill dry-run: 3 observations would be created." in result.output

        with Session(repo.engine) as session:
            count = session.query(PriceObservationRow).count()
        assert count == 1  # only the original real observation, nothing backfilled

    def test_happy_path_real_backfill(self, tmp_path):
        """Real DB with 1 observation from D-3 -> creates 3 (D-2..D)."""
        db_url = f"sqlite:///{tmp_path}/t.db"
        runner = CliRunner()

        repo = Repository(db_url=db_url)
        today = date.today()
        with Session(repo.engine) as session:
            session.add(
                PriceObservationRow(
                    source="liga",
                    external_id="liga_1",
                    observed_at=today - timedelta(days=3),
                    median_price=Decimal("10.00"),
                )
            )
            session.commit()

        result = runner.invoke(cli, ["backfill-snapshots", "--db", db_url, "--days", "5"])

        assert result.exit_code == 0
        assert "Backfill complete: 3 observations created." in result.output

        with Session(repo.engine) as session:
            count = session.query(PriceObservationRow).count()
        assert count == 4  # original + 3 backfilled

    def test_days_zero_returns_friendly_error(self, tmp_path):
        """--days 0 exits with a non-zero code and a friendly message."""
        db_url = f"sqlite:///{tmp_path}/t.db"
        runner = CliRunner()

        result = runner.invoke(cli, ["backfill-snapshots", "--db", db_url, "--days", "0"])

        assert result.exit_code != 0
        assert "days" in result.output.lower()


class TestDailySnapshotBat:
    """Tests for bats/daily-snapshot.bat (F176-T11)."""

    def test_bat_file_follows_process_queue_pattern(self):
        bat_path = Path(__file__).resolve().parent.parent / "bats" / "daily-snapshot.bat"
        assert bat_path.exists(), "bats/daily-snapshot.bat must exist"

        content = bat_path.read_text()
        assert 'cd /d "%~dp0\\.."' in content
        assert "python -m src.cli.main daily-snapshot" in content
