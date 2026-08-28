"""Tests for src.database.cleanup.reset_database — full DB reset keeping collection."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from unittest.mock import patch

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from src.database.cleanup import reset_database
from src.database.models import (
    CardLegalityRow,
    CardRow,
    CollectionErrorRow,
    DeckCardRow,
    DeckRow,
    ExchangeRateRow,
    LegalityHistoryRow,
    PortfolioSnapshotRow,
    PriceObservationRow,
    ScanRunRow,
    SourceCardRow,
    UserCollectionRow,
    UserRow,
)
from src.database.repository import Repository


@pytest.fixture()
def repo(tmp_path):
    """Create a Repository backed by a temp SQLite DB."""
    db_path = tmp_path / "test.db"
    db_url = f"sqlite:///{db_path}"
    return Repository(db_url=db_url)


@pytest.fixture()
def seeded_reset_repo(repo):
    """Seed repo with diverse data for reset testing.

    Cards:
    - c1 Lightning Bolt (2xm/1) — IN collection, card_id linked
    - c2 Counterspell (2xm/2) — NOT in collection
    - c3 Pikachu (sv1/25) — NOT in collection

    Source cards:
    - sc1 -> c1 (should survive)
    - sc2 -> c2 (should be deleted)
    - sc_orphan -> None (should be deleted)

    Plus: price_observations, scan_runs, portfolio_snapshots, collection_errors,
    card_legalities, legality_history, users, decks, exchange_rates.
    """
    engine = repo.engine
    with Session(engine) as session:
        # Cards
        c1 = CardRow(game="magic", name_en="Lightning Bolt", set_code="2xm", collector_number="1")
        c2 = CardRow(game="magic", name_en="Counterspell", set_code="2xm", collector_number="2")
        c3 = CardRow(game="pokemon", name_en="Pikachu", set_code="sv1", collector_number="25")
        session.add_all([c1, c2, c3])
        session.flush()

        # Source cards
        sc1 = SourceCardRow(
            source="liga",
            external_id="liga_1",
            card_id=c1.id,
            url="https://liga/1",
            name_en="Lightning Bolt",
        )
        sc2 = SourceCardRow(
            source="liga",
            external_id="liga_2",
            card_id=c2.id,
            url="https://liga/2",
            name_en="Counterspell",
        )
        sc_orphan = SourceCardRow(
            source="myp",
            external_id="orphan_1",
            card_id=None,
            url="https://myp/orphan",
        )
        session.add_all([sc1, sc2, sc_orphan])
        session.flush()

        # Price observations
        session.add_all(
            [
                PriceObservationRow(
                    source="liga",
                    external_id="liga_1",
                    observed_at=date(2026, 8, 20),
                    median_price=Decimal("10.00"),
                    currency="BRL",
                ),
                PriceObservationRow(
                    source="liga",
                    external_id="liga_2",
                    observed_at=date(2026, 8, 20),
                    median_price=Decimal("5.00"),
                    currency="BRL",
                ),
                PriceObservationRow(
                    source="myp",
                    external_id="orphan_1",
                    observed_at=date(2026, 8, 19),
                    median_price=Decimal("1.00"),
                    currency="BRL",
                ),
            ]
        )

        # Scan runs
        session.add(
            ScanRunRow(
                scan_type="collection",
                status="completed",
                cards_total=10,
                cards_processed=10,
            )
        )

        # Portfolio snapshots
        session.add(
            PortfolioSnapshotRow(
                user_id="user1",
                snapshot_date=date(2026, 8, 20),
                total_value_brl=Decimal("100.00"),
                priced_card_count=5,
                total_card_count=10,
            )
        )

        # Collection errors
        session.add(
            CollectionErrorRow(
                source="myp",
                url="https://myp/fail",
                error_type="timeout",
                error_message="timed out",
            )
        )

        # Card legalities
        session.add_all(
            [
                CardLegalityRow(card_id=c1.id, format="commander", status="legal"),
                CardLegalityRow(card_id=c2.id, format="commander", status="legal"),
            ]
        )

        # Legality history
        session.add_all(
            [
                LegalityHistoryRow(
                    card_id=c1.id,
                    format="commander",
                    old_status=None,
                    new_status="legal",
                    changed_at=datetime(2026, 8, 15),
                ),
                LegalityHistoryRow(
                    card_id=c2.id,
                    format="commander",
                    old_status=None,
                    new_status="legal",
                    changed_at=datetime(2026, 8, 15),
                ),
            ]
        )

        # User (should be preserved)
        session.add(
            UserRow(
                email="test@example.com",
                display_name="Test User",
                auth_provider="email",
            )
        )

        # Deck + deck_cards (should be preserved)
        deck = DeckRow(user_id="user1", name="My Deck")
        session.add(deck)
        session.flush()
        session.add(
            DeckCardRow(
                deck_id=deck.id,
                name_en="Lightning Bolt",
                quantity=1,
            )
        )

        # Exchange rate (should be preserved)
        session.add(
            ExchangeRateRow(
                rate_date=date(2026, 8, 20),
                rate=Decimal("5.50"),
            )
        )

        # Collection: only Lightning Bolt, with card_id linked
        session.add(
            UserCollectionRow(
                user_id="user1",
                card_id=c1.id,
                set_code="2xm",
                collector_number="1",
                name_en="Lightning Bolt",
            )
        )

        session.commit()

    return repo


class TestResetDryRunCounts:
    def test_reset_dry_run_counts(self, seeded_reset_repo):
        """Dry-run should report correct counts without deleting anything."""
        db_url = str(seeded_reset_repo.engine.url)
        result = reset_database(db_url, dry_run=True)

        assert result.dry_run is True
        assert result.prices_deleted == 3
        assert result.scan_runs_deleted == 1
        assert result.portfolio_snapshots_deleted == 1
        assert result.collection_errors_deleted == 1
        assert result.cards_deleted == 2  # c2 + c3
        assert result.source_cards_deleted == 2  # sc2 + sc_orphan
        assert result.legalities_deleted == 1  # c2 only
        assert result.legality_history_deleted == 1  # c2 only
        assert result.cards_kept == 1  # c1

        # Verify nothing was actually deleted
        with Session(seeded_reset_repo.engine) as session:
            assert (
                session.execute(select(func.count()).select_from(PriceObservationRow)).scalar() == 3
            )
            assert session.execute(select(func.count()).select_from(CardRow)).scalar() == 3
            assert session.execute(select(func.count()).select_from(ScanRunRow)).scalar() == 1


class TestResetDeletesCorrectData:
    def test_reset_deletes_correct_data(self, seeded_reset_repo):
        """Real reset should delete the right data and preserve sacred tables."""
        db_url = str(seeded_reset_repo.engine.url)
        result = reset_database(db_url, dry_run=False, skip_backup=True)

        assert result.dry_run is False
        assert result.prices_deleted == 3
        assert result.scan_runs_deleted == 1
        assert result.cards_deleted == 2
        assert result.source_cards_deleted == 2

        with Session(seeded_reset_repo.engine) as session:
            # Truncated tables should be empty
            assert (
                session.execute(select(func.count()).select_from(PriceObservationRow)).scalar() == 0
            )
            assert session.execute(select(func.count()).select_from(ScanRunRow)).scalar() == 0
            assert (
                session.execute(select(func.count()).select_from(PortfolioSnapshotRow)).scalar()
                == 0
            )
            assert (
                session.execute(select(func.count()).select_from(CollectionErrorRow)).scalar() == 0
            )

            # Only collection-linked card survives
            remaining_cards = session.execute(select(CardRow)).scalars().all()
            assert len(remaining_cards) == 1
            assert remaining_cards[0].name_en == "Lightning Bolt"

            # Only source_card for surviving card remains
            remaining_sc = session.execute(select(SourceCardRow)).scalars().all()
            assert len(remaining_sc) == 1
            assert remaining_sc[0].external_id == "liga_1"

            # Only legalities for surviving card remain
            assert session.execute(select(func.count()).select_from(CardLegalityRow)).scalar() == 1
            assert (
                session.execute(select(func.count()).select_from(LegalityHistoryRow)).scalar() == 1
            )

            # Sacred tables untouched
            assert (
                session.execute(select(func.count()).select_from(UserCollectionRow)).scalar() == 1
            )
            assert session.execute(select(func.count()).select_from(UserRow)).scalar() == 1
            assert session.execute(select(func.count()).select_from(DeckRow)).scalar() == 1
            assert session.execute(select(func.count()).select_from(DeckCardRow)).scalar() == 1
            assert session.execute(select(func.count()).select_from(ExchangeRateRow)).scalar() == 1


class TestResetRefusesEmptyCollection:
    def test_reset_refuses_empty_collection(self, repo):
        """Reset must refuse when user_collection has zero rows."""
        db_url = str(repo.engine.url)
        with pytest.raises(ValueError, match="Cannot reset with empty collection"):
            reset_database(db_url, dry_run=True)


class TestResetCreatesBackup:
    def test_reset_creates_backup(self, seeded_reset_repo, tmp_path):
        """Reset with skip_backup=False should produce a backup file."""
        db_url = str(seeded_reset_repo.engine.url)

        with patch("src.database.cleanup.backup_database") as mock_backup:
            mock_backup.return_value = Path(tmp_path / "backup.db")
            result = reset_database(db_url, dry_run=False, skip_backup=False)

        mock_backup.assert_called_once()
        assert result.backup_path is not None


class TestResetVacuumRuns:
    def test_reset_vacuum_runs(self, seeded_reset_repo):
        """Verify VACUUM executes without error on a real SQLite file."""
        db_url = str(seeded_reset_repo.engine.url)
        # Should not raise
        result = reset_database(db_url, dry_run=False, skip_backup=True)
        assert result.dry_run is False
