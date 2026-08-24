"""Tests for F41 banlist CLI command."""

from unittest.mock import patch

from click.testing import CliRunner

from src.cli.main import cli
from src.domain.models import BanlistSyncSummary


class TestBanlistSyncCommand:
    def test_command_exists(self):
        runner = CliRunner()
        result = runner.invoke(cli, ["banlist-sync", "--help"])
        assert result.exit_code == 0
        assert "Sync ban list" in result.output

    def test_has_bulk_option(self):
        runner = CliRunner()
        result = runner.invoke(cli, ["banlist-sync", "--help"])
        assert "--bulk" in result.output
        assert "--no-bulk" in result.output

    def test_has_limit_option(self):
        runner = CliRunner()
        result = runner.invoke(cli, ["banlist-sync", "--help"])
        assert "--limit" in result.output

    @patch("src.cli.main.asyncio.run")
    def test_calls_sync_with_bulk(self, mock_run):
        from datetime import datetime

        summary = BanlistSyncSummary(
            cards_processed=10,
            legalities_upserted=50,
            changes_detected=2,
            errors=0,
            started_at=datetime(2026, 8, 21, 10, 0, 0),
            finished_at=datetime(2026, 8, 21, 10, 1, 0),
        )
        mock_run.return_value = summary

        runner = CliRunner()
        result = runner.invoke(cli, ["banlist-sync", "--db", "sqlite:///:memory:"])
        assert result.exit_code == 0
        assert "Cards processed:" in result.output
        assert "10" in result.output
        assert "Changes detected:" in result.output
        assert "2" in result.output
