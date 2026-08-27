"""LigaMagic provider implementation.

Uses Playwright async API for browser automation since LigaMagic
requires JavaScript rendering and blocks direct HTTP requests with 403.
"""

from __future__ import annotations

import asyncio
import sys
from datetime import datetime
from urllib.parse import quote_plus

import structlog

from src.domain.interfaces import CardSourceProvider
from src.domain.models import HistoricalPrice, PriceSnapshot, SourceCard
from src.providers.liga.config import LigaConfig
from src.providers.liga.exceptions import (
    LigaError,
    LigaNotFoundError,
    LigaRateLimitError,
    LigaServerError,
)
from src.providers.liga.parser import parse_card_prices

log = structlog.get_logger()

BASE_URL = "https://www.ligamagic.com.br"

# Default browser user-agent to appear as a normal Chrome session
_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)


def _build_card_url(card_name: str) -> str:
    """Build a LigaMagic card search URL from a card name."""
    encoded = quote_plus(card_name.strip())
    return f"{BASE_URL}/?view=cards/card&card={encoded}&show=1"


class LigaMagicProvider(CardSourceProvider):
    """CardSourceProvider backed by LigaMagic via Playwright browser automation.

    Usage::

        config = LigaConfig(headless=True, delay_seconds=4.0)
        provider = LigaMagicProvider(config)
        await provider.open()
        try:
            snapshot = await provider.get_current_price(card)
        finally:
            await provider.close()

    Or as an async context manager::

        async with LigaMagicProvider(config) as provider:
            snapshot = await provider.get_current_price(card)
    """

    def __init__(self, config: LigaConfig | None = None) -> None:
        self.config = config or LigaConfig()
        self._playwright = None
        self._browser = None
        self._context = None
        self._page = None
        self._request_count = 0
        self._lock = asyncio.Lock()
        self._unavailable = False

    @property
    def source_name(self) -> str:
        return "liga"

    # --- Lifecycle management ---

    async def open(self) -> None:
        """Start the browser and create a reusable page.

        Imports playwright lazily so the module can be imported
        even when playwright is not installed (useful for tests
        that mock the browser layer).

        On Windows, Playwright's async API requires
        ``asyncio.create_subprocess_exec`` which is not supported
        by the default ``SelectorEventLoop``.  Rather than changing
        the global event-loop policy (which could break uvicorn),
        the provider marks itself as unavailable and returns early.
        """
        if self._page is not None:
            return  # Already open

        if sys.platform == "win32":
            self._unavailable = True
            log.info(
                "liga_provider_skipped",
                reason="Windows does not support async subprocesses for Playwright",
            )
            return

        from playwright.async_api import async_playwright

        self._playwright = await async_playwright().start()
        self._browser = await self._playwright.chromium.launch(
            headless=self.config.headless,
        )
        self._context = await self._browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent=_USER_AGENT,
            locale="pt-BR",
        )
        self._page = await self._context.new_page()
        log.info("liga_browser_opened", headless=self.config.headless)

    async def close(self) -> None:
        """Shut down the browser and release resources."""
        if self._unavailable:
            return
        if self._browser:
            await self._browser.close()
            self._browser = None
        if self._playwright:
            await self._playwright.stop()
            self._playwright = None
        self._context = None
        self._page = None
        log.info("liga_browser_closed", requests=self._request_count)

    async def __aenter__(self) -> LigaMagicProvider:
        await self.open()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        await self.close()

    # --- Internal helpers ---

    async def _ensure_page(self):
        """Ensure the browser page is available, opening if needed."""
        if self._unavailable:
            raise LigaError(
                "Liga provider is unavailable on this platform",
                url="",
                status_code=0,
                attempts=0,
            )
        if self._page is None:
            await self.open()
        return self._page

    async def _reset_browser(self) -> None:
        """Best-effort browser cleanup for recovery after crashes."""
        try:
            if self._browser:
                await self._browser.close()
        except Exception:
            pass
        try:
            if self._playwright:
                await self._playwright.stop()
        except Exception:
            pass
        self._browser = None
        self._context = None
        self._page = None
        self._playwright = None
        # Brief pause to let Playwright subprocess fully exit before re-open
        await asyncio.sleep(0.5)
        log.info("liga_browser_reset")

    async def _fetch_page(self, url: str) -> str:
        """Navigate to URL and return rendered HTML.

        Applies rate limiting, retries on failure, and raises typed
        exceptions based on HTTP status.
        """
        last_status = 0
        timeout_ms = int(self.config.timeout_seconds * 1000)

        for attempt in range(1, self.config.max_retries + 1):
            # Rate limit between requests (skip on first ever request)
            if self._request_count > 0:
                await asyncio.sleep(self.config.delay_seconds)
            self._request_count += 1

            try:
                page = await self._ensure_page()
                response = await page.goto(
                    url,
                    wait_until="networkidle",
                    timeout=timeout_ms,
                )
                last_status = response.status if response else 0

                # 404: permanent — raise immediately
                if last_status == 404:
                    raise LigaNotFoundError(
                        f"HTTP 404 for {url}",
                        url=url,
                        status_code=404,
                        attempts=attempt,
                    )

                # 429: rate limited — retry with backoff
                if last_status == 429:
                    wait = min(2**attempt * 5, 60)
                    log.warning(
                        "liga_rate_limited",
                        url=url,
                        attempt=attempt,
                        wait_seconds=wait,
                    )
                    await asyncio.sleep(wait)
                    continue

                # 403: blocked — retry with longer backoff
                if last_status == 403:
                    wait = min(2**attempt * 10, 120)
                    log.warning(
                        "liga_forbidden",
                        url=url,
                        attempt=attempt,
                        wait_seconds=wait,
                    )
                    await asyncio.sleep(wait)
                    continue

                # 5xx: server error — retry
                if last_status >= 500:
                    log.warning(
                        "liga_server_error",
                        url=url,
                        status=last_status,
                        attempt=attempt,
                    )
                    if attempt == self.config.max_retries:
                        raise LigaServerError(
                            f"HTTP {last_status} for {url}",
                            url=url,
                            status_code=last_status,
                            attempts=attempt,
                        )
                    await asyncio.sleep(2**attempt)
                    continue

                # Other 4xx: raise immediately
                if last_status >= 400:
                    raise LigaError(
                        f"HTTP {last_status} for {url}",
                        url=url,
                        status_code=last_status,
                        attempts=attempt,
                    )

                # Wait extra for JS rendering (LigaMagic is JS-heavy)
                await page.wait_for_timeout(2000)

                return await page.content()

            except LigaError:
                raise
            except Exception as e:
                log.warning(
                    "liga_request_error",
                    url=url,
                    attempt=attempt,
                    error=str(e) or "(no message)",
                    exc_type=type(e).__name__,
                )
                # Reset browser on non-timeout errors (likely dead browser/page)
                if not isinstance(e, TimeoutError):
                    await self._reset_browser()
                if attempt == self.config.max_retries:
                    etype = type(e).__name__
                    msg = (
                        f"Request failed ({etype}): {e}"
                        if str(e)
                        else f"Request failed ({etype}, no details) after {attempt} attempts: {url}"
                    )
                    raise LigaError(
                        msg,
                        url=url,
                        status_code=0,
                        attempts=attempt,
                    ) from e
                await asyncio.sleep(2**attempt)

        # Retries exhausted
        if last_status == 429:
            raise LigaRateLimitError(
                f"Rate limited after {self.config.max_retries} attempts: {url}",
                url=url,
                status_code=429,
                attempts=self.config.max_retries,
            )
        raise LigaError(
            f"Failed after {self.config.max_retries} attempts: {url}",
            url=url,
            status_code=last_status,
            attempts=self.config.max_retries,
        )

    # --- CardSourceProvider interface ---

    async def discover_sets(self) -> list[str]:
        """Return list of set identifiers available at LigaMagic.

        Not implemented yet — returns empty list.
        """
        return []

    async def discover_cards(self, set_id: str | None = None) -> list[SourceCard]:
        """Discover cards from LigaMagic.

        Not implemented yet — returns empty list.
        """
        return []

    async def get_current_price(self, card: SourceCard) -> PriceSnapshot | None:
        """Fetch current price for a card from LigaMagic.

        Navigates to the card page, extracts prices using the parser,
        and returns a PriceSnapshot domain object.
        """
        async with self._lock:
            return await self._get_current_price_unlocked(card)

    async def _get_current_price_unlocked(self, card: SourceCard) -> PriceSnapshot | None:
        card_name = ""
        if card.identity and card.identity.name_en:
            card_name = card.identity.name_en

        # Use card URL if available, otherwise build from name
        url = card.url if card.url else _build_card_url(card_name)

        try:
            html = await self._fetch_page(url)
        except LigaNotFoundError:
            log.warning("liga_card_not_found", card=card_name, url=url)
            return None
        except LigaError as e:
            log.warning(
                "liga_price_fetch_failed",
                card=card_name,
                url=url,
                error=str(e),
            )
            return None

        prices = parse_card_prices(html, card_name)
        min_price = prices["normal"]["low"]
        avg_price = prices["normal"]["mid"]

        # If we have no prices at all, return None
        if min_price is None and avg_price is None:
            # Check if there's a high price we can use
            high = prices["normal"]["high"]
            if high is None:
                log.info("liga_no_prices_found", card=card_name, url=url)
                return None
            avg_price = high

        return PriceSnapshot(
            source="liga",
            external_id=card.external_id,
            observed_at=datetime.now(),
            min_price=min_price,
            avg_price=avg_price,
            currency="BRL",
        )

    async def get_price_history(self, card: SourceCard, days: int = 1095) -> list[HistoricalPrice]:
        """Get historical price data from LigaMagic.

        LigaMagic does not expose public price history — always
        returns an empty list.
        """
        return []

    # --- Convenience methods (not in ABC) ---

    async def search_card(self, card_name: str) -> dict:
        """Search for a card by name and return parsed price data.

        Convenience method for direct card lookups by name.
        Returns the parsed price dict from parse_card_prices.
        """
        if not card_name or not card_name.strip():
            return parse_card_prices("", card_name)

        async with self._lock:
            return await self._search_card_unlocked(card_name)

    async def _search_card_unlocked(self, card_name: str) -> dict:
        url = _build_card_url(card_name)

        try:
            html = await self._fetch_page(url)
        except LigaError as e:
            log.warning(
                "liga_search_failed",
                card=card_name,
                error=str(e),
                exc_type=type(e).__name__,
            )
            return parse_card_prices("", card_name)
        except Exception as e:
            msg = (
                f"Unexpected {type(e).__name__}: {e}"
                if str(e)
                else f"Unexpected {type(e).__name__} (no message)"
            )
            log.warning(
                "liga_search_unexpected_error",
                card=card_name,
                error=repr(e),
                exc_type=type(e).__name__,
            )
            raise LigaError(msg, url=url) from e

        return parse_card_prices(html, card_name)
