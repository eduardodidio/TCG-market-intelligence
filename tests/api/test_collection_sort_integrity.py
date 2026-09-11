"""Tests for collection sort integrity — verifies price sort order, NULL handling,
tiebreakers, and name sort across the backend stack.

This file tests actual DB sort behavior (not mocked), ensuring that:
- Price sort DESC: cards with prices ordered high-to-low, NULLs at end
- Price sort ASC: cards with prices ordered low-to-high, NULLs at end
- Sort stability: cards with same price ordered by id ASC
- Name sort ASC/DESC
- Foil/manual price entries do not break sort order
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from src.database.models import Base, CardRow, PriceObservationRow, UserCollectionRow
from src.database.repository import Repository


@pytest.fixture()
def repo(tmp_path):
    """Create an in-memory SQLite repo with schema."""
    db_path = tmp_path / "test.db"
    engine = create_engine(f"sqlite:///{db_path}")
    Base.metadata.create_all(engine)
    r = Repository.__new__(Repository)
    r.engine = engine
    return r


def _seed_collection_with_prices(repo: Repository, user_id: str = "u1"):
    """Seed 5 cards: 3 with prices (10, 50, 50), 2 without prices.

    Returns the list of created UserCollectionRow ids in insertion order.
    """
    with Session(repo.engine) as session:
        # Create card rows first (needed for card_id foreign key pattern)
        cards = []
        for i in range(1, 6):
            card = CardRow(
                id=i,
                game="magic",
                name_en=f"Card {i}",
                set_code="TST",
                collector_number=str(i),
            )
            cards.append(card)
            session.add(card)
        session.flush()

        # Create collection entries
        entries = []
        for i in range(1, 6):
            entry = UserCollectionRow(
                user_id=user_id,
                card_id=i,
                set_code="TST",
                collector_number=str(i),
                name_en=f"Card {i}",
                name_pt=f"Carta {i}",
                quantity=1,
                quality="NM",
                language="EN",
                created_at=datetime(2026, 1, i),
            )
            entries.append(entry)
            session.add(entry)
        session.flush()
        entry_ids = [e.id for e in entries]

        # Add price observations for cards 1, 2, 3
        # Card 1: price 50.00
        # Card 2: price 10.00
        # Card 3: price 50.00 (same as card 1 — tests tiebreaker)
        # Cards 4, 5: no price (NULL)
        prices = [
            (1, Decimal("50.00")),
            (2, Decimal("10.00")),
            (3, Decimal("50.00")),
        ]
        for card_id, price in prices:
            obs = PriceObservationRow(
                source="liga",
                external_id=f"liga_{card_id}",
                observed_at=date(2026, 1, 1),
                median_price=price,
            )
            session.add(obs)

        session.commit()
        return entry_ids


class TestPriceSortDesc:
    def test_price_desc_order(self, repo):
        """Cards should be ordered high-to-low by median_price, NULLs last."""
        _seed_collection_with_prices(repo)
        rows = repo.list_collection("u1", sort_by="price", sort_dir="desc", limit=50)

        names = [r.name_en for r in rows]
        # Card 1 (50), Card 3 (50) first (tiebreak by id asc),
        # then Card 2 (10), then Card 4 + Card 5 (NULL)
        assert names == ["Card 1", "Card 3", "Card 2", "Card 4", "Card 5"]

    def test_price_desc_nulls_at_end(self, repo):
        """Cards without prices should always appear at the end in DESC sort."""
        _seed_collection_with_prices(repo)
        rows = repo.list_collection("u1", sort_by="price", sort_dir="desc", limit=50)

        # Last two cards should have no price (card_id 4 and 5)
        assert rows[-1].card_id == 5
        assert rows[-2].card_id == 4


class TestPriceSortAsc:
    def test_price_asc_order(self, repo):
        """Cards should be ordered low-to-high by median_price, NULLs last."""
        _seed_collection_with_prices(repo)
        rows = repo.list_collection("u1", sort_by="price", sort_dir="asc", limit=50)

        names = [r.name_en for r in rows]
        # Card 2 (10) first, then Card 1 (50) and Card 3 (50) by id asc, then NULLs
        assert names == ["Card 2", "Card 1", "Card 3", "Card 4", "Card 5"]

    def test_price_asc_nulls_at_end(self, repo):
        """NULLs should be at end even in ASC sort (not at beginning)."""
        _seed_collection_with_prices(repo)
        rows = repo.list_collection("u1", sort_by="price", sort_dir="asc", limit=50)

        # First card should have a price, not NULL
        assert rows[0].card_id == 2  # cheapest card
        # Last two should be NULL-priced
        assert rows[-1].card_id == 5
        assert rows[-2].card_id == 4


class TestSortStability:
    def test_same_price_ordered_by_id_asc(self, repo):
        """Cards with identical prices should be ordered by id ASC (stable)."""
        _seed_collection_with_prices(repo)
        rows = repo.list_collection("u1", sort_by="price", sort_dir="desc", limit=50)

        # Card 1 and Card 3 both have price 50.00
        # Card 1 has lower id, so it should come first
        priced_50 = [r for r in rows if r.card_id in (1, 3)]
        assert priced_50[0].card_id == 1
        assert priced_50[1].card_id == 3

    def test_null_priced_ordered_by_id_asc(self, repo):
        """Cards with no price (NULL) should be ordered by id ASC among themselves."""
        _seed_collection_with_prices(repo)
        rows = repo.list_collection("u1", sort_by="price", sort_dir="desc", limit=50)

        null_priced = [r for r in rows if r.card_id in (4, 5)]
        assert null_priced[0].card_id == 4
        assert null_priced[1].card_id == 5


class TestNameSort:
    def test_name_asc(self, repo):
        """Name sort ASC should order alphabetically."""
        _seed_collection_with_prices(repo)
        rows = repo.list_collection("u1", sort_by="name", sort_dir="asc", limit=50)

        names = [r.name_en for r in rows]
        assert names == sorted(names)

    def test_name_desc(self, repo):
        """Name sort DESC should order reverse alphabetically."""
        _seed_collection_with_prices(repo)
        rows = repo.list_collection("u1", sort_by="name", sort_dir="desc", limit=50)

        names = [r.name_en for r in rows]
        assert names == sorted(names, reverse=True)


class TestFoilPriceSort:
    def test_foil_entry_uses_foil_price_in_sort(self, repo):
        """Foil entries with liga_{id}_foil external_id should sort by foil price."""
        with Session(repo.engine) as session:
            card = CardRow(
                id=1, game="magic", name_en="Foil Card", set_code="TST", collector_number="1"
            )
            session.add(card)
            session.flush()

            # Non-foil entry
            entry1 = UserCollectionRow(
                user_id="u1",
                card_id=1,
                set_code="TST",
                collector_number="1",
                name_en="Foil Card",
                quantity=1,
                quality="NM",
                language="EN",
                created_at=datetime(2026, 1, 1),
            )
            session.add(entry1)

            # Card 2 with lower price
            card2 = CardRow(
                id=2, game="magic", name_en="Cheap Card", set_code="TST", collector_number="2"
            )
            session.add(card2)
            session.flush()

            entry2 = UserCollectionRow(
                user_id="u1",
                card_id=2,
                set_code="TST",
                collector_number="2",
                name_en="Cheap Card",
                quantity=1,
                quality="NM",
                language="EN",
                created_at=datetime(2026, 1, 2),
            )
            session.add(entry2)
            session.flush()

            # Price for card 1: 100
            session.add(
                PriceObservationRow(
                    source="liga",
                    external_id="liga_1",
                    observed_at=date(2026, 1, 1),
                    median_price=Decimal("100"),
                )
            )
            # Price for card 2: 5
            session.add(
                PriceObservationRow(
                    source="liga",
                    external_id="liga_2",
                    observed_at=date(2026, 1, 1),
                    median_price=Decimal("5"),
                )
            )
            session.commit()

        rows = repo.list_collection("u1", sort_by="price", sort_dir="desc", limit=50)
        assert rows[0].name_en == "Foil Card"  # 100 > 5
        assert rows[1].name_en == "Cheap Card"


class TestManualPriceSort:
    def test_manual_price_entries_do_not_break_sort(self, repo):
        """Manual prices use external_id='manual_{id}' which is NOT matched by
        the sort subquery (source='liga' only). Manual-priced cards without
        a liga price will sort as NULL-priced (at end)."""
        with Session(repo.engine) as session:
            card = CardRow(
                id=1, game="magic", name_en="Manual Card", set_code="TST", collector_number="1"
            )
            session.add(card)
            card2 = CardRow(
                id=2, game="magic", name_en="Liga Card", set_code="TST", collector_number="2"
            )
            session.add(card2)
            session.flush()

            session.add(
                UserCollectionRow(
                    user_id="u1",
                    card_id=1,
                    set_code="TST",
                    collector_number="1",
                    name_en="Manual Card",
                    quantity=1,
                    quality="NM",
                    language="EN",
                    created_at=datetime(2026, 1, 1),
                )
            )
            session.add(
                UserCollectionRow(
                    user_id="u1",
                    card_id=2,
                    set_code="TST",
                    collector_number="2",
                    name_en="Liga Card",
                    quantity=1,
                    quality="NM",
                    language="EN",
                    created_at=datetime(2026, 1, 2),
                )
            )
            session.flush()

            # Manual price for card 1 (source != 'liga', won't be picked up by sort subquery)
            session.add(
                PriceObservationRow(
                    source="manual",
                    external_id="manual_1",
                    observed_at=date(2026, 1, 1),
                    median_price=Decimal("500"),
                )
            )
            # Liga price for card 2
            session.add(
                PriceObservationRow(
                    source="liga",
                    external_id="liga_2",
                    observed_at=date(2026, 1, 1),
                    median_price=Decimal("10"),
                )
            )
            session.commit()

        rows = repo.list_collection("u1", sort_by="price", sort_dir="desc", limit=50)
        # Liga Card has liga price (10), Manual Card has no liga price -> NULL -> at end
        assert rows[0].name_en == "Liga Card"
        assert rows[1].name_en == "Manual Card"


class TestMixedSourcePriceSort:
    def test_liga_and_myp_prices_sort_by_liga_only(self, repo):
        """The sort subquery only uses source='liga'. MYP prices do not affect sort order.
        Cards with only MYP prices sort as NULL-priced."""
        with Session(repo.engine) as session:
            for i in range(1, 4):
                session.add(
                    CardRow(
                        id=i,
                        game="magic",
                        name_en=f"Card {i}",
                        set_code="TST",
                        collector_number=str(i),
                    )
                )
            session.flush()

            for i in range(1, 4):
                session.add(
                    UserCollectionRow(
                        user_id="u1",
                        card_id=i,
                        set_code="TST",
                        collector_number=str(i),
                        name_en=f"Card {i}",
                        quantity=1,
                        quality="NM",
                        language="EN",
                        created_at=datetime(2026, 1, i),
                    )
                )
            session.flush()

            # Card 1: liga price 20
            session.add(
                PriceObservationRow(
                    source="liga",
                    external_id="liga_1",
                    observed_at=date(2026, 1, 1),
                    median_price=Decimal("20"),
                )
            )
            # Card 2: MYP price 100 (not used in sort)
            session.add(
                PriceObservationRow(
                    source="myp",
                    external_id="myp_2",
                    observed_at=date(2026, 1, 1),
                    median_price=Decimal("100"),
                )
            )
            # Card 3: liga price 30
            session.add(
                PriceObservationRow(
                    source="liga",
                    external_id="liga_3",
                    observed_at=date(2026, 1, 1),
                    median_price=Decimal("30"),
                )
            )
            session.commit()

        rows = repo.list_collection("u1", sort_by="price", sort_dir="desc", limit=50)
        # Card 3 (30) > Card 1 (20) > Card 2 (NULL in liga -> at end)
        assert rows[0].name_en == "Card 3"
        assert rows[1].name_en == "Card 1"
        assert rows[2].name_en == "Card 2"
