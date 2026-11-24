"""Tests for F213-T01: Reality Fracture catalog seed CLI commands.

Verifies that the CLI commands referenced by ``bats/catalog-seed-fra.bat``
are registered and accept the expected parameters.
"""

from __future__ import annotations

from click.testing import CliRunner

from src.cli.main import cli


class TestCatalogSeedCommand:
    """Verify ``catalog seed`` command registration and options."""

    def test_catalog_seed_registered(self):
        """The ``catalog seed`` subcommand exists under the catalog group."""
        runner = CliRunner()
        result = runner.invoke(cli, ["catalog", "seed", "--help"])
        assert result.exit_code == 0
        assert "seed" in result.output.lower()

    def test_catalog_seed_has_dry_run(self):
        """The ``catalog seed`` command accepts --dry-run."""
        runner = CliRunner()
        result = runner.invoke(cli, ["catalog", "seed", "--help"])
        assert result.exit_code == 0
        assert "--dry-run" in result.output

    def test_catalog_seed_has_batch_size(self):
        """The ``catalog seed`` command accepts --batch-size."""
        runner = CliRunner()
        result = runner.invoke(cli, ["catalog", "seed", "--help"])
        assert result.exit_code == 0
        assert "--batch-size" in result.output

    def test_catalog_seed_has_skip_download(self):
        """The ``catalog seed`` command accepts --skip-download."""
        runner = CliRunner()
        result = runner.invoke(cli, ["catalog", "seed", "--help"])
        assert result.exit_code == 0
        assert "--skip-download" in result.output


class TestMypSweepCommand:
    """Verify ``myp-sweep`` command registration and --set parameter.

    The FRA bat script uses ``myp-sweep --set fra`` for price scanning
    (Liga provider was removed in F210).
    """

    def test_myp_sweep_registered(self):
        """The ``myp-sweep`` command is registered on the CLI."""
        runner = CliRunner()
        result = runner.invoke(cli, ["myp-sweep", "--help"])
        assert result.exit_code == 0
        assert "myp" in result.output.lower()

    def test_myp_sweep_has_set_filter(self):
        """The ``myp-sweep`` command accepts --set for filtering by set code."""
        runner = CliRunner()
        result = runner.invoke(cli, ["myp-sweep", "--help"])
        assert result.exit_code == 0
        assert "--set" in result.output

    def test_myp_sweep_has_dry_run(self):
        """The ``myp-sweep`` command accepts --dry-run."""
        runner = CliRunner()
        result = runner.invoke(cli, ["myp-sweep", "--help"])
        assert result.exit_code == 0
        assert "--dry-run" in result.output

    def test_myp_sweep_has_batch_size(self):
        """The ``myp-sweep`` command accepts --batch-size."""
        runner = CliRunner()
        result = runner.invoke(cli, ["myp-sweep", "--help"])
        assert result.exit_code == 0
        assert "--batch-size" in result.output

    def test_myp_sweep_has_batch_pause(self):
        """The ``myp-sweep`` command accepts --batch-pause."""
        runner = CliRunner()
        result = runner.invoke(cli, ["myp-sweep", "--help"])
        assert result.exit_code == 0
        assert "--batch-pause" in result.output

    def test_myp_sweep_has_delay(self):
        """The ``myp-sweep`` command accepts --delay."""
        runner = CliRunner()
        result = runner.invoke(cli, ["myp-sweep", "--help"])
        assert result.exit_code == 0
        assert "--delay" in result.output


class TestCatalogGroupCommands:
    """Verify the catalog command group lists expected subcommands."""

    def test_catalog_group_help(self):
        """The ``catalog`` group shows help with available subcommands."""
        runner = CliRunner()
        result = runner.invoke(cli, ["catalog", "--help"])
        assert result.exit_code == 0
        assert "seed" in result.output
        assert "stats" in result.output

    def test_catalog_stats_registered(self):
        """The ``catalog stats`` subcommand exists."""
        runner = CliRunner()
        result = runner.invoke(cli, ["catalog", "stats", "--help"])
        assert result.exit_code == 0
