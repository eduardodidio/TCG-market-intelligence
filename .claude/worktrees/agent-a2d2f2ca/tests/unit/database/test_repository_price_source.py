"""F50-T02: Tests for price source priority logic in get_latest_prices_batch.

Tests scenarios #18 and #19 from the test plan:
- Manual wins same day (source priority)
- Latest date wins cross-day (temporal priority)
"""

from __future__ import annotations

from datetime import date
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
    db_path = tmp_path / "test.db"
    return Repository(f"sqlite:///{db_path}")


@pytest.fixture()
def seeded_repo(repo):
    """Seed repo with a card, source card, and collection entry."""
    with Session(repo.engine) as session:
        card = CardRow(
            game="magic",
            name_en="Lightning Bolt",
            set_code="DMR",
            collector_number="123",
        )
        session.add(card)
        session.flush()

        source_card = SourceCardRow(
            source="myp",
            external_id="99999",
            card_id=card.id,
            sku="magic_dmr_123",
            url="https://mypcards.com/magic/99999/lightning-bolt",
        )
        session.add(source_card)

        entry = UserCollectionRow(
            user_id="u1",
            card_id=card.id,
            set_code="DMR",
            collector_number="123",
            name_en="Lightning Bolt",
            quantity=1,
        )
        session.add(entry)
        session.commit()
        session.refresh(card)
        session.refresh(entry)

    return repo, card.id, entry.id


class TestPriceSourcePriority:
    """get_latest_prices_batch price source priority logic."""

    def test_manual_wins_same_day(self, seeded_repo):
        """Scenario #18: manual beats MYP when both have same observed_at date."""
        repo, card_id, entry_id = seeded_repo
        same_day = date(2026, 8, 22)

        with Session(repo.engine) as session:
            # MYP observation
            myp_obs = PriceObservationRow(
                source="myp",
                external_id="99999",
                observed_at=same_day,
                median_price=Decimal("8.00"),
                currency="BRL",
            )
            session.add(myp_obs)

            # Manual observation on same day
            manual_obs = PriceObservationRow(
                source="manual",
                external_id=f"manual_{card_id}",
                observed_at=same_day,
                median_price=Decimal("12.00"),
                currency="BRL",
            )
            session.add(manual_obs)
            session.commit()

        result = repo.get_latest_prices_batch([card_id])
        winner = result[card_id]
        assert winner is not None
        assert winner.source == "manual"
        assert winner.median_price == Decimal("12.00")

    def test_latest_date_wins(self, seeded_repo):
        """Scenario #19: newer MYP observation beats older manual observation."""
        repo, card_id, entry_id = seeded_repo

        with Session(repo.engine) as session:
            # Older manual observation
            manual_obs = PriceObservationRow(
                source="manual",
                external_id=f"manual_{card_id}",
                observed_at=date(2026, 8, 20),
                median_price=Decimal("12.00"),
                currency="BRL",
            )
            session.add(manual_obs)

            # Newer MYP observation
            myp_obs = PriceObservationRow(
                source="myp",
                external_id="99999",
                observed_at=date(2026, 8, 22),
                median_price=Decimal("8.00"),
                currency="BRL",
            )
            session.add(myp_obs)
            session.commit()

        result = repo.get_latest_prices_batch([card_id])
        winner = result[card_id]
        assert winner is not None
        assert winner.source == "myp"
        assert winner.median_price == Decimal("8.00")

    def test_returns_manual_source_when_only_manual(self, seeded_repo):
        """Manual observation returned when it is the only observation."""
        repo, card_id, entry_id = seeded_repo

        with Session(repo.engine) as session:
            manual_obs = PriceObservationRow(
                source="manual",
                external_id=f"manual_{card_id}",
                observed_at=date(2026, 8, 22),
                median_price=Decimal("15.00"),
                currency="BRL",
            )
            session.add(manual_obs)
            session.commit()

        result = repo.get_latest_prices_batch([card_id])
        winner = result[card_id]
        assert winner is not None
        assert winner.source == "manual"
        assert winner.median_price == Decimal("15.00")

    def test_returns_myp_source_when_only_myp(self, seeded_repo):
        """MYP observation returned when it is the only observation."""
        repo, card_id, entry_id = seeded_repo

        with Session(repo.engine) as session:
            myp_obs = PriceObservationRow(
                source="myp",
                external_id="99999",
                observed_at=date(2026, 8, 22),
                median_price=Decimal("8.50"),
                currency="BRL",
            )
            session.add(myp_obs)
            session.commit()

        result = repo.get_latest_prices_batch([card_id])
        winner = result[card_id]
        assert winner is not None
        assert winner.source == "myp"

    def test_returns_none_when_no_observations(self, seeded_repo):
        """Returns None when card has no price observations."""
        repo, card_id, entry_id = seeded_repo

        result = repo.get_latest_prices_batch([card_id])
        assert result[card_id] is None

    def test_jsonld_snapshot_source_returned(self, seeded_repo):
        """jsonld_snapshot source is returned when it is the latest."""
        repo, card_id, entry_id = seeded_repo

        with Session(repo.engine) as session:
            obs = PriceObservationRow(
                source="jsonld_snapshot",
                external_id="99999",
                observed_at=date(2026, 8, 22),
                median_price=Decimal("9.00"),
                currency="BRL",
            )
            session.add(obs)
            session.commit()

        result = repo.get_latest_prices_batch([card_id])
        winner = result[card_id]
        assert winner is not None
        assert winner.source == "jsonld_snapshot"

    def test_manual_wins_over_jsonld_same_day(self, seeded_repo):
        """Manual beats jsonld_snapshot on same day."""
        repo, card_id, entry_id = seeded_repo
        same_day = date(2026, 8, 22)

        with Session(repo.engine) as session:
            jsonld_obs = PriceObservationRow(
                source="jsonld_snapshot",
                external_id="99999",
                observed_at=same_day,
                median_price=Decimal("9.00"),
                currency="BRL",
            )
            session.add(jsonld_obs)

            manual_obs = PriceObservationRow(
                source="manual",
                external_id=f"manual_{card_id}",
                observed_at=same_day,
                median_price=Decimal("11.00"),
                currency="BRL",
            )
            session.add(manual_obs)
            session.commit()

        result = repo.get_latest_prices_batch([card_id])
        winner = result[card_id]
        assert winner is not None
        assert winner.source == "manual"
        assert winner.median_price == Decimal("11.00")
