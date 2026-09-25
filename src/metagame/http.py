"""Polite HTTP layer for metagame sources (F173-T04).

Every external metagame request goes through :class:`PoliteFetcher`, which:

- checks ``robots.txt`` per host before fetching (disallowed → ``RobotsDisallowed``);
- keeps a minimum interval between requests to the same host (or the
  ``Crawl-delay`` from robots.txt when it is larger);
- caches bodies on disk (``<sha256(url)>.body`` + ``.meta.json``) with a TTL;
- retries 429/5xx/timeouts up to 3 attempts with exponential backoff,
  honoring ``Retry-After``.

Policy values (UA, interval, TTLs) come from ADR 0016.
"""

from __future__ import annotations

import hashlib
import json
import time
from collections.abc import Callable
from pathlib import Path
from urllib.parse import urlsplit
from urllib.robotparser import RobotFileParser

import httpx
import structlog
from tenacity import (
    RetryCallState,
    Retrying,
    retry_if_exception_type,
    stop_after_attempt,
)

log = structlog.get_logger()

DEFAULT_USER_AGENT = (
    "TEDHC-Market/1.0 (+https://github.com/eduardodidio/TCG-market-intelligence)"
)
DEFAULT_CACHE_DIR = Path("data/cache/metagame")
MAX_ATTEMPTS = 3
BACKOFF_BASE_S = 1.0
MAX_RETRY_AFTER_S = 300.0


class RobotsDisallowed(Exception):
    """The URL is disallowed by the host's robots.txt (or robots is unreachable)."""


class FetchError(Exception):
    """The URL could not be fetched (HTTP error, network error, invalid body)."""


class _RetryableError(Exception):
    """Internal: a 429/5xx/timeout that tenacity should retry."""

    def __init__(self, message: str, retry_after: float | None = None) -> None:
        super().__init__(message)
        self.retry_after = retry_after


def _parse_retry_after(value: str | None) -> float | None:
    if not value:
        return None
    try:
        seconds = float(value.strip())
    except ValueError:
        return None  # HTTP-date form is not supported; fall back to backoff
    if seconds < 0:
        return None
    return min(seconds, MAX_RETRY_AFTER_S)


def _wait(state: RetryCallState) -> float:
    exc = state.outcome.exception() if state.outcome else None
    if isinstance(exc, _RetryableError) and exc.retry_after is not None:
        return exc.retry_after
    return BACKOFF_BASE_S * (2 ** (state.attempt_number - 1))


class PoliteFetcher:
    def __init__(
        self,
        *,
        cache_dir: Path = DEFAULT_CACHE_DIR,
        ttl_hours: float = 24,
        min_interval_s: float = 3.0,
        user_agent: str = DEFAULT_USER_AGENT,
        client: httpx.Client | None = None,
        clock: Callable[[], float] = time.monotonic,
        sleep: Callable[[float], None] = time.sleep,
        wall_clock: Callable[[], float] = time.time,
    ) -> None:
        self.cache_dir = Path(cache_dir)
        self.ttl_hours = ttl_hours
        self.min_interval_s = min_interval_s
        self.user_agent = user_agent
        self._client = client or httpx.Client(timeout=30.0, follow_redirects=True)
        self._clock = clock
        self._sleep = sleep
        self._wall_clock = wall_clock
        self._robots: dict[str, RobotFileParser] = {}
        self._last_request: dict[str, float] = {}

    # ── public API ──────────────────────────────────────────────────────────

    def get_text(
        self, url: str, *, ttl_hours: float | None = None, use_cache: bool = True
    ) -> str:
        """Fetch ``url`` as text. ``use_cache=False`` skips the read but still writes."""
        ttl = self.ttl_hours if ttl_hours is None else ttl_hours
        if use_cache:
            cached = self._read_cache(url, ttl)
            if cached is not None:
                log.debug("metagame_fetch_cache_hit", url=url)
                return cached

        self._check_robots(url)
        text = self._fetch_with_retry(url)
        self._write_cache(url, text)
        return text

    def get_json(
        self, url: str, *, ttl_hours: float | None = None, use_cache: bool = True
    ) -> dict | list:
        text = self.get_text(url, ttl_hours=ttl_hours, use_cache=use_cache)
        try:
            data = json.loads(text)
        except json.JSONDecodeError as exc:
            raise FetchError(f"invalid JSON from {url}: {exc}") from exc
        if not isinstance(data, (dict, list)):
            raise FetchError(f"unexpected JSON type from {url}: {type(data).__name__}")
        return data

    def close(self) -> None:
        self._client.close()

    # ── robots.txt ──────────────────────────────────────────────────────────

    def _robots_for(self, url: str) -> RobotFileParser:
        parts = urlsplit(url)
        origin = f"{parts.scheme}://{parts.netloc}"
        parser = self._robots.get(origin)
        if parser is not None:
            return parser

        parser = RobotFileParser()
        robots_url = f"{origin}/robots.txt"
        parser.set_url(robots_url)
        self._throttle(parts.netloc, self.min_interval_s)
        try:
            resp = self._client.get(robots_url, headers=self._headers())
        except httpx.HTTPError as exc:
            log.warning("metagame_robots_unreachable", url=robots_url, error=str(exc))
            parser.disallow_all = True
        else:
            if resp.status_code in (401, 403):
                parser.disallow_all = True
            elif 400 <= resp.status_code < 500:
                parser.allow_all = True
            elif resp.status_code >= 500:
                log.warning(
                    "metagame_robots_unreachable",
                    url=robots_url,
                    status=resp.status_code,
                )
                parser.disallow_all = True
            else:
                parser.parse(resp.text.splitlines())
        parser.modified()
        self._robots[origin] = parser
        return parser

    def _check_robots(self, url: str) -> None:
        parser = self._robots_for(url)
        if not parser.can_fetch(self.user_agent, url):
            log.warning("metagame_robots_disallowed", url=url)
            raise RobotsDisallowed(url)

    def _interval_for(self, url: str) -> float:
        parser = self._robots_for(url)
        delay = parser.crawl_delay(self.user_agent)
        try:
            delay_s = float(delay) if delay is not None else 0.0
        except (TypeError, ValueError):
            delay_s = 0.0
        return max(self.min_interval_s, delay_s)

    # ── rate limit ──────────────────────────────────────────────────────────

    def _throttle(self, host: str, interval: float) -> None:
        last = self._last_request.get(host)
        if last is not None:
            wait = interval - (self._clock() - last)
            if wait > 0:
                self._sleep(wait)
        self._last_request[host] = self._clock()

    # ── fetching ────────────────────────────────────────────────────────────

    def _headers(self) -> dict[str, str]:
        return {"User-Agent": self.user_agent}

    def _fetch_once(self, url: str) -> str:
        self._throttle(urlsplit(url).netloc, self._interval_for(url))
        try:
            resp = self._client.get(url, headers=self._headers())
        except httpx.TimeoutException as exc:
            raise _RetryableError(f"timeout fetching {url}: {exc}") from exc
        except httpx.HTTPError as exc:
            raise FetchError(f"network error fetching {url}: {exc}") from exc

        status = resp.status_code
        if status == 429 or status >= 500:
            raise _RetryableError(
                f"HTTP {status} from {url}",
                retry_after=_parse_retry_after(resp.headers.get("Retry-After")),
            )
        if status >= 400:
            raise FetchError(f"HTTP {status} from {url}")
        return resp.text

    def _fetch_with_retry(self, url: str) -> str:
        retrying = Retrying(
            stop=stop_after_attempt(MAX_ATTEMPTS),
            wait=_wait,
            retry=retry_if_exception_type(_RetryableError),
            sleep=self._sleep,
            reraise=True,
        )
        try:
            return retrying(self._fetch_once, url)
        except _RetryableError as exc:
            log.warning("metagame_fetch_failed", url=url, error=str(exc))
            raise FetchError(f"{exc} (after {MAX_ATTEMPTS} attempts)") from exc

    # ── disk cache ──────────────────────────────────────────────────────────

    def _cache_paths(self, url: str) -> tuple[Path, Path]:
        key = hashlib.sha256(url.encode("utf-8")).hexdigest()
        return self.cache_dir / f"{key}.body", self.cache_dir / f"{key}.meta.json"

    def _read_cache(self, url: str, ttl_hours: float) -> str | None:
        if ttl_hours <= 0:
            return None
        body_path, meta_path = self._cache_paths(url)
        try:
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
            fetched_at = float(meta["fetched_at"])
            if meta.get("url") != url:
                return None
            if self._wall_clock() - fetched_at >= ttl_hours * 3600:
                return None
            return body_path.read_text(encoding="utf-8")
        except (OSError, ValueError, KeyError, TypeError):
            return None

    def _write_cache(self, url: str, text: str) -> None:
        body_path, meta_path = self._cache_paths(url)
        try:
            self.cache_dir.mkdir(parents=True, exist_ok=True)
            body_path.write_text(text, encoding="utf-8")
            meta_path.write_text(
                json.dumps(
                    {"url": url, "fetched_at": self._wall_clock(), "status": 200}
                ),
                encoding="utf-8",
            )
        except OSError as exc:
            log.warning("metagame_cache_write_failed", url=url, error=str(exc))
