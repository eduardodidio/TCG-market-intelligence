"""Tests for snapshot-related repository methods (F12-T04).

Covers test plan scenarios I01-I10:
 I01. get_linked_collection_with_source: returns linked entries with source card info
 I02. get_linked_collection_with_source: filters by source
 I03. get_linked_collection_with_source: no linked entries returns empty list
 I04. get_linked_collection_with_source: slug extracted from URL
 I05. get_linked_collection_with_source: multiple entries for same card
 I06. has_snapshot_for_date: returns True when snapshot exists
 I07. has_snapshot_for_date: returns False when no snapshot
 I08. has_snapshot_for_date: different date returns False
 I09. has_snapshot_for_date: different source returns False
 I10. has_snapshot_for_date: different external_id returns False
"""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

import pytest
from sqlalchemy.orm import Session

from src.database.models import (
    CardRow,
    PriceObservationRow,
    SourceCardRow,
    UserCollectionRow,
)
from src.database.repository import Repository


@pytest.fixture()
def repo(tmp_path):
    """Create a Repository backed by a temp SQLite DB."""
    db_path = tmp_path / "test_snapshot.db"
    db_url = f"sqlite:///{db_path}"
    return Repository(db_url=db_url)


@pytest.fixture()
def seeded_repo(repo):
    """Seed repo with cards, source_cards, and user_collection entries."""
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
            set_code="2XM",
            collector_number="2",
        )
        session.add_all([c1, c2])
        session.flush()

        # Source cards (myp)
        sc1 = SourceCardRow(
            source="myp",
            external_id="ext1",
            card_id=c1.id,
            url="https://mypcards.com/magic/produto/ext1/lightning-bolt",
            name_en="Lightning Bolt",
            set_code="2XM",
            collector_number="1",
        )
        sc2 = SourceCardRow(
            source="myp",
            external_id="ext2",
            card_id=c2.id,
            url="https://mypcards.com/magic/produto/ext2/counterspell",
            name_en="Counterspell",
            set_code="2XM",
            collector_number="2",
        )
        # Source card from a different source
        sc3 = SourceCardRow(
            source="other",
            external_id="ext3",
            card_id=c1.id,
            url="https://other.com/cards/ext3/bolt",
            name_en="Lightning Bolt",
            set_code="2XM",
            collector_number="1",
        )
        session.add_all([sc1, sc2, sc3])
        session.flush()

        # User collection entries
        # Linked entry (card_id set)
        uc1 = UserCollectionRow(
            user_id="eduardo",
            card_id=c1.id,
            set_code="2XM",
            collector_number="1",
            name_en="Lightning Bolt",
            quantity=2,
        )
        # Another linked entry (different card)
        uc2 = UserCollectionRow(
            user_id="eduardo",
            card_id=c2.id,
            set_code="2XM",
            collector_number="2",
            name_en="Counterspell",
            quantity=1,
        )
        # Unlinked entry (card_id is NULL)
        uc3 = UserCollectionRow(
            user_id="eduardo",
            card_id=None,
            set_code="MOM",
            collector_number="99",
            name_en="Unlinked Card",
            quantity=1,
        )
        session.add_all([uc1, uc2, uc3])
        session.commit()

        repo._test_ids = {
            "c1": c1.id,
            "c2": c2.id,
            "sc1": sc1.id,
            "sc2": sc2.id,
            "sc3": sc3.id,
            "uc1": uc1.id,
            "uc2": uc2.id,
            "uc3": uc3.id,
        }
    return repo


class TestGetLinkedCollectionWithSource:
    """Tests for Repository.get_linked_collection_with_source()."""

    def test_returns_linked_entries_with_source_info(self, seeded_repo):
        """I01: returns linked entries with correct dict keys."""
        results = seeded_repo.get_linked_collection_with_source(source="myp")

        assert len(results) == 2
        for entry in results:
            assert "entry_id" in entry
            assert "card_id" in entry
            assert "external_id" in entry
            assert "slug" in entry
            assert "url" in entry

        # Check specific data
        external_ids = {e["external_id"] for e in results}
        assert external_ids == {"ext1", "ext2"}

    def test_filters_by_source(self, seeded_repo):
        """I02: only returns entries linked through the requested source."""
        myp_results = seeded_repo.get_linked_collection_with_source(source="myp")
        other_results = seeded_repo.get_linked_collection_with_source(source="other")

        # Both linked entries have myp source cards
        assert len(myp_results) == 2
        # c1 also has an "other" source card, so 1 entry for "other"
        assert len(other_results) == 1
        assert other_results[0]["external_id"] == "ext3"

    def test_no_linked_entries_returns_empty(self, repo):
        """I03: all entries unlinked -> returns empty list."""
        engine = repo.engine
        with Session(engine) as session:
            uc = UserCollectionRow(
                user_id="testuser",
                card_id=None,
                set_code="TST",
                collector_number="1",
                name_en="Unlinked",
                quantity=1,
            )
            session.add(uc)
            session.commit()

        results = repo.get_linked_collection_with_source(source="myp")
        assert results == []

    def test_slug_extracted_from_url(self, seeded_repo):
        """I04: slug is correctly extracted from the source_card URL."""
        results = seeded_repo.get_linked_collection_with_source(source="myp")

        slugs = {e["external_id"]: e["slug"] for e in results}
        assert slugs["ext1"] == "lightning-bolt"
        assert slugs["ext2"] == "counterspell"

    def test_multiple_entries_for_same_card(self, seeded_repo):
        """I05: multiple collection entries for the same card_id."""
        ids = seeded_repo._test_ids
        engine = seeded_repo.engine
        with Session(engine) as session:
            # Add a second collection entry for c1
            uc_extra = UserCollectionRow(
                user_id="eduardo",
                card_id=ids["c1"],
                set_code="2XM",
                collector_number="1",
                name_en="Lightning Bolt (foil)",
                quantity=1,
            )
            session.add(uc_extra)
            session.commit()

        results = seeded_repo.get_linked_collection_with_source(source="myp")

        # c1 now has 2 collection entries, c2 has 1 -> total 3
        ext1_entries = [e for e in results if e["external_id"] == "ext1"]
        assert len(ext1_entries) == 2

    def test_empty_db_returns_empty(self, repo):
        """Empty database returns empty list."""
        results = repo.get_linked_collection_with_source(source="myp")
        assert results == []


class TestHasSnapshotForDate:
    """Tests for Repository.has_snapshot_for_date()."""

    def test_returns_true_when_snapshot_exists(self, repo):
        """I06: returns True when jsonld_snapshot observation exists for date."""
        today = date.today()
        engine = repo.engine
        with Session(engine) as session:
            obs = PriceObservationRow(
                source="jsonld_snapshot",
                external_id="ext1",
                observed_at=today,
                median_price=Decimal("10.00"),
                currency="BRL",
            )
            session.add(obs)
            session.commit()

        assert repo.has_snapshot_for_date("ext1", today) is True

    def test_returns_false_when_no_snapshot(self, repo):
        """I07: returns False when no matching observation exists."""
        assert repo.has_snapshot_for_date("ext1", date.today()) is False

    def test_returns_false_for_different_date(self, repo):
        """I08: observation exists for different date -> False."""
        yesterday = date.today() - timedelta(days=1)
        today = date.today()
        engine = repo.engine
        with Session(engine) as session:
            obs = PriceObservationRow(
                source="jsonld_snapshot",
                external_id="ext1",
                observed_at=yesterday,
                median_price=Decimal("10.00"),
                currency="BRL",
            )
            session.add(obs)
            session.commit()

        assert repo.has_snapshot_for_date("ext1", today) is False
        # But yesterday should be True
        assert repo.has_snapshot_for_date("ext1", yesterday) is True

    def test_returns_false_for_different_source(self, repo):
        """I09: observation exists with source='myp' for same date -> False."""
        today = date.today()
        engine = repo.engine
        with Session(engine) as session:
            obs = PriceObservationRow(
                source="myp",  # Not jsonld_snapshot
                external_id="ext1",
                observed_at=today,
                median_price=Decimal("10.00"),
                currency="BRL",
            )
            session.add(obs)
            session.commit()

        assert repo.has_snapshot_for_date("ext1", today) is False

    def test_returns_false_for_different_external_id(self, repo):
        """I10: observation for different card on same date -> False."""
        today = date.today()
        engine = repo.engine
        with Session(engine) as session:
            obs = PriceObservationRow(
                source="jsonld_snapshot",
                external_id="ext999",
                observed_at=today,
                median_price=Decimal("10.00"),
                currency="BRL",
            )
            session.add(obs)
            session.commit()

        assert repo.has_snapshot_for_date("ext1", today) is False
