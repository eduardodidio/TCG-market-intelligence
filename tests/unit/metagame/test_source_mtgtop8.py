"""Tests for the MTGTop8 constructed-format adapter (F173-T08). No network."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from pathlib import Path

import httpx
import pytest

from src.metagame.http import FetchError, RobotsDisallowed
from src.metagame.sources.base import MetaSource
from src.metagame.sources.mtgtop8 import (
    DECKLIST_TTL_HOURS,
    FORMAT_CODES,
    Mtgtop8Source,
    _parse_archetype_page,
    _parse_decklist,
    _parse_meta_page,
    _parse_share,
)

FIXTURES = Path(__file__).resolve().parents[2] / "fixtures" / "metagame" / "mtgtop8"
BASE = "https://www.mtgtop8.com/"


def _fixture(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


def _archetype_html(deck_id: str, event_id: str = "61001") -> str:
    return (
        _fixture("archetype_MO_1452.html")
        .replace("d=712345", f"d={deck_id}")
        .replace("e=61001&amp;d", f"e={event_id}&amp;d")
    )


class FakeFetcher:
    """Serves canned text by URL; raises for unknown URLs or mapped exceptions."""

    def __init__(self, pages: dict[str, str | Exception]) -> None:
        self.pages = pages
        self.calls: list[tuple[str, float | None]] = []

    def get_text(self, url: str, *, ttl_hours: float | None = None, use_cache: bool = True) -> str:
        self.calls.append((url, ttl_hours))
        page = self.pages.get(url)
        if page is None:
            raise FetchError(f"no fixture for {url}")
        if isinstance(page, Exception):
            raise page
        return page


def _modern_pages() -> dict[str, str | Exception]:
    return {
        f"{BASE}format?f=MO": _fixture("format_MO.html"),
        f"{BASE}archetype?a=1452&meta=44&f=MO": _fixture("archetype_MO_1452.html"),
        f"{BASE}mtgo?d=712345": _fixture("decklist_boros-energy.txt"),
        f"{BASE}archetype?a=1399&meta=44&f=MO": _archetype_html("800001", "61002"),
        f"{BASE}mtgo?d=800001": _fixture("decklist_ruby-storm.txt"),
        f"{BASE}archetype?a=1287&meta=44&f=MO": _archetype_html("800002"),
        f"{BASE}mtgo?d=800002": _fixture("decklist_boros-energy.txt"),
        f"{BASE}archetype?a=1105&meta=44&f=MO": _archetype_html("800003"),
        f"{BASE}mtgo?d=800003": _fixture("decklist_ruby-storm.txt"),
        f"{BASE}archetype?a=999&meta=44&f=MO": _archetype_html("800004"),
        f"{BASE}mtgo?d=800004": _fixture("decklist_boros-energy.txt"),
    }


def _qty(cards, board: str) -> int:
    return sum(c.quantity for c in cards if c.board == board)


# ── _parse_share ─────────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("12.5 %", Decimal("12.5")),
        ("12,5%", Decimal("12.5")),
        ("18 %", Decimal("18")),
        ("0 %", Decimal("0")),
        ("", None),
        (None, None),
        ("n/a", None),
    ],
)
def test_parse_share(text, expected):
    assert _parse_share(text) == expected


# ── _parse_meta_page ─────────────────────────────────────────────────────────


def test_parse_meta_page_orders_by_share_and_ignores_events():
    rows = _parse_meta_page(_fixture("format_MO.html"))
    assert [r["archetype"] for r in rows] == [
        "Boros Energy",
        "Ruby Storm",
        "Amulet Titan",
        "Eldrazi Tron",
        "Rogue Brew",
    ]
    assert [r["meta_share_pct"] for r in rows] == [
        Decimal("18"),
        Decimal("9.5"),
        Decimal("7.5"),
        Decimal("6"),
        None,
    ]
    assert rows[0]["external_id"] == "1452"
    assert rows[0]["href"] == "archetype?a=1452&meta=44&f=MO"


def test_parse_meta_page_sorts_unordered_rows_and_skips_bad_links():
    html = """
    <table>
     <tr class="hover_tr"><td><a href="archetype?a=2">Low</a></td><td>3 %</td></tr>
     <tr class="hover_tr"><td><a href="archetype?a=">No id</a></td><td>50 %</td></tr>
     <tr class="hover_tr"><td><a href="archetype?a=9"></a></td><td>40 %</td></tr>
     <tr class="hover_tr"><td><a href="archetype?a=1">High</a></td><td>12,5%</td></tr>
     <tr class="hover_tr"><td><a href="archetype?a=1">High dup</a></td><td>1 %</td></tr>
     <tr class="hover_tr"><td><a href="archetype?a=3">Blank</a></td></tr>
    </table>
    """
    rows = _parse_meta_page(html)
    assert [(r["external_id"], r["meta_share_pct"]) for r in rows] == [
        ("1", Decimal("12.5")),
        ("2", Decimal("3")),
        ("3", None),
    ]


def test_parse_meta_page_without_table_returns_empty(caplog):
    assert _parse_meta_page("<html><body><p>Maintenance</p></body></html>") == []


# ── _parse_archetype_page ────────────────────────────────────────────────────


def test_parse_archetype_page_picks_first_deck_row():
    info = _parse_archetype_page(_fixture("archetype_MO_1452.html"))
    assert info == {"deck_id": "712345", "event_id": "61001", "event_date": date(2026, 9, 21)}


def test_parse_archetype_page_bad_or_missing_date():
    html = """
    <tr class="hover_tr"><td>header</td></tr>
    <tr class="hover_tr"><td><a href="event?e=1">no deck id</a></td></tr>
    <tr class="hover_tr"><td><a href="event?e=5&d=77&f=MO">Deck</a></td><td>31/02/26</td></tr>
    """
    assert _parse_archetype_page(html) == {"deck_id": "77", "event_id": "5", "event_date": None}

    no_date = '<tr class="hover_tr"><td><a href="event?d=8">Deck</a></td><td>yesterday</td></tr>'
    assert _parse_archetype_page(no_date) == {"deck_id": "8", "event_id": None, "event_date": None}


def test_parse_archetype_page_without_decks():
    assert _parse_archetype_page("<table></table>") is None


# ── _parse_decklist ──────────────────────────────────────────────────────────


def test_parse_decklist_boros_energy_60_plus_15():
    cards = _parse_decklist(_fixture("decklist_boros-energy.txt"))
    assert _qty(cards, "main") == 60
    assert _qty(cards, "side") == 15
    assert cards[0].name == "Guide of Souls" and cards[0].quantity == 4
    assert any(c.name == "Wear // Tear" and c.board == "side" for c in cards)
    assert {c.board for c in cards} == {"main", "side"}


def test_parse_decklist_handles_1x_prefix():
    cards = _parse_decklist(_fixture("decklist_ruby-storm.txt"))
    assert _qty(cards, "main") == 60
    assert _qty(cards, "side") == 15
    relay = next(c for c in cards if c.name == "Galvanic Relay")
    assert relay.quantity == 1 and relay.board == "main"


def test_parse_decklist_edge_lines():
    text = "\n\n4x Lightning Bolt\n\n2 Opt [dmu]\n0 Ghost Card\nSideboard:\n\n1X Pyroblast\n"
    cards = _parse_decklist(text)
    assert [(c.name, c.quantity, c.board, c.set_code) for c in cards] == [
        ("Lightning Bolt", 4, "main", None),
        ("Opt", 2, "main", "dmu"),
        ("Pyroblast", 1, "side", None),
    ]


def test_parse_decklist_empty():
    assert _parse_decklist("") == ()


# ── Mtgtop8Source ────────────────────────────────────────────────────────────


def test_source_satisfies_protocol_and_formats():
    source: MetaSource = Mtgtop8Source(FakeFetcher({}))
    assert source.name == "mtgtop8"
    assert source.formats == ("standard", "pioneer", "modern", "legacy", "vintage", "pauper")
    assert set(FORMAT_CODES.values()) == {"ST", "PI", "MO", "LE", "VI", "PAU"}


def test_fetch_top_decks_modern_happy_path():
    fetcher = FakeFetcher(_modern_pages())
    decks = Mtgtop8Source(fetcher).fetch_top_decks("modern")

    assert [d.rank for d in decks] == [1, 2, 3, 4, 5]
    assert decks[0].archetype == "Boros Energy"
    assert decks[0].meta_share_pct == Decimal("18")
    assert decks[-1].meta_share_pct is None
    shares = [d.meta_share_pct for d in decks if d.meta_share_pct is not None]
    assert shares == sorted(shares, reverse=True)

    top = decks[0]
    assert top.source == "mtgtop8"
    assert top.format == "modern"
    assert top.external_id == "1452"
    assert top.event_date == date(2026, 9, 21)
    assert top.source_url == f"{BASE}event?e=61001&d=712345&f=MO"
    assert top.deck_count is None and top.colors is None and top.commander_name is None
    assert _qty(top.cards, "main") == 60 and _qty(top.cards, "side") == 15
    assert decks[1].source_url == f"{BASE}event?e=61002&d=800001&f=MO"

    decklist_calls = [ttl for url, ttl in fetcher.calls if "mtgo?d=" in url]
    assert decklist_calls and all(ttl == DECKLIST_TTL_HOURS for ttl in decklist_calls)


def test_fetch_top_decks_unsupported_format():
    fetcher = FakeFetcher({})
    with pytest.raises(ValueError):
        Mtgtop8Source(fetcher).fetch_top_decks("commander")
    with pytest.raises(ValueError):
        Mtgtop8Source(fetcher).fetch_top_decks("brawl")
    assert fetcher.calls == []


@pytest.mark.parametrize(("limit", "expected"), [(0, 0), (-1, 0), (1, 1), (2, 2), (50, 5)])
def test_fetch_top_decks_limit(limit, expected):
    fetcher = FakeFetcher(_modern_pages())
    decks = Mtgtop8Source(fetcher).fetch_top_decks("modern", limit=limit)
    assert len(decks) == expected
    if limit <= 0:
        assert fetcher.calls == []


@pytest.mark.parametrize(
    "failure",
    [
        FetchError("boom"),
        RobotsDisallowed("nope"),
        httpx.ConnectError("down"),
        "",  # empty decklist
        "Sideboard\n1 Pyroblast\n",  # no main deck
    ],
)
def test_failed_decklist_skips_archetype(failure):
    pages = _modern_pages()
    pages[f"{BASE}mtgo?d=800001"] = failure
    decks = Mtgtop8Source(FakeFetcher(pages)).fetch_top_decks("modern")
    assert [d.archetype for d in decks] == [
        "Boros Energy",
        "Amulet Titan",
        "Eldrazi Tron",
        "Rogue Brew",
    ]
    assert decks[1].rank == 3  # rank keeps meta-share position


def test_archetype_page_without_decks_is_skipped():
    pages = _modern_pages()
    pages[f"{BASE}archetype?a=1452&meta=44&f=MO"] = "<html></html>"
    decks = Mtgtop8Source(FakeFetcher(pages)).fetch_top_decks("modern", limit=1)
    assert [d.archetype for d in decks] == ["Ruby Storm"]


def test_limit_counts_only_successful_decks():
    pages = _modern_pages()
    pages[f"{BASE}mtgo?d=712345"] = FetchError("boom")
    decks = Mtgtop8Source(FakeFetcher(pages)).fetch_top_decks("modern", limit=2)
    assert [d.rank for d in decks] == [2, 3]


def test_meta_page_without_table_returns_empty():
    fetcher = FakeFetcher({f"{BASE}format?f=ST": "<html><body>nothing</body></html>"})
    assert Mtgtop8Source(fetcher).fetch_top_decks("standard") == []


def test_meta_page_fetch_error_propagates():
    with pytest.raises(FetchError):
        Mtgtop8Source(FakeFetcher({})).fetch_top_decks("pauper")


def test_source_url_falls_back_to_archetype_when_no_event_id():
    pages = {
        f"{BASE}format?f=LE": (
            '<tr class="hover_tr"><td><a href="archetype?a=7&f=LE">Doomsday</a></td>'
            "<td>10 %</td></tr>"
        ),
        f"{BASE}archetype?a=7&f=LE": (
            '<tr class="hover_tr"><td><a href="event?d=55">x</a></td></tr>'
        ),
        f"{BASE}mtgo?d=55": "4 Doomsday\n",
    }
    decks = Mtgtop8Source(FakeFetcher(pages)).fetch_top_decks("legacy")
    assert len(decks) == 1
    assert decks[0].source_url == f"{BASE}archetype?a=7&f=LE"
    assert decks[0].event_date is None
