"""Tests for the liga-verify-links CLI command (F169-T03)."""

from __future__ import annotations

from datetime import datetime
from unittest.mock import MagicMock, patch

from click.testing import CliRunner

from src.cli.main import cli


def _make_url_row(external_id: str, url: str):
    """Create a mock LigaCardUrlRow."""
    row = MagicMock()
    row.external_id = external_id
    row.url = url
    row.updated_at = datetime(2026, 9, 20, 12, 0, 0)
    return row


class TestLigaVerifyLinksDryRun:
    def test_dry_run_shows_would_verify(self):
        mock_repo = MagicMock()
        mock_repo.get_all_liga_card_urls.return_value = [
            _make_url_row("liga_1", "https://ligamagic.com.br/?view=cards/card&card=Sol+Ring"),
            _make_url_row(
                "liga_2", "https://ligamagic.com.br/?view=cards/card&card=Lightning+Bolt"
            ),
        ]
        mock_repo.get_card_name_by_liga_external_id.side_effect = lambda eid: {
            "liga_1": "Sol Ring",
            "liga_2": "Lightning Bolt",
        }.get(eid)

        with patch("src.database.repository.Repository", return_value=mock_repo):
            runner = CliRunner()
            result = runner.invoke(
                cli, ["liga-verify-links", "--dry-run", "--db", "sqlite:///test.db"]
            )

        assert result.exit_code == 0
        assert "Would verify" in result.output
        assert "Sol Ring" in result.output
        assert "Lightning Bolt" in result.output
        # No Playwright import should happen in dry-run

    def test_dry_run_shows_orphans(self):
        mock_repo = MagicMock()
        mock_repo.get_all_liga_card_urls.return_value = [
            _make_url_row("liga_99", "https://ligamagic.com.br/?view=cards/card&card=Gone"),
        ]
        mock_repo.get_card_name_by_liga_external_id.return_value = None

        with patch("src.database.repository.Repository", return_value=mock_repo):
            runner = CliRunner()
            result = runner.invoke(
                cli, ["liga-verify-links", "--dry-run", "--db", "sqlite:///test.db"]
            )

        assert result.exit_code == 0
        assert "[ORPHAN]" in result.output


class TestLigaVerifyLinksOrphan:
    def test_orphan_detected_when_no_card_name(self):
        """When get_card_name returns None, the URL should be marked as orphan."""
        mock_repo = MagicMock()
        mock_repo.get_all_liga_card_urls.return_value = [
            _make_url_row("liga_999", "https://ligamagic.com.br/?view=cards/card&card=Missing"),
        ]
        mock_repo.get_card_name_by_liga_external_id.return_value = None

        mock_pw_ctx = MagicMock()
        mock_browser = MagicMock()
        mock_pw_ctx.__enter__ = MagicMock(return_value=mock_pw_ctx)
        mock_pw_ctx.__exit__ = MagicMock(return_value=False)
        mock_pw_ctx.chromium.launch.return_value = mock_browser

        with (
            patch("src.database.repository.Repository", return_value=mock_repo),
            patch("playwright.sync_api.sync_playwright", return_value=mock_pw_ctx),
        ):
            runner = CliRunner()
            result = runner.invoke(cli, ["liga-verify-links", "--db", "sqlite:///test.db"])

        assert result.exit_code == 0
        assert "[ORPHAN]" in result.output


class TestLigaVerifyLinksLimit:
    def test_respects_limit(self):
        """With 10 URLs and --limit 3, only 3 should be processed."""
        urls = [
            _make_url_row(f"liga_{i}", f"https://ligamagic.com.br/?card={i}") for i in range(10)
        ]

        mock_repo = MagicMock()
        mock_repo.get_all_liga_card_urls.return_value = urls
        mock_repo.get_card_name_by_liga_external_id.return_value = "Card"

        with patch("src.database.repository.Repository", return_value=mock_repo):
            runner = CliRunner()
            result = runner.invoke(
                cli, ["liga-verify-links", "--dry-run", "--limit", "3", "--db", "sqlite:///test.db"]
            )

        assert result.exit_code == 0
        # Should only have 3 "Would verify" lines
        verify_count = result.output.count("Would verify")
        assert verify_count == 3
