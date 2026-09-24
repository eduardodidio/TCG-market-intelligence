"""Tests for the news fetcher service (F166, rewritten F178 — httpx + stdlib XML)."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

import httpx
import pytest

from src.database.repository import Repository
from src.services.news_fetcher import (
    SOURCES,
    FeedEntry,
    FeedParseError,
    _categorize,
    _clean_summary,
    fetch_feed,
    fetch_news,
    load_sources,
    parse_feed,
)

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures" / "news"


def _read_fixture(name: str) -> bytes:
    return (FIXTURES_DIR / name).read_bytes()


RSS_BYTES = _read_fixture("rss_sample.xml")
ATOM_BYTES = _read_fixture("atom_sample.xml")
INVALID_BYTES = _read_fixture("invalid.xml")


class TestCleanSummary:
    def test_strips_html(self):
        assert _clean_summary("<p>Hello <b>world</b></p>") == "Hello world"

    def test_truncates_long_text(self):
        text = "a" * 600
        result = _clean_summary(text)
        assert len(result) == 500
        assert result.endswith("...")

    def test_returns_none_for_empty(self):
        assert _clean_summary(None) is None
        assert _clean_summary("") is None

    def test_unescapes_html_entities(self):
        assert _clean_summary("&amp; &lt;") == "& <"


class TestCategorize:
    def test_ban_keyword(self):
        assert _categorize("Card X banned in Standard") == "ban"

    def test_release_keyword(self):
        assert _categorize("New set release: Aether Revolt") == "release"

    def test_event_keyword(self):
        assert _categorize("Grand Prix results") == "event"

    def test_reprint_keyword(self):
        assert _categorize("Secret Lair drop announced") == "reprint"

    def test_other_default(self):
        assert _categorize("Random article about game design") == "other"

    def test_summary_used(self):
        assert _categorize("Update", "Cards banned in Pioneer") == "ban"


class TestParseFeedRss:
    def test_parses_all_items(self):
        entries = parse_feed(RSS_BYTES)
        assert len(entries) == 4
        assert all(isinstance(e, FeedEntry) for e in entries)

    def test_item_a_enclosure_image_and_ban_category(self):
        entries = parse_feed(RSS_BYTES)
        item_a = entries[0]
        assert item_a.title == "New card banned in Commander"
        assert item_a.link == "https://example.com/news/item-a"
        assert item_a.image_url == "https://example.com/images/a.jpg"
        assert "HTML" in item_a.summary
        assert _categorize(item_a.title, item_a.summary) == "ban"

    def test_item_b_media_content_image_and_negative_offset_date(self):
        entries = parse_feed(RSS_BYTES)
        item_b = entries[1]
        assert item_b.image_url == "https://example.com/images/b.png"
        assert item_b.published_at == datetime(2026, 9, 22, 14, 30, 0)

    def test_item_c_media_thumbnail_and_content_encoded_and_bad_date(self):
        entries = parse_feed(RSS_BYTES)
        item_c = entries[2]
        assert item_c.image_url == "https://example.com/images/c-thumb.jpg"
        assert "Full article body" in item_c.summary
        assert item_c.published_at is None

    def test_item_d_missing_link_kept_empty(self):
        entries = parse_feed(RSS_BYTES)
        item_d = entries[3]
        assert item_d.link == ""
        assert item_d.title == "Missing link item, must be skipped"

    def test_item_a_positive_offset_utc_conversion(self):
        entries = parse_feed(RSS_BYTES)
        item_a = entries[0]
        assert item_a.published_at == datetime(2026, 9, 22, 14, 30, 0)


class TestParseFeedAtom:
    def test_parses_all_entries(self):
        entries = parse_feed(ATOM_BYTES)
        assert len(entries) == 3

    def test_alternate_link_and_summary(self):
        entries = parse_feed(ATOM_BYTES)
        assert entries[0].link == "https://example.com/news/entry-1"
        assert entries[0].summary == "A short summary of entry one."
        assert entries[0].published_at == datetime(2026, 9, 20, 10, 0, 0)

    def test_plain_link_and_content_and_updated_fallback(self):
        entries = parse_feed(ATOM_BYTES)
        assert entries[1].link == "https://example.com/news/entry-2"
        assert "Full HTML body" in entries[1].summary
        assert entries[1].published_at == datetime(2026, 9, 21, 8, 15, 0)

    def test_alternate_preferred_over_self(self):
        entries = parse_feed(ATOM_BYTES)
        assert entries[2].link == "https://example.com/news/entry-3"


class TestParseFeedInvalid:
    def test_raises_feed_parse_error(self):
        with pytest.raises(FeedParseError):
            parse_feed(INVALID_BYTES)

    def test_empty_channel(self):
        empty_rss = b"""<?xml version="1.0"?>
        <rss version="2.0"><channel><title>Empty</title></channel></rss>"""
        assert parse_feed(empty_rss) == []

    def test_unsupported_root_raises(self):
        with pytest.raises(FeedParseError):
            parse_feed(b"<?xml version='1.0'?><notafeed></notafeed>")


class TestFetchFeed:
    def test_returns_body_on_success(self):
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, content=RSS_BYTES)

        with httpx.Client(transport=httpx.MockTransport(handler)) as client:
            body = fetch_feed("https://example.com/feed", client=client)
        assert body == RSS_BYTES

    def test_raises_on_http_error(self):
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(403, content=b"forbidden")

        with httpx.Client(transport=httpx.MockTransport(handler)) as client:
            with pytest.raises(httpx.HTTPStatusError):
                fetch_feed("https://example.com/feed", client=client)

    def test_sends_expected_headers(self):
        captured = {}

        def handler(request: httpx.Request) -> httpx.Response:
            captured["headers"] = request.headers
            return httpx.Response(200, content=RSS_BYTES)

        with httpx.Client(transport=httpx.MockTransport(handler)) as client:
            fetch_feed("https://example.com/feed", client=client)
        assert "TEDHC-Market" in captured["headers"]["user-agent"]


class TestLoadSources:
    def test_env_with_valid_pairs(self, monkeypatch):
        monkeypatch.setenv("NEWS_FEED_SOURCES", "Foo|https://foo.com/feed;Bar|https://bar.com/feed")
        sources = load_sources()
        assert sources == [
            {"name": "Foo", "url": "https://foo.com/feed"},
            {"name": "Bar", "url": "https://bar.com/feed"},
        ]

    def test_env_with_malformed_pair_skipped(self, monkeypatch):
        monkeypatch.setenv("NEWS_FEED_SOURCES", "Foo|https://foo.com/feed;malformed;Bar|https://bar.com/feed")
        sources = load_sources()
        assert sources == [
            {"name": "Foo", "url": "https://foo.com/feed"},
            {"name": "Bar", "url": "https://bar.com/feed"},
        ]

    def test_empty_env_falls_back_to_defaults(self, monkeypatch):
        monkeypatch.delenv("NEWS_FEED_SOURCES", raising=False)
        assert load_sources() == SOURCES


class TestFetchNews:
    @pytest.fixture()
    def repo(self, tmp_path):
        db_path = tmp_path / "test_news_fetcher.db"
        return Repository(db_url=f"sqlite:///{db_path}")

    def _client_for(
        self,
        body_by_url: dict[str, bytes],
        status_by_url: dict[str, int] | None = None,
        raise_by_url: dict[str, Exception] | None = None,
    ) -> httpx.Client:
        status_by_url = status_by_url or {}
        raise_by_url = raise_by_url or {}

        def handler(request: httpx.Request) -> httpx.Response:
            url = str(request.url)
            if url in raise_by_url:
                raise raise_by_url[url]
            status = status_by_url.get(url, 200)
            body = body_by_url.get(url, b"")
            return httpx.Response(status, content=body)

        return httpx.Client(transport=httpx.MockTransport(handler))

    def test_rss_fixture_stores_three_skips_one(self, repo):
        sources = [{"name": "Test", "url": "https://test.com/feed"}]
        client = self._client_for({"https://test.com/feed": RSS_BYTES})
        stats = fetch_news(repo, sources=sources, client=client)
        client.close()

        assert stats["fetched"] == 4
        assert stats["new"] == 3
        assert stats["skipped"] == 1
        assert stats["errors"] == 0
        assert stats["sources"][0]["ok"] is True
        assert stats["sources"][0]["entries"] == 4
        assert stats["sources"][0]["new"] == 3

    def test_atom_fixture_stores_three(self, repo):
        sources = [{"name": "Test", "url": "https://test.com/feed"}]
        client = self._client_for({"https://test.com/feed": ATOM_BYTES})
        stats = fetch_news(repo, sources=sources, client=client)
        client.close()

        assert stats["fetched"] == 3
        assert stats["new"] == 3
        assert stats["skipped"] == 0

    def test_categorizes_ban_news(self, repo):
        sources = [{"name": "Test", "url": "https://test.com/feed"}]
        client = self._client_for({"https://test.com/feed": RSS_BYTES})
        fetch_news(repo, sources=sources, client=client)
        client.close()
        items = repo.list_news_items(user_id=1)
        titles = {i["source_url"]: i["category"] for i in items}
        assert titles["https://example.com/news/item-a"] == "ban"

    def test_idempotency_second_run_skips(self, repo):
        sources = [{"name": "Test", "url": "https://test.com/feed"}]
        client1 = self._client_for({"https://test.com/feed": RSS_BYTES})
        fetch_news(repo, sources=sources, client=client1)
        client1.close()

        client2 = self._client_for({"https://test.com/feed": RSS_BYTES})
        stats = fetch_news(repo, sources=sources, client=client2)
        client2.close()

        assert stats["fetched"] == 4
        assert stats["new"] == 0
        assert stats["skipped"] == 4

    def test_403_source_isolated_from_others(self, repo):
        sources = [
            {"name": "Bad", "url": "https://bad.com/feed"},
            {"name": "Good", "url": "https://good.com/feed"},
        ]
        client = self._client_for(
            {"https://good.com/feed": RSS_BYTES},
            status_by_url={"https://bad.com/feed": 403},
        )
        stats = fetch_news(repo, sources=sources, client=client)
        client.close()

        bad_report = next(s for s in stats["sources"] if s["name"] == "Bad")
        good_report = next(s for s in stats["sources"] if s["name"] == "Good")
        assert bad_report["ok"] is False
        assert bad_report["http_status"] == 403
        assert good_report["ok"] is True
        assert good_report["new"] == 3
        assert stats["errors"] == 1

    def test_timeout_source_isolated_from_others(self, repo):
        sources = [
            {"name": "Slow", "url": "https://slow.com/feed"},
            {"name": "Good", "url": "https://good.com/feed"},
        ]
        client = self._client_for(
            {"https://good.com/feed": RSS_BYTES},
            raise_by_url={"https://slow.com/feed": httpx.TimeoutException("timed out")},
        )
        stats = fetch_news(repo, sources=sources, client=client)
        client.close()

        slow_report = next(s for s in stats["sources"] if s["name"] == "Slow")
        assert slow_report["ok"] is False
        assert slow_report["http_status"] is None
        assert slow_report["error"] is not None

    def test_invalid_xml_source_isolated_from_others(self, repo):
        sources = [
            {"name": "Broken", "url": "https://broken.com/feed"},
            {"name": "Good", "url": "https://good.com/feed"},
        ]
        client = self._client_for(
            {
                "https://broken.com/feed": INVALID_BYTES,
                "https://good.com/feed": RSS_BYTES,
            }
        )
        stats = fetch_news(repo, sources=sources, client=client)
        client.close()

        broken_report = next(s for s in stats["sources"] if s["name"] == "Broken")
        good_report = next(s for s in stats["sources"] if s["name"] == "Good")
        assert broken_report["ok"] is False
        assert good_report["ok"] is True
        assert good_report["new"] == 3

    def test_max_per_source_limit(self, repo):
        sources = [{"name": "Test", "url": "https://test.com/feed"}]
        client = self._client_for({"https://test.com/feed": RSS_BYTES})
        stats = fetch_news(repo, max_per_source=1, sources=sources, client=client)
        client.close()

        assert stats["fetched"] == 1

    def test_payload_too_large_treated_as_error(self, repo):
        sources = [{"name": "Huge", "url": "https://huge.com/feed"}]
        huge_body = b"<rss></rss>" + b" " * 5_000_001
        client = self._client_for({"https://huge.com/feed": huge_body})
        stats = fetch_news(repo, sources=sources, client=client)
        client.close()

        report = stats["sources"][0]
        assert report["ok"] is False
        assert report["error"] == "payload too large"
        assert stats["errors"] == 1

    def test_empty_channel_ok_zero_entries(self, repo):
        sources = [{"name": "Empty", "url": "https://empty.com/feed"}]
        empty_rss = b"""<?xml version="1.0"?>
        <rss version="2.0"><channel><title>Empty</title></channel></rss>"""
        client = self._client_for({"https://empty.com/feed": empty_rss})
        stats = fetch_news(repo, sources=sources, client=client)
        client.close()

        report = stats["sources"][0]
        assert report["ok"] is True
        assert report["entries"] == 0

    def test_dry_run_never_writes_and_repo_may_be_none(self):
        sources = [{"name": "Test", "url": "https://test.com/feed"}]
        client = self._client_for({"https://test.com/feed": RSS_BYTES})
        stats = fetch_news(None, sources=sources, dry_run=True, client=client)
        client.close()

        assert stats["new"] == 0
        assert stats["sources"][0]["entries"] == 4

    def test_dry_run_does_not_call_upsert(self, repo, monkeypatch):
        called = []
        monkeypatch.setattr(repo, "upsert_news_item", lambda data: called.append(data))
        sources = [{"name": "Test", "url": "https://test.com/feed"}]
        client = self._client_for({"https://test.com/feed": RSS_BYTES})
        fetch_news(repo, sources=sources, dry_run=True, client=client)
        client.close()

        assert called == []
