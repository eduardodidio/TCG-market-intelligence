"""Tests for scan-related repository methods (F13-T03).

Covers:
 1. CRUD happy path: create -> get -> update -> get
 2. List with filters: create 3 runs with different types, list with type filter
 3. List ordering: runs listed newest-first
 4. Pagination: create 5 runs, list with limit=2 offset=2
 5. get_cards_for_scan (collection): returns all linked cards
 6. get_cards_for_scan (set filter): returns only cards from specified set
 7. get_cards_for_scan (limit): respects limit parameter
 8. get_scan_run (not found): returns None for non-existent ID
"""

from __future__ import annotations

from datetime import datetime

import pytest
from sqlalchemy.orm import Session

from src.database.models import (
    CardRow,
    SourceCardRow,
    UserCollectionRow,
)
from src.database.repository import Repository
from src.domain.models import ScanFilter, ScanType


@pytest.fixture()
def repo(tmp_path):
    """Create a Repository backed by an in-memory SQLite DB."""
    db_url = "sqlite:///:memory:"
    return Repository(db_url=db_url)


@pytest.fixture()
def seeded_repo(repo):
    """Seed repo with cards, source_cards, and user_collection for scan tests."""
    engine = repo.engine
    with Session(engine) as session:
        # Cards
        c1 = CardRow(
            game="magic",
            name_en="Lightning Bolt",
            set_code="2XM",
            collector_number="1",
        )
        c2 = CardRow(
            game="magic",
            name_en="Counterspell",
            set_code="MH3",
            collector_number="42",
        )
        c3 = CardRow(
            game="magic",
            name_en="Swords to Plowshares",
            set_code="2XM",
            collector_number="10",
        )
        session.add_all([c1, c2, c3])
        session.flush()

        # Source cards (MYP)
        sc1 = SourceCardRow(
            source="myp",
            external_id="100",
            card_id=c1.id,
            url="/magic/produto/100/lightning-bolt",
            name_en="Lightning Bolt",
            set_code="2XM",
        )
        sc2 = SourceCardRow(
            source="myp",
            external_id="200",
            card_id=c2.id,
            url="/magic/produto/200/counterspell",
            name_en="Counterspell",
            set_code="MH3",
        )
        sc3 = SourceCardRow(
            source="myp",
            external_id="300",
            card_id=c3.id,
            url="/magic/produto/300/swords-to-plowshares",
            name_en="Swords to Plowshares",
            set_code="2XM",
        )
        session.add_all([sc1, sc2, sc3])
        session.flush()

        # User collection entries (linked)
        uc1 = UserCollectionRow(
            user_id="default",
            card_id=c1.id,
            set_code="2XM",
            collector_number="1",
            name_en="Lightning Bolt",
            rarity="R",
        )
        uc2 = UserCollectionRow(
            user_id="default",
            card_id=c2.id,
            set_code="MH3",
            collector_number="42",
            name_en="Counterspell",
            rarity="U",
        )
        uc3 = UserCollectionRow(
            user_id="default",
            card_id=c3.id,
            set_code="2XM",
            collector_number="10",
            name_en="Swords to Plowshares",
            rarity="R",
        )
        session.add_all([uc1, uc2, uc3])
        session.commit()

    return repo


class TestScanRunCrud:
    """1. CRUD happy path: create -> get -> update -> get."""

    def test_create_get_update_get(self, repo) -> None:
        run_id = repo.create_scan_run("collection", '{"limit": 10}')
        assert isinstance(run_id, int)

        run = repo.get_scan_run(run_id)
        assert run is not None
        assert run["id"] == run_id
        assert run["scan_type"] == "collection"
        assert run["filters_json"] == '{"limit": 10}'
        assert run["status"] == "pending"
        assert run["cards_total"] == 0

        now = datetime(2026, 8, 20, 15, 0, 0)
        repo.update_scan_run(
            run_id,
            status="running",
            cards_total=50,
            started_at=now,
        )

        run = repo.get_scan_run(run_id)
        assert run["status"] == "running"
        assert run["cards_total"] == 50
        assert run["started_at"] == now


class TestScanRunListFilters:
    """2. List with filters: create 3 runs with different types."""

    def test_list_with_type_filter(self, repo) -> None:
        repo.create_scan_run("collection")
        repo.create_scan_run("set")
        repo.create_scan_run("collection")

        all_runs = repo.list_scan_runs()
        assert len(all_runs) == 3

        collection_runs = repo.list_scan_runs(scan_type="collection")
        assert len(collection_runs) == 2
        assert all(r["scan_type"] == "collection" for r in collection_runs)

        set_runs = repo.list_scan_runs(scan_type="set")
        assert len(set_runs) == 1
        assert set_runs[0]["scan_type"] == "set"

    def test_list_with_status_filter(self, repo) -> None:
        id1 = repo.create_scan_run("collection")
        id2 = repo.create_scan_run("collection")
        repo.update_scan_run(id1, status="completed")

        completed = repo.list_scan_runs(status="completed")
        assert len(completed) == 1
        assert completed[0]["id"] == id1

        pending = repo.list_scan_runs(status="pending")
        assert len(pending) == 1
        assert pending[0]["id"] == id2


class TestScanRunListOrdering:
    """3. List ordering: runs listed newest-first."""

    def test_newest_first(self, repo) -> None:
        id1 = repo.create_scan_run("collection")
        id2 = repo.create_scan_run("collection")
        id3 = repo.create_scan_run("collection")

        runs = repo.list_scan_runs()
        ids = [r["id"] for r in runs]
        # newest (highest id / latest created_at) should come first
        assert ids == [id3, id2, id1]


class TestScanRunPagination:
    """4. Pagination: create 5 runs, list with limit=2 offset=2."""

    def test_limit_and_offset(self, repo) -> None:
        created_ids = []
        for _ in range(5):
            created_ids.append(repo.create_scan_run("collection"))

        # Ordered newest-first: [id5, id4, id3, id2, id1]
        page = repo.list_scan_runs(limit=2, offset=2)
        assert len(page) == 2

        all_runs = repo.list_scan_runs(limit=20)
        # page should be items at indices 2 and 3 of the full list
        expected_ids = [r["id"] for r in all_runs[2:4]]
        actual_ids = [r["id"] for r in page]
        assert actual_ids == expected_ids


class TestGetCardsForScanCollection:
    """5. get_cards_for_scan (collection): returns all linked cards."""

    def test_returns_all_linked(self, seeded_repo) -> None:
        scan_filter = ScanFilter(scan_type=ScanType.COLLECTION)
        cards = seeded_repo.get_cards_for_scan(scan_filter)

        assert len(cards) == 3
        ext_ids = {c["external_id"] for c in cards}
        assert ext_ids == {"100", "200", "300"}

        # Verify dict shape
        for card in cards:
            assert "external_id" in card
            assert "slug" in card
            assert "card_id" in card
            assert "set_code" in card
            assert "name_en" in card


class TestGetCardsForScanSetFilter:
    """6. get_cards_for_scan (set filter): returns only cards from specified set."""

    def test_filters_by_set_code(self, seeded_repo) -> None:
        scan_filter = ScanFilter(
            scan_type=ScanType.SET,
            set_codes=["2XM"],
        )
        cards = seeded_repo.get_cards_for_scan(scan_filter)

        assert len(cards) == 2
        assert all(c["set_code"] == "2XM" for c in cards)
        names = {c["name_en"] for c in cards}
        assert names == {"Lightning Bolt", "Swords to Plowshares"}

    def test_filters_by_rarity(self, seeded_repo) -> None:
        scan_filter = ScanFilter(
            scan_type=ScanType.COLLECTION,
            rarities=["U"],
        )
        cards = seeded_repo.get_cards_for_scan(scan_filter)
        assert len(cards) == 1
        assert cards[0]["name_en"] == "Counterspell"


class TestGetCardsForScanLimit:
    """7. get_cards_for_scan (limit): respects limit parameter."""

    def test_respects_limit(self, seeded_repo) -> None:
        scan_filter = ScanFilter(
            scan_type=ScanType.COLLECTION,
            limit=2,
        )
        cards = seeded_repo.get_cards_for_scan(scan_filter)
        assert len(cards) == 2


class TestGetScanRunNotFound:
    """8. get_scan_run (not found): returns None for non-existent ID."""

    def test_returns_none_for_missing(self, repo) -> None:
        result = repo.get_scan_run(99999)
        assert result is None


class TestGetCardsForScanSlug:
    """Verify slug extraction from URL."""

    def test_slug_extracted_from_url(self, seeded_repo) -> None:
        scan_filter = ScanFilter(scan_type=ScanType.COLLECTION)
        cards = seeded_repo.get_cards_for_scan(scan_filter)

        slugs = {c["external_id"]: c["slug"] for c in cards}
        assert slugs["100"] == "lightning-bolt"
        assert slugs["200"] == "counterspell"
        assert slugs["300"] == "swords-to-plowshares"
