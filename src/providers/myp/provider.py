"""MYP Cards provider implementation."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass

import structlog
from curl_cffi.requests import AsyncSession

from src.domain.interfaces import CardSourceProvider
from src.domain.models import (
    HistoricalPrice,
    PriceSnapshot,
    SourceCard,
)
from src.parsers.myp import (
    parse_card_links,
    parse_card_page,
    parse_pagination_max,
    parse_price_history,
    parse_price_snapshot,
    parse_set_links,
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
        """Fetch URL with rate limiting and retry."""
        session = await self._get_session()

        for attempt in range(1, self.config.max_retries + 1):
            await asyncio.sleep(self.config.delay_seconds)
            self._request_count += 1

            try:
                resp = await session.get(url)

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

                if resp.status_code >= 400:
                    log.warning(
                        "http_error",
                        url=url,
                        status=resp.status_code,
                        attempt=attempt,
                    )
                    if attempt == self.config.max_retries:
                        raise RuntimeError(
                            f"HTTP {resp.status_code} for {url}"
                        )
                    await asyncio.sleep(2**attempt)
                    continue

                return resp.text

            except (TimeoutError, OSError) as e:
                log.warning("request_error", url=url, attempt=attempt, error=str(e))
                if attempt == self.config.max_retries:
                    raise
                await asyncio.sleep(2**attempt)

        raise RuntimeError(f"Failed after {self.config.max_retries} attempts: {url}")

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

    async def get_price_history(
        self, card: SourceCard, days: int = 1095
    ) -> list[HistoricalPrice]:
        slug = card.url.rsplit("/", 1)[-1]
        url = f"{BASE_URL}/magic/preco/{card.external_id}/{slug}?dias={days}"
        html = await self._fetch(url)
        return parse_price_history(html, card.external_id)
