"""Tests for CLI snapshot-prices command and _print_snapshot_summary."""

from __future__ import annotations

from datetime import datetime
from unittest.mock import patch

from click.testing import CliRunner

from src.cli.main import cli
from src.domain.models import CollectionError, SnapshotSummary

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_snapshot_summary(
    *,
    total_entries: int = 120,
    fetched: int = 100,
    stored: int = 95,
    skipped_existing: int = 15,
    skipped_zero_price: int = 5,
    errors: int = 0,
    with_errors: bool = False,
    many_errors: bool = False,
    no_finished: bool = False,
) -> SnapshotSummary:
    """Build a SnapshotSummary for testing."""
    started = datetime(2026, 8, 20, 14, 0, 0)
    finished = None if no_finished else datetime(2026, 8, 20, 14, 3, 25, 500000)

    error_details: list[CollectionError] = []
    if with_errors:
        errors = 3
        error_details = [
            CollectionError(
                source="jsonld_snapshot",
                external_id=str(1000 + i),
                url=f"https://mypcards.com/magic/produto/{1000 + i}/card-{i}",
                error_type="TimeoutError",
                error_message=f"Request timed out for card {i}",
            )
            for i in range(3)
        ]
    if many_errors:
        errors = 25
        error_details = [
            CollectionError(
                source="jsonld_snapshot",
                external_id=str(1000 + i),
                url=f"https://mypcards.com/magic/produto/{1000 + i}/card-{i}",
                error_type="TimeoutError",
                error_message=f"Request timed out for card {i}",
            )
            for i in range(25)
        ]

    summary = SnapshotSummary(
        total_entries=total_entries,
        fetched=fetched,
        stored=stored,
        skipped_existing=skipped_existing,
        skipped_zero_price=skipped_zero_price,
        errors=errors,
        error_details=error_details,
        started_at=started,
        finished_at=finished,
    )
    return summary


# ---------------------------------------------------------------------------
# snapshot-prices command -- argument passing
# ---------------------------------------------------------------------------


class TestSnapshotPricesCommand:
    def test_snapshot_prices_defaults(self):
        """snapshot-prices runs with default options and prints summary."""
        runner = CliRunner()
        summary = _make_snapshot_summary()

        with patch("src.cli.main.asyncio.run", return_value=summary) as mock_run:
            result = runner.invoke(cli, ["snapshot-prices"])

        assert result.exit_code == 0
        assert "SNAPSHOT PRICES SUMMARY" in result.output
        assert "Total entries:           120" in result.output
        assert "Fetched:                 100" in result.output
        assert "Stored:                  95" in result.output
        mock_run.assert_called_once()

    def test_snapshot_prices_with_all_options(self):
        """snapshot-prices passes all CLI options correctly."""
        runner = CliRunner()
        summary = _make_snapshot_summary()

        with patch("src.cli.main.asyncio.run", return_value=summary):
            result = runner.invoke(
                cli,
                [
                    "snapshot-prices",
                    "--db",
                    "sqlite:///custom.db",
                    "--limit",
                    "10",
                    "--dry-run",
                    "--delay",
                    "2.5",
                    "--concurrency",
                    "5",
                ],
            )

        assert result.exit_code == 0
        assert "DRY RUN" in result.output

    def test_dry_run_flag_passes_through(self):
        """--dry-run flag is correctly passed and shown in summary."""
        runner = CliRunner()
        summary = _make_snapshot_summary()

        with patch("src.cli.main.asyncio.run", return_value=summary):
            result = runner.invoke(cli, ["snapshot-prices", "--dry-run"])

        assert result.exit_code == 0
        assert "DRY RUN -- no data was written" in result.output

    def test_limit_option_passes_through(self):
        """--limit option is accepted and command runs successfully."""
        runner = CliRunner()
        summary = _make_snapshot_summary(total_entries=5, fetched=5, stored=5)

        with patch("src.cli.main.asyncio.run", return_value=summary):
            result = runner.invoke(cli, ["snapshot-prices", "--limit", "5"])

        assert result.exit_code == 0
        assert "Total entries:           5" in result.output

    def test_delay_and_concurrency_accepted(self):
        """--delay and --concurrency options are accepted."""
        runner = CliRunner()
        summary = _make_snapshot_summary()

        with patch("src.cli.main.asyncio.run", return_value=summary) as mock_run:
            result = runner.invoke(
                cli,
                ["snapshot-prices", "--delay", "0.5", "--concurrency", "6"],
            )

        assert result.exit_code == 0
        mock_run.assert_called_once()
        # Close the coroutine to avoid ResourceWarning
        coro = mock_run.call_args[0][0]
        coro.close()


# ---------------------------------------------------------------------------
# _print_snapshot_summary output
# ---------------------------------------------------------------------------


class TestPrintSnapshotSummary:
    def test_summary_shows_all_counts(self):
        """Summary output shows every SnapshotSummary field."""
        runner = CliRunner()
        summary = _make_snapshot_summary()

        with patch("src.cli.main.asyncio.run", return_value=summary):
            result = runner.invoke(cli, ["snapshot-prices"])

        assert result.exit_code == 0
        assert "Total entries:           120" in result.output
        assert "Fetched:                 100" in result.output
        assert "Stored:                  95" in result.output
        assert "Skipped (existing):      15" in result.output
        assert "Skipped (zero price):    5" in result.output
        assert "Errors:                  0" in result.output

    def test_summary_shows_elapsed_time(self):
        """Summary shows elapsed time in seconds."""
        runner = CliRunner()
        summary = _make_snapshot_summary()

        with patch("src.cli.main.asyncio.run", return_value=summary):
            result = runner.invoke(cli, ["snapshot-prices"])

        assert result.exit_code == 0
        assert "Elapsed:" in result.output
        # 3 min 25.5 sec = 205.5s
        assert "205.5s" in result.output

    def test_summary_no_finished_time(self):
        """Summary omits elapsed when finished_at is None."""
        runner = CliRunner()
        summary = _make_snapshot_summary(no_finished=True)

        with patch("src.cli.main.asyncio.run", return_value=summary):
            result = runner.invoke(cli, ["snapshot-prices"])

        assert result.exit_code == 0
        assert "Elapsed:" not in result.output

    def test_summary_dry_run_banner(self):
        """Dry run shows the DRY RUN banner before summary title."""
        runner = CliRunner()
        summary = _make_snapshot_summary()

        with patch("src.cli.main.asyncio.run", return_value=summary):
            result = runner.invoke(cli, ["snapshot-prices", "--dry-run"])

        assert result.exit_code == 0
        # DRY RUN banner appears before the summary title
        dry_run_pos = result.output.index("DRY RUN")
        summary_pos = result.output.index("SNAPSHOT PRICES SUMMARY")
        assert dry_run_pos < summary_pos

    def test_summary_no_dry_run_no_banner(self):
        """Normal run does not show DRY RUN banner."""
        runner = CliRunner()
        summary = _make_snapshot_summary()

        with patch("src.cli.main.asyncio.run", return_value=summary):
            result = runner.invoke(cli, ["snapshot-prices"])

        assert result.exit_code == 0
        assert "DRY RUN" not in result.output

    def test_summary_with_errors(self):
        """Summary prints error details when errors exist."""
        runner = CliRunner()
        summary = _make_snapshot_summary(with_errors=True)

        with patch("src.cli.main.asyncio.run", return_value=summary):
            result = runner.invoke(cli, ["snapshot-prices"])

        assert result.exit_code == 0
        assert "Error details (3):" in result.output
        assert "1000: TimeoutError" in result.output
        assert "Request timed out for card 0" in result.output

    def test_summary_with_many_errors_truncated(self):
        """Summary truncates error list at 20 and shows overflow count."""
        runner = CliRunner()
        summary = _make_snapshot_summary(many_errors=True)

        with patch("src.cli.main.asyncio.run", return_value=summary):
            result = runner.invoke(cli, ["snapshot-prices"])

        assert result.exit_code == 0
        assert "Error details (25):" in result.output
        assert "... and 5 more" in result.output

    def test_summary_no_errors_omits_error_section(self):
        """Summary does not show error section when no errors exist."""
        runner = CliRunner()
        summary = _make_snapshot_summary()

        with patch("src.cli.main.asyncio.run", return_value=summary):
            result = runner.invoke(cli, ["snapshot-prices"])

        assert result.exit_code == 0
        assert "Error details" not in result.output

    def test_summary_separator_lines(self):
        """Summary is framed with separator lines."""
        runner = CliRunner()
        summary = _make_snapshot_summary()

        with patch("src.cli.main.asyncio.run", return_value=summary):
            result = runner.invoke(cli, ["snapshot-prices"])

        assert result.exit_code == 0
        assert "=" * 60 in result.output


# ---------------------------------------------------------------------------
# CLI help
# ---------------------------------------------------------------------------


class TestSnapshotPricesHelp:
    def test_snapshot_prices_shows_in_help(self):
        """snapshot-prices appears in the top-level CLI help."""
        runner = CliRunner()
        result = runner.invoke(cli, ["--help"])

        assert result.exit_code == 0
        assert "snapshot-prices" in result.output

    def test_snapshot_prices_help_shows_all_options(self):
        """snapshot-prices --help shows all expected options."""
        runner = CliRunner()
        result = runner.invoke(cli, ["snapshot-prices", "--help"])

        assert result.exit_code == 0
        assert "--db" in result.output
        assert "--limit" in result.output
        assert "--dry-run" in result.output
        assert "--delay" in result.output
        assert "--concurrency" in result.output
        assert "Daily price snapshot from JSON-LD on product pages" in result.output
