"""MTG News fetcher — RSS/Atom feed aggregator (F166, rewritten F178).

Fetches news from configured MTG sources and upserts into the database.
Uses httpx for transport and the stdlib xml.etree.ElementTree parser —
no undeclared dependencies.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from html import unescape
from xml.etree import ElementTree as ET

import httpx
import structlog

log = structlog.get_logger()

MAX_BODY_BYTES = 5_000_000

_ATOM_NS = "http://www.w3.org/2005/Atom"
_MEDIA_NS = "http://search.yahoo.com/mrss/"
_CONTENT_NS = "http://purl.org/rss/1.0/modules/content/"

_REQUEST_HEADERS = {
    "User-Agent": "TEDHC-Market/1.0 (+news fetcher)",
    "Accept": "application/rss+xml, application/atom+xml, application/xml;q=0.9, */*;q=0.5",
}


class FeedParseError(Exception):
    """Raised when a feed body cannot be parsed as RSS or Atom XML."""


@dataclass(frozen=True)
class FeedEntry:
    title: str
    link: str
    summary: str | None
    image_url: str | None
    published_at: datetime | None


# ── Feed sources ──────────────────────────────────────────────────

SOURCES: list[dict[str, str]] = [
    {"name": "MTG Official", "url": "https://magic.wizards.com/en/rss/rss.xml"},
    {"name": "Scryfall Blog", "url": "https://scryfall.com/blog/feed.atom"},
    {"name": "MTGGoldfish", "url": "https://www.mtggoldfish.com/feed"},
    {"name": "EDHREC", "url": "https://edhrec.com/articles/feed"},
    {"name": "Hipsters of the Coast", "url": "https://www.hipstersofthecoast.com/feed/"},
]


def load_sources() -> list[dict[str, str]]:
    """Load feed sources from NEWS_FEED_SOURCES env var, or fall back to SOURCES.

    Format: "Name|url;Name2|url2". Malformed pairs are skipped with a warning.
    """
    raw = os.environ.get("NEWS_FEED_SOURCES", "").strip()
    if not raw:
        return SOURCES

    sources: list[dict[str, str]] = []
    for pair in raw.split(";"):
        pair = pair.strip()
        if not pair:
            continue
        parts = pair.split("|", 1)
        if len(parts) != 2 or not parts[0].strip() or not parts[1].strip():
            log.warning("news_source_malformed", pair=pair)
            continue
        sources.append({"name": parts[0].strip(), "url": parts[1].strip()})

    return sources or SOURCES


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


def _to_naive_utc(dt: datetime) -> datetime:
    if dt.tzinfo is not None:
        dt = dt.astimezone(timezone.utc).replace(tzinfo=None)
    return dt


def _parse_rss_date(raw: str | None) -> datetime | None:
    if not raw:
        return None
    try:
        dt = parsedate_to_datetime(raw)
    except (TypeError, ValueError):
        return None
    if dt is None:
        return None
    return _to_naive_utc(dt)


def _parse_atom_date(raw: str | None) -> datetime | None:
    if not raw:
        return None
    try:
        value = raw.strip()
        if value.endswith("Z"):
            value = value[:-1] + "+00:00"
        dt = datetime.fromisoformat(value)
    except ValueError:
        return None
    return _to_naive_utc(dt)


def _find_text(element: ET.Element, tag: str) -> str | None:
    child = element.find(tag)
    if child is None or child.text is None:
        return None
    return child.text.strip() or None


def _rss_image(item: ET.Element) -> str | None:
    enclosure = item.find("enclosure")
    if enclosure is not None:
        url = enclosure.get("url")
        etype = enclosure.get("type", "")
        if url and (not etype or "image" in etype):
            return url

    media_content = item.find(f"{{{_MEDIA_NS}}}content")
    if media_content is not None:
        url = media_content.get("url")
        if url:
            return url

    media_thumbnail = item.find(f"{{{_MEDIA_NS}}}thumbnail")
    if media_thumbnail is not None:
        url = media_thumbnail.get("url")
        if url:
            return url

    return None


def _rss_summary(item: ET.Element) -> str | None:
    description = _find_text(item, "description")
    if description:
        return description
    return _find_text(item, f"{{{_CONTENT_NS}}}encoded")


def _parse_rss(root: ET.Element) -> list[FeedEntry]:
    entries: list[FeedEntry] = []
    channel = root.find("channel")
    if channel is None:
        return entries

    for item in channel.findall("item"):
        title = _find_text(item, "title") or ""
        link = _find_text(item, "link") or ""
        summary = _clean_summary(_rss_summary(item))
        image_url = _rss_image(item)
        published_at = _parse_rss_date(_find_text(item, "pubDate"))
        entries.append(
            FeedEntry(
                title=title,
                link=link,
                summary=summary,
                image_url=image_url,
                published_at=published_at,
            )
        )
    return entries


def _atom_link(entry: ET.Element) -> str:
    alternate = None
    fallback = None
    for link in entry.findall(f"{{{_ATOM_NS}}}link"):
        rel = link.get("rel")
        href = link.get("href")
        if not href:
            continue
        if rel in (None, "alternate"):
            alternate = href
        elif fallback is None:
            fallback = href
    return alternate or fallback or ""


def _atom_summary(entry: ET.Element) -> str | None:
    summary = _find_text(entry, f"{{{_ATOM_NS}}}summary")
    if summary:
        return summary
    return _find_text(entry, f"{{{_ATOM_NS}}}content")


def _parse_atom(root: ET.Element) -> list[FeedEntry]:
    entries: list[FeedEntry] = []
    for entry in root.findall(f"{{{_ATOM_NS}}}entry"):
        title = _find_text(entry, f"{{{_ATOM_NS}}}title") or ""
        link = _atom_link(entry)
        summary = _clean_summary(_atom_summary(entry))
        published_raw = _find_text(entry, f"{{{_ATOM_NS}}}published") or _find_text(
            entry, f"{{{_ATOM_NS}}}updated"
        )
        published_at = _parse_atom_date(published_raw)
        entries.append(
            FeedEntry(
                title=title,
                link=link,
                summary=summary,
                image_url=None,
                published_at=published_at,
            )
        )
    return entries


def parse_feed(xml_bytes: bytes) -> list[FeedEntry]:
    """Parse RSS 2.0 or Atom feed bytes into a list of FeedEntry.

    Entries missing a title or link are still returned (with ""), so the
    caller can decide how to count them.
    """
    try:
        root = ET.fromstring(xml_bytes)
    except ET.ParseError as exc:
        raise FeedParseError(str(exc)) from exc

    tag = root.tag
    if tag == f"{{{_ATOM_NS}}}feed":
        return _parse_atom(root)
    if tag == "rss" or tag.endswith("}rss"):
        return _parse_rss(root)

    raise FeedParseError(f"unsupported feed root element: {tag}")


def fetch_feed(url: str, *, client: httpx.Client) -> bytes:
    """Fetch feed bytes from url. Raises on HTTP errors/timeouts."""
    response = client.get(url, headers=_REQUEST_HEADERS, timeout=15, follow_redirects=True)
    response.raise_for_status()
    return response.content


# ── Main fetcher ──────────────────────────────────────────────────


def fetch_news(
    repo: object,
    *,
    max_per_source: int = 20,
    sources: list[dict[str, str]] | None = None,
    dry_run: bool = False,
    client: httpx.Client | None = None,
) -> dict:
    """Fetch news from RSS/Atom feeds and upsert into the database.

    Returns stats: {fetched, new, skipped, errors, sources}.
    When dry_run=True, feeds are fetched and parsed but repo.upsert_news_item
    is never called (repo may be None).
    """
    feed_sources = sources or load_sources()
    stats: dict = {"fetched": 0, "new": 0, "skipped": 0, "errors": 0, "sources": []}

    owns_client = client is None
    if owns_client:
        client = httpx.Client()

    try:
        for source in feed_sources:
            source_name = source["name"]
            feed_url = source["url"]
            source_report = {
                "name": source_name,
                "url": feed_url,
                "ok": True,
                "http_status": None,
                "entries": 0,
                "new": 0,
                "error": None,
            }

            try:
                body = fetch_feed(feed_url, client=client)
                if len(body) > MAX_BODY_BYTES:
                    raise FeedParseError("payload too large")

                entries = parse_feed(body)
                source_report["entries"] = len(entries)

                for entry in entries[:max_per_source]:
                    stats["fetched"] += 1

                    if not entry.link or not entry.title:
                        stats["skipped"] += 1
                        continue

                    if dry_run:
                        continue

                    try:
                        data = {
                            "title": entry.title[:500],
                            "summary": entry.summary,
                            "source_url": entry.link[:1000],
                            "source_name": source_name,
                            "category": _categorize(entry.title, entry.summary),
                            "image_url": entry.image_url,
                            "published_at": entry.published_at,
                            "fetched_at": datetime.now(),
                        }
                        is_new = repo.upsert_news_item(data)
                        if is_new:
                            stats["new"] += 1
                            source_report["new"] += 1
                        else:
                            stats["skipped"] += 1
                    except Exception:
                        log.warning("news_entry_error", source=source_name, exc_info=True)
                        stats["errors"] += 1

            except httpx.HTTPStatusError as exc:
                source_report["ok"] = False
                source_report["http_status"] = exc.response.status_code
                source_report["error"] = str(exc)
                stats["errors"] += 1
                log.warning(
                    "news_feed_fetch_error",
                    source=source_name,
                    error=str(exc),
                    http_status=exc.response.status_code,
                )
            except httpx.HTTPError as exc:
                source_report["ok"] = False
                source_report["error"] = str(exc)
                stats["errors"] += 1
                log.warning("news_feed_fetch_error", source=source_name, error=str(exc))
            except FeedParseError as exc:
                source_report["ok"] = False
                source_report["error"] = str(exc)
                stats["errors"] += 1
                log.warning("news_feed_parse_error", source=source_name, error=str(exc))
            except Exception as exc:
                source_report["ok"] = False
                source_report["error"] = str(exc)
                stats["errors"] += 1
                log.warning(
                    "news_feed_fetch_error",
                    source=source_name,
                    error=str(exc),
                    exc_info=True,
                )

            stats["sources"].append(source_report)
    finally:
        if owns_client:
            client.close()

    log.info(
        "news_fetch_complete",
        fetched=stats["fetched"],
        new=stats["new"],
        skipped=stats["skipped"],
        errors=stats["errors"],
    )
    return stats
