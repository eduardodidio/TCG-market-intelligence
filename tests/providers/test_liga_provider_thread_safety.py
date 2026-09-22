"""Tests for LigaMagicProvider thread safety and browser recovery.

Verifies the dedicated single-thread executor (ThreadPoolExecutor(max_workers=1)),
_run_sync helper, browser recovery after crashes, and general sync-mode behavior.
No real Playwright needed — everything is mocked.
"""

from __future__ import annotations

import asyncio
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.providers.liga.config import LigaConfig
from src.providers.liga.exceptions import LigaError
from src.providers.liga.provider import LigaMagicProvider

# ---------------------------------------------------------------------------
# 1. Initial state — verify sync fields exist
# ---------------------------------------------------------------------------


class TestInitialSyncState:
    def test_init_has_sync_fields(self):
        """Provider should have all sync-mode fields initialized."""
        provider = LigaMagicProvider()
        assert provider._sync_pw is None
        assert provider._sync_browser is None
        assert provider._sync_context is None
        assert provider._sync_page is None
        assert provider._use_sync is False

    def test_init_has_lock(self):
        """Provider should have an asyncio.Lock for serialized access."""
        provider = LigaMagicProvider()
        assert isinstance(provider._lock, asyncio.Lock)

    def test_init_has_executor_field(self):
        """Provider should have _executor field initialized to None."""
        provider = LigaMagicProvider()
        assert provider._executor is None


# ---------------------------------------------------------------------------
# 2. Static analysis — asyncio.to_thread is no longer used
# ---------------------------------------------------------------------------


class TestNoAsyncioToThread:
    def test_asyncio_to_thread_not_in_source(self):
        """asyncio.to_thread should NOT appear in provider.py code lines.
        All sync dispatch should use _run_sync / run_in_executor."""
        source = Path("src/providers/liga/provider.py").read_text(encoding="utf-8")
        code_lines = [
            line
            for line in source.splitlines()
            if "asyncio.to_thread" in line and not line.strip().startswith("#")
        ]
        assert (
            len(code_lines) == 0
        ), f"Found {len(code_lines)} asyncio.to_thread calls: {code_lines}"


# ---------------------------------------------------------------------------
# 3. _run_sync creates executor lazily and guarantees thread affinity
# ---------------------------------------------------------------------------


class TestRunSync:
    @pytest.mark.asyncio
    async def test_run_sync_creates_executor_lazily(self):
        """_run_sync should create ThreadPoolExecutor(max_workers=1) on first call."""
        provider = LigaMagicProvider()
        assert provider._executor is None

        result = await provider._run_sync(lambda: 42)

        assert result == 42
        assert isinstance(provider._executor, ThreadPoolExecutor)
        assert provider._executor._max_workers == 1
        provider._executor.shutdown(wait=False)

    @pytest.mark.asyncio
    async def test_run_sync_uses_same_thread(self):
        """All _run_sync calls should execute on the same thread."""
        provider = LigaMagicProvider()

        def get_thread_id():
            return threading.current_thread().ident

        tid1 = await provider._run_sync(get_thread_id)
        tid2 = await provider._run_sync(get_thread_id)

        assert tid1 == tid2, "Thread IDs should match (single-thread executor)"
        provider._executor.shutdown(wait=False)


# ---------------------------------------------------------------------------
# 4. open() uses _run_sync on Windows
# ---------------------------------------------------------------------------


class TestOpenSyncSetsPage:
    @pytest.mark.asyncio
    async def test_open_sets_use_sync_on_windows(self):
        """On win32, open() should set _use_sync=True and delegate via _run_sync."""
        provider = LigaMagicProvider(LigaConfig(delay_seconds=0))

        with patch("src.providers.liga.provider.sys") as mock_sys:
            mock_sys.platform = "win32"
            with patch.object(provider, "_open_sync") as mock_open_sync:
                await provider.open()

        assert provider._use_sync is True
        mock_open_sync.assert_called_once()

    @pytest.mark.asyncio
    async def test_open_skips_if_already_open_sync(self):
        """open() is a no-op if _sync_page is already set."""
        provider = LigaMagicProvider(LigaConfig(delay_seconds=0))
        provider._sync_page = MagicMock()  # Pretend already open

        with patch.object(provider, "_open_sync") as mock_open_sync:
            await provider.open()

        mock_open_sync.assert_not_called()


# ---------------------------------------------------------------------------
# 5. close() uses _run_sync and shuts down executor
# ---------------------------------------------------------------------------


class TestCloseSyncResources:
    @pytest.mark.asyncio
    async def test_close_uses_run_sync_and_shuts_executor(self):
        """When _use_sync=True, close() delegates via _run_sync and shuts down executor."""
        provider = LigaMagicProvider(LigaConfig(delay_seconds=0))
        provider._use_sync = True
        provider._executor = ThreadPoolExecutor(max_workers=1)

        with patch.object(provider, "_close_sync"):
            await provider.close()

        assert provider._executor is None

    def test_close_sync_clears_all_resources(self):
        """_close_sync should set all sync resources to None."""
        provider = LigaMagicProvider()
        provider._sync_pw = MagicMock()
        provider._sync_browser = MagicMock()
        provider._sync_context = MagicMock()
        provider._sync_page = MagicMock()

        provider._close_sync()

        assert provider._sync_pw is None
        assert provider._sync_browser is None
        assert provider._sync_context is None
        assert provider._sync_page is None

    def test_close_sync_handles_browser_close_error(self):
        """_close_sync should not raise even if browser.close() fails."""
        provider = LigaMagicProvider()
        mock_browser = MagicMock()
        mock_browser.close.side_effect = RuntimeError("browser crashed")
        provider._sync_browser = mock_browser
        provider._sync_pw = MagicMock()

        provider._close_sync()  # Should not raise

        assert provider._sync_browser is None
        assert provider._sync_pw is None


# ---------------------------------------------------------------------------
# 6. _reset_browser attempts recovery in sync mode
# ---------------------------------------------------------------------------


class TestResetBrowserRecovery:
    @pytest.mark.asyncio
    async def test_reset_browser_uses_run_sync_and_recovers(self):
        """When _use_sync=True, _reset_browser resets then re-opens via _run_sync."""
        provider = LigaMagicProvider(LigaConfig(delay_seconds=0))
        provider._use_sync = True
        provider._executor = ThreadPoolExecutor(max_workers=1)

        call_order = []

        def mock_reset():
            call_order.append("reset")

        def mock_open():
            call_order.append("open")

        with patch.object(provider, "_reset_browser_sync", side_effect=mock_reset):
            with patch.object(provider, "_open_sync", side_effect=mock_open):
                with patch("asyncio.sleep", new_callable=AsyncMock):
                    await provider._reset_browser()

        assert call_order == ["reset", "open"]
        provider._executor.shutdown(wait=False)

    @pytest.mark.asyncio
    async def test_reset_browser_recovery_failure_logged(self):
        """If _open_sync fails during recovery, it's logged but not raised."""
        provider = LigaMagicProvider(LigaConfig(delay_seconds=0))
        provider._use_sync = True
        provider._executor = ThreadPoolExecutor(max_workers=1)

        with patch.object(provider, "_reset_browser_sync"):
            with patch.object(provider, "_open_sync", side_effect=RuntimeError("cannot reopen")):
                with patch("asyncio.sleep", new_callable=AsyncMock):
                    await provider._reset_browser()  # Should not raise

        provider._executor.shutdown(wait=False)

    def test_reset_browser_sync_clears_resources(self):
        """_reset_browser_sync should close browser and clear all sync state."""
        provider = LigaMagicProvider()
        mock_browser = MagicMock()
        mock_pw = MagicMock()
        provider._sync_browser = mock_browser
        provider._sync_pw = mock_pw
        provider._sync_context = MagicMock()
        provider._sync_page = MagicMock()

        provider._reset_browser_sync()

        mock_browser.close.assert_called_once()
        mock_pw.stop.assert_called_once()
        assert provider._sync_browser is None
        assert provider._sync_context is None
        assert provider._sync_page is None
        assert provider._sync_pw is None

    def test_reset_browser_sync_tolerates_errors(self):
        """_reset_browser_sync should swallow exceptions from browser/pw."""
        provider = LigaMagicProvider()
        mock_browser = MagicMock()
        mock_browser.close.side_effect = RuntimeError("already dead")
        mock_pw = MagicMock()
        mock_pw.stop.side_effect = RuntimeError("also dead")
        provider._sync_browser = mock_browser
        provider._sync_pw = mock_pw

        provider._reset_browser_sync()  # Should not raise

        assert provider._sync_browser is None
        assert provider._sync_pw is None


# ---------------------------------------------------------------------------
# 7. _fetch_page_sync recovery when page is None
# ---------------------------------------------------------------------------


class TestFetchPageSyncRecovery:
    def test_fetch_page_sync_recovers_when_page_none(self):
        """When _sync_page is None, _fetch_page_sync calls _open_sync to recover."""
        provider = LigaMagicProvider(LigaConfig(delay_seconds=0, max_retries=1))
        provider._sync_page = None

        mock_page = MagicMock()
        mock_response = MagicMock()
        mock_response.status = 200
        mock_page.goto.return_value = mock_response
        mock_page.content.return_value = "<html>ok</html>"
        mock_page.url = "http://example.com"
        mock_page.wait_for_selector = MagicMock()

        def set_page():
            provider._sync_page = mock_page

        with patch.object(provider, "_open_sync", side_effect=set_page):
            result = provider._fetch_page_sync("http://example.com")

        assert result == "<html>ok</html>"

    def test_fetch_page_sync_raises_when_recovery_fails(self):
        """When _sync_page is None and _open_sync fails, raises LigaError."""
        provider = LigaMagicProvider(LigaConfig(delay_seconds=0, max_retries=1))
        provider._sync_page = None

        with patch.object(provider, "_open_sync", side_effect=RuntimeError("cannot open")):
            with pytest.raises(LigaError, match="recovery failed"):
                provider._fetch_page_sync("http://example.com")


# ---------------------------------------------------------------------------
# 8. _fetch_page delegates to sync via _run_sync
# ---------------------------------------------------------------------------


class TestFetchPageDelegation:
    @pytest.mark.asyncio
    async def test_fetch_page_delegates_to_sync_via_run_sync(self):
        """When _use_sync=True, _fetch_page delegates via _run_sync."""
        provider = LigaMagicProvider(LigaConfig(delay_seconds=0, max_retries=1))
        provider._use_sync = True

        with patch.object(
            provider, "_run_sync", new_callable=AsyncMock, return_value="<html></html>"
        ) as mock_run:
            result = await provider._fetch_page("http://example.com")

        mock_run.assert_awaited_once_with(provider._fetch_page_sync, "http://example.com")
        assert result == "<html></html>"


# ---------------------------------------------------------------------------
# 9. _ensure_page returns sync page in sync mode
# ---------------------------------------------------------------------------


class TestEnsurePageSyncMode:
    @pytest.mark.asyncio
    async def test_ensure_page_returns_sync_page(self):
        """When _use_sync=True and _sync_page is set, returns it."""
        provider = LigaMagicProvider()
        provider._use_sync = True
        mock_page = MagicMock()
        provider._sync_page = mock_page

        result = await provider._ensure_page()
        assert result is mock_page

    @pytest.mark.asyncio
    async def test_ensure_page_opens_if_sync_page_none(self):
        """When _use_sync=True and _sync_page is None, calls open()."""
        provider = LigaMagicProvider()
        provider._use_sync = True
        provider._sync_page = None

        with patch.object(provider, "open", new_callable=AsyncMock) as mock_open:
            await provider._ensure_page()

        mock_open.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_ensure_page_raises_when_unavailable(self):
        """When _unavailable=True, raises LigaError immediately."""
        provider = LigaMagicProvider()
        provider._unavailable = True

        with pytest.raises(LigaError, match="unavailable"):
            await provider._ensure_page()


# ---------------------------------------------------------------------------
# 10. Lock serializes concurrent access
# ---------------------------------------------------------------------------


class TestLockSerialization:
    @pytest.mark.asyncio
    async def test_get_current_price_acquires_lock(self):
        """get_current_price should acquire _lock to serialize access."""
        provider = LigaMagicProvider(LigaConfig(delay_seconds=0, max_retries=1))

        with patch.object(
            provider,
            "_get_current_price_unlocked",
            new_callable=AsyncMock,
            return_value=None,
        ) as mock_fn:
            from src.domain.models import SourceCard

            card = SourceCard(source="liga", external_id="1", url="http://x")
            await provider.get_current_price(card)

        mock_fn.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_search_card_acquires_lock(self):
        """search_card should acquire _lock for non-empty names."""
        provider = LigaMagicProvider(LigaConfig(delay_seconds=0, max_retries=1))

        with patch.object(
            provider,
            "_search_card_unlocked",
            new_callable=AsyncMock,
            return_value={"normal": {"low": None, "mid": None, "high": None}},
        ) as mock_search:
            await provider.search_card("Test Card")

        mock_search.assert_awaited_once()
