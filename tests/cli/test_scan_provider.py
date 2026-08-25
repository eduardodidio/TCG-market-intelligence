"""Tests for the CLI scan --provider flag (F60-T06).

Covers:
 1. --provider liga: passes provider_name="liga" to run_scan (no provider instance)
 2. --provider myp: creates MypCardsProvider and passes provider_name="myp"
 3. --provider auto: defaults to liga behavior
 4. Default (no flag): defaults to liga
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

    def test_provider_liga_passes_provider_name_liga(self):
        """--provider liga passes provider_name='liga' to run_scan."""
        runner = CliRunner()
        scan_run = _make_scan_run()
        captured_kwargs = {}

        async def capture_scan(**kwargs):
            captured_kwargs.update(kwargs)
            return scan_run

        with patch("src.collectors.scan.run_scan", side_effect=capture_scan):
            result = runner.invoke(cli, ["scan", "--provider", "liga"])

        assert result.exit_code == 0
        assert captured_kwargs["provider_name"] == "liga"
        assert captured_kwargs["provider"] is None

    def test_provider_myp_creates_myp_provider(self):
        """--provider myp creates a MypCardsProvider and passes provider_name='myp'."""
        runner = CliRunner()
        scan_run = _make_scan_run()
        captured_kwargs = {}

        async def capture_scan(**kwargs):
            captured_kwargs.update(kwargs)
            return scan_run

        with (
            patch("src.collectors.scan.run_scan", side_effect=capture_scan),
            patch(
                "src.providers.myp.provider.MypCardsProvider",
                autospec=True,
            ) as MockMypProvider,
        ):
            result = runner.invoke(cli, ["scan", "--provider", "myp"])

        assert result.exit_code == 0
        assert captured_kwargs["provider_name"] == "myp"
        # MypCardsProvider was instantiated (via _resolve_provider)
        MockMypProvider.assert_called_once()
        assert captured_kwargs["provider"] is not None

    def test_provider_auto_defaults_to_liga(self):
        """--provider auto defaults to liga behavior."""
        runner = CliRunner()
        scan_run = _make_scan_run()
        captured_kwargs = {}

        async def capture_scan(**kwargs):
            captured_kwargs.update(kwargs)
            return scan_run

        with patch("src.collectors.scan.run_scan", side_effect=capture_scan):
            result = runner.invoke(cli, ["scan", "--provider", "auto"])

        assert result.exit_code == 0
        assert captured_kwargs["provider_name"] == "liga"
        assert captured_kwargs["provider"] is None

    def test_provider_default_is_liga(self):
        """No --provider flag defaults to liga."""
        runner = CliRunner()
        scan_run = _make_scan_run()
        captured_kwargs = {}

        async def capture_scan(**kwargs):
            captured_kwargs.update(kwargs)
            return scan_run

        with patch("src.collectors.scan.run_scan", side_effect=capture_scan):
            result = runner.invoke(cli, ["scan"])

        assert result.exit_code == 0
        assert captured_kwargs["provider_name"] == "liga"

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
