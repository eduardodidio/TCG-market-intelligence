"""Tests for the CLI scan --provider flag.

Covers:
 1. --provider myp: creates MypCardsProvider and passes provider_name="myp"
 2. Default (no flag): defaults to myp
 3. Invalid provider rejected
 4. scan --help shows --provider option
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

    def test_provider_default_is_myp(self):
        """No --provider flag defaults to myp."""
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
            ),
        ):
            result = runner.invoke(cli, ["scan"])

        assert result.exit_code == 0
        assert captured_kwargs["provider_name"] == "myp"

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
        assert "myp" in result.output


class TestSnapshotPricesProviderFlag:
    """Tests for --provider flag on snapshot-prices."""

    def test_snapshot_help_shows_provider_option(self):
        """snapshot-prices --help lists the --provider option."""
        runner = CliRunner()
        result = runner.invoke(cli, ["snapshot-prices", "--help"])

        assert result.exit_code == 0
        assert "--provider" in result.output
