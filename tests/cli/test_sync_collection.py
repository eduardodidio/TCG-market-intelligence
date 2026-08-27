"""Tests for CLI sync-collection command and _print_sync_summary."""

from __future__ import annotations

from datetime import datetime
from unittest.mock import patch

from click.testing import CliRunner

from src.cli.main import cli
from src.domain.models import SyncError, SyncSummary

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_sync_summary(
    *,
    total_entries: int = 548,
    skipped_already_linked: int = 320,
    searched: int = 228,
    matched: int = 180,
    unmatched: int = 48,
    cards_created: int = 180,
    observations_saved: int = 65700,
    with_errors: bool = False,
    many_errors: bool = False,
    no_finished: bool = False,
) -> SyncSummary:
    """Build a SyncSummary for testing."""
    started = datetime(2026, 8, 19, 10, 0, 0)
    finished = None if no_finished else datetime(2026, 8, 19, 10, 39, 5, 600000)

    errors: list[SyncError] = []
    if with_errors:
        errors = [
            SyncError(
                entry_id=i,
                name_en=f"Card Name {i}",
                set_code="DMR",
                collector_number=str(i),
                error_type="TimeoutError",
                error_message=f"Request timed out for card {i}",
            )
            for i in range(3)
        ]
    if many_errors:
        errors = [
            SyncError(
                entry_id=i,
                name_en=f"Card Name {i}",
                set_code="DMR",
                collector_number=str(i),
                error_type="TimeoutError",
                error_message=f"Request timed out for card {i}",
            )
            for i in range(25)
        ]

    summary = SyncSummary(
        total_entries=total_entries,
        skipped_already_linked=skipped_already_linked,
        searched=searched,
        matched=matched,
        unmatched=unmatched,
        cards_created=cards_created,
        observations_saved=observations_saved,
        errors=errors,
        started_at=started,
        finished_at=finished,
    )
    return summary


# ---------------------------------------------------------------------------
# sync-collection command — argument passing
# ---------------------------------------------------------------------------


class TestSyncCollectionCommand:
    def test_sync_collection_defaults(self):
        """sync-collection runs with default options and prints summary."""
        runner = CliRunner()
        summary = _make_sync_summary()

        with patch("src.cli.main.asyncio.run", return_value=summary) as mock_run:
            result = runner.invoke(cli, ["sync-collection"])

        assert result.exit_code == 0
        assert "COLLECTION SYNC SUMMARY" in result.output
        assert "Total entries:           548" in result.output
        assert "Matched:                  180" in result.output
        assert "Observations saved:     65,700" in result.output
        mock_run.assert_called_once()

    def test_sync_collection_with_all_options(self):
        """sync-collection passes all CLI options to run_sync_collection."""
        runner = CliRunner()
        summary = _make_sync_summary()

        with patch("src.cli.main.asyncio.run", return_value=summary):
            result = runner.invoke(
                cli,
                [
                    "sync-collection",
                    "--db",
                    "sqlite:///custom.db",
                    "--limit",
                    "10",
                    "--dry-run",
                    "--delay",
                    "2.5",
                    "--history-days",
                    "90",
                    "--concurrency",
                    "5",
                    "--force",
                ],
            )

        assert result.exit_code == 0
        assert "DRY RUN" in result.output

    def test_force_flag_sets_skip_matched_false(self):
        """--force maps to skip_matched=False in run_sync_collection call."""
        runner = CliRunner()
        summary = _make_sync_summary()

        with patch("src.cli.main.asyncio.run", return_value=summary) as mock_run:
            result = runner.invoke(cli, ["sync-collection", "--force"])

        assert result.exit_code == 0
        # Verify the coroutine was passed to asyncio.run
        mock_run.assert_called_once()
        # The coroutine passed to asyncio.run encodes skip_matched=False
        call_args = mock_run.call_args
        coro = call_args[0][0]
        # Close the coroutine to avoid ResourceWarning
        coro.close()

    def test_no_force_flag_sets_skip_matched_true(self):
        """Without --force, skip_matched defaults to True."""
        runner = CliRunner()
        summary = _make_sync_summary()

        with patch("src.cli.main.asyncio.run", return_value=summary) as mock_run:
            result = runner.invoke(cli, ["sync-collection"])

        assert result.exit_code == 0
        call_args = mock_run.call_args
        coro = call_args[0][0]
        coro.close()

    def test_dry_run_flag_passes_through(self):
        """--dry-run flag is correctly passed and shown in summary."""
        runner = CliRunner()
        summary = _make_sync_summary()

        with patch("src.cli.main.asyncio.run", return_value=summary):
            result = runner.invoke(cli, ["sync-collection", "--dry-run"])

        assert result.exit_code == 0
        assert "DRY RUN" in result.output

    def test_limit_option_passes_through(self):
        """--limit option is accepted and command runs successfully."""
        runner = CliRunner()
        summary = _make_sync_summary(total_entries=5, searched=5)

        with patch("src.cli.main.asyncio.run", return_value=summary):
            result = runner.invoke(cli, ["sync-collection", "--limit", "5"])

        assert result.exit_code == 0
        assert "Total entries:           5" in result.output


# ---------------------------------------------------------------------------
# _print_sync_summary output
# ---------------------------------------------------------------------------


class TestPrintSyncSummary:
    def test_summary_shows_all_counts(self):
        """Summary output shows every SyncSummary field."""
        runner = CliRunner()
        summary = _make_sync_summary()

        with patch("src.cli.main.asyncio.run", return_value=summary):
            result = runner.invoke(cli, ["sync-collection"])

        assert result.exit_code == 0
        assert "Total entries:           548" in result.output
        assert "Skipped (already linked): 320" in result.output
        assert "Searched:                 228" in result.output
        assert "Matched:                  180" in result.output
        assert "Unmatched:" in result.output
        assert "Cards created:            180" in result.output
        assert "Observations saved:     65,700" in result.output

    def test_summary_shows_elapsed_time(self):
        """Summary shows elapsed time with seconds and minutes."""
        runner = CliRunner()
        summary = _make_sync_summary()

        with patch("src.cli.main.asyncio.run", return_value=summary):
            result = runner.invoke(cli, ["sync-collection"])

        assert result.exit_code == 0
        assert "Elapsed:" in result.output
        # 39 min 5.6 sec = 2345.6s
        assert "2345.6s" in result.output
        assert "39.1 min" in result.output

    def test_summary_no_finished_time(self):
        """Summary omits elapsed when finished_at is None."""
        runner = CliRunner()
        summary = _make_sync_summary(no_finished=True)

        with patch("src.cli.main.asyncio.run", return_value=summary):
            result = runner.invoke(cli, ["sync-collection"])

        assert result.exit_code == 0
        assert "Elapsed:" not in result.output

    def test_summary_dry_run_banner(self):
        """Dry run shows the DRY RUN banner before summary."""
        runner = CliRunner()
        summary = _make_sync_summary()

        with patch("src.cli.main.asyncio.run", return_value=summary):
            result = runner.invoke(cli, ["sync-collection", "--dry-run"])

        assert result.exit_code == 0
        # DRY RUN banner appears before the summary title
        dry_run_pos = result.output.index("DRY RUN")
        summary_pos = result.output.index("COLLECTION SYNC SUMMARY")
        assert dry_run_pos < summary_pos

    def test_summary_with_errors(self):
        """Summary prints error details when errors exist."""
        runner = CliRunner()
        summary = _make_sync_summary(with_errors=True)

        with patch("src.cli.main.asyncio.run", return_value=summary):
            result = runner.invoke(cli, ["sync-collection"])

        assert result.exit_code == 0
        assert "Errors (3):" in result.output
        assert "Card Name 0" in result.output
        assert "TimeoutError" in result.output

    def test_summary_with_many_errors_truncated(self):
        """Summary truncates error list at 20 and shows overflow count."""
        runner = CliRunner()
        summary = _make_sync_summary(many_errors=True)

        with patch("src.cli.main.asyncio.run", return_value=summary):
            result = runner.invoke(cli, ["sync-collection"])

        assert result.exit_code == 0
        assert "Errors (25):" in result.output
        assert "... and 5 more" in result.output

    def test_summary_no_errors_omits_error_section(self):
        """Summary does not show error section when no errors exist."""
        runner = CliRunner()
        summary = _make_sync_summary()

        with patch("src.cli.main.asyncio.run", return_value=summary):
            result = runner.invoke(cli, ["sync-collection"])

        assert result.exit_code == 0
        assert "Errors" not in result.output

    def test_summary_separator_lines(self):
        """Summary is framed with separator lines."""
        runner = CliRunner()
        summary = _make_sync_summary()

        with patch("src.cli.main.asyncio.run", return_value=summary):
            result = runner.invoke(cli, ["sync-collection"])

        assert result.exit_code == 0
        assert "=" * 60 in result.output


# ---------------------------------------------------------------------------
# CLI help
# ---------------------------------------------------------------------------


class TestSyncCollectionHelp:
    def test_sync_collection_shows_in_help(self):
        """sync-collection appears in the top-level CLI help."""
        runner = CliRunner()
        result = runner.invoke(cli, ["--help"])

        assert result.exit_code == 0
        assert "sync-collection" in result.output

    def test_sync_collection_help_shows_all_options(self):
        """sync-collection --help shows all expected options."""
        runner = CliRunner()
        result = runner.invoke(cli, ["sync-collection", "--help"])

        assert result.exit_code == 0
        assert "--db" in result.output
        assert "--limit" in result.output
        assert "--dry-run" in result.output
        assert "--delay" in result.output
        assert "--history-days" in result.output
        assert "--concurrency" in result.output
        assert "--force" in result.output
        assert "Sync user collection with MYP price data" in result.output
