"""Tests for TradeQueries (F174-T03)."""

from __future__ import annotations

from datetime import date, datetime

import pytest
from sqlalchemy.orm import Session

from src.database.models import (
    CardRow,
    PriceObservationRow,
    SharedCollectionRow,
    UserCollectionRow,
)
from src.database.repository import Repository
from src.marketplace.trade_queries import TradeQueries


@pytest.fixture()
def repo(tmp_path):
    db_path = tmp_path / "test_trade_queries.db"
    return Repository(db_url=f"sqlite:///{db_path}")


@pytest.fixture()
def queries(repo):
    return TradeQueries(repo)


def _make_user(repo: Repository, email: str) -> int:
    return repo.create_user(email=email, display_name=email).id


def _share(repo: Repository, user_id: int, share_code: str, *, is_shared: int = 1) -> None:
    with Session(repo.engine) as session:
        session.add(
            SharedCollectionRow(
                user_id=user_id,
                is_shared=is_shared,
                share_code=share_code,
                shared_at=datetime.now(),
            )
        )
        session.commit()


def _add_card(repo: Repository, name_en: str, set_code: str, number: str) -> int:
    with Session(repo.engine) as session:
        card = CardRow(
            game="magic",
            name_en=name_en,
            set_code=set_code,
            collector_number=number,
        )
        session.add(card)
        session.commit()
        session.refresh(card)
        return card.id


def _add_entry(
    repo: Repository,
    user_id: int,
    *,
    name_en: str,
    name_pt: str | None = None,
    set_code: str = "mh3",
    set_name_en: str | None = None,
    number: str = "1",
    quantity: int = 1,
    card_id: int | None = None,
    rarity: str | None = "C",
) -> int:
    with Session(repo.engine) as session:
        entry = UserCollectionRow(
            user_id=str(user_id),
            name_en=name_en,
            name_pt=name_pt,
            set_code=set_code,
            set_name_en=set_name_en or set_code.upper(),
            collector_number=number,
            quantity=quantity,
            card_id=card_id,
            rarity=rarity,
        )
        session.add(entry)
        session.commit()
        session.refresh(entry)
        return entry.id


def _add_price(repo: Repository, card_id: int, price: str, *, observed_at: date | None = None) -> None:
    with Session(repo.engine) as session:
        session.add(
            PriceObservationRow(
                source="liga",
                external_id=f"liga_{card_id}",
                observed_at=observed_at or date.today(),
                median_price=price,
            )
        )
        session.commit()


@pytest.fixture()
def seeded(repo):
    """3 shared users x cards in 2 sets, mirroring the T03 test scenarios."""
    viewer = _make_user(repo, "viewer@example.com")
    u1 = _make_user(repo, "u1@example.com")
    u2 = _make_user(repo, "u2@example.com")
    _share(repo, u1, "SHARE1")
    _share(repo, u2, "SHARE2")
    _share(repo, viewer, "SHAREV")

    bolt = _add_card(repo, "Lightning Bolt", "lea", "161")
    _add_price(repo, bolt, "5.00")
    counter = _add_card(repo, "Counterspell", "lea", "55")
    _add_price(repo, counter, "3.00")

    e_bolt = _add_entry(
        repo, u1, name_en="Lightning Bolt", name_pt="Raio", set_code="lea",
        set_name_en="Limited Edition Alpha", number="161", card_id=bolt,
    )
    e_counter = _add_entry(
        repo, u2, name_en="Counterspell", name_pt=None, set_code="lea",
        set_name_en="Limited Edition Alpha", number="55", card_id=counter,
    )
    e_no_price = _add_entry(
        repo, u2, name_en="Unpriced Card", set_code="mh3",
        set_name_en="Modern Horizons 3", number="10", card_id=None,
    )
    e_viewer = _add_entry(
        repo, viewer, name_en="Viewer Card", set_code="mh3",
        set_name_en="Modern Horizons 3", number="20", card_id=None,
    )
    return {
        "viewer": viewer,
        "u1": u1,
        "u2": u2,
        "entries": {
            "bolt": e_bolt,
            "counter": e_counter,
            "no_price": e_no_price,
            "viewer": e_viewer,
        },
    }


@pytest.fixture()
def dup_seeded(repo):
    """Duplicates fixture: quantity>1 vs quantity==1, with/without price."""
    user_id = _make_user(repo, "dup@example.com")
    bolt = _add_card(repo, "Lightning Bolt", "lea", "161")
    _add_price(repo, bolt, "5.00")
    counter = _add_card(repo, "Counterspell", "lea", "55")
    _add_price(repo, counter, "3.00")

    dup_bolt = _add_entry(
        repo, user_id, name_en="Lightning Bolt", name_pt="Raio", set_code="lea",
        set_name_en="Limited Edition Alpha", number="161", quantity=3, card_id=bolt,
    )
    dup_counter = _add_entry(
        repo, user_id, name_en="Counterspell", set_code="mh3",
        set_name_en="Modern Horizons 3", number="55", quantity=2, card_id=counter,
    )
    dup_no_price = _add_entry(
        repo, user_id, name_en="No Price Duplicate", set_code="mh3",
        set_name_en="Modern Horizons 3", number="99", quantity=2, card_id=None,
    )
    unpriced = _add_card(repo, "Unpriced Card", "mh3", "77")
    dup_unpriced = _add_entry(
        repo, user_id, name_en="Unlinked Price Duplicate", set_code="mh3",
        set_name_en="Modern Horizons 3", number="77", quantity=2, card_id=unpriced,
    )
    _add_entry(
        repo, user_id, name_en="Single Copy", set_code="lea",
        set_name_en="Limited Edition Alpha", number="1", quantity=1, card_id=bolt,
    )
    return {
        "user_id": user_id,
        "entries": {
            "bolt": dup_bolt,
            "counter": dup_counter,
            "no_price": dup_no_price,
            "unpriced": dup_unpriced,
        },
        "card_ids": {
            "bolt": bolt,
            "counter": counter,
            "unpriced": unpriced,
        },
    }


class TestListListings:
    def test_matches_repository_default_order(self, repo, queries, seeded):
        legacy = repo.list_marketplace_entries(limit=20, offset=0)
        new = queries.list_listings(limit=20, offset=0)
        assert new == legacy

    def test_search_matches_name_en_or_pt(self, queries, seeded):
        result = queries.list_listings(search="bolt")
        assert {r["card_name_en"] for r in result} == {"Lightning Bolt"}

        result_pt = queries.list_listings(search="raio")
        assert {r["card_name_en"] for r in result_pt} == {"Lightning Bolt"}

    def test_search_is_case_insensitive_and_strips_whitespace(self, queries, seeded):
        result = queries.list_listings(search="  BOLT  ")
        assert len(result) == 1

    def test_empty_search_is_ignored(self, repo, queries, seeded):
        result = queries.list_listings(search="   ")
        legacy = repo.list_marketplace_entries(limit=20, offset=0)
        assert result == legacy

    def test_set_filter_case_insensitive(self, queries, seeded):
        result = queries.list_listings(set_code="LEA")
        assert {r["set_code"] for r in result} == {"lea"}

    def test_exclude_user_id_omits_viewer_cards(self, queries, seeded):
        result = queries.list_listings(exclude_user_id=seeded["viewer"])
        names = {r["card_name_en"] for r in result}
        assert "Viewer Card" not in names

    def test_sort_price_desc_puts_null_last(self, queries, seeded):
        result = queries.list_listings(sort_by="price", sort_dir="desc")
        prices = [r["latest_price"] for r in result]
        assert prices[-1] is None
        non_null = [p for p in prices if p is not None]
        assert non_null == sorted(non_null, reverse=True)

    def test_sort_price_asc_puts_null_last(self, queries, seeded):
        result = queries.list_listings(sort_by="price", sort_dir="asc")
        prices = [r["latest_price"] for r in result]
        assert prices[-1] is None
        non_null = [p for p in prices if p is not None]
        assert non_null == sorted(non_null)

    def test_sort_by_name_desc(self, queries, seeded):
        result = queries.list_listings(sort_by="name", sort_dir="desc")
        names = [r["card_name_en"] for r in result]
        assert names == sorted(names, reverse=True)

    def test_sort_by_set(self, queries, seeded):
        result = queries.list_listings(sort_by="set", sort_dir="asc")
        codes = [r["set_code"] for r in result]
        assert codes == sorted(codes)

    def test_sort_by_number(self, queries, seeded):
        result = queries.list_listings(sort_by="number", sort_dir="asc")
        numbers = [r["collector_number"] for r in result]
        assert numbers == sorted(numbers)

    def test_unknown_sort_by_raises(self, queries, seeded):
        with pytest.raises(ValueError):
            queries.list_listings(sort_by="drop table")

    def test_unknown_sort_dir_raises(self, queries, seeded):
        with pytest.raises(ValueError):
            queries.list_listings(sort_dir="up")

    def test_pagination_disjoint_pages(self, queries, seeded):
        page1 = queries.list_listings(limit=1, offset=0)
        page2 = queries.list_listings(limit=1, offset=1)
        assert page1 != page2
        assert page1[0]["entry_id"] != page2[0]["entry_id"]

    def test_pagination_offset_beyond_total(self, queries, seeded):
        result = queries.list_listings(limit=10, offset=1000)
        assert result == []

    def test_share_code_filter(self, queries, seeded):
        result = queries.list_listings(share_code="SHARE1")
        assert all(r["share_code"] == "SHARE1" for r in result)
        assert len(result) == 1


class TestListListingSets:
    def test_excludes_viewer(self, queries, seeded):
        sets = queries.list_listing_sets(exclude_user_id=seeded["viewer"])
        codes = {s["set_code"] for s in sets}
        assert "mh3" in codes  # u2's unpriced card is in mh3
        for s in sets:
            assert set(s.keys()) == {"set_code", "set_name", "count"}

    def test_ordered_by_set_code(self, queries, seeded):
        sets = queries.list_listing_sets()
        codes = [s["set_code"] for s in sets]
        assert codes == sorted(codes)


class TestListDuplicates:
    def test_matches_repository_default_order(self, repo, queries, dup_seeded):
        legacy = repo.get_user_duplicates(dup_seeded["user_id"])
        new = queries.list_duplicates(dup_seeded["user_id"])
        assert new == legacy

    def test_excludes_quantity_one(self, queries, dup_seeded):
        result, total = queries.list_duplicates(dup_seeded["user_id"])
        assert all(r["quantity"] > 1 for r in result)
        # dup_no_price has quantity>1 but card_id is None, so it is excluded
        # (mirrors Repository.get_user_duplicates' card_id.isnot(None) filter).
        # bolt, counter, unpriced (quantity>1 with card_id set) remain.
        assert total == 3

    def test_quantity_two_is_included(self, queries, dup_seeded):
        result, _total = queries.list_duplicates(dup_seeded["user_id"])
        names = {r["name_en"] for r in result}
        assert "Counterspell" in names

    def test_search_filters(self, queries, dup_seeded):
        result, total = queries.list_duplicates(dup_seeded["user_id"], search="bolt")
        assert total == 1
        assert result[0]["name_en"] == "Lightning Bolt"

    def test_set_filter_case_insensitive(self, queries, dup_seeded):
        result, total = queries.list_duplicates(dup_seeded["user_id"], set_code="LEA")
        assert total == 1
        assert result[0]["set_code"] == "lea"

    def test_sort_price_desc_null_last(self, queries, dup_seeded):
        result, _ = queries.list_duplicates(
            dup_seeded["user_id"], sort_by="price", sort_dir="desc"
        )
        card_ids = [r["card_id"] for r in result]
        # "unpriced" has a card_id but no price observation, so its price is
        # NULL and it must sort last regardless of direction.
        assert card_ids[-1] == dup_seeded["card_ids"]["unpriced"]

    def test_sort_price_asc_null_last(self, queries, dup_seeded):
        result, _ = queries.list_duplicates(
            dup_seeded["user_id"], sort_by="price", sort_dir="asc"
        )
        card_ids = [r["card_id"] for r in result]
        assert card_ids[-1] == dup_seeded["card_ids"]["unpriced"]

    def test_unknown_sort_by_raises(self, queries, dup_seeded):
        with pytest.raises(ValueError):
            queries.list_duplicates(dup_seeded["user_id"], sort_by="drop table")

    def test_unknown_sort_dir_raises(self, queries, dup_seeded):
        with pytest.raises(ValueError):
            queries.list_duplicates(dup_seeded["user_id"], sort_dir="up")

    def test_pagination_disjoint_pages(self, queries, dup_seeded):
        page1, _ = queries.list_duplicates(dup_seeded["user_id"], limit=1, offset=0)
        page2, _ = queries.list_duplicates(dup_seeded["user_id"], limit=1, offset=1)
        assert page1[0]["card_id"] != page2[0]["card_id"] or page1[0]["name_en"] != page2[0]["name_en"]

    def test_pagination_offset_beyond_total(self, queries, dup_seeded):
        result, total = queries.list_duplicates(dup_seeded["user_id"], limit=10, offset=1000)
        assert result == []
        assert total == 3


class TestListDuplicateSets:
    def test_only_quantity_gt_one_with_card_id(self, queries, dup_seeded):
        sets = queries.list_duplicate_sets(dup_seeded["user_id"])
        for s in sets:
            assert set(s.keys()) == {"set_code", "set_name", "count"}
        codes = {s["set_code"] for s in sets}
        assert "lea" in codes
        # "lea" set count should only include the dup_bolt entry (qty=3),
        # not the single-copy entry (qty=1)
        lea_set = next(s for s in sets if s["set_code"] == "lea")
        assert lea_set["count"] == 1

    def test_ordered_by_set_code(self, queries, dup_seeded):
        sets = queries.list_duplicate_sets(dup_seeded["user_id"])
        codes = [s["set_code"] for s in sets]
        assert codes == sorted(codes)
