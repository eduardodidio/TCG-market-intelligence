"""F60-T02: Tests for Liga scan repo method and price priority update.

Covers:
1. get_cards_for_liga_scan returns entries with card_id (no MYP source needed)
2. get_cards_for_liga_scan with max_age_days skips recently-scanned
3. get_cards_for_liga_scan respects filters (set_codes, rarities, limit)
4. Price priority: liga beats jsonld_snapshot on same date
5. Price priority: manual beats liga on same date
6. Price priority: newer liga beats older manual (date still wins first)
7. Regression: existing MYP price tests still pass (covered in test_repository_price_source.py)
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
from src.domain.models import ScanFilter, ScanType


@pytest.fixture()
def repo(tmp_path):
    db_path = tmp_path / "test.db"
    return Repository(f"sqlite:///{db_path}")


@pytest.fixture()
def seeded_repo(repo):
    """Seed repo with cards and collection entries (NO source_cards required for Liga)."""
    with Session(repo.engine) as session:
        c1 = CardRow(
            game="magic",
            name_en="Lightning Bolt",
            name_pt="Raio",
            set_code="2XM",
            collector_number="1",
        )
        c2 = CardRow(
            game="magic",
            name_en="Counterspell",
            name_pt="Contramágica",
            set_code="MH3",
            collector_number="42",
        )
        c3 = CardRow(
            game="magic",
            name_en="Swords to Plowshares",
            name_pt="Espadas em Relhas de Arado",
            set_code="2XM",
            collector_number="10",
        )
        session.add_all([c1, c2, c3])
        session.flush()

        # Collection entries linked to cards (no source_cards needed for Liga)
        uc1 = UserCollectionRow(
            user_id="user1",
            card_id=c1.id,
            set_code="2XM",
            collector_number="1",
            name_en="Lightning Bolt",
            name_pt="Raio",
            rarity="R",
        )
        uc2 = UserCollectionRow(
            user_id="user1",
            card_id=c2.id,
            set_code="MH3",
            collector_number="42",
            name_en="Counterspell",
            name_pt="Contramágica",
            rarity="U",
        )
        uc3 = UserCollectionRow(
            user_id="user1",
            card_id=c3.id,
            set_code="2XM",
            collector_number="10",
            name_en="Swords to Plowshares",
            name_pt="Espadas em Relhas de Arado",
            rarity="R",
        )
        # An entry without card_id (should be excluded)
        uc4 = UserCollectionRow(
            user_id="user1",
            card_id=None,
            set_code="DMR",
            collector_number="99",
            name_en="Orphan Card",
            rarity="C",
        )
        session.add_all([uc1, uc2, uc3, uc4])
        session.commit()

    return repo


class TestGetCardsForLigaScan:
    """Tests for get_cards_for_liga_scan repository method."""

    def test_returns_entries_with_card_id(self, seeded_repo):
        """Only returns entries that have card_id set (excludes orphans)."""
        sf = ScanFilter(scan_type=ScanType.COLLECTION)
        cards = seeded_repo.get_cards_for_liga_scan(sf)

        assert len(cards) == 3
        for card in cards:
            assert card["card_id"] is not None
            assert "entry_id" in card
            assert "name_en" in card
            assert "name_pt" in card
            assert "set_code" in card
            assert "collector_number" in card

    def test_does_not_require_source_card(self, repo):
        """Liga scan works without any source_cards in the database."""
        with Session(repo.engine) as session:
            card = CardRow(
                game="magic",
                name_en="Dark Ritual",
                set_code="A25",
                collector_number="82",
            )
            session.add(card)
            session.flush()
            entry = UserCollectionRow(
                user_id="u1",
                card_id=card.id,
                set_code="A25",
                collector_number="82",
                name_en="Dark Ritual",
            )
            session.add(entry)
            session.commit()

        # No SourceCardRow created — Liga should still find this card
        sf = ScanFilter(scan_type=ScanType.COLLECTION)
        cards = repo.get_cards_for_liga_scan(sf)
        assert len(cards) == 1
        assert cards[0]["name_en"] == "Dark Ritual"

    def test_excludes_entries_without_card_id(self, seeded_repo):
        """Entries with card_id=None are not returned."""
        sf = ScanFilter(scan_type=ScanType.COLLECTION)
        cards = seeded_repo.get_cards_for_liga_scan(sf)

        names = {c["name_en"] for c in cards}
        assert "Orphan Card" not in names

    def test_filters_by_set_codes(self, seeded_repo):
        """set_codes filter returns only matching sets."""
        sf = ScanFilter(scan_type=ScanType.SET, set_codes=["2XM"])
        cards = seeded_repo.get_cards_for_liga_scan(sf)

        assert len(cards) == 2
        assert all(c["set_code"] == "2XM" for c in cards)

    def test_filters_by_rarities(self, seeded_repo):
        """rarities filter returns only matching rarities."""
        sf = ScanFilter(scan_type=ScanType.COLLECTION, rarities=["U"])
        cards = seeded_repo.get_cards_for_liga_scan(sf)

        assert len(cards) == 1
        assert cards[0]["name_en"] == "Counterspell"

    def test_filters_by_card_ids(self, seeded_repo):
        """card_ids filter returns only matching card_ids."""
        # Get first card's id
        sf = ScanFilter(scan_type=ScanType.COLLECTION)
        all_cards = seeded_repo.get_cards_for_liga_scan(sf)
        target_id = all_cards[0]["card_id"]

        sf = ScanFilter(scan_type=ScanType.COLLECTION, card_ids=[target_id])
        cards = seeded_repo.get_cards_for_liga_scan(sf)
        assert len(cards) == 1
        assert cards[0]["card_id"] == target_id

    def test_respects_limit(self, seeded_repo):
        """limit parameter caps the number of results."""
        sf = ScanFilter(scan_type=ScanType.COLLECTION, limit=2)
        cards = seeded_repo.get_cards_for_liga_scan(sf)

        assert len(cards) == 2

    def test_filters_by_user_id(self, seeded_repo):
        """user_id parameter filters to specific user's entries."""
        # user1 has entries, user2 does not
        sf = ScanFilter(scan_type=ScanType.COLLECTION)
        cards = seeded_repo.get_cards_for_liga_scan(sf, user_id="user1")
        assert len(cards) == 3

        cards = seeded_repo.get_cards_for_liga_scan(sf, user_id="user2")
        assert len(cards) == 0

    def test_returns_name_pt(self, seeded_repo):
        """Results include name_pt for Liga Portuguese search fallback."""
        sf = ScanFilter(scan_type=ScanType.COLLECTION)
        cards = seeded_repo.get_cards_for_liga_scan(sf)

        bolt = next(c for c in cards if c["name_en"] == "Lightning Bolt")
        assert bolt["name_pt"] == "Raio"


class TestGetCardsForLigaScanMaxAge:
    """Tests for max_age_days freshness filter."""

    def test_skips_recently_scanned(self, seeded_repo):
        """Cards with a recent liga observation are excluded when max_age_days is set."""
        # Add a recent liga observation for Lightning Bolt
        with Session(seeded_repo.engine) as session:
            obs = PriceObservationRow(
                source="liga",
                external_id="liga_1",
                observed_at=date.today(),
                median_price=Decimal("5.00"),
                currency="BRL",
            )
            session.add(obs)
            session.commit()

        sf = ScanFilter(scan_type=ScanType.COLLECTION)
        cards = seeded_repo.get_cards_for_liga_scan(sf, max_age_days=7)

        names = {c["name_en"] for c in cards}
        assert "Lightning Bolt" not in names
        assert "Counterspell" in names
        assert "Swords to Plowshares" in names
        assert len(cards) == 2

    def test_includes_old_scanned_cards(self, seeded_repo):
        """Cards with liga observation older than max_age_days are included."""
        with Session(seeded_repo.engine) as session:
            obs = PriceObservationRow(
                source="liga",
                external_id="liga_1",
                observed_at=date.today() - timedelta(days=10),
                median_price=Decimal("5.00"),
                currency="BRL",
            )
            session.add(obs)
            session.commit()

        sf = ScanFilter(scan_type=ScanType.COLLECTION)
        cards = seeded_repo.get_cards_for_liga_scan(sf, max_age_days=7)

        names = {c["name_en"] for c in cards}
        assert "Lightning Bolt" in names
        assert len(cards) == 3

    def test_without_max_age_includes_all(self, seeded_repo):
        """Without max_age_days, all cards with card_id are returned."""
        with Session(seeded_repo.engine) as session:
            obs = PriceObservationRow(
                source="liga",
                external_id="liga_1",
                observed_at=date.today(),
                median_price=Decimal("5.00"),
                currency="BRL",
            )
            session.add(obs)
            session.commit()

        sf = ScanFilter(scan_type=ScanType.COLLECTION)
        cards = seeded_repo.get_cards_for_liga_scan(sf)

        assert len(cards) == 3  # No filtering applied

    def test_myp_observations_do_not_affect_max_age(self, seeded_repo):
        """MYP observations should NOT cause cards to be skipped by max_age_days."""
        with Session(seeded_repo.engine) as session:
            obs = PriceObservationRow(
                source="myp",
                external_id="99999",
                observed_at=date.today(),
                median_price=Decimal("5.00"),
                currency="BRL",
            )
            session.add(obs)
            session.commit()

        sf = ScanFilter(scan_type=ScanType.COLLECTION)
        cards = seeded_repo.get_cards_for_liga_scan(sf, max_age_days=7)

        # MYP observation should not exclude any card
        assert len(cards) == 3


class TestPricePriorityWithLiga:
    """Tests for updated price priority in get_latest_prices_batch."""

    @pytest.fixture()
    def price_repo(self, repo):
        """Seed repo with a card + source_card + collection entry for price tests."""
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

        return repo, card.id

    def test_liga_beats_jsonld_same_date(self, price_repo):
        """Liga observation wins over jsonld_snapshot on the same date."""
        repo, card_id = price_repo
        same_day = date(2026, 8, 25)

        with Session(repo.engine) as session:
            jsonld_obs = PriceObservationRow(
                source="jsonld_snapshot",
                external_id="99999",
                observed_at=same_day,
                median_price=Decimal("8.00"),
                currency="BRL",
            )
            liga_obs = PriceObservationRow(
                source="liga",
                external_id="liga_1",
                observed_at=same_day,
                median_price=Decimal("10.00"),
                currency="BRL",
            )
            session.add_all([jsonld_obs, liga_obs])
            session.commit()

        result = repo.get_latest_prices_batch([card_id])
        winner = result[card_id]
        assert winner is not None
        assert winner.source == "liga"
        assert winner.median_price == Decimal("10.00")

    def test_manual_beats_liga_same_date(self, price_repo):
        """Manual observation wins over liga on the same date."""
        repo, card_id = price_repo
        same_day = date(2026, 8, 25)

        with Session(repo.engine) as session:
            liga_obs = PriceObservationRow(
                source="liga",
                external_id="liga_1",
                observed_at=same_day,
                median_price=Decimal("10.00"),
                currency="BRL",
            )
            manual_obs = PriceObservationRow(
                source="manual",
                external_id=f"manual_{card_id}",
                observed_at=same_day,
                median_price=Decimal("15.00"),
                currency="BRL",
            )
            session.add_all([liga_obs, manual_obs])
            session.commit()

        result = repo.get_latest_prices_batch([card_id])
        winner = result[card_id]
        assert winner is not None
        assert winner.source == "manual"
        assert winner.median_price == Decimal("15.00")

    def test_newer_liga_beats_older_manual(self, price_repo):
        """Date wins first: newer liga beats older manual."""
        repo, card_id = price_repo

        with Session(repo.engine) as session:
            manual_obs = PriceObservationRow(
                source="manual",
                external_id=f"manual_{card_id}",
                observed_at=date(2026, 8, 20),
                median_price=Decimal("15.00"),
                currency="BRL",
            )
            liga_obs = PriceObservationRow(
                source="liga",
                external_id="liga_1",
                observed_at=date(2026, 8, 25),
                median_price=Decimal("10.00"),
                currency="BRL",
            )
            session.add_all([manual_obs, liga_obs])
            session.commit()

        result = repo.get_latest_prices_batch([card_id])
        winner = result[card_id]
        assert winner is not None
        assert winner.source == "liga"
        assert winner.median_price == Decimal("10.00")

    def test_liga_beats_myp_same_date(self, price_repo):
        """Liga observation wins over MYP on the same date."""
        repo, card_id = price_repo
        same_day = date(2026, 8, 25)

        with Session(repo.engine) as session:
            myp_obs = PriceObservationRow(
                source="myp",
                external_id="99999",
                observed_at=same_day,
                median_price=Decimal("7.00"),
                currency="BRL",
            )
            liga_obs = PriceObservationRow(
                source="liga",
                external_id="liga_1",
                observed_at=same_day,
                median_price=Decimal("10.00"),
                currency="BRL",
            )
            session.add_all([myp_obs, liga_obs])
            session.commit()

        result = repo.get_latest_prices_batch([card_id])
        winner = result[card_id]
        assert winner is not None
        assert winner.source == "liga"
        assert winner.median_price == Decimal("10.00")

    def test_full_priority_chain_same_date(self, price_repo):
        """All four sources on same date: manual > liga > jsonld > myp."""
        repo, card_id = price_repo
        same_day = date(2026, 8, 25)

        with Session(repo.engine) as session:
            session.add_all(
                [
                    PriceObservationRow(
                        source="myp",
                        external_id="99999",
                        observed_at=same_day,
                        median_price=Decimal("5.00"),
                        currency="BRL",
                    ),
                    PriceObservationRow(
                        source="jsonld_snapshot",
                        external_id="99999",
                        observed_at=same_day,
                        median_price=Decimal("6.00"),
                        currency="BRL",
                    ),
                    PriceObservationRow(
                        source="liga",
                        external_id="liga_1",
                        observed_at=same_day,
                        median_price=Decimal("7.00"),
                        currency="BRL",
                    ),
                    PriceObservationRow(
                        source="manual",
                        external_id=f"manual_{card_id}",
                        observed_at=same_day,
                        median_price=Decimal("8.00"),
                        currency="BRL",
                    ),
                ]
            )
            session.commit()

        result = repo.get_latest_prices_batch([card_id])
        winner = result[card_id]
        assert winner is not None
        assert winner.source == "manual"
        assert winner.median_price == Decimal("8.00")

    def test_liga_only_observation(self, price_repo):
        """Liga observation returned when it is the only observation."""
        repo, card_id = price_repo

        with Session(repo.engine) as session:
            liga_obs = PriceObservationRow(
                source="liga",
                external_id="liga_1",
                observed_at=date(2026, 8, 25),
                median_price=Decimal("10.00"),
                currency="BRL",
            )
            session.add(liga_obs)
            session.commit()

        result = repo.get_latest_prices_batch([card_id])
        winner = result[card_id]
        assert winner is not None
        assert winner.source == "liga"
        assert winner.median_price == Decimal("10.00")
