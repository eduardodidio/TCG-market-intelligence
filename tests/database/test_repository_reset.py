"""Tests for Repository.delete_all_price_observations."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from src.database.models import PriceObservationRow
from src.database.repository import Repository


@pytest.fixture()
def repo(tmp_path):
    """Create a Repository backed by a temp SQLite DB."""
    db_path = tmp_path / "test.db"
    db_url = f"sqlite:///{db_path}"
    return Repository(db_url=db_url)


def _seed_observations(repo: Repository) -> None:
    """Insert observations from liga, myp, and manual sources."""
    with Session(repo.engine) as session:
        session.add_all(
            [
                PriceObservationRow(
                    source="liga",
                    external_id="ext1",
                    observed_at=date(2026, 8, 20),
                    median_price=Decimal("10.00"),
                    currency="BRL",
                ),
                PriceObservationRow(
                    source="liga",
                    external_id="ext2",
                    observed_at=date(2026, 8, 20),
                    median_price=Decimal("15.00"),
                    currency="BRL",
                ),
                PriceObservationRow(
                    source="myp",
                    external_id="ext1",
                    observed_at=date(2026, 8, 19),
                    median_price=Decimal("5.50"),
                    currency="BRL",
                ),
                PriceObservationRow(
                    source="manual",
                    external_id="manual_ext1",
                    observed_at=date(2026, 8, 21),
                    median_price=Decimal("20.00"),
                    currency="BRL",
                ),
            ]
        )
        session.commit()


def _count_observations(repo: Repository, source: str | None = None) -> int:
    with Session(repo.engine) as session:
        stmt = select(func.count()).select_from(PriceObservationRow)
        if source is not None:
            stmt = stmt.where(PriceObservationRow.source == source)
        return session.execute(stmt).scalar() or 0


class TestDeleteAll:
    def test_delete_all_returns_correct_count(self, repo):
        """Calling with source=None should delete all rows and return count."""
        _seed_observations(repo)
        assert _count_observations(repo) == 4

        deleted = repo.delete_all_price_observations(source=None)

        assert deleted == 4
        assert _count_observations(repo) == 0

    def test_delete_all_including_protected_sources(self, repo):
        """No PROTECTED_SOURCES check -- liga and manual are deleted too."""
        _seed_observations(repo)

        deleted = repo.delete_all_price_observations()

        assert deleted == 4
        assert _count_observations(repo, "liga") == 0
        assert _count_observations(repo, "manual") == 0


class TestDeleteBySource:
    def test_delete_only_liga(self, repo):
        """Filtering by source='liga' should only delete liga rows."""
        _seed_observations(repo)

        deleted = repo.delete_all_price_observations(source="liga")

        assert deleted == 2
        assert _count_observations(repo, "liga") == 0
        # Others preserved
        assert _count_observations(repo, "myp") == 1
        assert _count_observations(repo, "manual") == 1

    def test_delete_only_myp(self, repo):
        """Filtering by source='myp' should only delete myp rows."""
        _seed_observations(repo)

        deleted = repo.delete_all_price_observations(source="myp")

        assert deleted == 1
        assert _count_observations(repo, "myp") == 0
        assert _count_observations(repo) == 3  # liga(2) + manual(1)


class TestEmptyTable:
    def test_empty_table_returns_zero(self, repo):
        """Calling on empty table should return 0 without error."""
        deleted = repo.delete_all_price_observations()

        assert deleted == 0

    def test_empty_table_with_source_returns_zero(self, repo):
        """Calling on empty table with source filter should return 0."""
        deleted = repo.delete_all_price_observations(source="liga")

        assert deleted == 0


class TestNoMatch:
    def test_no_matching_source_returns_zero(self, repo):
        """When source has no rows, returns 0 and preserves other data."""
        _seed_observations(repo)

        deleted = repo.delete_all_price_observations(source="nonexistent")

        assert deleted == 0
        assert _count_observations(repo) == 4  # all preserved

    def test_filter_liga_when_only_myp_exists(self, repo):
        """Filtering by liga when only myp rows exist returns 0."""
        with Session(repo.engine) as session:
            session.add(
                PriceObservationRow(
                    source="myp",
                    external_id="ext1",
                    observed_at=date(2026, 8, 20),
                    median_price=Decimal("5.00"),
                    currency="BRL",
                )
            )
            session.commit()

        deleted = repo.delete_all_price_observations(source="liga")

        assert deleted == 0
        assert _count_observations(repo, "myp") == 1
