from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy.orm import Session

from src.database.models import (
    CardRow,
    PriceObservationRow,
    SourceCardRow,
)
from src.database.repository import Repository


@pytest.fixture()
def repo(tmp_path):
    """Create a Repository backed by a temp SQLite DB."""
    db_path = tmp_path / "test.db"
    db_url = f"sqlite:///{db_path}"
    r = Repository(db_url=db_url)
    return r


@pytest.fixture()
def seeded_repo(repo):
    """Seed repo with cards, source cards, and price obs."""
    engine = repo.engine
    with Session(engine) as session:
        # Cards
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
            name_pt="Contrafeitico",
            set_code="2XM",
            collector_number="2",
        )
        c3 = CardRow(
            game="pokemon",
            name_en="Pikachu",
            name_pt="Pikachu",
            set_code="SV1",
            collector_number="25",
        )
        session.add_all([c1, c2, c3])
        session.flush()

        # Source cards
        sc1 = SourceCardRow(
            source="myp",
            external_id="ext1",
            card_id=c1.id,
            url="https://myp/ext1",
            name_en="Lightning Bolt",
            set_code="2XM",
            collector_number="1",
        )
        sc2 = SourceCardRow(
            source="myp",
            external_id="ext2",
            card_id=c2.id,
            url="https://myp/ext2",
            name_en="Counterspell",
            set_code="2XM",
            collector_number="2",
        )
        session.add_all([sc1, sc2])
        session.flush()

        # Price observations
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
        session.commit()

        # Store IDs for assertions
        repo._test_ids = {
            "c1": c1.id,
            "c2": c2.id,
            "c3": c3.id,
            "sc1": sc1.id,
            "sc2": sc2.id,
        }
    return repo


class TestListCards:
    def test_list_all(self, seeded_repo):
        cards = seeded_repo.list_cards()
        assert len(cards) == 3

    def test_filter_by_game(self, seeded_repo):
        cards = seeded_repo.list_cards(game="magic")
        assert len(cards) == 2
        assert all(c.game == "magic" for c in cards)

    def test_filter_by_set_code(self, seeded_repo):
        cards = seeded_repo.list_cards(set_code="SV1")
        assert len(cards) == 1
        assert cards[0].name_en == "Pikachu"

    def test_filter_by_name_search(self, seeded_repo):
        cards = seeded_repo.list_cards(name_search="bolt")
        assert len(cards) == 1
        assert cards[0].name_en == "Lightning Bolt"

    def test_pagination_after_id(self, seeded_repo):
        all_cards = seeded_repo.list_cards()
        first_id = all_cards[0].id
        rest = seeded_repo.list_cards(after_id=first_id)
        assert len(rest) == 2
        assert all(c.id > first_id for c in rest)

    def test_limit(self, seeded_repo):
        # limit=1 should return 2 (limit+1 for next page detection)
        cards = seeded_repo.list_cards(limit=1)
        assert len(cards) == 2

    def test_empty_result(self, seeded_repo):
        cards = seeded_repo.list_cards(game="yugioh")
        assert cards == []


class TestCountCards:
    def test_count_all(self, seeded_repo):
        assert seeded_repo.count_cards() == 3

    def test_count_with_game_filter(self, seeded_repo):
        assert seeded_repo.count_cards(game="magic") == 2

    def test_count_with_set_filter(self, seeded_repo):
        assert seeded_repo.count_cards(set_code="SV1") == 1

    def test_count_with_name_search(self, seeded_repo):
        assert seeded_repo.count_cards(name_search="bolt") == 1

    def test_count_zero(self, seeded_repo):
        assert seeded_repo.count_cards(game="yugioh") == 0


class TestGetCardById:
    def test_found(self, seeded_repo):
        card_id = seeded_repo._test_ids["c1"]
        card = seeded_repo.get_card_by_id(card_id)
        assert card is not None
        assert card.name_en == "Lightning Bolt"

    def test_not_found(self, seeded_repo):
        card = seeded_repo.get_card_by_id(99999)
        assert card is None


class TestGetSourceCardsForCard:
    def test_with_source_cards(self, seeded_repo):
        card_id = seeded_repo._test_ids["c1"]
        scs = seeded_repo.get_source_cards_for_card(card_id)
        assert len(scs) == 1
        assert scs[0].external_id == "ext1"

    def test_no_source_cards(self, seeded_repo):
        card_id = seeded_repo._test_ids["c3"]
        scs = seeded_repo.get_source_cards_for_card(card_id)
        assert scs == []


class TestGetLatestPricesBatch:
    def test_with_prices(self, seeded_repo):
        ids = seeded_repo._test_ids
        result = seeded_repo.get_latest_prices_batch([ids["c1"], ids["c2"]])
        assert result[ids["c1"]].median_price == Decimal("6.00")
        assert result[ids["c1"]].observed_at == date(2026, 8, 15)
        assert result[ids["c2"]].median_price == Decimal("3.00")

    def test_card_without_prices(self, seeded_repo):
        ids = seeded_repo._test_ids
        result = seeded_repo.get_latest_prices_batch([ids["c3"]])
        assert result[ids["c3"]] is None

    def test_empty_list(self, seeded_repo):
        result = seeded_repo.get_latest_prices_batch([])
        assert result == {}


class TestListSets:
    def test_groups_by_game_and_set(self, seeded_repo):
        results = seeded_repo.list_sets()
        assert len(results) == 2
        # Ordered by game, set_code: magic/2XM, pokemon/SV1
        assert results[0] == ("magic", "2XM", 2)
        assert results[1] == ("pokemon", "SV1", 1)

    def test_filter_by_game(self, seeded_repo):
        results = seeded_repo.list_sets(game="magic")
        assert len(results) == 1
        assert results[0] == ("magic", "2XM", 2)

    def test_empty_db(self, repo):
        results = repo.list_sets()
        assert results == []


class TestGetMovers:
    def test_identifies_gainers_and_losers(self, seeded_repo):
        """Lightning Bolt went 5.50->6.00 (+9.09%),
        Counterspell has only one observation so no change."""
        gainers, losers = seeded_repo.get_movers(days=30)
        # Lightning Bolt is a gainer (price went up)
        assert len(gainers) >= 1
        assert gainers[0][1] == "Lightning Bolt"
        assert gainers[0][5] > 0  # positive change

    def test_empty_db(self, repo):
        gainers, losers = repo.get_movers(days=30)
        assert gainers == []
        assert losers == []


class TestGetMarketStats:
    def test_aggregation(self, seeded_repo):
        stats = seeded_repo.get_market_stats()
        assert stats["total_cards"] == 3
        assert stats["total_observations"] == 3
        assert stats["avg_price"] is not None
        assert stats["date_range_start"] == date(2026, 8, 10)
        assert stats["date_range_end"] == date(2026, 8, 15)

    def test_filter_by_game(self, seeded_repo):
        stats = seeded_repo.get_market_stats(game="magic")
        assert stats["total_cards"] == 2

    def test_empty_db(self, repo):
        stats = repo.get_market_stats()
        assert stats["total_cards"] == 0
        assert stats["total_observations"] == 0
        assert stats["avg_price"] is None
        assert stats["date_range_start"] is None
        assert stats["date_range_end"] is None
