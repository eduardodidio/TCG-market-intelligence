"""Tests for the liga-relink CLI command (F169-T04)."""

from __future__ import annotations

import json
import os
import tempfile
from unittest.mock import MagicMock, patch

from click.testing import CliRunner

from src.cli.main import cli


def _mock_repo():
    """Create a mock Repository with liga helpers."""
    repo = MagicMock()
    repo.get_card_name_by_liga_external_id.side_effect = lambda eid: {
        "liga_1": "Sol Ring",
        "liga_2": "Lightning Bolt",
    }.get(eid)
    repo.get_liga_card_url.return_value = (
        "https://www.ligamagic.com.br/?view=cards/card&card=Wrong+Card"
    )
    return repo


def _mock_playwright_ctx(
    final_url: str = "https://www.ligamagic.com.br/?view=cards/card&card=Sol+Ring",
):
    """Build a mock sync_playwright() context manager."""
    mock_page = MagicMock()
    mock_page.url = final_url
    mock_page.goto = MagicMock()

    mock_browser = MagicMock()
    mock_browser.new_page.return_value = mock_page

    mock_pw = MagicMock()
    mock_pw.chromium.launch.return_value = mock_browser

    mock_ctx = MagicMock()
    mock_ctx.__enter__ = MagicMock(return_value=mock_pw)
    mock_ctx.__exit__ = MagicMock(return_value=False)

    return mock_ctx, mock_page


class TestRelinkDryRun:
    def test_dry_run_no_db_writes(self):
        """Dry run should NOT call upsert and should show [SKIPPED]."""
        repo = _mock_repo()

        with patch("src.database.repository.Repository", return_value=repo):
            runner = CliRunner()
            result = runner.invoke(
                cli,
                [
                    "liga-relink",
                    "--external-ids",
                    "liga_1",
                    "--dry-run",
                    "--db",
                    "sqlite:///test.db",
                ],
            )

        assert result.exit_code == 0
        assert "[SKIPPED]" in result.output
        assert "Sol Ring" in result.output
        repo.upsert_liga_card_url.assert_not_called()

    def test_dry_run_shows_orphan(self):
        """Dry run with an unknown external_id should show [ORPHAN]."""
        repo = _mock_repo()

        with patch("src.database.repository.Repository", return_value=repo):
            runner = CliRunner()
            result = runner.invoke(
                cli,
                [
                    "liga-relink",
                    "--external-ids",
                    "liga_unknown",
                    "--dry-run",
                    "--db",
                    "sqlite:///test.db",
                ],
            )

        assert result.exit_code == 0
        assert "[ORPHAN]" in result.output
        repo.upsert_liga_card_url.assert_not_called()


class TestRelinkFromExternalIds:
    def test_relink_calls_upsert(self):
        """With valid external_ids, should navigate and upsert the new URL."""
        repo = _mock_repo()
        final_url = "https://www.ligamagic.com.br/?view=cards/card&card=Sol+Ring"
        mock_ctx, _page = _mock_playwright_ctx(final_url)

        with (
            patch("src.database.repository.Repository", return_value=repo),
            patch("playwright.sync_api.sync_playwright", return_value=mock_ctx),
        ):
            runner = CliRunner()
            result = runner.invoke(
                cli,
                [
                    "liga-relink",
                    "--external-ids",
                    "liga_1",
                    "--delay",
                    "0",
                    "--db",
                    "sqlite:///test.db",
                ],
            )

        assert result.exit_code == 0
        assert "[RELINKED]" in result.output
        repo.upsert_liga_card_url.assert_called_once_with("liga_1", final_url)

    def test_relink_multiple_ids(self):
        """Comma-separated external_ids should all be processed."""
        repo = _mock_repo()
        final_url = "https://www.ligamagic.com.br/?view=cards/card&card=Sol+Ring"
        mock_ctx, _page = _mock_playwright_ctx(final_url)

        with (
            patch("src.database.repository.Repository", return_value=repo),
            patch("playwright.sync_api.sync_playwright", return_value=mock_ctx),
        ):
            runner = CliRunner()
            result = runner.invoke(
                cli,
                [
                    "liga-relink",
                    "--external-ids",
                    "liga_1,liga_2",
                    "--delay",
                    "0",
                    "--db",
                    "sqlite:///test.db",
                ],
            )

        assert result.exit_code == 0
        assert repo.upsert_liga_card_url.call_count == 2


class TestRelinkFromJsonInput:
    def test_reads_mismatches_from_json(self):
        """Reads a JSON file and filters only MISMATCH entries."""
        repo = _mock_repo()
        final_url = "https://www.ligamagic.com.br/?view=cards/card&card=Sol+Ring"
        mock_ctx, _page = _mock_playwright_ctx(final_url)

        data = [
            {"external_id": "liga_1", "status": "mismatch", "url": "https://old.url"},
            {"external_id": "liga_2", "status": "match", "url": "https://ok.url"},
        ]

        with tempfile.NamedTemporaryFile(
            mode="w",
            suffix=".json",
            delete=False,
            encoding="utf-8",
        ) as f:
            json.dump(data, f)
            tmp_path = f.name

        try:
            with (
                patch("src.database.repository.Repository", return_value=repo),
                patch("playwright.sync_api.sync_playwright", return_value=mock_ctx),
            ):
                runner = CliRunner()
                result = runner.invoke(
                    cli,
                    [
                        "liga-relink",
                        "--input",
                        tmp_path,
                        "--delay",
                        "0",
                        "--db",
                        "sqlite:///test.db",
                    ],
                )
        finally:
            os.unlink(tmp_path)

        assert result.exit_code == 0
        assert "1 MISMATCH" in result.output
        # Only liga_1 (mismatch) should be relinked, not liga_2 (match)
        repo.upsert_liga_card_url.assert_called_once_with("liga_1", final_url)

    def test_no_mismatches_in_json(self):
        """JSON with no mismatches should do nothing."""
        repo = _mock_repo()

        data = [
            {"external_id": "liga_1", "status": "match", "url": "https://ok.url"},
        ]

        with tempfile.NamedTemporaryFile(
            mode="w",
            suffix=".json",
            delete=False,
            encoding="utf-8",
        ) as f:
            json.dump(data, f)
            tmp_path = f.name

        try:
            with patch("src.database.repository.Repository", return_value=repo):
                runner = CliRunner()
                result = runner.invoke(
                    cli,
                    ["liga-relink", "--input", tmp_path, "--db", "sqlite:///test.db"],
                )
        finally:
            os.unlink(tmp_path)

        assert result.exit_code == 0
        assert "Nothing to relink" in result.output


class TestRelinkOrphanSkipped:
    def test_orphan_not_upserted(self):
        """When card name cannot be resolved, skip with [ORPHAN]."""
        repo = _mock_repo()
        repo.get_card_name_by_liga_external_id.return_value = None

        final_url = "https://www.ligamagic.com.br/?view=cards/card&card=Sol+Ring"
        mock_ctx, _page = _mock_playwright_ctx(final_url)

        with (
            patch("src.database.repository.Repository", return_value=repo),
            patch("playwright.sync_api.sync_playwright", return_value=mock_ctx),
        ):
            runner = CliRunner()
            result = runner.invoke(
                cli,
                [
                    "liga-relink",
                    "--external-ids",
                    "liga_orphan",
                    "--delay",
                    "0",
                    "--db",
                    "sqlite:///test.db",
                ],
            )

        assert result.exit_code == 0
        assert "[ORPHAN]" in result.output
        repo.upsert_liga_card_url.assert_not_called()


class TestRelinkErrorHandling:
    def test_no_input_shows_error(self):
        """Must provide --input or --external-ids."""
        repo = _mock_repo()

        with patch("src.database.repository.Repository", return_value=repo):
            runner = CliRunner()
            result = runner.invoke(
                cli,
                ["liga-relink", "--db", "sqlite:///test.db"],
            )

        assert result.exit_code != 0
        assert "Provide --input or --external-ids" in result.output

    def test_both_inputs_shows_error(self):
        """Cannot use --input and --external-ids together."""
        repo = _mock_repo()

        with tempfile.NamedTemporaryFile(
            mode="w",
            suffix=".json",
            delete=False,
            encoding="utf-8",
        ) as f:
            json.dump([], f)
            tmp_path = f.name

        try:
            with patch("src.database.repository.Repository", return_value=repo):
                runner = CliRunner()
                result = runner.invoke(
                    cli,
                    [
                        "liga-relink",
                        "--input",
                        tmp_path,
                        "--external-ids",
                        "liga_1",
                        "--db",
                        "sqlite:///test.db",
                    ],
                )
        finally:
            os.unlink(tmp_path)

        assert result.exit_code != 0
        assert "not both" in result.output

    def test_invalid_url_from_playwright(self):
        """If Playwright returns a non-Liga URL, should show [ERROR]."""
        repo = _mock_repo()
        mock_ctx, _page = _mock_playwright_ctx("https://google.com/not-liga")

        with (
            patch("src.database.repository.Repository", return_value=repo),
            patch("playwright.sync_api.sync_playwright", return_value=mock_ctx),
        ):
            runner = CliRunner()
            result = runner.invoke(
                cli,
                [
                    "liga-relink",
                    "--external-ids",
                    "liga_1",
                    "--delay",
                    "0",
                    "--db",
                    "sqlite:///test.db",
                ],
            )

        assert result.exit_code == 0
        assert "[ERROR]" in result.output
        repo.upsert_liga_card_url.assert_not_called()


class TestRelinkSummary:
    def test_summary_printed(self):
        """Summary section should appear at the end."""
        repo = _mock_repo()
        final_url = "https://www.ligamagic.com.br/?view=cards/card&card=Sol+Ring"
        mock_ctx, _page = _mock_playwright_ctx(final_url)

        with (
            patch("src.database.repository.Repository", return_value=repo),
            patch("playwright.sync_api.sync_playwright", return_value=mock_ctx),
        ):
            runner = CliRunner()
            result = runner.invoke(
                cli,
                [
                    "liga-relink",
                    "--external-ids",
                    "liga_1",
                    "--delay",
                    "0",
                    "--db",
                    "sqlite:///test.db",
                ],
            )

        assert result.exit_code == 0
        assert "LIGA RELINK SUMMARY" in result.output
        assert "Relinked:" in result.output
