"""Tests for the CLI scan --provider flag (F57-T05).

Covers:
 1. --provider auto: lets run_scan create its own provider (passes None)
 2. --provider myp: creates MypCardsProvider and passes it
 3. --provider liga: falls back to MYP with note message
 4. Default (no flag): same as auto
 5. snapshot-prices --provider flag accepted
"""

from __future__ import annotations

from datetime import datetime
from unittest.mock import patch

from click.testing import CliRunner

from src.cli.main import cli
from src.domain.models import ScanRun


def _make_scan_run(**overrides) -> ScanRun:
    """Build a ScanRun for testing."""
    defaults = {
        "id": 1,
        "scan_type": "collection",
        "filters_json": "{}",
        "status": "completed",
        "cards_total": 5,
        "cards_processed": 5,
        "cards_failed": 0,
        "observations_saved": 5,
        "error_summary": None,
        "started_at": datetime(2026, 8, 24, 10, 0, 0),
        "finished_at": datetime(2026, 8, 24, 10, 1, 0),
    }
    defaults.update(overrides)
    return ScanRun(**defaults)


class TestScanProviderFlag:
    """Tests for --provider flag on the scan CLI command."""

    def test_provider_auto_passes_none(self):
        """--provider auto passes provider=None to run_scan."""
        runner = CliRunner()
        scan_run = _make_scan_run()

        with patch("src.cli.main.asyncio.run", return_value=scan_run) as mock_run:
            result = runner.invoke(cli, ["scan", "--provider", "auto"])

        assert result.exit_code == 0
        # asyncio.run receives the coroutine — inspect its creation
        mock_run.assert_called_once()
        coro = mock_run.call_args[0][0]
        coro.close()

    def test_provider_myp_creates_myp_provider(self):
        """--provider myp creates a MypCardsProvider and passes it."""
        runner = CliRunner()
        scan_run = _make_scan_run()

        with (
            patch("src.cli.main.asyncio.run", return_value=scan_run),
            patch(
                "src.providers.myp.provider.MypCardsProvider",
                autospec=True,
            ) as MockMypProvider,
        ):
            result = runner.invoke(cli, ["scan", "--provider", "myp"])

        assert result.exit_code == 0
        # MypCardsProvider was instantiated (via _resolve_provider)
        MockMypProvider.assert_called_once()

    def test_provider_liga_shows_fallback_note(self):
        """--provider liga shows MYP fallback note."""
        runner = CliRunner()
        scan_run = _make_scan_run()

        with patch("src.cli.main.asyncio.run", return_value=scan_run):
            result = runner.invoke(cli, ["scan", "--provider", "liga"])

        assert result.exit_code == 0
        assert "LigaMagic CLI provider not yet wired" in result.output
        assert "MYP fallback" in result.output

    def test_provider_default_is_auto(self):
        """No --provider flag defaults to auto behavior."""
        runner = CliRunner()
        scan_run = _make_scan_run()

        with patch("src.cli.main.asyncio.run", return_value=scan_run):
            result = runner.invoke(cli, ["scan"])

        assert result.exit_code == 0

    def test_provider_invalid_choice_rejected(self):
        """Invalid --provider value is rejected by Click."""
        runner = CliRunner()
        result = runner.invoke(cli, ["scan", "--provider", "invalid"])

        assert result.exit_code != 0
        assert "Invalid value" in result.output or "invalid" in result.output.lower()

    def test_scan_help_shows_provider_option(self):
        """scan --help lists the --provider option."""
        runner = CliRunner()
        result = runner.invoke(cli, ["scan", "--help"])

        assert result.exit_code == 0
        assert "--provider" in result.output
        assert "auto" in result.output
        assert "liga" in result.output
        assert "myp" in result.output


class TestSnapshotPricesProviderFlag:
    """Tests for --provider flag on snapshot-prices."""

    def test_snapshot_help_shows_provider_option(self):
        """snapshot-prices --help lists the --provider option."""
        runner = CliRunner()
        result = runner.invoke(cli, ["snapshot-prices", "--help"])

        assert result.exit_code == 0
        assert "--provider" in result.output

    def test_snapshot_provider_liga_shows_note(self):
        """snapshot-prices --provider liga shows note about MYP fallback."""
        runner = CliRunner()

        # Build a minimal SnapshotSummary
        from src.domain.models import SnapshotSummary

        summary = SnapshotSummary(
            total_entries=0,
            fetched=0,
            stored=0,
            skipped_existing=0,
            skipped_zero_price=0,
            errors=0,
            error_details=[],
            started_at=datetime(2026, 8, 24, 10, 0, 0),
            finished_at=datetime(2026, 8, 24, 10, 0, 1),
        )

        with patch("src.cli.main.asyncio.run", return_value=summary):
            result = runner.invoke(cli, ["snapshot-prices", "--provider", "liga"])

        assert result.exit_code == 0
        assert "LigaMagic not yet wired for snapshots" in result.output
