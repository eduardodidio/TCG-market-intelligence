"""Tests for the Liga URL resolver (F169-T04)."""

from __future__ import annotations

from unittest.mock import MagicMock

from src.providers.liga.url_resolver import resolve_liga_page_url_sync


class TestResolveLigaPageUrlSync:
    def test_resolve_returns_final_url(self):
        """Should return the page URL after navigation."""
        page = MagicMock()
        page.url = "https://www.ligamagic.com.br/?view=cards/card&card=Sol+Ring&show=1"

        result = resolve_liga_page_url_sync("Sol Ring", page)

        assert result == page.url
        page.goto.assert_called_once()
        # Verify the URL passed to goto contains the card name
        call_args = page.goto.call_args
        assert "Sol+Ring" in call_args[0][0]

    def test_resolve_returns_none_on_timeout(self):
        """Should return None when page.goto raises an exception."""
        page = MagicMock()
        page.goto.side_effect = TimeoutError("Navigation timeout")

        result = resolve_liga_page_url_sync("Dark Ritual", page)

        assert result is None

    def test_resolve_returns_none_on_generic_error(self):
        """Should return None on any exception, not just TimeoutError."""
        page = MagicMock()
        page.goto.side_effect = RuntimeError("Browser crashed")

        result = resolve_liga_page_url_sync("Lightning Bolt", page)

        assert result is None

    def test_resolve_passes_correct_timeout(self):
        """Should pass timeout=30000 to page.goto."""
        page = MagicMock()
        page.url = "https://www.ligamagic.com.br/?view=cards/card&card=Test"

        resolve_liga_page_url_sync("Test", page)

        call_kwargs = page.goto.call_args[1]
        assert call_kwargs["timeout"] == 30000

    def test_resolve_uses_domcontentloaded(self):
        """Should use wait_until='domcontentloaded' for faster page loads."""
        page = MagicMock()
        page.url = "https://www.ligamagic.com.br/?view=cards/card&card=Test"

        resolve_liga_page_url_sync("Test", page)

        call_kwargs = page.goto.call_args[1]
        assert call_kwargs["wait_until"] == "domcontentloaded"
