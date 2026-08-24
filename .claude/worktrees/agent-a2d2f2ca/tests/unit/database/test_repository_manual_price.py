"""Tests for Repository.upsert_manual_price."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy.orm import Session

from src.database.models import CardRow, PriceObservationRow, UserCollectionRow
from src.database.repository import Repository


@pytest.fixture()
def repo(tmp_path):
    db_path = tmp_path / "test.db"
    return Repository(f"sqlite:///{db_path}")


@pytest.fixture()
def seeded_repo(repo):
    """Seed repo with a card + collection entry for manual price tests."""
    with Session(repo.engine) as session:
        card = CardRow(
            game="magic",
            name_en="Lightning Bolt",
            name_pt="Raio",
            set_code="DMR",
            collector_number="123",
        )
        session.add(card)
        session.flush()
        entry = UserCollectionRow(
            user_id="u1",
            set_code="DMR",
            collector_number="123",
            name_en="Lightning Bolt",
            name_pt="Raio",
            quantity=1,
            card_id=card.id,
        )
        session.add(entry)
        session.commit()
        session.refresh(card)
        session.refresh(entry)
    return repo, card.id, entry.id


class TestUpsertManualPrice:
    def test_creates_observation_with_source_manual(self, seeded_repo):
        repo, card_id, _entry_id = seeded_repo
        obs_id = repo.upsert_manual_price(card_id, Decimal("10.50"), date(2026, 8, 22))

        with Session(repo.engine) as session:
            obs = session.get(PriceObservationRow, obs_id)
            assert obs is not None
            assert obs.source == "manual"
            assert obs.median_price == Decimal("10.50")
            assert obs.currency == "BRL"
            assert obs.observed_at == date(2026, 8, 22)

    def test_external_id_format(self, seeded_repo):
        repo, card_id, _entry_id = seeded_repo
        obs_id = repo.upsert_manual_price(card_id, Decimal("5.00"), date(2026, 8, 22))

        with Session(repo.engine) as session:
            obs = session.get(PriceObservationRow, obs_id)
            assert obs.external_id == f"manual_{card_id}"

    def test_upserts_same_day(self, seeded_repo):
        """Second call on the same day updates existing row, not creates duplicate."""
        repo, card_id, _entry_id = seeded_repo
        repo.upsert_manual_price(card_id, Decimal("10.00"), date(2026, 8, 22))
        repo.upsert_manual_price(card_id, Decimal("15.00"), date(2026, 8, 22))

        with Session(repo.engine) as session:
            all_obs = (
                session.query(PriceObservationRow)
                .filter(
                    PriceObservationRow.source == "manual",
                    PriceObservationRow.external_id == f"manual_{card_id}",
                )
                .all()
            )
            assert len(all_obs) == 1
            assert all_obs[0].median_price == Decimal("15.00")

    def test_creates_new_day(self, seeded_repo):
        """Call on a different day creates a new observation row."""
        repo, card_id, _entry_id = seeded_repo
        repo.upsert_manual_price(card_id, Decimal("10.00"), date(2026, 8, 22))
        repo.upsert_manual_price(card_id, Decimal("12.00"), date(2026, 8, 23))

        with Session(repo.engine) as session:
            all_obs = (
                session.query(PriceObservationRow)
                .filter(
                    PriceObservationRow.source == "manual",
                    PriceObservationRow.external_id == f"manual_{card_id}",
                )
                .all()
            )
            assert len(all_obs) == 2
            prices = sorted([obs.median_price for obs in all_obs])
            assert prices == [Decimal("10.00"), Decimal("12.00")]

    def test_round_trip_upsert_then_read_via_get_latest_prices_batch(self, seeded_repo):
        """Round-trip regression test for B1 fix: write via upsert_manual_price,
        read back via get_latest_prices_batch. Both must use card_id in
        external_id so the manual price is found on read."""
        repo, card_id, _entry_id = seeded_repo
        repo.upsert_manual_price(card_id, Decimal("25.00"), date(2026, 8, 22))

        result = repo.get_latest_prices_batch([card_id])
        obs = result.get(card_id)
        assert obs is not None, "get_latest_prices_batch must find the manual price"
        assert obs.source == "manual"
        assert obs.median_price == Decimal("25.00")
        assert obs.external_id == f"manual_{card_id}"

    def test_auto_creates_card_via_repository(self, repo):
        """Verify create_canonical_card + link works for unlinked entry."""
        with Session(repo.engine) as session:
            entry = UserCollectionRow(
                user_id="u1",
                set_code="DMR",
                collector_number="123",
                name_en="Lightning Bolt",
                name_pt="Raio",
                quantity=1,
            )
            session.add(entry)
            session.commit()
            session.refresh(entry)
            entry_id = entry.id

        # Entry starts with no card_id
        entry = repo.get_collection_entry(entry_id)
        assert entry.card_id is None

        # Create a card and link it (this is what the endpoint does)
        card_id = repo.create_canonical_card(
            game="magic",
            name_en="Lightning Bolt",
            name_pt="Raio",
            set_code="DMR",
            collector_number="123",
        )
        repo.link_collection_entry(entry_id, card_id)

        # Now entry should have a card_id
        entry = repo.get_collection_entry(entry_id)
        assert entry.card_id == card_id

        # And the card exists
        with Session(repo.engine) as session:
            card = session.get(CardRow, card_id)
            assert card is not None
            assert card.name_en == "Lightning Bolt"
