"""Verifies backfill-achievement-rewards is registered on the main CLI group (F179-T09)."""

from __future__ import annotations

from click.testing import CliRunner

from src.cli.main import cli


def test_backfill_achievement_rewards_registered_on_main_cli():
    runner = CliRunner()
    result = runner.invoke(cli, ["backfill-achievement-rewards", "--help"])

    assert result.exit_code == 0, result.output
    assert "backfill-achievement-rewards" in result.output or "Usage" in result.output


def test_main_cli_help_lists_command():
    runner = CliRunner()
    result = runner.invoke(cli, ["--help"])

    assert result.exit_code == 0, result.output
    assert "backfill-achievement-rewards" in result.output
