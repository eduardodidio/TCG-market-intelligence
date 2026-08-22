"""MYP Cards provider implementation."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from urllib.parse import quote

import structlog
from curl_cffi.requests import AsyncSession

from src.domain.interfaces import CardSourceProvider
from src.domain.models import (
    HistoricalPrice,
    JsonLdPrice,
    MypSearchResult,
    PriceSnapshot,
    SourceCard,
)
from src.parsers.myp import (
    parse_card_links,
    parse_card_page,
    parse_jsonld_price,
    parse_pagination_max,
    parse_price_history,
    parse_price_snapshot,
    parse_search_results,
    parse_set_links,
)
from src.providers.myp.exceptions import (
    MypError,
    NotFoundError,
    RateLimitError,
    ServerError,
)

log = structlog.get_logger()

BASE_URL = "https://mypcards.com"


@dataclass
class MypConfig:
    delay_seconds: float = 1.0
    max_retries: int = 3
    timeout_seconds: float = 30.0
    history_days: int = 1095
    max_editions_pages: int = 50


class MypCardsProvider(CardSourceProvider):
    def __init__(self, config: MypConfig | None = None):
        self.config = config or MypConfig()
        self._session: AsyncSession | None = None
        self._request_count = 0

    @property
    def source_name(self) -> str:
        return "myp"

    async def _get_session(self) -> AsyncSession:
        if self._session is None:
            self._session = AsyncSession(
                impersonate="chrome",
                timeout=self.config.timeout_seconds,
            )
        return self._session

    async def close(self) -> None:
        if self._session:
            await self._session.close()
            self._session = None

    async def _fetch(self, url: str) -> str:
        """Fetch URL with rate limiting and retry.

        Raises typed exceptions based on the final HTTP status:
        - NotFoundError for 404 (immediate, no retry)
        - RateLimitError for 429 (after retries exhausted)
        - ServerError for 5xx (after retries exhausted)
        - MypError for 403 / other 4xx (after retries exhausted)
        """
        session = await self._get_session()
        last_status = 0

        for attempt in range(1, self.config.max_retries + 1):
            await asyncio.sleep(self.config.delay_seconds)
            self._request_count += 1

            try:
                resp = await session.get(url)
                last_status = resp.status_code

                # 404: permanent — raise immediately, no retry
                if resp.status_code == 404:
                    raise NotFoundError(
                        f"HTTP 404 for {url}",
                        url=url,
                        status_code=404,
                        attempts=attempt,
                    )

                # 429: transient — retry with backoff
                if resp.status_code == 429:
                    wait = min(2**attempt * 5, 60)
                    log.warning(
                        "rate_limited",
                        url=url,
                        attempt=attempt,
                        wait_seconds=wait,
                    )
                    await asyncio.sleep(wait)
                    continue

                # 403: Cloudflare — retry with longer backoff
                if resp.status_code == 403:
                    wait = min(2**attempt * 10, 120)
                    log.warning(
                        "forbidden_retrying",
                        url=url,
                        attempt=attempt,
                        wait_seconds=wait,
                    )
                    await asyncio.sleep(wait)
                    continue

                # 5xx: server error — retry with backoff
                if resp.status_code >= 500:
                    log.warning(
                        "server_error",
                        url=url,
                        status=resp.status_code,
                        attempt=attempt,
                    )
                    if attempt == self.config.max_retries:
                        raise ServerError(
                            f"HTTP {resp.status_code} for {url}",
                            url=url,
                            status_code=resp.status_code,
                            attempts=attempt,
                        )
                    await asyncio.sleep(2**attempt)
                    continue

                # Other 4xx: raise immediately
                if resp.status_code >= 400:
                    raise MypError(
                        f"HTTP {resp.status_code} for {url}",
                        url=url,
                        status_code=resp.status_code,
                        attempts=attempt,
                    )

                return resp.content.decode("utf-8")

            except (TimeoutError, OSError) as e:
                log.warning("request_error", url=url, attempt=attempt, error=str(e))
                if attempt == self.config.max_retries:
                    raise
                await asyncio.sleep(2**attempt)

        # Retries exhausted — select typed exception based on last status
        if last_status == 429:
            raise RateLimitError(
                f"Rate limited after {self.config.max_retries} attempts: {url}",
                url=url,
                status_code=429,
                attempts=self.config.max_retries,
            )
        if last_status == 403:
            raise MypError(
                f"Forbidden after {self.config.max_retries} attempts: {url}",
                url=url,
                status_code=403,
                attempts=self.config.max_retries,
            )
        raise MypError(
            f"Failed after {self.config.max_retries} attempts: {url}",
            url=url,
            status_code=last_status,
            attempts=self.config.max_retries,
        )

    async def search_card(self, term: str) -> list[MypSearchResult]:
        """Search MYP for cards matching *term*.

        Uses the ``/produto/search`` endpoint with ``marca=magic``.
        Returns an empty list when *term* is blank, the API returns no
        results, or the response cannot be parsed.
        """
        if not term or not term.strip():
            return []

        encoded_term = quote(term.strip())
        url = f"{BASE_URL}/produto/search?marca=magic&term={encoded_term}"

        try:
            raw = await self._fetch(url)
        except (NotFoundError, RateLimitError):
            raise
        except (MypError, RuntimeError, TimeoutError, OSError):
            log.warning("search_card_fetch_failed", term=term)
            return []

        return parse_search_results(raw)

    async def discover_sets(self) -> list[str]:
        """Discover all Magic set slugs from the editions pages."""
        all_slugs: set[str] = set()

        url = f"{BASE_URL}/magic/edicoes"
        html = await self._fetch(url)
        slugs = parse_set_links(html)
        all_slugs.update(slugs)
        max_page = parse_pagination_max(html)
        max_page = min(max_page, self.config.max_editions_pages)

        log.info("discovering_sets", page=1, found=len(slugs), max_page=max_page)

        for page in range(2, max_page + 1):
            html = await self._fetch(f"{url}?page={page}")
            slugs = parse_set_links(html)
            all_slugs.update(slugs)
            log.info("discovering_sets", page=page, found=len(slugs), total=len(all_slugs))

        return sorted(all_slugs)

    async def discover_cards(self, set_id: str | None = None) -> list[SourceCard]:
        """Discover cards from a set page (or all sets if None)."""
        if set_id:
            return await self._discover_cards_in_set(set_id)

        sets = await self.discover_sets()
        all_cards: list[SourceCard] = []
        for s in sets:
            cards = await self._discover_cards_in_set(s)
            all_cards.extend(cards)
            log.info("set_discovered", set=s, cards=len(cards), total=len(all_cards))

        return all_cards

    async def _discover_cards_in_set(self, set_slug: str) -> list[SourceCard]:
        """Discover all cards in a specific set."""
        url = f"{BASE_URL}/magic/{set_slug}"
        html = await self._fetch(url)
        card_tuples = parse_card_links(html)
        max_page = parse_pagination_max(html)

        for page in range(2, max_page + 1):
            html = await self._fetch(f"{url}?page={page}")
            card_tuples.extend(parse_card_links(html))

        # Deduplicate
        seen = set()
        cards = []
        for card_id, slug in card_tuples:
            if card_id not in seen:
                seen.add(card_id)
                cards.append(
                    SourceCard(
                        source="myp",
                        external_id=card_id,
                        url=f"{BASE_URL}/magic/produto/{card_id}/{slug}",
                    )
                )

        return cards

    async def get_card_details(self, card: SourceCard) -> SourceCard | None:
        """Fetch full card details from its product page."""
        html = await self._fetch(card.url)
        slug = card.url.rsplit("/", 1)[-1]
        return parse_card_page(html, card.external_id, slug)

    async def get_current_price(self, card: SourceCard) -> PriceSnapshot | None:
        html = await self._fetch(card.url)
        return parse_price_snapshot(html, card.external_id)

    async def fetch_current_price(self, product_id: str, slug: str) -> JsonLdPrice | None:
        """Fetch product page and extract current price from JSON-LD.

        Args:
            product_id: MYP product ID (e.g., "179334").
            slug: URL slug (e.g., "tutor-esclarecido").

        Returns:
            JsonLdPrice with current price data, or None on fetch failure.
        """
        url = f"{BASE_URL}/magic/produto/{product_id}/{slug}"
        try:
            html = await self._fetch(url)
        except (NotFoundError, RateLimitError):
            raise
        except (MypError, RuntimeError, TimeoutError, OSError):
            log.warning(
                "fetch_current_price_failed",
                product_id=product_id,
                slug=slug,
            )
            return None
        return parse_jsonld_price(html)

    async def get_price_history(self, card: SourceCard, days: int = 1095) -> list[HistoricalPrice]:
        slug = card.url.rsplit("/", 1)[-1]
        url = f"{BASE_URL}/magic/preco/{card.external_id}/{slug}?dias={days}"
        html = await self._fetch(url)
        return parse_price_history(html, card.external_id)
