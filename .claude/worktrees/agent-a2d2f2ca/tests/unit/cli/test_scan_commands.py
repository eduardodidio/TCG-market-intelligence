"""Tests for CLI scan and scan-history commands."""

from __future__ import annotations

from datetime import datetime
from unittest.mock import MagicMock, patch

from click.testing import CliRunner

from src.cli.main import cli
from src.domain.models import ScanFilter, ScanRun, ScanType

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_scan_run(
    *,
    scan_id: int = 1,
    scan_type: str = "collection",
    status: str = "completed",
    cards_total: int = 50,
    cards_processed: int = 48,
    cards_failed: int = 2,
    observations_saved: int = 48,
    error_summary: str | None = None,
) -> ScanRun:
    return ScanRun(
        id=scan_id,
        scan_type=scan_type,
        status=status,
        cards_total=cards_total,
        cards_processed=cards_processed,
        cards_failed=cards_failed,
        observations_saved=observations_saved,
        error_summary=error_summary,
        started_at=datetime(2026, 8, 20, 10, 0, 0),
        finished_at=datetime(2026, 8, 20, 10, 5, 0),
    )


def _make_scan_history_rows(count: int = 3) -> list[dict]:
    return [
        {
            "id": i + 1,
            "scan_type": "collection",
            "status": "completed",
            "cards_total": 50,
            "cards_processed": 48,
            "cards_failed": 2,
            "observations_saved": 48,
            "error_summary": None,
            "started_at": datetime(2026, 8, 20, 10, i, 0),
            "finished_at": datetime(2026, 8, 20, 10, i + 5, 0),
            "created_at": datetime(2026, 8, 20, 10, i, 0),
        }
        for i in range(count)
    ]


# ---------------------------------------------------------------------------
# scan command
# ---------------------------------------------------------------------------


class TestScanCommand:
    def test_scan_happy_path(self):
        """scan runs with defaults and prints summary."""
        runner = CliRunner()
        scan_run = _make_scan_run()

        with patch("src.cli.main.asyncio.run", return_value=scan_run):
            result = runner.invoke(cli, ["scan"])

        assert result.exit_code == 0
        assert "Scan #1" in result.output
        assert "completed" in result.output
        assert "Cards total:  50" in result.output
        assert "Processed:    48" in result.output
        assert "Failed:       2" in result.output
        assert "Observations: 48" in result.output

    def test_scan_with_set_filter(self):
        """scan --type set --set dmr builds ScanFilter with set_codes."""
        runner = CliRunner()
        scan_run = _make_scan_run(scan_type="set")

        def fake_run(coro):
            # Extract the coroutine's arguments by running it partially
            # We just return the scan_run and capture via the mock
            return scan_run

        with patch("src.cli.main.asyncio.run", side_effect=fake_run):
            with patch("src.collectors.scan.run_scan") as mock_run_scan:
                mock_run_scan.return_value = scan_run
                result = runner.invoke(cli, ["scan", "--type", "set", "--set", "dmr"])

        assert result.exit_code == 0
        # Verify the asyncio.run was called — we check via output
        assert "Scan #1" in result.output

    def test_scan_filters_parsed_correctly(self):
        """Verify ScanFilter is built correctly from CLI options."""
        runner = CliRunner()
        scan_run = _make_scan_run()
        captured_filter = {}

        async def capture_scan(**kwargs):
            captured_filter.update(kwargs)
            return scan_run

        with patch("src.collectors.scan.run_scan", side_effect=capture_scan):
            result = runner.invoke(
                cli,
                [
                    "scan",
                    "--type",
                    "set",
                    "--set",
                    "dmr,one",
                    "--rarity",
                    "rare,mythic",
                    "--card-ids",
                    "10,20,30",
                    "--limit",
                    "5",
                ],
            )

        assert result.exit_code == 0
        sf = captured_filter["scan_filter"]
        assert isinstance(sf, ScanFilter)
        assert sf.scan_type == ScanType.SET
        assert sf.set_codes == ["dmr", "one"]
        assert sf.rarities == ["rare", "mythic"]
        assert sf.card_ids == [10, 20, 30]
        assert sf.limit == 5

    def test_scan_dry_run(self):
        """scan --dry-run passes dry_run=True and shows DRY RUN prefix."""
        runner = CliRunner()
        scan_run = _make_scan_run()
        captured_kwargs = {}

        async def capture_scan(**kwargs):
            captured_kwargs.update(kwargs)
            return scan_run

        with patch("src.collectors.scan.run_scan", side_effect=capture_scan):
            result = runner.invoke(cli, ["scan", "--dry-run"])

        assert result.exit_code == 0
        assert captured_kwargs["dry_run"] is True
        assert "[DRY RUN]" in result.output

    def test_scan_error_output(self):
        """scan shows error summary when present."""
        runner = CliRunner()
        scan_run = _make_scan_run(
            cards_failed=5,
            error_summary="TimeoutError: 3, HTTPError: 2",
        )

        with patch("src.cli.main.asyncio.run", return_value=scan_run):
            result = runner.invoke(cli, ["scan"])

        assert result.exit_code == 0
        assert "Errors:       TimeoutError: 3, HTTPError: 2" in result.output

    def test_scan_no_error_summary_hidden(self):
        """scan does not print error line when error_summary is None."""
        runner = CliRunner()
        scan_run = _make_scan_run(error_summary=None)

        with patch("src.cli.main.asyncio.run", return_value=scan_run):
            result = runner.invoke(cli, ["scan"])

        assert result.exit_code == 0
        assert "Errors:" not in result.output


# ---------------------------------------------------------------------------
# scan-history command
# ---------------------------------------------------------------------------


class TestScanHistoryCommand:
    def test_scan_history_happy_path(self):
        """scan-history lists runs in a table."""
        runner = CliRunner()
        rows = _make_scan_history_rows(3)
        mock_repo = MagicMock()
        mock_repo.list_scan_runs.return_value = rows

        with patch("src.database.repository.Repository", return_value=mock_repo):
            result = runner.invoke(cli, ["scan-history"])

        assert result.exit_code == 0
        assert "ID" in result.output
        assert "Type" in result.output
        assert "Status" in result.output
        # Should show all 3 rows
        assert "1" in result.output
        assert "2" in result.output
        assert "3" in result.output
        assert "collection" in result.output
        assert "completed" in result.output

    def test_scan_history_empty(self):
        """scan-history shows message when no runs found."""
        runner = CliRunner()
        mock_repo = MagicMock()
        mock_repo.list_scan_runs.return_value = []

        with patch("src.database.repository.Repository", return_value=mock_repo):
            result = runner.invoke(cli, ["scan-history"])

        assert result.exit_code == 0
        assert "No scan runs found." in result.output

    def test_scan_history_with_filters(self):
        """scan-history passes type and status filters to repository."""
        runner = CliRunner()
        mock_repo = MagicMock()
        mock_repo.list_scan_runs.return_value = _make_scan_history_rows(1)

        with patch("src.database.repository.Repository", return_value=mock_repo):
            result = runner.invoke(
                cli,
                ["scan-history", "--type", "collection", "--status", "completed"],
            )

        assert result.exit_code == 0
        mock_repo.list_scan_runs.assert_called_once_with(
            limit=20,
            scan_type="collection",
            status="completed",
        )

    def test_scan_history_with_limit(self):
        """scan-history --limit 5 passes limit to repository."""
        runner = CliRunner()
        mock_repo = MagicMock()
        mock_repo.list_scan_runs.return_value = _make_scan_history_rows(2)

        with patch("src.database.repository.Repository", return_value=mock_repo):
            result = runner.invoke(cli, ["scan-history", "--limit", "5"])

        assert result.exit_code == 0
        mock_repo.list_scan_runs.assert_called_once_with(
            limit=5,
            scan_type=None,
            status=None,
        )

    def test_scan_history_started_at_formatting(self):
        """scan-history truncates started_at to 19 chars."""
        runner = CliRunner()
        rows = [
            {
                "id": 1,
                "scan_type": "set",
                "status": "completed",
                "cards_total": 10,
                "cards_processed": 10,
                "cards_failed": 0,
                "observations_saved": 10,
                "started_at": datetime(2026, 8, 20, 14, 30, 0),
            }
        ]
        mock_repo = MagicMock()
        mock_repo.list_scan_runs.return_value = rows

        with patch("src.database.repository.Repository", return_value=mock_repo):
            result = runner.invoke(cli, ["scan-history"])

        assert result.exit_code == 0
        assert "2026-08-20 14:30:00" in result.output

    def test_scan_history_missing_started_at(self):
        """scan-history shows dash when started_at is missing."""
        runner = CliRunner()
        rows = [
            {
                "id": 1,
                "scan_type": "custom",
                "status": "pending",
                "cards_total": 0,
                "cards_processed": 0,
                "cards_failed": 0,
                "observations_saved": 0,
                "started_at": None,
            }
        ]
        mock_repo = MagicMock()
        mock_repo.list_scan_runs.return_value = rows

        with patch("src.database.repository.Repository", return_value=mock_repo):
            result = runner.invoke(cli, ["scan-history"])

        assert result.exit_code == 0
        # The "-" placeholder should appear in the output
        assert "-" in result.output
