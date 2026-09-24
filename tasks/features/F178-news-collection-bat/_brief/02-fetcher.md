# F178 — Component: news fetcher (httpx + stdlib XML)

File: `src/services/news_fetcher.py` (sole owner: F178-T02).

## Keep (unchanged public helpers — existing tests cover them)
`_clean_summary`, `_categorize`, `_CATEGORY_KEYWORDS`. Keep the `fetch_news(repo, *, max_per_source=20, sources=None)` signature.

## Replace
- Remove `import feedparser`. Use `httpx` (already a dependency) and
  `xml.etree.ElementTree` (Python 3.14 bundled expat has billion-laughs
  protection; still reject bodies > 5 MB before parsing).
- New pure function `parse_feed(xml_bytes: bytes) -> list[FeedEntry]` where
  `FeedEntry` is a `@dataclass(frozen=True)` with
  `title, link, summary, image_url, published_at`.
  Must support:
  - **RSS 2.0**: `channel/item` → `title`, `link`, `description`,
    `pubDate` (RFC 822 → `email.utils.parsedate_to_datetime`),
    `enclosure[@url,@type]`, `media:content[@url]`, `media:thumbnail[@url]`
    (ns `http://search.yahoo.com/mrss/`), `content:encoded` as summary fallback.
  - **Atom**: `{http://www.w3.org/2005/Atom}entry` → `title`,
    `link[@rel='alternate' or no rel]/@href`, `summary` or `content`,
    `published` or `updated` (ISO 8601 → `datetime.fromisoformat`).
  - Timezone-aware dates → convert to UTC and drop tzinfo (DB column is naive `DateTime`).
  - Unparseable date → `None` (never raise).
  - Invalid XML → raise `FeedParseError` (custom exception).
- New `fetch_feed(url, *, client: httpx.Client) -> bytes`: GET with
  `timeout=15`, `follow_redirects=True`, headers
  `User-Agent: "TEDHC-Market/1.0 (+news fetcher)"`,
  `Accept: "application/rss+xml, application/atom+xml, application/xml;q=0.9, */*;q=0.5"`.
  `response.raise_for_status()`.
- `SOURCES`: keep the list shape `{"name", "url"}`. Proposed default set
  (T08 validates live and prunes):
  1. `MTG Official` — `https://magic.wizards.com/en/rss/rss.xml`
  2. `Scryfall Blog` — `https://scryfall.com/blog/feed.atom` (fallback `https://scryfall.com/blog/rss`)
  3. `MTGGoldfish` — `https://www.mtggoldfish.com/feed`
  4. `EDHREC` — `https://edhrec.com/articles/feed`
  5. `Hipsters of the Coast` — `https://www.hipstersofthecoast.com/feed/`
  Env override: `NEWS_FEED_SOURCES` = `Name|url;Name2|url2` (parsed by
  `load_sources()`; malformed pairs skipped with a warning). No secrets involved.
- `fetch_news(...)` return shape becomes:
  ```python
  {
    "fetched": int, "new": int, "skipped": int, "errors": int,
    "sources": [
      {"name": str, "url": str, "ok": bool, "http_status": int | None,
       "entries": int, "new": int, "error": str | None},
    ],
  }
  ```
  (top-level keys unchanged → backward compatible with any caller).
- New kwarg `dry_run: bool = False` → fetch + parse, fill `sources[*].entries`,
  but **never** call `repo.upsert_news_item` (`repo` may be `None` when dry_run).
- New kwarg `client: httpx.Client | None = None` for test injection; create
  and close one internally when `None`.
- One failing source must not stop the others (per-source try/except, log
  with `structlog` `log.warning("news_feed_fetch_error", source=..., error=...)`).
