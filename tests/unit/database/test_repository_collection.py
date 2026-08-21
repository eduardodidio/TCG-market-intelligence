"""Tests for Repository.list_collection sorting and offset pagination."""

from __future__ import annotations

from datetime import datetime

import pytest
from sqlalchemy.orm import Session

from src.database.models import UserCollectionRow
from src.database.repository import Repository


@pytest.fixture()
def repo(tmp_path):
    db_path = tmp_path / "test.db"
    return Repository(f"sqlite:///{db_path}")


@pytest.fixture()
def seeded_repo(repo):
    """Seed repo with collection entries for sorting tests."""
    engine = repo.engine
    with Session(engine) as session:
        rows = [
            UserCollectionRow(
                user_id="u1",
                set_code="DMR",
                collector_number="10",
                name_en="Counterspell",
                name_pt="Contrafeitico",
                quantity=1,
                created_at=datetime(2026, 1, 3),
            ),
            UserCollectionRow(
                user_id="u1",
                set_code="2XM",
                collector_number="5",
                name_en="Lightning Bolt",
                name_pt="Raio",
                quantity=2,
                created_at=datetime(2026, 1, 1),
            ),
            UserCollectionRow(
                user_id="u1",
                set_code="MH2",
                collector_number="1",
                name_en="Aether Vial",
                name_pt=None,
                quantity=1,
                created_at=datetime(2026, 1, 2),
            ),
            UserCollectionRow(
                user_id="u1",
                set_code="DMR",
                collector_number="20",
                name_en=None,
                name_pt="Carta Sem Nome EN",
                quantity=1,
                created_at=datetime(2026, 1, 4),
            ),
        ]
        session.add_all(rows)
        session.commit()
        repo._test_ids = [r.id for r in rows]
    return repo


class TestListCollectionSorting:
    def test_default_sort_by_name_asc(self, seeded_repo):
        rows = seeded_repo.list_collection("u1")
        names = [r.name_en or "" for r in rows]
        assert names == sorted(names)

    def test_sort_by_name_desc(self, seeded_repo):
        rows = seeded_repo.list_collection("u1", sort_by="name", sort_dir="desc")
        names = [r.name_en or "" for r in rows]
        assert names == sorted(names, reverse=True)

    def test_sort_by_set_asc(self, seeded_repo):
        rows = seeded_repo.list_collection("u1", sort_by="set", sort_dir="asc")
        sets = [r.set_code for r in rows]
        assert sets == sorted(sets)

    def test_sort_by_set_desc(self, seeded_repo):
        rows = seeded_repo.list_collection("u1", sort_by="set", sort_dir="desc")
        sets = [r.set_code for r in rows]
        assert sets == sorted(sets, reverse=True)

    def test_sort_by_number_asc(self, seeded_repo):
        rows = seeded_repo.list_collection("u1", sort_by="number", sort_dir="asc")
        numbers = [r.collector_number for r in rows]
        assert numbers == sorted(numbers)

    def test_sort_by_added_asc(self, seeded_repo):
        rows = seeded_repo.list_collection("u1", sort_by="added", sort_dir="asc")
        dates = [r.created_at for r in rows]
        assert dates == sorted(dates)

    def test_sort_by_added_desc(self, seeded_repo):
        rows = seeded_repo.list_collection("u1", sort_by="added", sort_dir="desc")
        dates = [r.created_at for r in rows]
        assert dates == sorted(dates, reverse=True)

    def test_invalid_sort_by_falls_back_to_name(self, seeded_repo):
        rows = seeded_repo.list_collection("u1", sort_by="invalid")
        names = [r.name_en or "" for r in rows]
        assert names == sorted(names)

    def test_null_name_en_sorts_to_beginning_asc(self, seeded_repo):
        """NULL name_en should coalesce to '' and appear first in asc."""
        rows = seeded_repo.list_collection("u1", sort_by="name", sort_dir="asc")
        # The entry with name_en=None should sort as '' (first)
        assert rows[0].name_en is None

    def test_stable_ordering_with_same_sort_key(self, repo):
        """Entries with same sort key should be ordered by id asc."""
        engine = repo.engine
        with Session(engine) as session:
            r1 = UserCollectionRow(
                user_id="u1",
                set_code="DMR",
                collector_number="1",
                name_en="Same Name",
                quantity=1,
            )
            r2 = UserCollectionRow(
                user_id="u1",
                set_code="DMR",
                collector_number="2",
                name_en="Same Name",
                quantity=1,
            )
            session.add_all([r1, r2])
            session.commit()
            id1, id2 = r1.id, r2.id

        rows = repo.list_collection("u1", sort_by="name")
        assert rows[0].id == id1
        assert rows[1].id == id2


class TestListCollectionOffset:
    def test_offset_skips_rows(self, seeded_repo):
        all_rows = seeded_repo.list_collection("u1", limit=50)
        offset_rows = seeded_repo.list_collection("u1", offset=2, limit=50)
        assert len(offset_rows) == len(all_rows) - 2

    def test_offset_zero_returns_all(self, seeded_repo):
        all_rows = seeded_repo.list_collection("u1", limit=50)
        offset_rows = seeded_repo.list_collection("u1", offset=0, limit=50)
        assert len(offset_rows) == len(all_rows)

    def test_offset_with_limit(self, seeded_repo):
        # limit=1 -> returns limit+1=2 for has_next detection
        rows = seeded_repo.list_collection("u1", offset=0, limit=1)
        assert len(rows) == 2  # limit+1

    def test_offset_beyond_data_returns_empty(self, seeded_repo):
        rows = seeded_repo.list_collection("u1", offset=100, limit=50)
        assert rows == []

    def test_offset_combined_with_sort(self, seeded_repo):
        all_rows = seeded_repo.list_collection(
            "u1",
            sort_by="added",
            sort_dir="desc",
            limit=50,
        )
        offset_rows = seeded_repo.list_collection(
            "u1",
            sort_by="added",
            sort_dir="desc",
            offset=1,
            limit=50,
        )
        assert offset_rows[0].id == all_rows[1].id


class TestListCollectionBackwardCompat:
    def test_after_id_still_works(self, seeded_repo):
        all_rows = seeded_repo.list_collection("u1", limit=50)
        first_id = all_rows[0].id
        rest = seeded_repo.list_collection("u1", after_id=first_id, limit=50)
        assert all(r.id > first_id for r in rest)

    def test_after_id_takes_precedence_over_offset(self, seeded_repo):
        """When both after_id and offset are provided, after_id wins."""
        all_rows = seeded_repo.list_collection("u1", limit=50)
        first_id = all_rows[0].id
        rows = seeded_repo.list_collection(
            "u1",
            after_id=first_id,
            offset=0,
            limit=50,
        )
        assert all(r.id > first_id for r in rows)

    def test_name_search_filter_still_works(self, seeded_repo):
        rows = seeded_repo.list_collection("u1", name_search="bolt", limit=50)
        assert len(rows) == 1
        assert rows[0].name_en == "Lightning Bolt"

    def test_set_code_filter_still_works(self, seeded_repo):
        rows = seeded_repo.list_collection("u1", set_code="DMR", limit=50)
        assert all(r.set_code == "DMR" for r in rows)


class TestCountCollection:
    def test_count_all(self, seeded_repo):
        assert seeded_repo.count_collection("u1") == 4

    def test_count_with_name_search(self, seeded_repo):
        assert seeded_repo.count_collection("u1", name_search="bolt") == 1

    def test_count_with_set_code(self, seeded_repo):
        assert seeded_repo.count_collection("u1", set_code="DMR") == 2

    def test_count_zero(self, seeded_repo):
        assert seeded_repo.count_collection("nobody") == 0
