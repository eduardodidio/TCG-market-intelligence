"""F87-T03: Tests for foil-aware price lookup in get_latest_prices_batch.

Covers:
1. Foil entry gets foil price from liga_{card_id}_foil external_id
2. Non-foil entry gets normal price from liga_{card_id} external_id
3. Manual price still wins over foil Liga price
4. Entry with no foil observation falls back to normal Liga price
5. Mixed foil/non-foil batch returns correct prices for each
6. foil_card_ids=None preserves existing behavior (backward compat)
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
    """Seed repo with a card, source_card, and collection entry."""
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

    return repo, card.id


class TestFoilPriceLookup:
    """Tests for foil_card_ids parameter in get_latest_prices_batch."""

    def test_foil_entry_gets_foil_price(self, seeded_repo):
        """Foil entry returns foil-specific Liga observation."""
        repo, card_id = seeded_repo
        same_day = date(2026, 8, 28)

        with Session(repo.engine) as session:
            normal_obs = PriceObservationRow(
                source="liga",
                external_id=f"liga_{card_id}",
                observed_at=same_day,
                median_price=Decimal("5.00"),
                currency="BRL",
            )
            foil_obs = PriceObservationRow(
                source="liga",
                external_id=f"liga_{card_id}_foil",
                observed_at=same_day,
                median_price=Decimal("15.00"),
                currency="BRL",
            )
            session.add_all([normal_obs, foil_obs])
            session.commit()

        result = repo.get_latest_prices_batch([card_id], foil_card_ids={card_id})
        winner = result[card_id]
        assert winner is not None
        assert winner.external_id == f"liga_{card_id}_foil"
        assert winner.median_price == Decimal("15.00")

    def test_non_foil_entry_gets_normal_price(self, seeded_repo):
        """Non-foil entry returns normal Liga observation (no foil_card_ids)."""
        repo, card_id = seeded_repo
        same_day = date(2026, 8, 28)

        with Session(repo.engine) as session:
            normal_obs = PriceObservationRow(
                source="liga",
                external_id=f"liga_{card_id}",
                observed_at=same_day,
                median_price=Decimal("5.00"),
                currency="BRL",
            )
            foil_obs = PriceObservationRow(
                source="liga",
                external_id=f"liga_{card_id}_foil",
                observed_at=same_day,
                median_price=Decimal("15.00"),
                currency="BRL",
            )
            session.add_all([normal_obs, foil_obs])
            session.commit()

        # No foil_card_ids — should get normal price
        result = repo.get_latest_prices_batch([card_id])
        winner = result[card_id]
        assert winner is not None
        assert winner.external_id == f"liga_{card_id}"
        assert winner.median_price == Decimal("5.00")

    def test_manual_beats_foil_liga_same_date(self, seeded_repo):
        """Manual price wins over foil Liga price on the same date."""
        repo, card_id = seeded_repo
        same_day = date(2026, 8, 28)

        with Session(repo.engine) as session:
            foil_obs = PriceObservationRow(
                source="liga",
                external_id=f"liga_{card_id}_foil",
                observed_at=same_day,
                median_price=Decimal("15.00"),
                currency="BRL",
            )
            manual_obs = PriceObservationRow(
                source="manual",
                external_id=f"manual_{card_id}",
                observed_at=same_day,
                median_price=Decimal("20.00"),
                currency="BRL",
            )
            session.add_all([foil_obs, manual_obs])
            session.commit()

        result = repo.get_latest_prices_batch([card_id], foil_card_ids={card_id})
        winner = result[card_id]
        assert winner is not None
        assert winner.source == "manual"
        assert winner.median_price == Decimal("20.00")

    def test_foil_entry_falls_back_to_normal_when_no_foil_obs(self, seeded_repo):
        """Foil entry with no foil observation falls back to normal Liga price."""
        repo, card_id = seeded_repo
        same_day = date(2026, 8, 28)

        with Session(repo.engine) as session:
            normal_obs = PriceObservationRow(
                source="liga",
                external_id=f"liga_{card_id}",
                observed_at=same_day,
                median_price=Decimal("5.00"),
                currency="BRL",
            )
            session.add(normal_obs)
            session.commit()

        # Card is foil but no foil observation exists — should fall back to normal
        result = repo.get_latest_prices_batch([card_id], foil_card_ids={card_id})
        winner = result[card_id]
        assert winner is not None
        assert winner.external_id == f"liga_{card_id}"
        assert winner.median_price == Decimal("5.00")

    def test_foil_entry_returns_none_when_no_observations(self, seeded_repo):
        """Foil entry with no observations at all returns None."""
        repo, card_id = seeded_repo

        result = repo.get_latest_prices_batch([card_id], foil_card_ids={card_id})
        winner = result[card_id]
        assert winner is None

    def test_backward_compat_no_foil_card_ids(self, seeded_repo):
        """foil_card_ids=None preserves existing behavior."""
        repo, card_id = seeded_repo
        same_day = date(2026, 8, 28)

        with Session(repo.engine) as session:
            normal_obs = PriceObservationRow(
                source="liga",
                external_id=f"liga_{card_id}",
                observed_at=same_day,
                median_price=Decimal("5.00"),
                currency="BRL",
            )
            foil_obs = PriceObservationRow(
                source="liga",
                external_id=f"liga_{card_id}_foil",
                observed_at=same_day,
                median_price=Decimal("15.00"),
                currency="BRL",
            )
            session.add_all([normal_obs, foil_obs])
            session.commit()

        # Without foil_card_ids, foil observation is not considered
        result = repo.get_latest_prices_batch([card_id], foil_card_ids=None)
        winner = result[card_id]
        assert winner is not None
        assert winner.external_id == f"liga_{card_id}"
        assert winner.median_price == Decimal("5.00")

    def test_empty_foil_card_ids_same_as_none(self, seeded_repo):
        """Empty set for foil_card_ids behaves same as None."""
        repo, card_id = seeded_repo
        same_day = date(2026, 8, 28)

        with Session(repo.engine) as session:
            normal_obs = PriceObservationRow(
                source="liga",
                external_id=f"liga_{card_id}",
                observed_at=same_day,
                median_price=Decimal("5.00"),
                currency="BRL",
            )
            session.add(normal_obs)
            session.commit()

        result = repo.get_latest_prices_batch([card_id], foil_card_ids=set())
        winner = result[card_id]
        assert winner is not None
        assert winner.external_id == f"liga_{card_id}"
        assert winner.median_price == Decimal("5.00")

    def test_foil_replaces_normal_liga_in_candidates(self, seeded_repo):
        """When foil obs exists, normal Liga obs is removed from candidates."""
        repo, card_id = seeded_repo
        same_day = date(2026, 8, 28)

        with Session(repo.engine) as session:
            # Normal liga has higher price but foil should replace it
            normal_obs = PriceObservationRow(
                source="liga",
                external_id=f"liga_{card_id}",
                observed_at=same_day,
                median_price=Decimal("50.00"),
                currency="BRL",
            )
            foil_obs = PriceObservationRow(
                source="liga",
                external_id=f"liga_{card_id}_foil",
                observed_at=same_day,
                median_price=Decimal("12.00"),
                currency="BRL",
            )
            session.add_all([normal_obs, foil_obs])
            session.commit()

        result = repo.get_latest_prices_batch([card_id], foil_card_ids={card_id})
        winner = result[card_id]
        assert winner is not None
        # Foil obs replaces normal, even though normal had higher price
        assert winner.external_id == f"liga_{card_id}_foil"
        assert winner.median_price == Decimal("12.00")


class TestFoilPriceBatchMixed:
    """Tests for mixed foil/non-foil batches."""

    @pytest.fixture()
    def two_card_repo(self, repo):
        """Seed repo with two cards."""
        with Session(repo.engine) as session:
            card1 = CardRow(
                game="magic",
                name_en="Lightning Bolt",
                set_code="DMR",
                collector_number="123",
            )
            card2 = CardRow(
                game="magic",
                name_en="Counterspell",
                set_code="MH3",
                collector_number="42",
            )
            session.add_all([card1, card2])
            session.flush()

            session.add_all(
                [
                    UserCollectionRow(
                        user_id="u1",
                        card_id=card1.id,
                        set_code="DMR",
                        collector_number="123",
                        name_en="Lightning Bolt",
                        extras="Foil",
                    ),
                    UserCollectionRow(
                        user_id="u1",
                        card_id=card2.id,
                        set_code="MH3",
                        collector_number="42",
                        name_en="Counterspell",
                    ),
                ]
            )
            session.commit()
            session.refresh(card1)
            session.refresh(card2)

        return repo, card1.id, card2.id

    def test_mixed_batch_returns_correct_prices(self, two_card_repo):
        """Foil card gets foil price, non-foil card gets normal price in same batch."""
        repo, foil_card_id, normal_card_id = two_card_repo
        same_day = date(2026, 8, 28)

        with Session(repo.engine) as session:
            session.add_all(
                [
                    # Card 1: normal + foil Liga prices
                    PriceObservationRow(
                        source="liga",
                        external_id=f"liga_{foil_card_id}",
                        observed_at=same_day,
                        median_price=Decimal("5.00"),
                        currency="BRL",
                    ),
                    PriceObservationRow(
                        source="liga",
                        external_id=f"liga_{foil_card_id}_foil",
                        observed_at=same_day,
                        median_price=Decimal("15.00"),
                        currency="BRL",
                    ),
                    # Card 2: only normal Liga price
                    PriceObservationRow(
                        source="liga",
                        external_id=f"liga_{normal_card_id}",
                        observed_at=same_day,
                        median_price=Decimal("3.00"),
                        currency="BRL",
                    ),
                ]
            )
            session.commit()

        result = repo.get_latest_prices_batch(
            [foil_card_id, normal_card_id],
            foil_card_ids={foil_card_id},
        )

        # Foil card gets foil price
        foil_winner = result[foil_card_id]
        assert foil_winner is not None
        assert foil_winner.external_id == f"liga_{foil_card_id}_foil"
        assert foil_winner.median_price == Decimal("15.00")

        # Non-foil card gets normal price
        normal_winner = result[normal_card_id]
        assert normal_winner is not None
        assert normal_winner.external_id == f"liga_{normal_card_id}"
        assert normal_winner.median_price == Decimal("3.00")
