"""Tests for the news fetcher service (F166)."""

from __future__ import annotations

from datetime import datetime
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from src.database.repository import Repository
from src.services.news_fetcher import (
    _categorize,
    _clean_summary,
    _extract_image,
    _parse_date,
    fetch_news,
)


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


class TestExtractImage:
    def test_media_content(self):
        entry = SimpleNamespace(
            media_content=[{"url": "https://example.com/img.jpg"}],
        )
        assert _extract_image(entry) == "https://example.com/img.jpg"

    def test_enclosures(self):
        entry = SimpleNamespace(
            media_content=None,
            enclosures=[{"href": "https://example.com/pic.png", "type": "image/png"}],
        )
        assert _extract_image(entry) == "https://example.com/pic.png"

    def test_media_thumbnail(self):
        entry = SimpleNamespace(
            media_content=None,
            enclosures=None,
            media_thumbnail=[{"url": "https://example.com/thumb.webp"}],
        )
        assert _extract_image(entry) == "https://example.com/thumb.webp"

    def test_no_image(self):
        entry = SimpleNamespace()
        assert _extract_image(entry) is None


class TestParseDate:
    def test_published_parsed(self):
        entry = SimpleNamespace(
            published_parsed=(2026, 9, 21, 12, 0, 0, 0, 0, 0),
        )
        result = _parse_date(entry)
        assert result == datetime(2026, 9, 21, 12, 0, 0)

    def test_updated_parsed_fallback(self):
        entry = SimpleNamespace(
            published_parsed=None,
            updated_parsed=(2026, 9, 20, 10, 0, 0, 0, 0, 0),
        )
        result = _parse_date(entry)
        assert result == datetime(2026, 9, 20, 10, 0, 0)

    def test_no_date(self):
        entry = SimpleNamespace()
        assert _parse_date(entry) is None


class TestFetchNews:
    @pytest.fixture()
    def repo(self, tmp_path):
        db_path = tmp_path / "test_news_fetcher.db"
        return Repository(db_url=f"sqlite:///{db_path}")

    def _make_feed(self, entries):
        """Create a mock feedparser result."""
        feed = SimpleNamespace(
            bozo=False,
            bozo_exception=None,
            entries=[],
        )
        for e in entries:
            entry = SimpleNamespace(
                title=e.get("title", "Test News"),
                link=e.get("link", "https://example.com/news/1"),
                summary=e.get("summary", "Test summary"),
                description=None,
                published_parsed=e.get("published_parsed", (2026, 9, 21, 12, 0, 0, 0, 0, 0)),
                updated_parsed=None,
            )
            feed.entries.append(entry)
        return feed

    @patch("src.services.news_fetcher.feedparser")
    def test_fetch_inserts_new_items(self, mock_fp, repo):
        mock_fp.parse.return_value = self._make_feed(
            [
                {"title": "News 1", "link": "https://example.com/1"},
                {"title": "News 2", "link": "https://example.com/2"},
            ]
        )
        sources = [{"name": "Test", "url": "https://test.com/feed"}]
        stats = fetch_news(repo, sources=sources)
        assert stats["fetched"] == 2
        assert stats["new"] == 2
        assert stats["skipped"] == 0

    @patch("src.services.news_fetcher.feedparser")
    def test_dedup_skips_existing(self, mock_fp, repo):
        mock_fp.parse.return_value = self._make_feed(
            [
                {"title": "News 1", "link": "https://example.com/1"},
            ]
        )
        sources = [{"name": "Test", "url": "https://test.com/feed"}]
        # First fetch
        fetch_news(repo, sources=sources)
        # Second fetch — should skip
        stats = fetch_news(repo, sources=sources)
        assert stats["fetched"] == 1
        assert stats["new"] == 0
        assert stats["skipped"] == 1

    @patch("src.services.news_fetcher.feedparser")
    def test_handles_bozo_error(self, mock_fp, repo):
        mock_fp.parse.return_value = SimpleNamespace(
            bozo=True,
            bozo_exception=Exception("parse error"),
            entries=[],
        )
        sources = [{"name": "Bad Feed", "url": "https://bad.com/feed"}]
        stats = fetch_news(repo, sources=sources)
        assert stats["errors"] == 1
        assert stats["fetched"] == 0

    @patch("src.services.news_fetcher.feedparser")
    def test_skips_entries_without_link(self, mock_fp, repo):
        entry = SimpleNamespace(
            title="No Link",
            link=None,
            summary=None,
            description=None,
            published_parsed=None,
            updated_parsed=None,
        )
        mock_fp.parse.return_value = SimpleNamespace(
            bozo=False,
            bozo_exception=None,
            entries=[entry],
        )
        sources = [{"name": "Test", "url": "https://test.com/feed"}]
        stats = fetch_news(repo, sources=sources)
        assert stats["skipped"] == 1
        assert stats["new"] == 0

    @patch("src.services.news_fetcher.feedparser")
    def test_max_per_source_limit(self, mock_fp, repo):
        entries = [{"title": f"News {i}", "link": f"https://example.com/{i}"} for i in range(10)]
        mock_fp.parse.return_value = self._make_feed(entries)
        sources = [{"name": "Test", "url": "https://test.com/feed"}]
        stats = fetch_news(repo, max_per_source=3, sources=sources)
        assert stats["fetched"] == 3
        assert stats["new"] == 3

    @patch("src.services.news_fetcher.feedparser")
    def test_categorizes_ban_news(self, mock_fp, repo):
        mock_fp.parse.return_value = self._make_feed(
            [
                {"title": "Card X Banned in Modern", "link": "https://example.com/ban"},
            ]
        )
        sources = [{"name": "Test", "url": "https://test.com/feed"}]
        fetch_news(repo, sources=sources)
        items = repo.list_news_items(user_id=1)
        assert items[0]["category"] == "ban"

    @patch("src.services.news_fetcher.feedparser")
    def test_fetch_exception_handled(self, mock_fp, repo):
        mock_fp.parse.side_effect = Exception("network error")
        sources = [{"name": "Bad", "url": "https://bad.com/feed"}]
        stats = fetch_news(repo, sources=sources)
        assert stats["errors"] == 1
