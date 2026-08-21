"""Tests for the update-exchange-rate CLI command (T06)."""

from click.testing import CliRunner

from src.cli.main import cli


class TestUpdateExchangeRateCommand:
    def test_command_is_registered(self):
        """The update-exchange-rate command is in the CLI group."""
        runner = CliRunner()
        result = runner.invoke(cli, ["update-exchange-rate", "--help"])
        assert result.exit_code == 0
        assert "Fetch USD/BRL exchange rate" in result.output

    def test_help_shows_options(self):
        runner = CliRunner()
        result = runner.invoke(cli, ["update-exchange-rate", "--help"])
        assert "--db" in result.output
        assert "--date" in result.output
        assert "--backfill-days" in result.output
