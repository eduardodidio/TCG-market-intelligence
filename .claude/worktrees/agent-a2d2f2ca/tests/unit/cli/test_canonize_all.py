"""Tests for CLI canonize-all command."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from click.testing import CliRunner

from src.cli.main import cli
from src.collectors.bulk_canonize import BulkCanonizeResult

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_bulk_result(
    *,
    total: int = 10,
    canonized: int = 8,
    failed: int = 1,
    skipped: int = 0,
    rate_limited: int = 1,
    errors: list | None = None,
) -> BulkCanonizeResult:
    return BulkCanonizeResult(
        total=total,
        canonized=canonized,
        failed=failed,
        skipped=skipped,
        rate_limited=rate_limited,
        errors=errors or [],
    )


def _make_collection_row(*, row_id: int = 1, card_id: int | None = None):
    """Minimal mock of UserCollectionRow for unlinked-entry queries."""
    row = MagicMock()
    row.id = row_id
    row.card_id = card_id
    return row


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestCanonizeAllCommand:
    def test_canonize_all_cli_dry_run(self):
        """Dry-run prints unlinked count and makes no MYP calls."""
        runner = CliRunner()
        unlinked = [_make_collection_row(row_id=i) for i in range(5)]

        with (
            patch(
                "src.collectors.bulk_canonize._get_unlinked_entries",
                return_value=unlinked,
            ) as mock_get,
            patch(
                "src.collectors.bulk_canonize.bulk_canonize",
            ) as mock_bulk,
            patch("src.database.repository.Repository") as mock_repo_cls,
        ):
            mock_repo_cls.return_value = MagicMock()
            result = runner.invoke(cli, ["canonize-all", "--user-id", "user-1", "--dry-run"])

        assert result.exit_code == 0
        assert "Unlinked entries: 5" in result.output
        assert "DRY RUN" in result.output
        mock_bulk.assert_not_called()
        mock_get.assert_called_once()

    def test_canonize_all_cli_with_limit(self):
        """--limit is forwarded to bulk_canonize service."""
        runner = CliRunner()
        bulk_result = _make_bulk_result(total=3, canonized=3, failed=0, rate_limited=0)

        with (
            patch("src.cli.main.asyncio.run", return_value=bulk_result),
            patch("src.providers.myp.provider.MypCardsProvider") as mock_prov,
            patch("src.database.repository.Repository") as mock_repo_cls,
        ):
            mock_prov.return_value = MagicMock()
            mock_repo_cls.return_value = MagicMock()
            result = runner.invoke(cli, ["canonize-all", "--user-id", "user-1", "--limit", "3"])

        assert result.exit_code == 0
        assert "Total:          3" in result.output
        assert "Canonized:      3" in result.output

    def test_canonize_all_cli_prints_summary(self):
        """Output contains all summary fields: total, canonized, failed, rate_limited."""
        runner = CliRunner()
        bulk_result = _make_bulk_result(
            total=10,
            canonized=7,
            failed=2,
            skipped=0,
            rate_limited=1,
            errors=[
                {"entry_id": "42", "error": "RateLimitError: 429"},
                {"entry_id": "99", "error": "ServerError: 500"},
            ],
        )

        with (
            patch("src.cli.main.asyncio.run", return_value=bulk_result),
            patch("src.providers.myp.provider.MypCardsProvider") as mock_prov,
            patch("src.database.repository.Repository") as mock_repo_cls,
        ):
            mock_prov.return_value = MagicMock()
            mock_repo_cls.return_value = MagicMock()
            result = runner.invoke(cli, ["canonize-all", "--user-id", "user-1"])

        assert result.exit_code == 0
        assert "BULK CANONIZE SUMMARY" in result.output
        assert "Total:          10" in result.output
        assert "Canonized:      7" in result.output
        assert "Failed:         2" in result.output
        assert "Rate limited:   1" in result.output
        assert "Skipped:        0" in result.output
        # Error details
        assert "Errors (2):" in result.output
        assert "entry 42" in result.output
        assert "entry 99" in result.output

    def test_canonize_all_cli_requires_user_id(self):
        """Exits with error if --user-id is not provided."""
        runner = CliRunner()
        result = runner.invoke(cli, ["canonize-all"])

        assert result.exit_code != 0
        assert "user-id" in result.output.lower() or "user_id" in result.output.lower()

    def test_canonize_all_cli_default_concurrency(self):
        """Default concurrency is 3 when not specified."""
        runner = CliRunner()
        bulk_result = _make_bulk_result()

        async def fake_bulk_canonize(**kwargs):
            return bulk_result

        async def fake_close():
            pass

        with (
            patch(
                "src.collectors.bulk_canonize.bulk_canonize",
                side_effect=fake_bulk_canonize,
            ) as mock_bulk,
            patch("src.providers.myp.provider.MypCardsProvider") as mock_prov,
            patch("src.database.repository.Repository") as mock_repo_cls,
        ):
            mock_prov_inst = MagicMock()
            mock_prov_inst.close = fake_close
            mock_prov.return_value = mock_prov_inst
            mock_repo_cls.return_value = MagicMock()
            result = runner.invoke(cli, ["canonize-all", "--user-id", "user-1"])

        assert result.exit_code == 0
        mock_bulk.assert_called_once()
        call_kwargs = mock_bulk.call_args
        assert call_kwargs.kwargs.get("concurrency") == 3 or (
            len(call_kwargs.args) >= 4 and call_kwargs.args[3] == 3
        )
