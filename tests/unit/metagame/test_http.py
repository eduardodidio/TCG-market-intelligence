"""Tests for PoliteFetcher and the MetaSource contract (F173-T04). No real network."""

from __future__ import annotations

import json
from collections.abc import Callable

import httpx
import pytest

from src.metagame import http as http_mod
from src.metagame.http import (
    DEFAULT_USER_AGENT,
    FetchError,
    PoliteFetcher,
    RobotsDisallowed,
    _parse_retry_after,
)
from src.metagame.sources import SOURCE_FOR_FORMAT, get_sources
from src.metagame.sources.base import (
    FORMATS,
    MetaCardEntry,
    MetaDeckEntry,
    MetaSource,
    normalize_colors,
)


class FakeTime:
    """Monotonic + wall clock where sleep() advances time and records durations."""

    def __init__(self, start: float = 1000.0) -> None:
        self.now = start
        self.sleeps: list[float] = []

    def clock(self) -> float:
        return self.now

    def sleep(self, seconds: float) -> None:
        self.sleeps.append(seconds)
        self.now += seconds


class Recorder:
    def __init__(self, handler: Callable[[httpx.Request], httpx.Response]) -> None:
        self.handler = handler
        self.requests: list[httpx.Request] = []

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        return self.handler(request)

    def paths(self) -> list[str]:
        return [r.url.path for r in self.requests]

    def count(self, path: str) -> int:
        return self.paths().count(path)


def make(
    tmp_path, handler, *, ft: FakeTime | None = None, **kwargs
) -> tuple[PoliteFetcher, Recorder, FakeTime]:
    ft = ft or FakeTime()
    rec = Recorder(handler)
    fetcher = PoliteFetcher(
        cache_dir=tmp_path / "cache",
        client=httpx.Client(transport=httpx.MockTransport(rec)),
        clock=ft.clock,
        sleep=ft.sleep,
        wall_clock=ft.clock,
        **kwargs,
    )
    return fetcher, rec, ft


def site(
    pages: dict[str, httpx.Response | Callable[[], httpx.Response]],
    robots: str | httpx.Response = "User-agent: *\nDisallow: /private\n",
):
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/robots.txt":
            if isinstance(robots, httpx.Response):
                return robots
            return httpx.Response(200, text=robots)
        page = pages.get(request.url.path)
        if page is None:
            return httpx.Response(404, text="not found")
        return page() if callable(page) else page

    return handler


# ── happy path / cache ──────────────────────────────────────────────────────


def test_get_text_then_cache_hit(tmp_path):
    fetcher, rec, _ = make(tmp_path, site({"/a": httpx.Response(200, text="hello")}))
    assert fetcher.get_text("https://ex.com/a") == "hello"
    assert fetcher.get_text("https://ex.com/a") == "hello"
    assert rec.count("/a") == 1
    assert rec.count("/robots.txt") == 1
    files = sorted(p.name for p in (tmp_path / "cache").iterdir())
    assert len(files) == 2
    assert any(f.endswith(".body") for f in files)
    meta_file = next((tmp_path / "cache").glob("*.meta.json"))
    meta = json.loads(meta_file.read_text())
    assert meta["url"] == "https://ex.com/a"
    assert meta["status"] == 200


def test_user_agent_header_sent(tmp_path):
    fetcher, rec, _ = make(tmp_path, site({"/a": httpx.Response(200, text="x")}))
    fetcher.get_text("https://ex.com/a")
    assert all(r.headers["User-Agent"] == DEFAULT_USER_AGENT for r in rec.requests)


def test_custom_user_agent(tmp_path):
    fetcher, rec, _ = make(
        tmp_path, site({"/a": httpx.Response(200, text="x")}), user_agent="Bot/2"
    )
    fetcher.get_text("https://ex.com/a")
    assert rec.requests[-1].headers["User-Agent"] == "Bot/2"


def test_cache_expired_refetches_at_exact_ttl(tmp_path):
    fetcher, rec, ft = make(tmp_path, site({"/a": httpx.Response(200, text="x")}))
    fetcher.get_text("https://ex.com/a", ttl_hours=1)
    ft.now += 3600 - 0.001
    fetcher.get_text("https://ex.com/a", ttl_hours=1)
    assert rec.count("/a") == 1
    ft.now += 0.001  # exactly 1h since fetch → expired
    fetcher.get_text("https://ex.com/a", ttl_hours=1)
    assert rec.count("/a") == 2


def test_ttl_zero_always_refetches(tmp_path):
    fetcher, rec, _ = make(tmp_path, site({"/a": httpx.Response(200, text="x")}))
    for _ in range(3):
        fetcher.get_text("https://ex.com/a", ttl_hours=0)
    assert rec.count("/a") == 3


def test_default_ttl_from_constructor(tmp_path):
    fetcher, rec, ft = make(
        tmp_path, site({"/a": httpx.Response(200, text="x")}), ttl_hours=2
    )
    fetcher.get_text("https://ex.com/a")
    ft.now += 3600
    fetcher.get_text("https://ex.com/a")
    assert rec.count("/a") == 1
    ft.now += 3600
    fetcher.get_text("https://ex.com/a")
    assert rec.count("/a") == 2


def test_use_cache_false_skips_read_but_writes(tmp_path):
    body = iter(["v1", "v2"])
    fetcher, rec, _ = make(
        tmp_path, site({"/a": lambda: httpx.Response(200, text=next(body))})
    )
    assert fetcher.get_text("https://ex.com/a") == "v1"
    assert fetcher.get_text("https://ex.com/a", use_cache=False) == "v2"
    assert fetcher.get_text("https://ex.com/a") == "v2"  # cache was rewritten
    assert rec.count("/a") == 2


def test_cache_persists_across_instances(tmp_path):
    handler = site({"/a": httpx.Response(200, text="x")})
    ft = FakeTime()
    f1, rec1, _ = make(tmp_path, handler, ft=ft)
    f1.get_text("https://ex.com/a")
    f2, rec2, _ = make(tmp_path, handler, ft=ft)
    assert f2.get_text("https://ex.com/a") == "x"
    assert rec2.requests == []


def test_corrupt_cache_meta_is_ignored(tmp_path):
    fetcher, rec, _ = make(tmp_path, site({"/a": httpx.Response(200, text="x")}))
    fetcher.get_text("https://ex.com/a")
    meta_file = next((tmp_path / "cache").glob("*.meta.json"))
    meta_file.write_text("{not json")
    assert fetcher.get_text("https://ex.com/a") == "x"
    assert rec.count("/a") == 2


def test_cache_meta_url_mismatch_is_ignored(tmp_path):
    fetcher, rec, _ = make(tmp_path, site({"/a": httpx.Response(200, text="x")}))
    fetcher.get_text("https://ex.com/a")
    meta_file = next((tmp_path / "cache").glob("*.meta.json"))
    meta = json.loads(meta_file.read_text())
    meta["url"] = "https://other/"
    meta_file.write_text(json.dumps(meta))
    fetcher.get_text("https://ex.com/a")
    assert rec.count("/a") == 2


def test_cache_write_failure_is_not_fatal(tmp_path):
    blocker = tmp_path / "blocker"
    blocker.write_text("file, not dir")
    rec = Recorder(site({"/a": httpx.Response(200, text="x")}))
    ft = FakeTime()
    fetcher = PoliteFetcher(
        cache_dir=blocker / "cache",
        client=httpx.Client(transport=httpx.MockTransport(rec)),
        clock=ft.clock,
        sleep=ft.sleep,
        wall_clock=ft.clock,
    )
    assert fetcher.get_text("https://ex.com/a") == "x"


def test_error_responses_are_not_cached(tmp_path):
    fetcher, rec, _ = make(tmp_path, site({}))
    with pytest.raises(FetchError):
        fetcher.get_text("https://ex.com/missing")
    assert not (tmp_path / "cache").exists()


# ── robots.txt ──────────────────────────────────────────────────────────────


def test_robots_disallowed_raises_without_request(tmp_path):
    fetcher, rec, _ = make(tmp_path, site({"/private/x": httpx.Response(200)}))
    with pytest.raises(RobotsDisallowed):
        fetcher.get_text("https://ex.com/private/x")
    assert rec.paths() == ["/robots.txt"]


def test_robots_cached_per_host(tmp_path):
    fetcher, rec, _ = make(
        tmp_path,
        site({"/a": httpx.Response(200, text="a"), "/b": httpx.Response(200, text="b")}),
    )
    fetcher.get_text("https://ex.com/a")
    fetcher.get_text("https://ex.com/b")
    assert rec.count("/robots.txt") == 1


def test_robots_404_allows_everything(tmp_path):
    fetcher, rec, _ = make(
        tmp_path,
        site({"/private/x": httpx.Response(200, text="ok")}, robots=httpx.Response(404)),
    )
    assert fetcher.get_text("https://ex.com/private/x") == "ok"


@pytest.mark.parametrize("status", [401, 403, 500, 503])
def test_robots_forbidden_or_server_error_disallows(tmp_path, status):
    fetcher, rec, _ = make(
        tmp_path,
        site({"/a": httpx.Response(200, text="ok")}, robots=httpx.Response(status)),
    )
    with pytest.raises(RobotsDisallowed):
        fetcher.get_text("https://ex.com/a")
    assert rec.count("/a") == 0


def test_robots_network_error_disallows(tmp_path):
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/robots.txt":
            raise httpx.ConnectError("boom", request=request)
        return httpx.Response(200, text="ok")

    fetcher, rec, _ = make(tmp_path, handler)
    with pytest.raises(RobotsDisallowed):
        fetcher.get_text("https://ex.com/a")
    assert rec.count("/a") == 0


def test_robots_specific_user_agent_rule(tmp_path):
    robots = "User-agent: TEDHC-Market\nDisallow: /\n\nUser-agent: *\nAllow: /\n"
    fetcher, rec, _ = make(
        tmp_path, site({"/a": httpx.Response(200, text="ok")}, robots=robots)
    )
    with pytest.raises(RobotsDisallowed):
        fetcher.get_text("https://ex.com/a")


# ── rate limit ──────────────────────────────────────────────────────────────


def test_rate_limit_same_host(tmp_path):
    fetcher, rec, ft = make(
        tmp_path,
        site({"/a": httpx.Response(200, text="a"), "/b": httpx.Response(200, text="b")}),
        min_interval_s=3.0,
    )
    fetcher.get_text("https://ex.com/a")
    ft.sleeps.clear()
    ft.now += 1.0
    fetcher.get_text("https://ex.com/b")
    assert ft.sleeps == [pytest.approx(2.0)]


def test_rate_limit_no_sleep_when_interval_elapsed(tmp_path):
    fetcher, rec, ft = make(
        tmp_path,
        site({"/a": httpx.Response(200, text="a"), "/b": httpx.Response(200, text="b")}),
    )
    fetcher.get_text("https://ex.com/a")
    ft.sleeps.clear()
    ft.now += 10
    fetcher.get_text("https://ex.com/b")
    assert ft.sleeps == []


def test_rate_limit_applies_between_robots_and_first_page(tmp_path):
    fetcher, rec, ft = make(
        tmp_path, site({"/a": httpx.Response(200, text="a")}), min_interval_s=3.0
    )
    fetcher.get_text("https://ex.com/a")
    assert ft.sleeps == [pytest.approx(3.0)]


def test_crawl_delay_larger_than_min_interval(tmp_path):
    robots = "User-agent: *\nCrawl-delay: 10\n"
    fetcher, rec, ft = make(
        tmp_path,
        site(
            {"/a": httpx.Response(200, text="a"), "/b": httpx.Response(200, text="b")},
            robots=robots,
        ),
        min_interval_s=3.0,
    )
    fetcher.get_text("https://ex.com/a")
    ft.sleeps.clear()
    fetcher.get_text("https://ex.com/b")
    assert ft.sleeps and ft.sleeps[0] >= 10


def test_crawl_delay_smaller_than_min_interval_uses_min(tmp_path):
    robots = "User-agent: *\nCrawl-delay: 1\n"
    fetcher, rec, ft = make(
        tmp_path,
        site(
            {"/a": httpx.Response(200, text="a"), "/b": httpx.Response(200, text="b")},
            robots=robots,
        ),
        min_interval_s=3.0,
    )
    fetcher.get_text("https://ex.com/a")
    ft.sleeps.clear()
    fetcher.get_text("https://ex.com/b")
    assert ft.sleeps == [pytest.approx(3.0)]


def test_different_hosts_do_not_share_rate_limit(tmp_path):
    fetcher, rec, ft = make(
        tmp_path, site({"/a": httpx.Response(200, text="a")}), min_interval_s=3.0
    )
    fetcher.get_text("https://one.com/a")
    ft.sleeps.clear()
    # new host: robots fetch has no wait, only robots→page wait of 3s
    fetcher.get_text("https://two.com/a")
    assert ft.sleeps == [pytest.approx(3.0)]
    assert fetcher._last_request.keys() == {"one.com", "two.com"}


def test_cache_hit_does_not_sleep(tmp_path):
    fetcher, rec, ft = make(tmp_path, site({"/a": httpx.Response(200, text="a")}))
    fetcher.get_text("https://ex.com/a")
    ft.sleeps.clear()
    fetcher.get_text("https://ex.com/a")
    assert ft.sleeps == []


# ── retry / errors ──────────────────────────────────────────────────────────


def test_429_with_retry_after_sleeps_and_retries(tmp_path):
    responses = iter(
        [httpx.Response(429, headers={"Retry-After": "2"}), httpx.Response(200, text="ok")]
    )
    fetcher, rec, ft = make(
        tmp_path, site({"/a": lambda: next(responses)}), min_interval_s=0
    )
    assert fetcher.get_text("https://ex.com/a") == "ok"
    assert rec.count("/a") == 2
    assert 2.0 in ft.sleeps


def test_500_three_times_raises_fetch_error(tmp_path):
    fetcher, rec, ft = make(
        tmp_path, site({"/a": httpx.Response(500)}), min_interval_s=0
    )
    with pytest.raises(FetchError, match="500"):
        fetcher.get_text("https://ex.com/a")
    assert rec.count("/a") == 3
    assert ft.sleeps == [1.0, 2.0]  # exponential backoff


def test_5xx_then_success(tmp_path):
    responses = iter([httpx.Response(502), httpx.Response(200, text="ok")])
    fetcher, rec, _ = make(tmp_path, site({"/a": lambda: next(responses)}))
    assert fetcher.get_text("https://ex.com/a") == "ok"
    assert rec.count("/a") == 2


def test_404_raises_without_retry(tmp_path):
    fetcher, rec, _ = make(tmp_path, site({}))
    with pytest.raises(FetchError, match="404"):
        fetcher.get_text("https://ex.com/missing")
    assert rec.count("/missing") == 1


def test_timeout_is_retried(tmp_path):
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/robots.txt":
            return httpx.Response(404)
        calls["n"] += 1
        raise httpx.ReadTimeout("slow", request=request)

    fetcher, rec, _ = make(tmp_path, handler)
    with pytest.raises(FetchError, match="timeout"):
        fetcher.get_text("https://ex.com/a")
    assert calls["n"] == 3


def test_connect_error_not_retried(tmp_path):
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/robots.txt":
            return httpx.Response(404)
        calls["n"] += 1
        raise httpx.ConnectError("refused", request=request)

    fetcher, rec, _ = make(tmp_path, handler)
    with pytest.raises(FetchError, match="network error"):
        fetcher.get_text("https://ex.com/a")
    assert calls["n"] == 1


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (None, None),
        ("", None),
        ("2", 2.0),
        (" 1.5 ", 1.5),
        ("-1", None),
        ("Wed, 21 Oct 2015 07:28:00 GMT", None),
        ("99999", http_mod.MAX_RETRY_AFTER_S),
    ],
)
def test_parse_retry_after(value, expected):
    assert _parse_retry_after(value) == expected


# ── JSON ────────────────────────────────────────────────────────────────────


def test_get_json_ok(tmp_path):
    fetcher, _, _ = make(
        tmp_path, site({"/j": httpx.Response(200, text='{"a": [1, 2]}')})
    )
    assert fetcher.get_json("https://ex.com/j") == {"a": [1, 2]}


def test_get_json_list(tmp_path):
    fetcher, _, _ = make(tmp_path, site({"/j": httpx.Response(200, text="[1]")}))
    assert fetcher.get_json("https://ex.com/j") == [1]


def test_get_json_invalid_raises(tmp_path):
    fetcher, _, _ = make(tmp_path, site({"/j": httpx.Response(200, text="<html>")}))
    with pytest.raises(FetchError, match="invalid JSON"):
        fetcher.get_json("https://ex.com/j")


def test_get_json_scalar_raises(tmp_path):
    fetcher, _, _ = make(tmp_path, site({"/j": httpx.Response(200, text="42")}))
    with pytest.raises(FetchError, match="unexpected JSON"):
        fetcher.get_json("https://ex.com/j")


def test_default_client_and_close(tmp_path):
    fetcher = PoliteFetcher(cache_dir=tmp_path)
    assert isinstance(fetcher._client, httpx.Client)
    fetcher.close()
    assert fetcher._client.is_closed


# ── sources/base.py ─────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("gUw", "WUG"),
        ("", None),
        (None, None),
        ("RGBUW", "WUBRG"),
        ("rrr", "R"),
        ("C", None),
        ("W/U", "WU"),
    ],
)
def test_normalize_colors(raw, expected):
    assert normalize_colors(raw) == expected


def test_formats():
    assert FORMATS == (
        "commander", "standard", "pioneer", "modern", "legacy", "vintage", "pauper"
    )


def test_dataclasses_and_protocol():
    card = MetaCardEntry(name="Sol Ring", quantity=1)
    assert card.board == "main" and card.set_code is None
    deck = MetaDeckEntry(
        source="edhrec", format="commander", external_id="x", archetype="A", rank=1,
        meta_share_pct=None, deck_count=10, colors="WU", commander_name="A",
        source_url="https://e", event_date=None, cards=(card,),
    )
    with pytest.raises(AttributeError):
        deck.rank = 2  # type: ignore[misc]

    class Fake:
        name = "fake"
        formats = ("modern",)

        def fetch_top_decks(self, fmt: str, *, limit: int = 20) -> list[MetaDeckEntry]:
            return [deck][:limit]

    src: MetaSource = Fake()
    assert src.fetch_top_decks("modern", limit=1) == [deck]


def test_registry_populated():
    # Populated by F173-T12; full coverage in tests/cli/test_cli_metagame.py.
    assert set(SOURCE_FOR_FORMAT) == set(FORMATS)
    assert set(get_sources(object())) == set(FORMATS)
