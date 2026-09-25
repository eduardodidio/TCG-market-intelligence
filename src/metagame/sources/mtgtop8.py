"""MTGTop8 adapter for constructed formats (F173-T08, ADR-0016).

Flow per format: meta page (``format?f=<CODE>``) → archetype page (first deck
row = representative deck) → MTGO text export (``mtgo?d=<deck_id>``).
"""

from __future__ import annotations

import re
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from urllib.parse import parse_qs, urljoin, urlparse

import httpx
import structlog
from bs4 import BeautifulSoup

from src.decks.parser import parse_deck_text
from src.metagame.http import FetchError, PoliteFetcher, RobotsDisallowed
from src.metagame.sources.base import MetaCardEntry, MetaDeckEntry

log = structlog.get_logger()

BASE_URL = "https://www.mtgtop8.com/"
FORMAT_CODES: dict[str, str] = {
    "standard": "ST",
    "pioneer": "PI",
    "modern": "MO",
    "legacy": "LE",
    "vintage": "VI",
    "pauper": "PAU",
}
DECKLIST_TTL_HOURS = 24 * 7

# ── selectors (keep together: MTGTop8 HTML changes break only these) ─────────
ROW_SELECTOR = "tr.hover_tr"
ARCHETYPE_LINK_SELECTOR = 'a[href^="archetype?a="]'
DECK_LINK_SELECTOR = 'a[href*="d="]'
SIDEBOARD_HEADER = "sideboard"

_SHARE_RE = re.compile(r"(\d+(?:[.,]\d+)?)")
_QTY_X_RE = re.compile(r"^(\d+)x\s+", re.IGNORECASE)
_DATE_RE = re.compile(r"\b(\d{2}/\d{2}/\d{2})\b")


def _parse_share(text: str | None) -> Decimal | None:
    """``"18 %"`` / ``"9,5 %"`` / ``"12.5%"`` → Decimal; empty/garbage → None."""
    if not text:
        return None
    match = _SHARE_RE.search(text)
    if not match:
        return None
    try:
        return Decimal(match.group(1).replace(",", "."))
    except InvalidOperation:  # pragma: no cover - regex guarantees a number
        return None


def _query_param(href: str, key: str) -> str | None:
    values = parse_qs(urlparse(href).query).get(key)
    return values[0] if values else None


def _parse_meta_page(html: str) -> list[dict]:
    """Archetype rows of a format page, ordered by meta share (desc, None last).

    Each dict: ``archetype``, ``external_id``, ``meta_share_pct``, ``href``.
    """
    soup = BeautifulSoup(html, "html.parser")
    rows: list[dict] = []
    seen: set[str] = set()
    for tr in soup.select(ROW_SELECTOR):
        link = tr.select_one(ARCHETYPE_LINK_SELECTOR)
        if link is None:
            continue
        href = link.get("href", "")
        archetype_id = _query_param(href, "a")
        name = link.get_text(strip=True)
        if not archetype_id or not name or archetype_id in seen:
            continue
        seen.add(archetype_id)
        share: Decimal | None = None
        for td in tr.find_all("td"):
            if td.find("a") is None:
                share = _parse_share(td.get_text(strip=True))
                if share is not None:
                    break
        rows.append(
            {
                "archetype": name,
                "external_id": archetype_id,
                "meta_share_pct": share,
                "href": href,
            }
        )
    if not rows:
        log.warning("mtgtop8_meta_page_no_archetypes")
    # stable sort: page order breaks ties; missing share goes last
    rows.sort(key=lambda r: (r["meta_share_pct"] is None, -(r["meta_share_pct"] or 0)))
    return rows


def _parse_archetype_page(html: str) -> dict | None:
    """First deck row of an archetype page → ``deck_id``, ``event_id``, ``event_date``."""
    soup = BeautifulSoup(html, "html.parser")
    for tr in soup.select(ROW_SELECTOR):
        link = tr.select_one(DECK_LINK_SELECTOR)
        if link is None:
            continue
        href = link.get("href", "")
        deck_id = _query_param(href, "d")
        if not deck_id:
            continue
        event_date: date | None = None
        cells = tr.find_all("td")
        if cells:
            match = _DATE_RE.search(cells[-1].get_text(strip=True))
            if match:
                try:
                    event_date = datetime.strptime(match.group(1), "%d/%m/%y").date()
                except ValueError:
                    event_date = None
        return {
            "deck_id": deck_id,
            "event_id": _query_param(href, "e"),
            "event_date": event_date,
        }
    return None


def _parse_decklist(text: str) -> tuple[MetaCardEntry, ...]:
    """MTGO text export → main entries, then side entries after ``Sideboard``."""
    main_lines: list[str] = []
    side_lines: list[str] = []
    current = main_lines
    for raw in text.splitlines():
        line = raw.strip()
        if line.lower().rstrip(":") == SIDEBOARD_HEADER:
            current = side_lines
            continue
        current.append(_QTY_X_RE.sub(r"\1 ", line))

    entries: list[MetaCardEntry] = []
    for board, lines in (("main", main_lines), ("side", side_lines)):
        for card in parse_deck_text("\n".join(lines)):
            if card["quantity"] <= 0:
                continue
            entries.append(
                MetaCardEntry(
                    name=card["name_en"],
                    quantity=card["quantity"],
                    board=board,
                    set_code=card["set_code"],
                    collector_number=card["collector_number"],
                )
            )
    return tuple(entries)


class Mtgtop8Source:
    name = "mtgtop8"
    formats: tuple[str, ...] = tuple(FORMAT_CODES)

    def __init__(self, fetcher: PoliteFetcher) -> None:
        self._fetcher = fetcher

    def fetch_top_decks(self, fmt: str, *, limit: int = 20) -> list[MetaDeckEntry]:
        code = FORMAT_CODES.get(fmt)
        if code is None:
            raise ValueError(f"mtgtop8 does not support format {fmt!r}")
        if limit <= 0:
            return []

        meta_html = self._fetcher.get_text(f"{BASE_URL}format?f={code}")
        decks: list[MetaDeckEntry] = []
        for rank, row in enumerate(_parse_meta_page(meta_html), start=1):
            if len(decks) >= limit:
                break
            deck = self._build_deck(fmt, code, rank, row)
            if deck is not None:
                decks.append(deck)
        return decks

    def _build_deck(self, fmt: str, code: str, rank: int, row: dict) -> MetaDeckEntry | None:
        archetype = row["archetype"]
        try:
            arch_html = self._fetcher.get_text(urljoin(BASE_URL, row["href"]))
            info = _parse_archetype_page(arch_html)
            if info is None:
                log.warning("mtgtop8_archetype_no_decks", format=fmt, archetype=archetype)
                return None
            text = self._fetcher.get_text(
                f"{BASE_URL}mtgo?d={info['deck_id']}", ttl_hours=DECKLIST_TTL_HOURS
            )
            cards = _parse_decklist(text)
        except (FetchError, RobotsDisallowed, httpx.HTTPError) as exc:
            log.warning(
                "mtgtop8_archetype_skipped", format=fmt, archetype=archetype, error=str(exc)
            )
            return None
        if not any(c.board == "main" for c in cards):
            log.warning("mtgtop8_empty_decklist", format=fmt, archetype=archetype)
            return None

        source_url = f"{BASE_URL}event?e={info['event_id']}&d={info['deck_id']}&f={code}"
        if not info["event_id"]:
            source_url = urljoin(BASE_URL, row["href"])
        return MetaDeckEntry(
            source=self.name,
            format=fmt,
            external_id=row["external_id"],
            archetype=archetype,
            rank=rank,
            meta_share_pct=row["meta_share_pct"],
            deck_count=None,
            colors=None,
            commander_name=None,
            source_url=source_url,
            event_date=info["event_date"],
            cards=cards,
        )
