"""Tests for EdhrecSource (F173-T07). No network: a FakeFetcher serves fixtures."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from structlog.testing import capture_logs

from src.metagame.http import FetchError, RobotsDisallowed
from src.metagame.sources.base import MetaCardEntry
from src.metagame.sources.edhrec import (
    DECKLIST_TTL_HOURS,
    DECKLIST_URL,
    LIST_TTL_HOURS,
    TOP_LIST_URL,
    EdhrecSource,
    _parse_decklist,
    _parse_top_list,
)

FIXTURES = Path(__file__).resolve().parents[2] / "fixtures" / "metagame" / "edhrec"


def _load(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def _fixture_routes() -> dict[str, object]:
    routes: dict[str, object] = {TOP_LIST_URL: _load("top_commanders.json")}
    for path in FIXTURES.glob("decklist_*.json"):
        slug = path.stem.removeprefix("decklist_")
        routes[DECKLIST_URL.format(slug=slug)] = _load(path.name)
    return routes


class FakeFetcher:
    """Maps URL → payload (or exception). Unknown URLs raise FetchError."""

    def __init__(self, routes: dict[str, object]) -> None:
        self.routes = routes
        self.calls: list[tuple[str, float | None]] = []

    def get_json(self, url: str, *, ttl_hours: float | None = None, use_cache: bool = True):
        self.calls.append((url, ttl_hours))
        value = self.routes.get(url)
        if value is None:
            raise FetchError(f"HTTP 404 from {url}")
        if isinstance(value, Exception):
            raise value
        return value

    def decklist_calls(self) -> list[str]:
        return [u for u, _ in self.calls if "/average-decks/" in u]


def _top_list(*views: dict) -> dict:
    return {"container": {"json_dict": {"cardlists": [{"cardviews": list(views)}]}}}


def _view(name: str, slug: str, num_decks=10, colors=("R",)) -> dict:
    return {"name": name, "sanitized": slug, "num_decks": num_decks, "color_identity": list(colors)}


# ── happy path ──────────────────────────────────────────────────────────────


def test_fetch_top_decks_from_fixtures_returns_ranked_decks():
    fetcher = FakeFetcher(_fixture_routes())
    source = EdhrecSource(fetcher)

    decks = source.fetch_top_decks("commander", limit=4)

    # Only atraxa (#1) and krenko (#4) have decklist fixtures; the others 404 and are skipped.
    assert [d.external_id for d in decks] == ["atraxa-praetors-voice", "krenko-mob-boss"]
    assert [d.rank for d in decks] == [1, 4]
    atraxa = decks[0]
    assert atraxa.source == "edhrec"
    assert atraxa.format == "commander"
    assert atraxa.archetype == "Atraxa, Praetors' Voice"
    assert atraxa.commander_name == "Atraxa, Praetors' Voice"
    assert atraxa.deck_count == 41872
    assert atraxa.meta_share_pct is None
    assert atraxa.colors == "WUBG"
    assert atraxa.event_date is None
    assert atraxa.source_url == "https://edhrec.com/average-decks/atraxa-praetors-voice"
    assert sum(c.quantity for c in atraxa.cards) == 100
    commanders = [c for c in atraxa.cards if c.board == "commander"]
    assert commanders == [MetaCardEntry("Atraxa, Praetors' Voice", 1, "commander")]
    assert decks[1].colors == "R"
    assert sum(c.quantity for c in decks[1].cards) == 100


def test_fetch_uses_adr_cache_ttls():
    fetcher = FakeFetcher(_fixture_routes())
    EdhrecSource(fetcher).fetch_top_decks("commander", limit=1)
    assert fetcher.calls == [
        (TOP_LIST_URL, LIST_TTL_HOURS),
        (DECKLIST_URL.format(slug="atraxa-praetors-voice"), DECKLIST_TTL_HOURS),
    ]
    assert DECKLIST_TTL_HOURS == 168
    assert LIST_TTL_HOURS == 24


def test_source_metadata():
    assert EdhrecSource.name == "edhrec"
    assert EdhrecSource.formats == ("commander",)


# ── limits / request count ──────────────────────────────────────────────────


def test_limit_one_makes_one_decklist_request():
    fetcher = FakeFetcher(_fixture_routes())
    decks = EdhrecSource(fetcher).fetch_top_decks("commander", limit=1)
    assert len(decks) == 1
    assert decks[0].rank == 1
    assert len(fetcher.calls) == 2
    assert len(fetcher.decklist_calls()) == 1


def test_limit_n_makes_one_plus_n_requests():
    fetcher = FakeFetcher(_fixture_routes())
    EdhrecSource(fetcher).fetch_top_decks("commander", limit=3)
    assert len(fetcher.calls) == 1 + 3


def test_limit_greater_than_list_returns_what_exists():
    view_a = _view("Alpha", "alpha")
    view_b = _view("Beta", "beta")
    deck = {"commander": "Alpha", "deck": ["1 Alpha", "99 Mountain"]}
    fetcher = FakeFetcher(
        {
            TOP_LIST_URL: _top_list(view_a, view_b),
            DECKLIST_URL.format(slug="alpha"): deck,
            DECKLIST_URL.format(slug="beta"): {"deck": ["1 Beta", "99 Island"]},
        }
    )
    decks = EdhrecSource(fetcher).fetch_top_decks("commander", limit=50)
    assert [d.rank for d in decks] == [1, 2]
    assert len(fetcher.decklist_calls()) == 2


def test_limit_zero_makes_no_requests():
    fetcher = FakeFetcher(_fixture_routes())
    assert EdhrecSource(fetcher).fetch_top_decks("commander", limit=0) == []
    assert fetcher.calls == []


# ── errors ──────────────────────────────────────────────────────────────────


@pytest.mark.parametrize("fmt", ["modern", "standard", "", "Commander"])
def test_unsupported_format_raises(fmt):
    fetcher = FakeFetcher(_fixture_routes())
    with pytest.raises(ValueError):
        EdhrecSource(fetcher).fetch_top_decks(fmt)
    assert fetcher.calls == []


def test_decklist_fetch_error_skips_only_that_deck():
    routes = _fixture_routes()
    routes[DECKLIST_URL.format(slug="atraxa-praetors-voice")] = FetchError("boom")
    fetcher = FakeFetcher(routes)
    with capture_logs() as logs:
        decks = EdhrecSource(fetcher).fetch_top_decks("commander", limit=4)
    assert [d.external_id for d in decks] == ["krenko-mob-boss"]
    assert any(e["event"] == "edhrec_decklist_failed" for e in logs)


def test_robots_disallowed_decklist_is_skipped():
    routes = _fixture_routes()
    routes[DECKLIST_URL.format(slug="atraxa-praetors-voice")] = RobotsDisallowed("x")
    decks = EdhrecSource(FakeFetcher(routes)).fetch_top_decks("commander", limit=1)
    assert decks == []


def test_top_list_fetch_error_returns_empty_with_warning():
    fetcher = FakeFetcher({TOP_LIST_URL: FetchError("down")})
    with capture_logs() as logs:
        assert EdhrecSource(fetcher).fetch_top_decks("commander") == []
    assert any(e["event"] == "edhrec_top_list_failed" for e in logs)


def test_top_list_without_expected_key_returns_empty_with_warning():
    fetcher = FakeFetcher({TOP_LIST_URL: {"header": "changed"}})
    with capture_logs() as logs:
        assert EdhrecSource(fetcher).fetch_top_decks("commander") == []
    assert any(e["event"] == "edhrec_top_list_unexpected_shape" for e in logs)
    assert fetcher.decklist_calls() == []


def test_decklist_without_deck_key_skips_deck():
    fetcher = FakeFetcher(
        {
            TOP_LIST_URL: _top_list(_view("Alpha", "alpha")),
            DECKLIST_URL.format(slug="alpha"): {"commander": "Alpha"},
        }
    )
    with capture_logs() as logs:
        assert EdhrecSource(fetcher).fetch_top_decks("commander") == []
    events = {e["event"] for e in logs}
    assert {"edhrec_decklist_unexpected_shape", "edhrec_deck_skipped"} <= events


# ── _parse_top_list ─────────────────────────────────────────────────────────


def test_parse_top_list_fixture_skips_entry_without_name():
    with capture_logs() as logs:
        entries = _parse_top_list(_load("top_commanders.json"))
    assert len(entries) == 5
    assert entries[0] == {
        "name": "Atraxa, Praetors' Voice",
        "slug": "atraxa-praetors-voice",
        "deck_count": 41872,
        "colors": "WUBG",
    }
    assert "missing-name-entry" not in [e["slug"] for e in entries]
    assert any(e["event"] == "edhrec_commander_skipped" for e in logs)


@pytest.mark.parametrize(
    "payload",
    [None, [], "x", {"container": None}, {"container": {"json_dict": {}}},
     {"container": {"json_dict": {"cardlists": "nope"}}}],
)
def test_parse_top_list_bad_shapes_return_empty(payload):
    assert _parse_top_list(payload) == []


def test_parse_top_list_edge_values():
    payload = {
        "container": {
            "json_dict": {
                "cardlists": [
                    "not-a-dict",
                    {"cardviews": None},
                    {
                        "cardviews": [
                            "not-a-dict",
                            {"name": "  Kenrith ,  the   Returned King ", "sanitized": " kenrith "},
                            {"name": "Dup", "sanitized": "kenrith"},
                            {"name": "", "sanitized": "empty"},
                            {"name": "No Slug"},
                            _view("Colorless", "colorless", num_decks=True, colors=()),
                            _view("Bad Colors", "bad-colors", num_decks="12", colors=("x", 3)),
                        ]
                    },
                ]
            }
        }
    }
    entries = _parse_top_list(payload)
    assert [e["slug"] for e in entries] == ["kenrith", "colorless", "bad-colors"]
    assert entries[0]["name"] == "Kenrith , the Returned King"
    assert entries[0]["deck_count"] is None
    assert entries[0]["colors"] is None
    assert entries[1]["deck_count"] is None  # bool is not a count
    assert entries[1]["colors"] is None
    assert entries[2]["deck_count"] is None
    assert entries[2]["colors"] is None


def test_parse_top_list_merges_multiple_cardlists_in_order():
    payload = {
        "container": {
            "json_dict": {
                "cardlists": [
                    {"cardviews": [_view("A", "a")]},
                    {"cardviews": [_view("B", "b"), _view("A again", "a")]},
                ]
            }
        }
    }
    assert [e["name"] for e in _parse_top_list(payload)] == ["A", "B"]


# ── _parse_decklist ─────────────────────────────────────────────────────────


def test_parse_decklist_fixture_preserves_split_cards():
    cards = _parse_decklist(_load("decklist_atraxa-praetors-voice.json"))
    names = [c.name for c in cards]
    assert "Fire // Ice" in names
    assert "Wear // Tear" in names
    assert "Commit // Memory" in names
    assert sum(c.quantity for c in cards) == 100
    assert cards[0].board == "commander"
    assert all(c.board == "main" for c in cards[1:])


def test_parse_decklist_missing_quantity_defaults_to_one_and_normalizes():
    payload = {
        "commander": "Alpha",
        "deck": ["Alpha", "Sol   Ring", "2x Island", "3 Fire//Ice", "  ", 7, "0 Forest"],
    }
    with capture_logs() as logs:
        cards = _parse_decklist(payload)
    assert cards == (
        MetaCardEntry("Alpha", 1, "commander"),
        MetaCardEntry("Sol Ring", 1, "main"),
        MetaCardEntry("Island", 2, "main"),
        MetaCardEntry("Fire // Ice", 3, "main"),
    )
    assert sum(1 for e in logs if e["event"] == "edhrec_card_skipped") == 3


def test_parse_decklist_uses_fallback_commander_name():
    cards = _parse_decklist({"deck": ["1 Alpha", "1 Sol Ring"]}, "Alpha")
    assert cards[0].board == "commander"
    assert cards[1].board == "main"


def test_parse_decklist_without_any_commander_name_is_all_main():
    cards = _parse_decklist({"deck": ["1 Alpha"]})
    assert cards == (MetaCardEntry("Alpha", 1, "main"),)


@pytest.mark.parametrize("payload", [None, [], {"deck": "1 Sol Ring"}, {"cards": []}])
def test_parse_decklist_bad_shapes_return_empty(payload):
    assert _parse_decklist(payload) == ()


def test_commander_missing_from_deck_is_prepended():
    fetcher = FakeFetcher(
        {
            TOP_LIST_URL: _top_list(_view("Alpha", "alpha")),
            DECKLIST_URL.format(slug="alpha"): {"deck": ["99 Mountain"]},
        }
    )
    with capture_logs():
        (deck,) = EdhrecSource(fetcher).fetch_top_decks("commander")
    assert deck.cards[0] == MetaCardEntry("Alpha", 1, "commander")
    assert sum(c.quantity for c in deck.cards) == 100
