"""Tests for the metagame top decks router (F173-T10)."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from src.api.app import create_app
from src.api.deps import get_db, get_optional_user
from src.api.routers.meta_decks import router
from src.database.models import CardRow, UserCollectionRow
from src.database.repository import Repository
from src.domain.models import User
from src.metagame.repository import MetagameRepository

SNAP = date(2026, 9, 24)
OLD_SNAP = date(2026, 9, 17)
USER = User(id=7, email="player@example.test")


# ── Fixtures / helpers ──────────────────────────────────────────────────


@pytest.fixture
def repo(tmp_path):
    return Repository(db_url=f"sqlite:///{tmp_path / 'meta.db'}")


@pytest.fixture
def meta(repo):
    return MetagameRepository.from_repo(repo)


@pytest.fixture
def prices(repo, monkeypatch):
    """``{card_id: Decimal | None}`` served by ``get_latest_prices_batch``."""
    table: dict[int, Decimal | None] = {}
    calls: list[list[int]] = []

    def fake_batch(card_ids, foil_card_ids=None):
        calls.append(list(card_ids))
        return {
            cid: (SimpleNamespace(median_price=table[cid]) if cid in table else None)
            for cid in card_ids
        }

    monkeypatch.setattr(repo, "get_latest_prices_batch", fake_batch)
    table_obj = SimpleNamespace(table=table, calls=calls)
    return table_obj


def _client(repo, user: User | None = None) -> TestClient:
    # Minimal app (create_app() may mount an SPA catch-all when frontend/dist
    # exists) with the production exception handlers for the error envelope.
    app = FastAPI()
    app.exception_handlers.update(create_app().exception_handlers)
    app.include_router(router, prefix="/api/v1")
    app.dependency_overrides[get_db] = lambda: repo
    app.dependency_overrides[get_optional_user] = lambda: user
    return TestClient(app)


def _add_card(repo, name, number, image_uri=None) -> int:
    with Session(repo.engine) as s:
        card = CardRow(
            game="magic",
            name_en=name,
            set_code="tst",
            collector_number=number,
            image_uri=image_uri,
        )
        s.add(card)
        s.commit()
        return card.id


def _own(repo, user_id: str, card_id: int, qty: int) -> None:
    with Session(repo.engine) as s:
        s.add(
            UserCollectionRow(
                user_id=user_id,
                card_id=card_id,
                set_code="tst",
                collector_number=str(card_id),
                quantity=qty,
            )
        )
        s.commit()


def _card(name, quantity=1, board="main"):
    return SimpleNamespace(
        name=name, quantity=quantity, board=board, set_code=None, collector_number=None
    )


def _deck(external_id, rank, cards, **kw):
    base = dict(
        external_id=external_id,
        archetype=f"Arch {external_id}",
        rank=rank,
        meta_share_pct=Decimal("12.5"),
        deck_count=10,
        colors="UR",
        commander_name=None,
        source_url=f"https://example.test/{external_id}",
        event_date=date(2026, 9, 20),
        cards=tuple(cards),
    )
    base.update(kw)
    return SimpleNamespace(**base)


@pytest.fixture
def seeded(repo, meta, prices):
    """3 modern decks (inserted out of rank order) + an older snapshot."""
    bolt = _add_card(repo, "Lightning Bolt", "1", image_uri="https://img.test/bolt.jpg")
    ragavan = _add_card(repo, "Ragavan", "2")
    thoughtseize = _add_card(repo, "Thoughtseize", "3")
    prices.table.update({bolt: Decimal("5.00"), ragavan: Decimal("300.00"), thoughtseize: None})

    decks = [
        _deck("c", 3, [_card("Thoughtseize", 4)]),
        _deck(
            "a",
            1,
            [
                _card("Lightning Bolt", 4),
                _card("Ragavan", 4),
                _card("Mountain", 2),
                _card("Unknown Card", 2),
                _card("Ragavan", 1, board="side"),
            ],
        ),
        _deck("b", 2, [_card("Lightning Bolt", 2)]),
    ]
    card_ids = {
        ("c", "Thoughtseize"): thoughtseize,
        ("a", "Lightning Bolt"): bolt,
        ("a", "Ragavan"): ragavan,
        ("a", "Mountain"): None,
        ("a", "Unknown Card"): None,
        ("b", "Lightning Bolt"): bolt,
    }
    meta.replace_snapshot("modern", "mtgtop8", SNAP, decks, card_ids)
    meta.replace_snapshot(
        "modern", "mtgtop8", OLD_SNAP, [_deck("old", 1, [_card("Ragavan", 1)])], {}
    )
    _own(repo, str(USER.id), bolt, 3)
    _own(repo, str(USER.id), bolt, 5)  # summed → 8, capped at deck qty
    _own(repo, str(USER.id), ragavan, 1)
    _own(repo, "someone-else", ragavan, 4)
    return SimpleNamespace(bolt=bolt, ragavan=ragavan, thoughtseize=thoughtseize)


def _deck_id(meta, fmt="modern", rank=1, snapshot_date=None) -> int:
    decks, _ = meta.list_decks(fmt, snapshot_date=snapshot_date)
    return next(d.id for d in decks if d.rank == rank)


# ── /formats ────────────────────────────────────────────────────────────


def test_formats_lists_format_count_and_date(repo, seeded, meta):
    meta.replace_snapshot("pauper", "mtgtop8", OLD_SNAP, [_deck("p", 1, [])], {})

    resp = _client(repo).get("/api/v1/meta-decks/formats")

    assert resp.status_code == 200
    body = resp.json()
    assert body["errors"] is None or body["errors"] == []
    assert body["data"]["formats"] == [
        {"format": "modern", "latest_snapshot_date": "2026-09-24", "deck_count": 3},
        {"format": "pauper", "latest_snapshot_date": "2026-09-17", "deck_count": 1},
    ]


def test_formats_empty(repo):
    resp = _client(repo).get("/api/v1/meta-decks/formats")
    assert resp.status_code == 200
    assert resp.json()["data"] == {"formats": []}


# ── list ────────────────────────────────────────────────────────────────


def test_list_ordered_by_rank_with_values_logged_in(repo, seeded, prices):
    resp = _client(repo, USER).get("/api/v1/meta-decks", params={"format": "modern"})

    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["format"] == "modern"
    assert data["snapshot_date"] == "2026-09-24"
    assert data["source"] == "mtgtop8"
    assert data["total"] == 3
    assert [d["rank"] for d in data["decks"]] == [1, 2, 3]

    top = data["decks"][0]
    assert set(top) == {
        "id",
        "rank",
        "archetype",
        "commander_name",
        "colors",
        "meta_share_pct",
        "deck_count",
        "source",
        "source_url",
        "event_date",
        "snapshot_date",
        "total_value_brl",
        "priced_pct",
        "owned_pct",
        "missing_value_brl",
        "total_copies",
    }
    assert top["archetype"] == "Arch a"
    assert top["meta_share_pct"] == 12.5
    assert top["event_date"] == "2026-09-20"
    # main board only: 4 bolt (5.00) + 4 ragavan (300.00) + 2 Mountain + 2 unknown
    assert top["total_copies"] == 12
    assert top["total_value_brl"] == 1220.0
    # priced: 4 + 4 + 2 basics = 10/12
    assert top["priced_pct"] == 83.3
    # owned: 4 bolt (capped) + 1 ragavan + 2 basics = 7/12
    assert top["owned_pct"] == 58.3
    assert top["missing_value_brl"] == 900.0

    second = data["decks"][1]
    assert second["total_value_brl"] == 10.0
    assert second["owned_pct"] == 100.0

    third = data["decks"][2]  # only an unpriced card
    assert third["total_value_brl"] is None
    assert third["owned_pct"] == 0.0

    # batch: one price call for all decks, no N+1
    assert len(prices.calls) == 1
    assert sorted(prices.calls[0]) == sorted([seeded.bolt, seeded.ragavan, seeded.thoughtseize])


def test_list_anonymous_owned_pct_null(repo, seeded):
    data = _client(repo).get("/api/v1/meta-decks", params={"format": "modern"}).json()["data"]

    assert all(d["owned_pct"] is None for d in data["decks"])
    assert all(d["missing_value_brl"] is None for d in data["decks"])
    assert data["decks"][0]["total_value_brl"] == 1220.0


def test_list_explicit_snapshot_date_returns_old_snapshot(repo, seeded):
    resp = _client(repo).get(
        "/api/v1/meta-decks", params={"format": "modern", "snapshot_date": "2026-09-17"}
    )

    data = resp.json()["data"]
    assert data["snapshot_date"] == "2026-09-17"
    assert data["total"] == 1
    assert data["decks"][0]["archetype"] == "Arch old"
    assert data["decks"][0]["total_value_brl"] == 300.0  # Ragavan resolved by name


def test_list_unknown_snapshot_date_is_empty(repo, seeded):
    data = (
        _client(repo)
        .get("/api/v1/meta-decks", params={"format": "modern", "snapshot_date": "2020-01-01"})
        .json()["data"]
    )
    assert data == {
        "format": "modern",
        "snapshot_date": None,
        "source": None,
        "total": 0,
        "decks": [],
    }


def test_list_without_snapshot_returns_empty(repo, prices):
    resp = _client(repo, USER).get("/api/v1/meta-decks", params={"format": "legacy"})

    assert resp.status_code == 200
    assert resp.json()["data"] == {
        "format": "legacy",
        "snapshot_date": None,
        "source": None,
        "total": 0,
        "decks": [],
    }
    assert prices.calls == []


def test_list_pagination(repo, seeded):
    data = (
        _client(repo)
        .get("/api/v1/meta-decks", params={"format": "modern", "limit": 1, "offset": 1})
        .json()["data"]
    )
    assert data["total"] == 3
    assert [d["rank"] for d in data["decks"]] == [2]


def test_list_offset_beyond_total(repo, seeded):
    resp = _client(repo).get("/api/v1/meta-decks", params={"format": "modern", "offset": 10})

    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["decks"] == []
    assert data["total"] == 3
    assert data["snapshot_date"] == "2026-09-24"


@pytest.mark.parametrize(
    ("params", "status"),
    [
        ({"format": "modern", "limit": 50}, 200),
        ({"format": "modern", "limit": 1}, 200),
        ({"format": "modern", "limit": 51}, 422),
        ({"format": "modern", "limit": 0}, 422),
        ({"format": "modern", "offset": -1}, 422),
        ({"format": "foo"}, 422),
        ({}, 422),
        ({"format": "modern", "snapshot_date": "not-a-date"}, 422),
    ],
)
def test_list_query_validation(repo, seeded, params, status):
    resp = _client(repo).get("/api/v1/meta-decks", params=params)
    assert resp.status_code == status
    if status == 422:
        assert resp.json()["errors"][0]["code"] == "VALIDATION_ERROR"


@pytest.mark.parametrize(
    "fmt", ["commander", "standard", "pioneer", "modern", "legacy", "pauper", "vintage"]
)
def test_list_accepts_every_format(repo, fmt):
    assert _client(repo).get("/api/v1/meta-decks", params={"format": fmt}).status_code == 200


# ── detail ──────────────────────────────────────────────────────────────


def test_detail_logged_in(repo, seeded, meta):
    deck_id = _deck_id(meta)

    resp = _client(repo, USER).get(f"/api/v1/meta-decks/{deck_id}")

    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["id"] == deck_id
    assert data["rank"] == 1
    assert data["total_value_brl"] == 1220.0
    assert data["owned_pct"] == 58.3

    cards = {(c["name"], c["board"]): c for c in data["cards"]}
    assert len(data["cards"]) == 5
    bolt = cards[("Lightning Bolt", "main")]
    assert bolt == {
        "name": "Lightning Bolt",
        "quantity": 4,
        "board": "main",
        "card_id": seeded.bolt,
        "price_brl": 5.0,
        "owned_qty": 8,
        "image_url": "https://img.test/bolt.jpg",
    }
    assert cards[("Ragavan", "main")]["price_brl"] == 300.0
    assert cards[("Ragavan", "main")]["owned_qty"] == 1
    assert cards[("Ragavan", "main")]["image_url"] is None
    assert cards[("Ragavan", "side")]["quantity"] == 1

    unknown = cards[("Unknown Card", "main")]
    assert unknown["card_id"] is None
    assert unknown["price_brl"] is None
    assert unknown["owned_qty"] == 0
    assert unknown["image_url"] is None

    mountain = cards[("Mountain", "main")]
    assert mountain["owned_qty"] == 2  # basics count as owned, like the valuation


def test_detail_anonymous(repo, seeded, meta):
    data = _client(repo).get(f"/api/v1/meta-decks/{_deck_id(meta)}").json()["data"]

    assert data["owned_pct"] is None
    assert data["missing_value_brl"] is None
    assert all(c["owned_qty"] is None for c in data["cards"])
    assert {c["price_brl"] for c in data["cards"]} == {5.0, 300.0, None}


def test_detail_unpriced_card(repo, seeded, meta):
    data = _client(repo, USER).get(f"/api/v1/meta-decks/{_deck_id(meta, rank=3)}").json()["data"]
    card = data["cards"][0]
    assert card["card_id"] == seeded.thoughtseize
    assert card["price_brl"] is None
    assert card["owned_qty"] == 0
    assert data["priced_pct"] == 0.0


def test_detail_deck_without_cards(repo, meta, prices):
    meta.replace_snapshot("commander", "edhrec", SNAP, [_deck("e", 1, [])], {})
    deck_id = _deck_id(meta, fmt="commander")

    data = _client(repo, USER).get(f"/api/v1/meta-decks/{deck_id}").json()["data"]

    assert data["cards"] == []
    assert data["total_copies"] == 0
    assert data["total_value_brl"] is None
    assert prices.calls == []


def test_detail_not_found_uses_error_envelope(repo):
    resp = _client(repo).get("/api/v1/meta-decks/9999")

    assert resp.status_code == 404
    body = resp.json()
    assert body["data"] is None
    assert body["errors"][0]["code"] == "RESOURCE_NOT_FOUND"
    assert "9999" in body["errors"][0]["message"]


def test_detail_non_integer_id_is_422(repo):
    assert _client(repo).get("/api/v1/meta-decks/abc").status_code == 422


def test_formats_route_not_shadowed_by_detail(repo):
    # "/formats" must resolve to the formats endpoint, not /{deck_id} (→ 422)
    assert _client(repo).get("/api/v1/meta-decks/formats").status_code == 200
