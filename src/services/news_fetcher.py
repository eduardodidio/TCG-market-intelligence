"""MTG News fetcher — RSS/Atom feed aggregator (F166).

Fetches news from configured MTG sources and upserts into the database.
"""

from __future__ import annotations

import re
from datetime import datetime
from html import unescape

import feedparser
import structlog

log = structlog.get_logger()

# ── Feed sources ──────────────────────────────────────────────────

SOURCES: list[dict[str, str]] = [
    {
        "name": "MTG Official",
        "url": "https://magic.wizards.com/en/rss/rss.xml",
    },
    {
        "name": "Scryfall Blog",
        "url": "https://scryfall.com/blog/rss",
    },
]


# ── Helpers ───────────────────────────────────────────────────────

_TAG_RE = re.compile(r"<[^>]+>")


def _clean_summary(raw: str | None) -> str | None:
    """Strip HTML tags and truncate to 500 chars."""
    if not raw:
        return None
    text = unescape(_TAG_RE.sub("", raw)).strip()
    if len(text) > 500:
        text = text[:497] + "..."
    return text or None


_CATEGORY_KEYWORDS: list[tuple[str, list[str]]] = [
    ("ban", ["ban", "banned", "unban", "restricted", "suspension"]),
    ("release", ["release", "preview", "spoiler", "reveal", "set release", "new set"]),
    ("event", ["event", "tournament", "championship", "grand prix", "pro tour"]),
    ("reprint", ["reprint", "secret lair"]),
]


def _categorize(title: str, summary: str | None = None) -> str:
    """Keyword-based category detection."""
    text = (title + " " + (summary or "")).lower()
    for category, keywords in _CATEGORY_KEYWORDS:
        for kw in keywords:
            if kw in text:
                return category
    return "other"


def _extract_image(entry: object) -> str | None:
    """Try to extract an image URL from media_content or enclosures."""
    # media_content (common in RSS 2.0 / Media RSS)
    img_exts = (".jpg", ".jpeg", ".png", ".webp", ".gif")
    media = getattr(entry, "media_content", None)
    if media:
        for m in media:
            url = m.get("url", "")
            if url and any(ext in url.lower() for ext in img_exts):
                return url

    # enclosures
    enclosures = getattr(entry, "enclosures", None)
    if enclosures:
        for enc in enclosures:
            url = enc.get("href", "") or enc.get("url", "")
            etype = enc.get("type", "")
            if url and ("image" in etype or any(ext in url.lower() for ext in img_exts)):
                return url

    # media_thumbnail
    thumbs = getattr(entry, "media_thumbnail", None)
    if thumbs:
        for t in thumbs:
            url = t.get("url", "")
            if url:
                return url

    return None


def _parse_date(entry: object) -> datetime | None:
    """Parse published date from feed entry."""
    parsed = getattr(entry, "published_parsed", None)
    if parsed:
        try:
            return datetime(*parsed[:6])
        except (TypeError, ValueError):
            pass
    # Fallback: updated_parsed
    updated = getattr(entry, "updated_parsed", None)
    if updated:
        try:
            return datetime(*updated[:6])
        except (TypeError, ValueError):
            pass
    return None


# ── Main fetcher ──────────────────────────────────────────────────


def fetch_news(
    repo: object,
    *,
    max_per_source: int = 20,
    sources: list[dict[str, str]] | None = None,
) -> dict[str, int]:
    """Fetch news from RSS feeds and upsert into the database.

    Returns stats: {fetched, new, skipped, errors}.
    """
    feed_sources = sources or SOURCES
    stats = {"fetched": 0, "new": 0, "skipped": 0, "errors": 0}

    for source in feed_sources:
        source_name = source["name"]
        feed_url = source["url"]
        try:
            feed = feedparser.parse(feed_url)
            if feed.bozo and not feed.entries:
                log.warning(
                    "news_feed_parse_error",
                    source=source_name,
                    error=str(feed.bozo_exception),
                )
                stats["errors"] += 1
                continue

            entries = feed.entries[:max_per_source]
            for entry in entries:
                stats["fetched"] += 1
                try:
                    link = getattr(entry, "link", None)
                    title = getattr(entry, "title", None)
                    if not link or not title:
                        stats["skipped"] += 1
                        continue

                    raw_summary = getattr(entry, "summary", None) or getattr(
                        entry, "description", None
                    )
                    summary = _clean_summary(raw_summary)

                    data = {
                        "title": title[:500],
                        "summary": summary,
                        "source_url": link[:1000],
                        "source_name": source_name,
                        "category": _categorize(title, summary),
                        "image_url": _extract_image(entry),
                        "published_at": _parse_date(entry),
                        "fetched_at": datetime.now(),
                    }

                    is_new = repo.upsert_news_item(data)
                    if is_new:
                        stats["new"] += 1
                    else:
                        stats["skipped"] += 1
                except Exception:
                    log.warning("news_entry_error", source=source_name, exc_info=True)
                    stats["errors"] += 1

        except Exception:
            log.warning("news_feed_fetch_error", source=source_name, exc_info=True)
            stats["errors"] += 1

    log.info("news_fetch_complete", **stats)
    return stats
