"""Tests for MetagameRepository (F173-T03)."""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal
from types import SimpleNamespace

import pytest
from sqlalchemy import create_engine, func, inspect, select
from sqlalchemy.orm import Session

from src.database.models import Base, CardRow, UserCollectionRow
from src.metagame.models import MetaDeckCardRow, MetaDeckRow
from src.metagame.repository import MetagameRepository

TODAY = date(2026, 9, 24)
YESTERDAY = TODAY - timedelta(days=1)


@pytest.fixture
def engine():
    eng = create_engine("sqlite:///:memory:")
    # Only the tables the repository depends on; meta tables come from __init__.
    Base.metadata.create_all(eng, tables=[CardRow.__table__, UserCollectionRow.__table__])
    return eng


@pytest.fixture
def repo(engine):
    return MetagameRepository(engine)


def _add_card(engine, name, set_code="set", number="1"):
    with Session(engine) as s:
        card = CardRow(game="magic", name_en=name, set_code=set_code, collector_number=number)
        s.add(card)
        s.commit()
        return card.id


def _card(name, quantity=1, board="main", set_code=None, collector_number=None):
    return SimpleNamespace(
        name=name,
        quantity=quantity,
        board=board,
        set_code=set_code,
        collector_number=collector_number,
    )


def _deck(external_id, rank, cards=(), **kw):
    base = dict(
        source="mtgtop8",
        format="modern",
        external_id=external_id,
        archetype=f"Arch {external_id}",
        rank=rank,
        meta_share_pct=Decimal("12.5"),
        deck_count=10,
        colors="UR",
        commander_name=None,
        source_url=f"https://example.test/{external_id}",
        event_date=None,
        cards=tuple(cards),
    )
    base.update(kw)
    return SimpleNamespace(**base)


def _count(engine, model):
    with Session(engine) as s:
        return s.execute(select(func.count()).select_from(model)).scalar()


# ── Schema ──────────────────────────────────────────────────────────────


def test_tables_created_automatically(engine, repo):
    names = inspect(engine).get_table_names()
    assert "meta_decks" in names
    assert "meta_deck_cards" in names


def test_from_repo_uses_engine(engine):
    fake = SimpleNamespace(engine=engine)
    assert MetagameRepository.from_repo(fake).engine is engine


# ── replace_snapshot / list_decks ───────────────────────────────────────


def test_happy_three_decks_ordered_by_rank(engine, repo):
    bolt = _add_card(engine, "Lightning Bolt")
    decks = [
        _deck("c", 3, [_card("Lightning Bolt", 4)]),
        _deck("a", 1, [_card("Lightning Bolt", 4), _card("Island", 2, "side")]),
        _deck("b", 2),
    ]
    assert repo.replace_snapshot("modern", "mtgtop8", TODAY, decks) == 3

    rows, total = repo.list_decks("modern")
    assert total == 3
    assert [r.rank for r in rows] == [1, 2, 3]
    assert rows[0].external_id == "a"
    assert rows[0].meta_share_pct == Decimal("12.5")
    assert rows[0].snapshot_date == TODAY

    cards = repo.get_deck_cards([rows[0].id])[rows[0].id]
    assert [(c.card_name, c.quantity, c.board, c.card_id) for c in cards] == [
        ("Lightning Bolt", 4, "main", bolt),
        ("Island", 2, "side", None),
    ]


def test_replace_snapshot_is_idempotent(engine, repo):
    decks = [_deck("a", 1, [_card("X"), _card("Y")]), _deck("b", 2, [_card("Z")])]
    repo.replace_snapshot("modern", "mtgtop8", TODAY, decks)
    repo.replace_snapshot("modern", "mtgtop8", TODAY, decks)
    assert _count(engine, MetaDeckRow) == 2
    assert _count(engine, MetaDeckCardRow) == 3


def test_replace_snapshot_keeps_other_days_and_formats(engine, repo):
    repo.replace_snapshot("modern", "mtgtop8", YESTERDAY, [_deck("a", 1, [_card("X")])])
    repo.replace_snapshot("pauper", "mtgtop8", TODAY, [_deck("a", 1, [_card("X")])])
    repo.replace_snapshot("modern", "mtgtop8", TODAY, [_deck("a", 1, [_card("X")])])
    assert _count(engine, MetaDeckRow) == 3
    assert _count(engine, MetaDeckCardRow) == 3


def test_two_snapshots_default_latest_and_explicit_old(repo):
    repo.replace_snapshot("modern", "mtgtop8", YESTERDAY, [_deck("old", 1)])
    repo.replace_snapshot("modern", "mtgtop8", TODAY, [_deck("new", 1), _deck("n2", 2)])

    rows, total = repo.list_decks("modern")
    assert total == 2
    assert rows[0].external_id == "new"

    rows, total = repo.list_decks("modern", snapshot_date=YESTERDAY)
    assert total == 1
    assert rows[0].external_id == "old"
    assert repo.latest_snapshot_date("modern") == TODAY


def test_format_without_data(repo):
    assert repo.list_decks("legacy") == ([], 0)
    assert repo.latest_snapshot_date("legacy") is None


def test_list_decks_limit_offset(repo):
    repo.replace_snapshot("modern", "mtgtop8", TODAY, [_deck(str(i), i) for i in range(1, 6)])
    rows, total = repo.list_decks("modern", limit=1, offset=2)
    assert total == 5
    assert [r.rank for r in rows] == [3]


def test_unresolved_card_persists_null(engine, repo):
    repo.replace_snapshot("modern", "mtgtop8", TODAY, [_deck("a", 1, [_card("Nope")])])
    with Session(engine) as s:
        row = s.execute(select(MetaDeckCardRow)).scalar_one()
    assert row.card_name == "Nope"
    assert row.card_id is None


def test_commander_fields_and_board(repo):
    deck = _deck(
        "atraxa",
        1,
        [_card("Atraxa", 1, "commander")],
        format="commander",
        commander_name="Atraxa",
        meta_share_pct=None,
        event_date=YESTERDAY,
    )
    repo.replace_snapshot("commander", "edhrec", TODAY, [deck])
    rows, _ = repo.list_decks("commander")
    assert rows[0].commander_name == "Atraxa"
    assert rows[0].meta_share_pct is None
    assert rows[0].event_date == YESTERDAY
    cards = repo.get_deck_cards([rows[0].id])[rows[0].id]
    assert cards[0].board == "commander"


def test_replace_snapshot_card_ids_map_and_custom_resolver(engine, repo):
    calls = []

    def resolver(card):
        calls.append(card.name)
        return None

    decks = [_deck("a", 1, [_card("Mapped"), _card("Other")])]
    repo.replace_snapshot(
        "modern", "mtgtop8", TODAY, decks, {("a", "Mapped"): 42}, resolver=resolver
    )
    assert calls == ["Other"]
    with Session(engine) as s:
        ids = dict(s.execute(select(MetaDeckCardRow.card_name, MetaDeckCardRow.card_id)).all())
    assert ids == {"Mapped": 42, "Other": None}


def test_default_resolver_caches_per_call(repo, monkeypatch):
    calls = []

    def fake_resolve(name, set_code=None, collector_number=None):
        calls.append(name)
        return None

    monkeypatch.setattr(repo, "resolve_card_id", fake_resolve)
    decks = [_deck("a", 1, [_card("Sol Ring")]), _deck("b", 2, [_card("sol ring")])]
    repo.replace_snapshot("commander", "edhrec", TODAY, decks)
    assert calls == ["Sol Ring"]


# ── get_deck / get_deck_cards ───────────────────────────────────────────


def test_get_deck(repo):
    repo.replace_snapshot("modern", "mtgtop8", TODAY, [_deck("a", 1)])
    rows, _ = repo.list_decks("modern")
    deck = repo.get_deck(rows[0].id)
    assert deck is not None
    assert deck.archetype == "Arch a"


def test_get_deck_missing_returns_none(repo):
    assert repo.get_deck(999) is None


def test_get_deck_cards_batch(repo):
    repo.replace_snapshot(
        "modern",
        "mtgtop8",
        TODAY,
        [_deck("a", 1, [_card("X"), _card("Y")]), _deck("b", 2, [_card("Z")]), _deck("c", 3)],
    )
    rows, _ = repo.list_decks("modern")
    ids = [r.id for r in rows]
    result = repo.get_deck_cards(ids + [999])
    assert [c.card_name for c in result[ids[0]]] == ["X", "Y"]
    assert [c.card_name for c in result[ids[1]]] == ["Z"]
    assert result[ids[2]] == []
    assert result[999] == []


def test_get_deck_cards_empty(repo):
    assert repo.get_deck_cards([]) == {}


# ── list_formats ────────────────────────────────────────────────────────


def test_list_formats(repo):
    repo.replace_snapshot("modern", "mtgtop8", YESTERDAY, [_deck("a", 1)])
    repo.replace_snapshot("modern", "mtgtop8", TODAY, [_deck("a", 1), _deck("b", 2)])
    repo.replace_snapshot("commander", "edhrec", TODAY, [_deck("x", 1)])
    assert repo.list_formats() == [
        {"format": "commander", "latest_snapshot_date": TODAY, "deck_count": 1},
        {"format": "modern", "latest_snapshot_date": TODAY, "deck_count": 2},
    ]


def test_list_formats_empty(repo):
    assert repo.list_formats() == []


# ── resolve_card_id ─────────────────────────────────────────────────────


def test_resolve_exact_set_number(engine, repo):
    _add_card(engine, "Sol Ring", "c21", "1")
    target = _add_card(engine, "Sol Ring", "cmr", "2")
    assert repo.resolve_card_id("Sol Ring", "CMR", "2") == target


def test_resolve_unique_name_case_insensitive(engine, repo):
    cid = _add_card(engine, "Lightning Bolt")
    assert repo.resolve_card_id("lightning bolt") == cid


def test_resolve_ambiguous_name_returns_none(engine, repo):
    _add_card(engine, "Sol Ring", "c21", "1")
    _add_card(engine, "Sol Ring", "cmr", "2")
    assert repo.resolve_card_id("Sol Ring") is None


def test_resolve_split_name_falls_back_to_front_face(engine, repo):
    cid = _add_card(engine, "Fable of the Mirror-Breaker")
    assert repo.resolve_card_id("Fable of the Mirror-Breaker // Reflection of Kiki-Jiki") == cid


def test_resolve_front_face_matches_double_card(engine, repo):
    cid = _add_card(engine, "Delver of Secrets // Insectile Aberration")
    assert repo.resolve_card_id("Delver of Secrets") == cid


def test_resolve_front_face_ambiguous_double_card(engine, repo):
    _add_card(engine, "Delver of Secrets // Insectile Aberration", "isd", "1")
    _add_card(engine, "Delver of Secrets // Insectile Aberration", "inr", "2")
    assert repo.resolve_card_id("Delver of Secrets") is None


def test_resolve_like_wildcards_are_escaped(engine, repo):
    _add_card(engine, "Axx // Bee")
    assert repo.resolve_card_id("A%") is None
    assert repo.resolve_card_id("A_x") is None


def test_resolve_not_found(repo):
    assert repo.resolve_card_id("Does Not Exist") is None
    assert repo.resolve_card_id(" // Back") is None


# ── owned_quantities ────────────────────────────────────────────────────


def _own(engine, user_id, card_id, qty):
    with Session(engine) as s:
        s.add(
            UserCollectionRow(
                user_id=user_id, card_id=card_id, set_code="set", collector_number="1", quantity=qty
            )
        )
        s.commit()


def test_owned_quantities_sums_per_card(engine, repo):
    a = _add_card(engine, "A", "s", "1")
    b = _add_card(engine, "B", "s", "2")
    c = _add_card(engine, "C", "s", "3")
    _own(engine, "u1", a, 1)
    _own(engine, "u1", a, 3)
    _own(engine, "u1", b, 2)
    _own(engine, "u2", c, 5)
    assert repo.owned_quantities("u1", [a, b, c, a]) == {a: 4, b: 2}


def test_owned_quantities_empty_list(repo):
    assert repo.owned_quantities("u1", []) == {}
