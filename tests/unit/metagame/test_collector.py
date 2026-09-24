"""Tests for the metagame collector service (F173-T09)."""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import MagicMock

import pytest
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session

from src.database.models import Base, CardRow, UserCollectionRow
from src.metagame.collector import CollectStats, collect_metagame
from src.metagame.http import FetchError, RobotsDisallowed
from src.metagame.models import MetaDeckCardRow, MetaDeckRow
from src.metagame.repository import MetagameRepository
from src.metagame.sources.base import MetaCardEntry, MetaDeckEntry

TODAY = date(2026, 9, 24)


class FakeSource:
    def __init__(self, name, decks_by_format=None, exc=None):
        self.name = name
        self.formats = tuple((decks_by_format or {}).keys())
        self._decks = decks_by_format or {}
        self._exc = exc
        self.calls: list[tuple[str, int]] = []

    def fetch_top_decks(self, fmt, *, limit=20):
        self.calls.append((fmt, limit))
        if self._exc is not None:
            raise self._exc
        return list(self._decks.get(fmt, []))[:limit]


def _deck(fmt, external_id, rank, cards):
    return MetaDeckEntry(
        source="fake",
        format=fmt,
        external_id=external_id,
        archetype=f"Arch {external_id}",
        rank=rank,
        meta_share_pct=Decimal("10.0"),
        deck_count=5,
        colors="UR",
        commander_name=None,
        source_url=f"https://example.test/{external_id}",
        event_date=None,
        cards=tuple(cards),
    )


def _decks(fmt, n=3, cards=None):
    cards = cards or [MetaCardEntry("Lightning Bolt", 4), MetaCardEntry("Mystery Card", 2)]
    return [_deck(fmt, f"{fmt}-{i}", i, cards) for i in range(1, n + 1)]


@pytest.fixture
def engine():
    eng = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(eng, tables=[CardRow.__table__, UserCollectionRow.__table__])
    return eng


@pytest.fixture
def repo(engine):
    return MetagameRepository(engine)


@pytest.fixture
def bolt_id(engine):
    with Session(engine) as s:
        card = CardRow(game="magic", name_en="Lightning Bolt", set_code="2x2", collector_number="1")
        s.add(card)
        s.commit()
        return card.id


def _count(engine, model):
    with Session(engine) as s:
        return s.execute(select(func.count()).select_from(model)).scalar()


# ── Happy path ──────────────────────────────────────────────────────────


def test_happy_two_formats_three_decks_each(engine, repo, bolt_id):
    sources = {
        "modern": FakeSource("mtgtop8", {"modern": _decks("modern")}),
        "commander": FakeSource("edhrec", {"commander": _decks("commander")}),
    }
    stats = collect_metagame(repo, sources, ["modern", "commander"], snapshot_date=TODAY)

    assert stats == CollectStats(formats=2, decks=6, cards=12, unresolved_cards=6, errors=[])
    assert _count(engine, MetaDeckRow) == 6
    assert _count(engine, MetaDeckCardRow) == 12

    rows, total = repo.list_decks("modern")
    assert total == 3
    assert {r.source for r in rows} == {"mtgtop8"}
    assert rows[0].snapshot_date == TODAY
    cards = repo.get_deck_cards([rows[0].id])[rows[0].id]
    ids = {c.card_name: c.card_id for c in cards}
    assert ids == {"Lightning Bolt": bolt_id, "Mystery Card": None}


def test_idempotent_same_day(engine, repo, bolt_id):
    sources = {"modern": FakeSource("mtgtop8", {"modern": _decks("modern")})}
    collect_metagame(repo, sources, ["modern"], snapshot_date=TODAY)
    stats = collect_metagame(repo, sources, ["modern"], snapshot_date=TODAY)

    assert stats.decks == 3
    assert _count(engine, MetaDeckRow) == 3
    assert _count(engine, MetaDeckCardRow) == 6


def test_different_day_keeps_previous_snapshot(engine, repo):
    sources = {"modern": FakeSource("mtgtop8", {"modern": _decks("modern")})}
    collect_metagame(repo, sources, ["modern"], snapshot_date=TODAY - timedelta(days=7))
    collect_metagame(repo, sources, ["modern"], snapshot_date=TODAY)
    assert _count(engine, MetaDeckRow) == 6
    assert repo.latest_snapshot_date("modern") == TODAY


def test_snapshot_date_defaults_to_today(repo):
    sources = {"modern": FakeSource("mtgtop8", {"modern": _decks("modern", 1)})}
    collect_metagame(repo, sources, ["modern"])
    assert repo.latest_snapshot_date("modern") == date.today()


# ── Edge cases ──────────────────────────────────────────────────────────


def test_dry_run_writes_nothing_but_fills_stats(engine, repo, bolt_id):
    sources = {"modern": FakeSource("mtgtop8", {"modern": _decks("modern")})}
    stats = collect_metagame(repo, sources, ["modern"], snapshot_date=TODAY, dry_run=True)

    assert stats == CollectStats(formats=1, decks=3, cards=6, unresolved_cards=3)
    assert _count(engine, MetaDeckRow) == 0
    assert _count(engine, MetaDeckCardRow) == 0


def test_dry_run_never_calls_replace_snapshot():
    repo = MagicMock(spec=MetagameRepository)
    repo.resolve_card_id.return_value = 1
    sources = {"modern": FakeSource("mtgtop8", {"modern": _decks("modern")})}
    stats = collect_metagame(repo, sources, ["modern"], dry_run=True)
    repo.replace_snapshot.assert_not_called()
    assert stats.unresolved_cards == 0


def test_same_card_across_decks_and_formats_resolved_once():
    repo = MagicMock(spec=MetagameRepository)
    repo.resolve_card_id.return_value = 42
    cards = [MetaCardEntry("Lightning Bolt", 4), MetaCardEntry("lightning bolt", 1, "side")]
    sources = {
        "modern": FakeSource("mtgtop8", {"modern": _decks("modern", cards=cards)}),
        "legacy": FakeSource("mtgtop8", {"legacy": _decks("legacy", cards=cards)}),
    }
    stats = collect_metagame(repo, sources, ["modern", "legacy"], snapshot_date=TODAY)

    repo.resolve_card_id.assert_called_once_with("Lightning Bolt", None, None)
    assert stats.cards == 12
    assert stats.unresolved_cards == 0


def test_cache_distinguishes_printings():
    repo = MagicMock(spec=MetagameRepository)
    repo.resolve_card_id.side_effect = [1, 2]
    cards = [
        MetaCardEntry("Bolt", 1, set_code="a", collector_number="1"),
        MetaCardEntry("Bolt", 1, set_code="b", collector_number="7"),
    ]
    sources = {"modern": FakeSource("s", {"modern": _decks("modern", 2, cards)})}
    collect_metagame(repo, sources, ["modern"])
    assert repo.resolve_card_id.call_count == 2


def test_custom_resolver_is_used_and_cached(engine, repo):
    calls = []

    def resolver(card):
        calls.append(card.name)
        return None

    sources = {"modern": FakeSource("mtgtop8", {"modern": _decks("modern")})}
    stats = collect_metagame(repo, sources, ["modern"], snapshot_date=TODAY, resolver=resolver)

    assert sorted(calls) == ["Lightning Bolt", "Mystery Card"]
    assert stats.unresolved_cards == 6


def test_resolved_ids_passed_to_replace_snapshot():
    repo = MagicMock(spec=MetagameRepository)
    repo.resolve_card_id.side_effect = lambda name, *_: 7 if name == "Lightning Bolt" else None
    decks = _decks("modern", 1)
    sources = {"modern": FakeSource("mtgtop8", {"modern": decks})}
    collect_metagame(repo, sources, ["modern"], snapshot_date=TODAY)

    repo.replace_snapshot.assert_called_once()
    args = repo.replace_snapshot.call_args.args
    assert args[:3] == ("modern", "mtgtop8", TODAY)
    assert args[4] == {("modern-1", "Lightning Bolt"): 7, ("modern-1", "Mystery Card"): None}


def test_duplicate_formats_collected_once():
    repo = MagicMock(spec=MetagameRepository)
    src = FakeSource("mtgtop8", {"modern": _decks("modern")})
    stats = collect_metagame(repo, {"modern": src}, ["modern", "modern"])
    assert len(src.calls) == 1
    assert stats.formats == 1


# ── Errors ──────────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "exc", [FetchError("boom"), RobotsDisallowed("robots says no"), ValueError("parse")]
)
def test_failing_format_isolated(engine, repo, exc):
    sources = {
        "modern": FakeSource("mtgtop8", exc=exc),
        "pauper": FakeSource("mtgtop8", {"pauper": _decks("pauper")}),
    }
    stats = collect_metagame(repo, sources, ["modern", "pauper"], snapshot_date=TODAY)

    assert stats.errors == [f"modern: {exc}"]
    assert stats.formats == 1
    assert stats.decks == 3
    assert repo.list_decks("pauper")[1] == 3
    assert repo.list_decks("modern")[1] == 0


def test_replace_snapshot_failure_isolated():
    repo = MagicMock(spec=MetagameRepository)
    repo.resolve_card_id.return_value = None
    repo.replace_snapshot.side_effect = [RuntimeError("db down"), 3]
    sources = {
        "modern": FakeSource("a", {"modern": _decks("modern")}),
        "legacy": FakeSource("b", {"legacy": _decks("legacy")}),
    }
    stats = collect_metagame(repo, sources, ["modern", "legacy"])
    assert stats.errors == ["modern: db down"]
    assert stats.formats == 1
    assert stats.decks == 3
    assert stats.cards == 6


def test_format_without_source_recorded(engine, repo):
    sources = {"modern": FakeSource("mtgtop8", {"modern": _decks("modern")})}
    stats = collect_metagame(repo, sources, ["vintage", "modern"], snapshot_date=TODAY)

    assert stats.errors == ["no source for vintage"]
    assert stats.formats == 1
    assert _count(engine, MetaDeckRow) == 3


# ── Boundaries ──────────────────────────────────────────────────────────


def test_empty_formats_zero_stats(repo):
    assert collect_metagame(repo, {"modern": FakeSource("x")}, []) == CollectStats()


def test_limit_one(engine, repo):
    src = FakeSource("mtgtop8", {"modern": _decks("modern")})
    stats = collect_metagame(repo, {"modern": src}, ["modern"], limit=1, snapshot_date=TODAY)
    assert src.calls == [("modern", 1)]
    assert stats.decks == 1
    assert _count(engine, MetaDeckRow) == 1


def test_limit_enforced_when_source_ignores_it(repo):
    class Greedy(FakeSource):
        def fetch_top_decks(self, fmt, *, limit=20):
            return _decks(fmt, 5)

    stats = collect_metagame(repo, {"modern": Greedy("g")}, ["modern"], limit=2)
    assert stats.decks == 2


def test_source_returns_no_decks(engine, repo):
    stats = collect_metagame(repo, {"modern": FakeSource("x", {"modern": []})}, ["modern"])
    assert stats == CollectStats(formats=1)
    assert _count(engine, MetaDeckRow) == 0
