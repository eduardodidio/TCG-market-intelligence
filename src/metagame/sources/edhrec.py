"""EDHREC adapter — Commander metagame source (F173-T07).

URLs, keys and cache policy come from ADR 0016. EDHREC's JSON is not an
official API, so every key lives in a constant here and any malformed entry is
skipped with a structlog warning instead of aborting the whole format (F11).
"""

from __future__ import annotations

import re

import structlog

from src.metagame.http import FetchError, PoliteFetcher, RobotsDisallowed
from src.metagame.sources.base import MetaCardEntry, MetaDeckEntry, normalize_colors

log = structlog.get_logger()

TOP_LIST_URL = "https://json.edhrec.com/pages/commanders/year.json"
DECKLIST_URL = "https://json.edhrec.com/pages/average-decks/{slug}.json"
SOURCE_URL = "https://edhrec.com/average-decks/{slug}"

LIST_TTL_HOURS = 24
DECKLIST_TTL_HOURS = 24 * 7

# top list: container.json_dict.cardlists[*].cardviews[*]
KEY_CONTAINER = "container"
KEY_JSON_DICT = "json_dict"
KEY_CARDLISTS = "cardlists"
KEY_CARDVIEWS = "cardviews"
KEY_NAME = "name"
KEY_SLUG = "sanitized"
KEY_NUM_DECKS = "num_decks"
KEY_COLORS = "color_identity"
# decklist
KEY_DECK = "deck"
KEY_COMMANDER = "commander"

_LINE_RE = re.compile(r"^\s*(?:(\d+)x?\s+)?(.+?)\s*$")
_SPACES_RE = re.compile(r"\s+")


def _normalize_name(name: str) -> str:
    """Collapse whitespace; keep ``//`` of split cards with single spaces around it."""
    name = _SPACES_RE.sub(" ", name).strip()
    return re.sub(r"\s*//\s*", " // ", name)


def _parse_top_list(payload: object) -> list[dict]:
    """Extract commanders from the top-list payload, in list order.

    Returns dicts with ``name``, ``slug``, ``deck_count``, ``colors``. Entries
    without ``name``/``sanitized`` are skipped; duplicate slugs keep the first.
    """
    try:
        cardlists = payload[KEY_CONTAINER][KEY_JSON_DICT][KEY_CARDLISTS]  # type: ignore[index]
    except (KeyError, TypeError, IndexError):
        log.warning("edhrec_top_list_unexpected_shape")
        return []
    if not isinstance(cardlists, list):
        log.warning("edhrec_top_list_unexpected_shape")
        return []

    result: list[dict] = []
    seen: set[str] = set()
    for cardlist in cardlists:
        views = cardlist.get(KEY_CARDVIEWS) if isinstance(cardlist, dict) else None
        if not isinstance(views, list):
            continue
        for view in views:
            if not isinstance(view, dict):
                log.warning("edhrec_commander_skipped", reason="not an object")
                continue
            name = view.get(KEY_NAME)
            slug = view.get(KEY_SLUG)
            if not (isinstance(name, str) and name.strip()) or not (
                isinstance(slug, str) and slug.strip()
            ):
                log.warning("edhrec_commander_skipped", reason="missing name/sanitized", slug=slug)
                continue
            slug = slug.strip()
            if slug in seen:
                continue
            seen.add(slug)

            num_decks = view.get(KEY_NUM_DECKS)
            is_count = isinstance(num_decks, int) and not isinstance(num_decks, bool)
            deck_count = num_decks if is_count else None
            identity = view.get(KEY_COLORS)
            colors = (
                normalize_colors("".join(c for c in identity if isinstance(c, str)))
                if isinstance(identity, list)
                else None
            )
            result.append(
                {
                    "name": _normalize_name(name),
                    "slug": slug,
                    "deck_count": deck_count,
                    "colors": colors,
                }
            )
    return result


def _parse_decklist(
    payload: object, commander_name: str | None = None
) -> tuple[MetaCardEntry, ...]:
    """Parse ``deck[]`` lines (``"<qty> <name>"``) into card entries.

    The line matching the commander (payload ``commander`` or ``commander_name``)
    gets ``board="commander"``. Missing quantity → 1. Blank/invalid lines are
    skipped with a warning. Unexpected payload shape → empty tuple.
    """
    if not isinstance(payload, dict) or not isinstance(payload.get(KEY_DECK), list):
        log.warning("edhrec_decklist_unexpected_shape")
        return ()

    commander = payload.get(KEY_COMMANDER)
    if not isinstance(commander, str) or not commander.strip():
        commander = commander_name
    commander_key = _normalize_name(commander).casefold() if commander else None

    cards: list[MetaCardEntry] = []
    for line in payload[KEY_DECK]:
        if not isinstance(line, str):
            log.warning("edhrec_card_skipped", reason="not a string", line=repr(line))
            continue
        match = _LINE_RE.match(line)
        if not match or not match.group(2).strip():
            log.warning("edhrec_card_skipped", reason="unparseable line", line=line)
            continue
        qty = int(match.group(1)) if match.group(1) else 1
        if qty <= 0:
            log.warning("edhrec_card_skipped", reason="non-positive quantity", line=line)
            continue
        name = _normalize_name(match.group(2))
        board = "commander" if commander_key and name.casefold() == commander_key else "main"
        cards.append(MetaCardEntry(name=name, quantity=qty, board=board))
    return tuple(cards)


class EdhrecSource:
    name = "edhrec"
    formats: tuple[str, ...] = ("commander",)

    def __init__(self, fetcher: PoliteFetcher) -> None:
        self._fetcher = fetcher

    def fetch_top_decks(self, fmt: str, *, limit: int = 20) -> list[MetaDeckEntry]:
        if fmt not in self.formats:
            raise ValueError(f"EdhrecSource does not support format {fmt!r}")
        if limit <= 0:
            return []

        try:
            payload = self._fetcher.get_json(TOP_LIST_URL, ttl_hours=LIST_TTL_HOURS)
        except (FetchError, RobotsDisallowed) as exc:
            log.warning("edhrec_top_list_failed", url=TOP_LIST_URL, error=str(exc))
            return []

        decks: list[MetaDeckEntry] = []
        for rank, commander in enumerate(_parse_top_list(payload)[:limit], start=1):
            deck = self._build_deck(rank, commander)
            if deck is not None:
                decks.append(deck)
        return decks

    def _build_deck(self, rank: int, commander: dict) -> MetaDeckEntry | None:
        slug = commander["slug"]
        url = DECKLIST_URL.format(slug=slug)
        try:
            payload = self._fetcher.get_json(url, ttl_hours=DECKLIST_TTL_HOURS)
        except (FetchError, RobotsDisallowed) as exc:
            log.warning("edhrec_decklist_failed", slug=slug, url=url, error=str(exc))
            return None

        cards = _parse_decklist(payload, commander["name"])
        if not cards:
            log.warning("edhrec_deck_skipped", slug=slug, reason="empty decklist")
            return None
        if not any(c.board == "commander" for c in cards):
            # The average deck should list its commander; add it so the deck is complete.
            cards = (MetaCardEntry(name=commander["name"], quantity=1, board="commander"), *cards)

        return MetaDeckEntry(
            source=self.name,
            format="commander",
            external_id=slug,
            archetype=commander["name"],
            rank=rank,
            meta_share_pct=None,
            deck_count=commander["deck_count"],
            colors=commander["colors"],
            commander_name=commander["name"],
            source_url=SOURCE_URL.format(slug=slug),
            event_date=None,
            cards=cards,
        )
