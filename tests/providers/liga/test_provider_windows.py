"""Tests for LigaMagic provider Windows sync Playwright path (F84).

These tests verify the sync-in-thread Playwright approach that F84-T01
introduces for Windows, where the async Playwright API cannot work due
to event-loop incompatibilities (uvicorn SelectorEventLoop vs.
ProactorEventLoop).

All Playwright interactions are mocked -- no real browser is needed.
"""

from __future__ import annotations

from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.domain.models import CardIdentity, PriceSnapshot, SourceCard
from src.providers.liga.config import LigaConfig
from src.providers.liga.exceptions import LigaError
from src.providers.liga.provider import LigaMagicProvider

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_provider(**overrides) -> LigaMagicProvider:
    defaults = {"delay_seconds": 0, "max_retries": 1}
    defaults.update(overrides)
    return LigaMagicProvider(LigaConfig(**defaults))


async def _fake_to_thread(fn, *args, **kwargs):
    """Replacement for asyncio.to_thread that runs fn synchronously."""
    return fn(*args, **kwargs)


def _make_sync_pw_mocks():
    """Build a mock graph for sync Playwright objects.

    Returns (sync_playwright_fn, pw_instance, browser, context, page).
    """
    mock_page = MagicMock()
    mock_page.goto = MagicMock(return_value=MagicMock(status=200))
    mock_page.content = MagicMock(return_value="<html></html>")
    mock_page.wait_for_selector = MagicMock()
    mock_page.wait_for_timeout = MagicMock()

    mock_context = MagicMock()
    mock_context.new_page = MagicMock(return_value=mock_page)

    mock_browser = MagicMock()
    mock_browser.new_context = MagicMock(return_value=mock_context)
    mock_browser.close = MagicMock()

    mock_pw = MagicMock()
    mock_pw.chromium = MagicMock()
    mock_pw.chromium.launch = MagicMock(return_value=mock_browser)
    mock_pw.stop = MagicMock()

    # sync_playwright() returns obj with .start() -> pw
    mock_starter = MagicMock()
    mock_starter.start = MagicMock(return_value=mock_pw)

    mock_sync_playwright_fn = MagicMock(return_value=mock_starter)

    return mock_sync_playwright_fn, mock_pw, mock_browser, mock_context, mock_page


def _make_async_pw_mocks():
    """Build a mock graph for async Playwright objects."""
    mock_page = AsyncMock()
    mock_context = AsyncMock()
    mock_context.new_page = AsyncMock(return_value=mock_page)

    mock_browser = AsyncMock()
    mock_browser.new_context = AsyncMock(return_value=mock_context)
    mock_browser.close = AsyncMock()

    mock_pw = MagicMock()
    mock_pw.chromium = MagicMock()
    mock_pw.chromium.launch = AsyncMock(return_value=mock_browser)
    mock_pw.stop = AsyncMock()

    mock_starter = MagicMock()
    mock_starter.start = AsyncMock(return_value=mock_pw)

    mock_async_playwright_fn = MagicMock(return_value=mock_starter)

    return mock_async_playwright_fn, mock_pw, mock_browser, mock_context, mock_page


# ---------------------------------------------------------------------------
# Windows sync path: open()
# ---------------------------------------------------------------------------


class TestOpenWindowsUsesSyncPlaywright:
    """On Windows, open() should import sync Playwright and start it via to_thread."""

    @pytest.mark.asyncio
    async def test_open_windows_sets_use_sync_flag(self):
        provider = _make_provider()
        sync_pw_fn, mock_pw, mock_browser, mock_context, mock_page = _make_sync_pw_mocks()

        sync_api_module = MagicMock(sync_playwright=sync_pw_fn)

        with (
            patch("src.providers.liga.provider.sys") as mock_sys,
            patch.dict("sys.modules", {"playwright.sync_api": sync_api_module}),
            patch("asyncio.to_thread", side_effect=_fake_to_thread),
        ):
            mock_sys.platform = "win32"
            await provider.open()

        assert provider._use_sync is True
        assert provider._unavailable is False

    @pytest.mark.asyncio
    async def test_open_windows_stores_sync_resources(self):
        provider = _make_provider()
        sync_pw_fn, mock_pw, mock_browser, mock_context, mock_page = _make_sync_pw_mocks()

        with (
            patch("src.providers.liga.provider.sys") as mock_sys,
            patch.dict(
                "sys.modules",
                {"playwright.sync_api": MagicMock(sync_playwright=sync_pw_fn)},
            ),
            patch("asyncio.to_thread", side_effect=_fake_to_thread),
        ):
            mock_sys.platform = "win32"
            await provider.open()

        assert provider._sync_pw is mock_pw
        assert provider._sync_browser is mock_browser
        assert provider._sync_context is mock_context
        assert provider._sync_page is mock_page

    @pytest.mark.asyncio
    async def test_open_windows_does_not_set_async_resources(self):
        """Async _playwright/_browser/_page should stay None on Windows."""
        provider = _make_provider()
        sync_pw_fn, *_ = _make_sync_pw_mocks()

        with (
            patch("src.providers.liga.provider.sys") as mock_sys,
            patch.dict(
                "sys.modules",
                {"playwright.sync_api": MagicMock(sync_playwright=sync_pw_fn)},
            ),
            patch("asyncio.to_thread", side_effect=_fake_to_thread),
        ):
            mock_sys.platform = "win32"
            await provider.open()

        assert provider._playwright is None
        assert provider._browser is None
        assert provider._page is None

    @pytest.mark.asyncio
    async def test_open_windows_idempotent(self):
        """Calling open() twice should not re-start Playwright."""
        provider = _make_provider()
        sync_pw_fn, mock_pw, mock_browser, mock_context, mock_page = _make_sync_pw_mocks()

        with (
            patch("src.providers.liga.provider.sys") as mock_sys,
            patch.dict(
                "sys.modules",
                {"playwright.sync_api": MagicMock(sync_playwright=sync_pw_fn)},
            ),
            patch("asyncio.to_thread", side_effect=_fake_to_thread),
        ):
            mock_sys.platform = "win32"
            await provider.open()
            await provider.open()  # second call should be no-op

        assert sync_pw_fn.call_count == 1


# ---------------------------------------------------------------------------
# _fetch_page delegates to sync path
# ---------------------------------------------------------------------------


class TestFetchPageWindowsDelegatesToSync:
    """When _use_sync is True, _fetch_page delegates to _fetch_page_sync via to_thread."""

    @pytest.mark.asyncio
    async def test_fetch_page_windows_returns_html(self):
        provider = _make_provider()
        expected_html = "<html><body>Liga prices</body></html>"

        # Set up provider as if open() ran on Windows
        mock_page = MagicMock()
        mock_page.goto = MagicMock(return_value=MagicMock(status=200))
        mock_page.content = MagicMock(return_value=expected_html)
        mock_page.wait_for_selector = MagicMock()

        provider._use_sync = True
        provider._sync_page = mock_page

        with patch("asyncio.to_thread", side_effect=_fake_to_thread):
            html = await provider._fetch_page("https://www.ligamagic.com.br/test")

        assert html == expected_html

    @pytest.mark.asyncio
    async def test_fetch_page_sync_calls_goto(self):
        provider = _make_provider()

        mock_page = MagicMock()
        mock_page.goto = MagicMock(return_value=MagicMock(status=200))
        mock_page.content = MagicMock(return_value="<html></html>")
        mock_page.wait_for_selector = MagicMock()

        provider._use_sync = True
        provider._sync_page = mock_page

        url = "https://www.ligamagic.com.br/?view=cards/card&card=Sol+Ring&show=1"

        with patch("asyncio.to_thread", side_effect=_fake_to_thread):
            await provider._fetch_page(url)

        mock_page.goto.assert_called_once_with(
            url,
            wait_until="networkidle",
            timeout=int(provider.config.timeout_seconds * 1000),
        )

    @pytest.mark.asyncio
    async def test_fetch_page_sync_increments_request_count(self):
        provider = _make_provider()
        provider._use_sync = True
        provider._request_count = 0

        mock_page = MagicMock()
        mock_page.goto = MagicMock(return_value=MagicMock(status=200))
        mock_page.content = MagicMock(return_value="<html></html>")
        mock_page.wait_for_selector = MagicMock()
        provider._sync_page = mock_page

        with patch("asyncio.to_thread", side_effect=_fake_to_thread):
            await provider._fetch_page("https://example.com")

        assert provider._request_count == 1

    @pytest.mark.asyncio
    async def test_fetch_page_sync_waits_for_price_selector(self):
        provider = _make_provider()
        provider._use_sync = True

        mock_page = MagicMock()
        mock_page.goto = MagicMock(return_value=MagicMock(status=200))
        mock_page.content = MagicMock(return_value="<html></html>")
        mock_page.wait_for_selector = MagicMock()
        provider._sync_page = mock_page

        with patch("asyncio.to_thread", side_effect=_fake_to_thread):
            await provider._fetch_page("https://example.com")

        mock_page.wait_for_selector.assert_called_once_with(
            '[class*="preco"], :text("R$")',
            timeout=8000,
        )

    @pytest.mark.asyncio
    async def test_fetch_page_sync_selector_timeout_falls_back(self):
        """When price selector times out, sync path waits 2s then returns content."""
        provider = _make_provider()
        provider._use_sync = True

        mock_page = MagicMock()
        mock_page.goto = MagicMock(return_value=MagicMock(status=200))
        mock_page.content = MagicMock(return_value="<html>fallback</html>")
        mock_page.wait_for_selector = MagicMock(side_effect=TimeoutError("timeout"))
        mock_page.wait_for_timeout = MagicMock()
        provider._sync_page = mock_page

        with patch("asyncio.to_thread", side_effect=_fake_to_thread):
            html = await provider._fetch_page("https://example.com")

        assert html == "<html>fallback</html>"
        mock_page.wait_for_timeout.assert_called_once_with(2000)


# ---------------------------------------------------------------------------
# close() cleans sync resources
# ---------------------------------------------------------------------------


class TestCloseWindowsCleansSyncResources:
    """close() should clean up sync Playwright resources on Windows."""

    @pytest.mark.asyncio
    async def test_close_windows_calls_browser_close_and_pw_stop(self):
        provider = _make_provider()
        provider._use_sync = True

        mock_browser = MagicMock()
        mock_pw = MagicMock()
        provider._sync_browser = mock_browser
        provider._sync_pw = mock_pw
        provider._sync_page = MagicMock()
        provider._sync_context = MagicMock()

        with patch("asyncio.to_thread", side_effect=_fake_to_thread):
            await provider.close()

        mock_browser.close.assert_called_once()
        mock_pw.stop.assert_called_once()

    @pytest.mark.asyncio
    async def test_close_windows_nulls_all_sync_references(self):
        provider = _make_provider()
        provider._use_sync = True
        provider._sync_pw = MagicMock()
        provider._sync_browser = MagicMock()
        provider._sync_context = MagicMock()
        provider._sync_page = MagicMock()

        with patch("asyncio.to_thread", side_effect=_fake_to_thread):
            await provider.close()

        assert provider._sync_pw is None
        assert provider._sync_browser is None
        assert provider._sync_context is None
        assert provider._sync_page is None

    @pytest.mark.asyncio
    async def test_close_windows_idempotent(self):
        """Calling close() twice should not raise."""
        provider = _make_provider()
        provider._use_sync = True
        provider._sync_browser = MagicMock()
        provider._sync_pw = MagicMock()
        provider._sync_page = MagicMock()
        provider._sync_context = MagicMock()

        with patch("asyncio.to_thread", side_effect=_fake_to_thread):
            await provider.close()
            await provider.close()  # should not raise

    @pytest.mark.asyncio
    async def test_close_windows_handles_browser_close_error(self):
        """close() should not raise even if browser.close() throws."""
        provider = _make_provider()
        provider._use_sync = True
        provider._sync_browser = MagicMock()
        provider._sync_browser.close = MagicMock(side_effect=Exception("crash"))
        provider._sync_pw = MagicMock()
        provider._sync_page = MagicMock()
        provider._sync_context = MagicMock()

        with patch("asyncio.to_thread", side_effect=_fake_to_thread):
            await provider.close()  # should not raise

        # Resources should still be cleaned up
        assert provider._sync_page is None


# ---------------------------------------------------------------------------
# search_card end-to-end on Windows
# ---------------------------------------------------------------------------


class TestSearchCardWindows:
    """End-to-end mock test of search_card through the Windows sync path."""

    @pytest.mark.asyncio
    async def test_search_card_returns_parsed_prices(self):
        provider = _make_provider()
        provider._use_sync = True
        provider._unavailable = False

        mock_prices = {
            "card_name": "Sol Ring",
            "normal": {
                "low": Decimal("3.50"),
                "mid": Decimal("5.00"),
                "high": Decimal("8.00"),
            },
            "foil": {"low": None, "mid": None, "high": None},
        }

        with patch.object(
            provider,
            "_fetch_page",
            new_callable=AsyncMock,
            return_value="<html>prices</html>",
        ):
            with patch(
                "src.providers.liga.provider.parse_card_prices",
                return_value=mock_prices,
            ):
                result = await provider.search_card("Sol Ring")

        assert result["card_name"] == "Sol Ring"
        assert result["normal"]["low"] == Decimal("3.50")

    @pytest.mark.asyncio
    async def test_search_card_windows_raises_liga_error(self):
        provider = _make_provider()
        provider._use_sync = True
        provider._unavailable = False

        with patch.object(
            provider,
            "_fetch_page",
            new_callable=AsyncMock,
            side_effect=LigaError("sync fetch failed", url="http://x"),
        ):
            with pytest.raises(LigaError, match="sync fetch failed"):
                await provider.search_card("Sol Ring")

    @pytest.mark.asyncio
    async def test_search_card_windows_empty_name(self):
        provider = _make_provider()
        provider._use_sync = True

        result = await provider.search_card("")
        assert result["normal"]["low"] is None


# ---------------------------------------------------------------------------
# Linux/macOS still uses async path
# ---------------------------------------------------------------------------


class TestOpenLinuxUsesAsyncPlaywright:
    """On non-Windows platforms, the async Playwright path should be used."""

    @pytest.mark.asyncio
    async def test_open_linux_does_not_set_use_sync(self):
        provider = _make_provider()
        async_pw_fn, mock_pw, mock_browser, mock_context, mock_page = _make_async_pw_mocks()

        with (
            patch("src.providers.liga.provider.sys") as mock_sys,
            patch(
                "playwright.async_api.async_playwright",
                async_pw_fn,
            ),
        ):
            mock_sys.platform = "linux"
            await provider.open()

        assert provider._use_sync is False
        assert provider._unavailable is False

    @pytest.mark.asyncio
    async def test_open_linux_stores_async_resources(self):
        provider = _make_provider()
        async_pw_fn, mock_pw, mock_browser, mock_context, mock_page = _make_async_pw_mocks()

        with (
            patch("src.providers.liga.provider.sys") as mock_sys,
            patch("playwright.async_api.async_playwright", async_pw_fn),
        ):
            mock_sys.platform = "linux"
            await provider.open()

        assert provider._playwright is not None
        assert provider._browser is not None
        assert provider._page is not None
        # Sync resources should remain None
        assert provider._sync_pw is None
        assert provider._sync_page is None

    @pytest.mark.asyncio
    async def test_open_darwin_uses_async_path(self):
        provider = _make_provider()
        async_pw_fn, mock_pw, mock_browser, mock_context, mock_page = _make_async_pw_mocks()

        with (
            patch("src.providers.liga.provider.sys") as mock_sys,
            patch("playwright.async_api.async_playwright", async_pw_fn),
        ):
            mock_sys.platform = "darwin"
            await provider.open()

        assert provider._use_sync is False


# ---------------------------------------------------------------------------
# _unavailable flag behavior
# ---------------------------------------------------------------------------


class TestUnavailableFlagNotSetOnWindows:
    """After F84-T01, _unavailable should NOT be set True on Windows."""

    @pytest.mark.asyncio
    async def test_unavailable_false_after_open_on_windows(self):
        provider = _make_provider()
        sync_pw_fn, *_ = _make_sync_pw_mocks()

        with (
            patch("src.providers.liga.provider.sys") as mock_sys,
            patch.dict(
                "sys.modules",
                {"playwright.sync_api": MagicMock(sync_playwright=sync_pw_fn)},
            ),
            patch("asyncio.to_thread", side_effect=_fake_to_thread),
        ):
            mock_sys.platform = "win32"
            await provider.open()

        assert (
            provider._unavailable is False
        ), "F84: Windows should use sync Playwright, NOT mark unavailable"

    @pytest.mark.asyncio
    async def test_ensure_page_returns_sync_page_on_windows(self):
        """_ensure_page should return _sync_page when _use_sync is True."""
        provider = _make_provider()
        provider._use_sync = True
        provider._unavailable = False

        mock_page = MagicMock()
        provider._sync_page = mock_page

        page = await provider._ensure_page()
        assert page is mock_page

    def test_unavailable_false_by_default(self):
        provider = _make_provider()
        assert provider._unavailable is False

    @pytest.mark.asyncio
    async def test_get_current_price_works_on_windows(self):
        """get_current_price should return a PriceSnapshot on Windows."""
        provider = _make_provider()
        provider._use_sync = True
        provider._unavailable = False

        mock_prices = {
            "card_name": "Lightning Bolt",
            "normal": {
                "low": Decimal("1.50"),
                "mid": Decimal("2.00"),
                "high": Decimal("3.00"),
            },
            "foil": {"low": None, "mid": None, "high": None},
        }

        with patch.object(
            provider,
            "_fetch_page",
            new_callable=AsyncMock,
            return_value="<html></html>",
        ):
            with patch(
                "src.providers.liga.provider.parse_card_prices",
                return_value=mock_prices,
            ):
                card = SourceCard(
                    source="liga",
                    external_id="42",
                    url="http://ligamagic/card",
                    identity=CardIdentity(game="magic", name_en="Lightning Bolt"),
                )
                result = await provider.get_current_price(card)

        assert result is not None
        assert isinstance(result, PriceSnapshot)
        assert result.avg_price == Decimal("1.50")
        assert result.source == "liga"
        assert result.currency == "BRL"
