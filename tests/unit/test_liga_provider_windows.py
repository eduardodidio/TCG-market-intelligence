"""Tests for LigaMagic provider Windows platform guard (F76)."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.providers.liga.config import LigaConfig
from src.providers.liga.exceptions import LigaError
from src.providers.liga.provider import LigaMagicProvider


@pytest.fixture
def provider():
    return LigaMagicProvider(LigaConfig())


class TestWindowsPlatformGuard:
    """open() should skip Playwright startup on Windows."""

    @pytest.mark.asyncio
    async def test_open_skips_playwright_on_windows(self, provider):
        with patch("src.providers.liga.provider.sys") as mock_sys:
            mock_sys.platform = "win32"
            await provider.open()

        assert provider._unavailable is True
        assert provider._playwright is None
        assert provider._browser is None
        assert provider._page is None

    @pytest.mark.asyncio
    async def test_close_is_noop_when_unavailable(self, provider):
        provider._unavailable = True
        # Should not raise or try to close browser resources
        await provider.close()

    @pytest.mark.asyncio
    async def test_ensure_page_raises_when_unavailable(self, provider):
        provider._unavailable = True
        with pytest.raises(LigaError, match="unavailable"):
            await provider._ensure_page()

    @pytest.mark.asyncio
    async def test_get_current_price_raises_when_unavailable(self, provider):
        from src.domain.models import CardIdentity, SourceCard

        provider._unavailable = True
        card = SourceCard(
            source="liga",
            external_id="123",
            url="https://example.com/card",
            identity=CardIdentity(game="mtg", name_en="Lightning Bolt"),
        )
        # get_current_price catches LigaError and returns None
        result = await provider.get_current_price(card)
        assert result is None

    @pytest.mark.asyncio
    async def test_search_card_returns_empty_when_unavailable(self, provider):
        provider._unavailable = True
        result = await provider.search_card("Lightning Bolt")
        # search_card catches LigaError internally and returns empty parse
        assert result["normal"]["low"] is None
        assert result["normal"]["mid"] is None

    @pytest.mark.asyncio
    async def test_context_manager_works_when_unavailable(self):
        with patch("src.providers.liga.provider.sys") as mock_sys:
            mock_sys.platform = "win32"
            async with LigaMagicProvider(LigaConfig()) as p:
                assert p._unavailable is True
        # Should not raise on __aexit__


class TestNonWindowsPlatform:
    """open() should proceed normally on Linux/macOS."""

    @pytest.mark.asyncio
    async def test_open_starts_playwright_on_linux(self, provider):
        mock_pw_instance = MagicMock()
        mock_browser = AsyncMock()
        mock_context = AsyncMock()
        mock_page = AsyncMock()

        mock_pw_instance.start = AsyncMock(
            return_value=MagicMock(
                chromium=MagicMock(launch=AsyncMock(return_value=mock_browser)),
            )
        )
        mock_browser.new_context = AsyncMock(return_value=mock_context)
        mock_context.new_page = AsyncMock(return_value=mock_page)

        with (
            patch("src.providers.liga.provider.sys") as mock_sys,
            patch("playwright.async_api.async_playwright", return_value=mock_pw_instance),
        ):
            mock_sys.platform = "linux"
            await provider.open()

        assert provider._unavailable is False
        assert provider._page is not None

    @pytest.mark.asyncio
    async def test_unavailable_flag_false_by_default(self, provider):
        assert provider._unavailable is False
