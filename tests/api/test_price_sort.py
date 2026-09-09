"""Tests for price-based sorting on collection and cards endpoints (F115-T01)."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy.orm import Session

from src.database.models import (
    CardRow,
    PriceObservationRow,
    UserCollectionRow,
)
from src.database.repository import Repository


@pytest.fixture()
def repo(tmp_path):
    db_path = tmp_path / "test_price_sort.db"
    return Repository(db_url=f"sqlite:///{db_path}")


USER = "test-user"


def _seed_collection_with_prices(repo: Repository):
    """Seed 3 collection entries with cards and price observations.

    Returns (cheap_id, mid_id, expensive_id, no_price_id) collection row IDs.
    """
    with Session(repo.engine) as session:
        # Create cards
        cards = []
        for i, (name, price) in enumerate(
            [
                ("Cheap Card", Decimal("1.00")),
                ("Mid Card", Decimal("10.00")),
                ("Expensive Card", Decimal("100.00")),
                ("No Price Card", None),
            ],
            start=1,
        ):
            card = CardRow(
                game="magic",
                name_en=name,
                set_code="TST",
                collector_number=str(i),
            )
            session.add(card)
            session.flush()
            cards.append(card)

            # Add collection entry
            entry = UserCollectionRow(
                user_id=USER,
                card_id=card.id,
                name_en=name,
                set_code="TST",
                collector_number=str(i),
                quantity=1,
            )
            session.add(entry)

            # Add price observation (except for last card)
            if price is not None:
                obs = PriceObservationRow(
                    source="liga",
                    external_id=f"liga_{card.id}",
                    observed_at=date(2026, 9, 1),
                    median_price=price,
                    currency="BRL",
                )
                session.add(obs)

        session.commit()
        return [c.id for c in cards]


class TestCollectionPriceSort:
    def test_sort_by_price_desc(self, repo):
        _seed_collection_with_prices(repo)
        rows = repo.list_collection(USER, sort_by="price", sort_dir="desc")
        names = [r.name_en for r in rows]
        assert names == [
            "Expensive Card",
            "Mid Card",
            "Cheap Card",
            "No Price Card",
        ]

    def test_sort_by_price_asc(self, repo):
        _seed_collection_with_prices(repo)
        rows = repo.list_collection(USER, sort_by="price", sort_dir="asc")
        names = [r.name_en for r in rows]
        assert names == [
            "Cheap Card",
            "Mid Card",
            "Expensive Card",
            "No Price Card",
        ]

    def test_nulls_at_end_for_desc(self, repo):
        _seed_collection_with_prices(repo)
        rows = repo.list_collection(USER, sort_by="price", sort_dir="desc")
        # Last entry should be the one with no price
        assert rows[-1].name_en == "No Price Card"

    def test_nulls_at_end_for_asc(self, repo):
        _seed_collection_with_prices(repo)
        rows = repo.list_collection(USER, sort_by="price", sort_dir="asc")
        # Last entry should be the one with no price
        assert rows[-1].name_en == "No Price Card"

    def test_existing_sort_options_still_work(self, repo):
        _seed_collection_with_prices(repo)
        for sort in ("name", "set", "number", "added"):
            rows = repo.list_collection(USER, sort_by=sort)
            assert len(rows) == 4

    def test_latest_price_used(self, repo):
        """When multiple price observations exist, the latest date wins."""
        with Session(repo.engine) as session:
            card = CardRow(
                game="magic",
                name_en="Test Card",
                set_code="TST",
                collector_number="1",
            )
            session.add(card)
            session.flush()
            entry = UserCollectionRow(
                user_id=USER,
                card_id=card.id,
                name_en="Test Card",
                set_code="TST",
                collector_number="1",
                quantity=1,
            )
            session.add(entry)
            # Old price: high
            session.add(
                PriceObservationRow(
                    source="liga",
                    external_id=f"liga_{card.id}",
                    observed_at=date(2026, 1, 1),
                    median_price=Decimal("999.00"),
                    currency="BRL",
                )
            )
            # New price: low
            session.add(
                PriceObservationRow(
                    source="liga",
                    external_id=f"liga_{card.id}",
                    observed_at=date(2026, 9, 1),
                    median_price=Decimal("1.00"),
                    currency="BRL",
                )
            )

            card2 = CardRow(
                game="magic",
                name_en="Other Card",
                set_code="TST",
                collector_number="2",
            )
            session.add(card2)
            session.flush()
            entry2 = UserCollectionRow(
                user_id=USER,
                card_id=card2.id,
                name_en="Other Card",
                set_code="TST",
                collector_number="2",
                quantity=1,
            )
            session.add(entry2)
            session.add(
                PriceObservationRow(
                    source="liga",
                    external_id=f"liga_{card2.id}",
                    observed_at=date(2026, 9, 1),
                    median_price=Decimal("50.00"),
                    currency="BRL",
                )
            )
            session.commit()

        rows = repo.list_collection(USER, sort_by="price", sort_dir="desc")
        # Other Card (50) should come before Test Card (1, latest price)
        assert rows[0].name_en == "Other Card"
        assert rows[1].name_en == "Test Card"


class TestCardsPriceSort:
    def test_sort_by_price_desc(self, repo):
        with Session(repo.engine) as session:
            for name, num, price in [
                ("Alpha", "1", Decimal("5.00")),
                ("Beta", "2", Decimal("50.00")),
                ("Gamma", "3", None),
            ]:
                card = CardRow(
                    game="magic",
                    name_en=name,
                    set_code="TST",
                    collector_number=num,
                )
                session.add(card)
                session.flush()
                if price is not None:
                    session.add(
                        PriceObservationRow(
                            source="liga",
                            external_id=f"liga_{card.id}",
                            observed_at=date(2026, 9, 1),
                            median_price=price,
                            currency="BRL",
                        )
                    )
            session.commit()

        rows = repo.list_cards(sort_by="price", sort_dir="desc")
        names = [r.name_en for r in rows]
        assert names == ["Beta", "Alpha", "Gamma"]

    def test_sort_by_price_asc(self, repo):
        with Session(repo.engine) as session:
            for name, num, price in [
                ("Alpha", "1", Decimal("5.00")),
                ("Beta", "2", Decimal("50.00")),
                ("Gamma", "3", None),
            ]:
                card = CardRow(
                    game="magic",
                    name_en=name,
                    set_code="TST",
                    collector_number=num,
                )
                session.add(card)
                session.flush()
                if price is not None:
                    session.add(
                        PriceObservationRow(
                            source="liga",
                            external_id=f"liga_{card.id}",
                            observed_at=date(2026, 9, 1),
                            median_price=price,
                            currency="BRL",
                        )
                    )
            session.commit()

        rows = repo.list_cards(sort_by="price", sort_dir="asc")
        names = [r.name_en for r in rows]
        assert names == ["Alpha", "Beta", "Gamma"]

    def test_sort_by_name_default(self, repo):
        with Session(repo.engine) as session:
            for name, num in [("Zebra", "1"), ("Alpha", "2")]:
                session.add(
                    CardRow(
                        game="magic",
                        name_en=name,
                        set_code="TST",
                        collector_number=num,
                    )
                )
            session.commit()

        rows = repo.list_cards(sort_by="name", sort_dir="asc")
        names = [r.name_en for r in rows]
        assert names == ["Alpha", "Zebra"]
