"""Tests for CLI collector commands (backfill, update, retry-failed) and _print_summary."""

from __future__ import annotations

from datetime import datetime
from unittest.mock import patch

from click.testing import CliRunner

from src.cli.main import cli
from src.domain.models import CollectionError, CollectionSummary

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_summary(
    *,
    dry_run: bool = False,
    with_errors: bool = False,
    many_errors: bool = False,
    no_finished: bool = False,
) -> CollectionSummary:
    """Build a CollectionSummary for testing _print_summary paths."""
    started = datetime(2026, 8, 18, 10, 0, 0)
    finished = None if no_finished else datetime(2026, 8, 18, 10, 1, 30)

    errors: list[CollectionError] = []
    if with_errors:
        errors = [
            CollectionError(
                source="myp",
                external_id=f"card_{i:03d}",
                url=f"https://mypcards.com/magic/{i}",
                error_type="TimeoutError",
                error_message=f"Request timed out for card {i}",
            )
            for i in range(3)
        ]
    if many_errors:
        errors = [
            CollectionError(
                source="myp",
                external_id=f"card_{i:03d}",
                url=f"https://mypcards.com/magic/{i}",
                error_type="TimeoutError",
                error_message=f"Request timed out for card {i}",
            )
            for i in range(25)
        ]

    return CollectionSummary(
        cards_discovered=100,
        cards_processed=95,
        cards_failed=len(errors),
        observations_saved=1800,
        errors=errors,
        started_at=started,
        finished_at=finished,
    )


# ---------------------------------------------------------------------------
# backfill command
# ---------------------------------------------------------------------------


class TestBackfillCommand:
    def test_backfill_defaults(self):
        """backfill runs with default options and prints summary."""
        runner = CliRunner()
        summary = _make_summary()

        with patch("src.cli.main.asyncio.run", return_value=summary) as mock_run:
            result = runner.invoke(cli, ["backfill"])

        assert result.exit_code == 0
        assert "Cards discovered:       100" in result.output
        assert "Cards processed:        95" in result.output
        assert "Observations saved:     1800" in result.output
        # asyncio.run was called once
        mock_run.assert_called_once()

    def test_backfill_with_options(self):
        """backfill passes all CLI options to run_backfill."""
        runner = CliRunner()
        summary = _make_summary()

        # Patch at the import point inside the function
        with patch("src.cli.main.asyncio.run", return_value=summary) as mock_run:
            result = runner.invoke(
                cli,
                [
                    "backfill",
                    "--db",
                    "sqlite:///custom.db",
                    "--set",
                    "dmr",
                    "--limit",
                    "10",
                    "--dry-run",
                    "--delay",
                    "2.5",
                    "--history-days",
                    "365",
                    "--concurrency",
                    "5",
                    "--no-resume",
                ],
            )

        assert result.exit_code == 0
        # Verify the coroutine was passed to asyncio.run
        mock_run.assert_called_once()
        # dry-run banner should appear
        assert "DRY RUN" in result.output

    def test_backfill_dry_run_banner(self):
        """dry-run shows the DRY RUN banner in summary."""
        runner = CliRunner()
        summary = _make_summary(dry_run=True)

        with patch("src.cli.main.asyncio.run", return_value=summary):
            result = runner.invoke(cli, ["backfill", "--dry-run"])

        assert result.exit_code == 0
        assert "DRY RUN" in result.output


# ---------------------------------------------------------------------------
# update command
# ---------------------------------------------------------------------------


class TestUpdateCommand:
    def test_update_defaults(self):
        """update runs with default options."""
        runner = CliRunner()
        summary = _make_summary()

        with patch("src.cli.main.asyncio.run", return_value=summary):
            result = runner.invoke(cli, ["update"])

        assert result.exit_code == 0
        assert "Cards discovered:       100" in result.output
        assert "Observations saved:     1800" in result.output

    def test_update_with_options(self):
        """update passes CLI options through."""
        runner = CliRunner()
        summary = _make_summary()

        with patch("src.cli.main.asyncio.run", return_value=summary):
            result = runner.invoke(
                cli,
                ["update", "--db", "sqlite:///other.db", "--delay", "3.0", "--history-days", "90"],
            )

        assert result.exit_code == 0
        assert "Cards processed:" in result.output


# ---------------------------------------------------------------------------
# retry-failed command
# ---------------------------------------------------------------------------


class TestRetryFailedCommand:
    def test_retry_failed_defaults(self):
        """retry-failed runs with default options."""
        runner = CliRunner()
        summary = _make_summary()

        with patch("src.cli.main.asyncio.run", return_value=summary):
            result = runner.invoke(cli, ["retry-failed"])

        assert result.exit_code == 0
        assert "Cards processed:" in result.output

    def test_retry_failed_with_options(self):
        """retry-failed passes CLI options through."""
        runner = CliRunner()
        summary = _make_summary()

        with patch("src.cli.main.asyncio.run", return_value=summary):
            result = runner.invoke(
                cli,
                [
                    "retry-failed",
                    "--db",
                    "sqlite:///other.db",
                    "--delay",
                    "5.0",
                    "--history-days",
                    "180",
                ],
            )

        assert result.exit_code == 0
        assert "Observations saved:" in result.output


# ---------------------------------------------------------------------------
# _print_summary edge cases
# ---------------------------------------------------------------------------


class TestPrintSummary:
    def test_summary_with_errors(self):
        """Summary prints failed card details when errors exist."""
        runner = CliRunner()
        summary = _make_summary(with_errors=True)

        with patch("src.cli.main.asyncio.run", return_value=summary):
            result = runner.invoke(cli, ["backfill"])

        assert result.exit_code == 0
        assert "Failed cards (3):" in result.output
        assert "card_000" in result.output
        assert "TimeoutError" in result.output

    def test_summary_with_many_errors_truncated(self):
        """Summary truncates error list at 20 and shows overflow count."""
        runner = CliRunner()
        summary = _make_summary(many_errors=True)

        with patch("src.cli.main.asyncio.run", return_value=summary):
            result = runner.invoke(cli, ["backfill"])

        assert result.exit_code == 0
        assert "Failed cards (25):" in result.output
        assert "... and 5 more" in result.output

    def test_summary_no_finished_time(self):
        """Summary omits elapsed time when finished_at is None."""
        runner = CliRunner()
        summary = _make_summary(no_finished=True)

        with patch("src.cli.main.asyncio.run", return_value=summary):
            result = runner.invoke(cli, ["backfill"])

        assert result.exit_code == 0
        assert "Elapsed:" not in result.output

    def test_summary_with_elapsed_time(self):
        """Summary shows elapsed time when finished_at is set."""
        runner = CliRunner()
        summary = _make_summary()

        with patch("src.cli.main.asyncio.run", return_value=summary):
            result = runner.invoke(cli, ["backfill"])

        assert result.exit_code == 0
        assert "Elapsed:" in result.output
        assert "90.0s" in result.output


# ---------------------------------------------------------------------------
# CLI group / help
# ---------------------------------------------------------------------------


class TestCLIGroup:
    def test_cli_help(self):
        """Top-level CLI shows help text."""
        runner = CliRunner()
        result = runner.invoke(cli, ["--help"])

        assert result.exit_code == 0
        assert "TCG Market Intelligence" in result.output

    def test_backfill_help(self):
        """backfill --help shows all options."""
        runner = CliRunner()
        result = runner.invoke(cli, ["backfill", "--help"])

        assert result.exit_code == 0
        assert "--concurrency" in result.output
        assert "--no-resume" in result.output
