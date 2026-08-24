"""Tests for src.database.cleanup -- non-collection data removal."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from pathlib import Path
from unittest.mock import patch

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from src.database.cleanup import cleanup_non_collection_data
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
    db_path = tmp_path / "test.db"
    db_url = f"sqlite:///{db_path}"
    return Repository(db_url=db_url)


@pytest.fixture()
def seeded_cleanup_repo(repo, tmp_path):
    """Seed repo with:
    - 3 cards: Lightning Bolt (2xm/1), Counterspell (2xm/2), Pikachu (sv1/25)
    - 2 source_cards: ext1 -> card1, ext2 -> card2
    - 3 observations: 2 for ext1, 1 for ext2
    - 1 collection entry: Lightning Bolt (2xm/1) -- so Counterspell + Pikachu should be deletable
    """
    engine = repo.engine
    with Session(engine) as session:
        c1 = CardRow(
            game="magic",
            name_en="Lightning Bolt",
            name_pt="Raio",
            set_code="2xm",
            collector_number="1",
        )
        c2 = CardRow(
            game="magic",
            name_en="Counterspell",
            name_pt="Contrafeitico",
            set_code="2xm",
            collector_number="2",
        )
        c3 = CardRow(
            game="pokemon",
            name_en="Pikachu",
            name_pt="Pikachu",
            set_code="sv1",
            collector_number="25",
        )
        session.add_all([c1, c2, c3])
        session.flush()

        sc1 = SourceCardRow(
            source="myp",
            external_id="ext1",
            card_id=c1.id,
            url="https://myp/ext1",
            name_en="Lightning Bolt",
            set_code="2xm",
            collector_number="1",
        )
        sc2 = SourceCardRow(
            source="myp",
            external_id="ext2",
            card_id=c2.id,
            url="https://myp/ext2",
            name_en="Counterspell",
            set_code="2xm",
            collector_number="2",
        )
        session.add_all([sc1, sc2])
        session.flush()

        obs1 = PriceObservationRow(
            source="myp",
            external_id="ext1",
            observed_at=date(2026, 8, 10),
            median_price=Decimal("5.50"),
            currency="BRL",
        )
        obs2 = PriceObservationRow(
            source="myp",
            external_id="ext1",
            observed_at=date(2026, 8, 15),
            median_price=Decimal("6.00"),
            currency="BRL",
        )
        obs3 = PriceObservationRow(
            source="myp",
            external_id="ext2",
            observed_at=date(2026, 8, 12),
            median_price=Decimal("3.00"),
            currency="BRL",
        )
        session.add_all([obs1, obs2, obs3])
        session.flush()

        # Collection: only Lightning Bolt
        uc1 = UserCollectionRow(
            user_id="user1",
            set_code="2xm",
            collector_number="1",
            name_en="Lightning Bolt",
        )
        session.add(uc1)
        session.commit()

    return repo


class TestCleanupRefusesEmptyCollection:
    def test_raises_with_empty_collection(self, repo):
        """Cleanup must refuse when user_collection has zero rows."""
        db_url = str(repo.engine.url)
        with pytest.raises(ValueError, match="Cannot cleanup with empty collection"):
            cleanup_non_collection_data(db_url)

    def test_raises_with_empty_collection_dry_run(self, repo):
        """Even dry-run should refuse with an empty collection."""
        db_url = str(repo.engine.url)
        with pytest.raises(ValueError, match="Cannot cleanup with empty collection"):
            cleanup_non_collection_data(db_url, dry_run=True)


class TestDryRun:
    def test_reports_correct_counts(self, seeded_cleanup_repo):
        """Dry-run should report counts but not delete anything."""
        db_url = str(seeded_cleanup_repo.engine.url)
        result = cleanup_non_collection_data(db_url, dry_run=True)

        assert result.dry_run is True
        # Counterspell (card) + Pikachu (card) = 2 cards
        assert result.cards_deleted == 2
        # Only sc2 (Counterspell) has a source_card linked to a card being deleted
        assert result.source_cards_deleted == 1
        # ext2 has 1 observation
        assert result.observations_deleted == 1

    def test_does_not_mutate_database(self, seeded_cleanup_repo):
        """After dry-run, row counts must be unchanged."""
        db_url = str(seeded_cleanup_repo.engine.url)
        cleanup_non_collection_data(db_url, dry_run=True)

        with Session(seeded_cleanup_repo.engine) as session:
            assert session.execute(select(func.count()).select_from(CardRow)).scalar() == 3
            assert session.execute(select(func.count()).select_from(SourceCardRow)).scalar() == 2
            assert (
                session.execute(select(func.count()).select_from(PriceObservationRow)).scalar() == 3
            )


class TestCleanupDeletesNonCollectionData:
    def test_deletes_cards_not_in_collection(self, seeded_cleanup_repo):
        """Counterspell and Pikachu are not in the collection and should be deleted."""
        db_url = str(seeded_cleanup_repo.engine.url)
        result = cleanup_non_collection_data(db_url, skip_backup=True)

        assert result.dry_run is False
        assert result.cards_deleted == 2
        assert result.source_cards_deleted == 1
        assert result.observations_deleted == 1

        with Session(seeded_cleanup_repo.engine) as session:
            remaining_cards = session.execute(select(CardRow)).scalars().all()
            assert len(remaining_cards) == 1
            assert remaining_cards[0].name_en == "Lightning Bolt"

    def test_preserves_collection_linked_data(self, seeded_cleanup_repo):
        """Lightning Bolt's card, source_card, and observations must survive."""
        db_url = str(seeded_cleanup_repo.engine.url)
        cleanup_non_collection_data(db_url, skip_backup=True)

        with Session(seeded_cleanup_repo.engine) as session:
            cards = session.execute(select(CardRow)).scalars().all()
            assert len(cards) == 1
            assert cards[0].name_en == "Lightning Bolt"

            source_cards = session.execute(select(SourceCardRow)).scalars().all()
            assert len(source_cards) == 1
            assert source_cards[0].external_id == "ext1"

            obs = session.execute(select(PriceObservationRow)).scalars().all()
            assert len(obs) == 2
            assert all(o.external_id == "ext1" for o in obs)

    def test_nothing_to_clean(self, repo):
        """When all DB cards are in the collection, report nothing to clean."""
        engine = repo.engine
        with Session(engine) as session:
            c1 = CardRow(
                game="magic",
                name_en="Bolt",
                set_code="2xm",
                collector_number="1",
            )
            session.add(c1)
            session.flush()
            uc = UserCollectionRow(
                user_id="user1",
                set_code="2xm",
                collector_number="1",
                name_en="Bolt",
            )
            session.add(uc)
            session.commit()

        db_url = str(repo.engine.url)
        result = cleanup_non_collection_data(db_url, skip_backup=True)

        assert result.cards_deleted == 0
        assert result.source_cards_deleted == 0
        assert result.observations_deleted == 0


class TestCleanupWithBackup:
    def test_creates_backup_before_delete(self, seeded_cleanup_repo, tmp_path):
        """Cleanup should call backup_database before deleting."""
        db_url = str(seeded_cleanup_repo.engine.url)

        with patch("src.database.cleanup.backup_database") as mock_backup:
            mock_backup.return_value = Path(tmp_path / "fake_backup.db")
            result = cleanup_non_collection_data(db_url, skip_backup=False)

        mock_backup.assert_called_once()
        assert result.backup_path is not None

    def test_skip_backup_flag(self, seeded_cleanup_repo):
        """With skip_backup=True, no backup should be created."""
        db_url = str(seeded_cleanup_repo.engine.url)

        with patch("src.database.cleanup.backup_database") as mock_backup:
            result = cleanup_non_collection_data(db_url, skip_backup=True)

        mock_backup.assert_not_called()
        assert result.backup_path is None


class TestCleanupSetCodeMatching:
    def test_lowercase_set_code_matching(self, repo):
        """After normalization, both cards and collection use lowercase set_code."""
        engine = repo.engine
        with Session(engine) as session:
            c1 = CardRow(
                game="magic",
                name_en="Bolt",
                set_code="2xm",
                collector_number="1",
            )
            c2 = CardRow(
                game="magic",
                name_en="Spell",
                set_code="2xm",
                collector_number="2",
            )
            session.add_all([c1, c2])
            session.flush()
            # Collection also uses lowercase set_code
            uc = UserCollectionRow(
                user_id="u1",
                set_code="2xm",
                collector_number="1",
                name_en="Bolt",
            )
            session.add(uc)
            session.commit()

        db_url = str(repo.engine.url)
        result = cleanup_non_collection_data(db_url, skip_backup=True)

        # Only c2 should be deleted; c1 matches via direct comparison
        assert result.cards_deleted == 1
        with Session(engine) as session:
            remaining = session.execute(select(CardRow)).scalars().all()
            assert len(remaining) == 1
            assert remaining[0].name_en == "Bolt"


class TestCleanupOrphanSourceCards:
    def test_deletes_orphan_source_cards(self, repo):
        """Source cards with card_id=None should also be cleaned up."""
        engine = repo.engine
        with Session(engine) as session:
            c1 = CardRow(
                game="magic",
                name_en="Bolt",
                set_code="2xm",
                collector_number="1",
            )
            session.add(c1)
            session.flush()

            sc_orphan = SourceCardRow(
                source="myp",
                external_id="orphan1",
                card_id=None,
                url="https://myp/orphan1",
            )
            obs_orphan = PriceObservationRow(
                source="myp",
                external_id="orphan1",
                observed_at=date(2026, 8, 10),
                median_price=Decimal("1.00"),
                currency="BRL",
            )
            session.add_all([sc_orphan, obs_orphan])
            session.flush()

            uc = UserCollectionRow(
                user_id="u1",
                set_code="2xm",
                collector_number="1",
                name_en="Bolt",
            )
            session.add(uc)
            session.commit()

        db_url = str(repo.engine.url)
        result = cleanup_non_collection_data(db_url, skip_backup=True)

        assert result.source_cards_deleted == 1
        assert result.observations_deleted == 1

        with Session(engine) as session:
            assert session.execute(select(func.count()).select_from(SourceCardRow)).scalar() == 0
            assert (
                session.execute(select(func.count()).select_from(PriceObservationRow)).scalar() == 0
            )
