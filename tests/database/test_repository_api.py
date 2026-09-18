from __future__ import annotations

from datetime import date, datetime, timedelta
from decimal import Decimal

import pytest
from sqlalchemy.orm import Session

from src.database.models import (
    CardRow,
    CollectionErrorRow,
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
    def test_identifies_gainers_and_losers(self, repo):
        """Lightning Bolt went 5.00->6.00 (+20%), using relative dates."""
        today = date.today()
        engine = repo.engine
        with Session(engine) as session:
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
            session.add_all([c1, c2])
            session.flush()

            sc1 = SourceCardRow(
                source="myp",
                external_id="mv_ext1",
                card_id=c1.id,
                url="https://myp/mv_ext1",
                name_en="Lightning Bolt",
                set_code="2XM",
                collector_number="1",
            )
            sc2 = SourceCardRow(
                source="myp",
                external_id="mv_ext2",
                card_id=c2.id,
                url="https://myp/mv_ext2",
                name_en="Counterspell",
                set_code="2XM",
                collector_number="2",
            )
            session.add_all([sc1, sc2])
            session.flush()

            # Lightning Bolt: price went up 5.00 -> 6.00
            session.add(
                PriceObservationRow(
                    source="myp",
                    external_id="mv_ext1",
                    observed_at=today - timedelta(days=10),
                    median_price=Decimal("5.00"),
                    currency="BRL",
                )
            )
            session.add(
                PriceObservationRow(
                    source="myp",
                    external_id="mv_ext1",
                    observed_at=today - timedelta(days=1),
                    median_price=Decimal("6.00"),
                    currency="BRL",
                )
            )
            # Counterspell: only one observation (no change possible)
            session.add(
                PriceObservationRow(
                    source="myp",
                    external_id="mv_ext2",
                    observed_at=today - timedelta(days=5),
                    median_price=Decimal("3.00"),
                    currency="BRL",
                )
            )
            session.commit()

        gainers, losers = repo.get_movers(days=30)
        # Lightning Bolt is a gainer (price went up)
        assert len(gainers) >= 1
        assert gainers[0][1] == "Lightning Bolt"
        assert float(gainers[0][6]) > 0  # positive change_pct

    def test_identifies_losers(self, repo):
        """Card that went down in price should appear in losers."""
        today = date.today()
        engine = repo.engine
        with Session(engine) as session:
            c = CardRow(
                game="magic",
                name_en="Falling Star",
                name_pt="Estrela",
                set_code="LEG",
                collector_number="1",
            )
            session.add(c)
            session.flush()
            sc = SourceCardRow(
                source="myp",
                external_id="fall_ext",
                card_id=c.id,
                url="https://myp/fall",
                name_en="Falling Star",
                set_code="LEG",
                collector_number="1",
            )
            session.add(sc)
            session.flush()
            session.add(
                PriceObservationRow(
                    source="myp",
                    external_id="fall_ext",
                    observed_at=today - timedelta(days=10),
                    median_price=Decimal("10.00"),
                    currency="BRL",
                )
            )
            session.add(
                PriceObservationRow(
                    source="myp",
                    external_id="fall_ext",
                    observed_at=today - timedelta(days=1),
                    median_price=Decimal("7.00"),
                    currency="BRL",
                )
            )
            session.commit()

        gainers, losers = repo.get_movers(days=30)
        assert len(losers) >= 1
        assert losers[0][1] == "Falling Star"
        assert float(losers[0][6]) < 0  # negative change_pct

    def test_excludes_zero_start_price(self, repo):
        """Cards with zero starting price are excluded."""
        today = date.today()
        engine = repo.engine
        with Session(engine) as session:
            c = CardRow(
                game="magic",
                name_en="Zero Card",
                name_pt="Zero",
                set_code="TST",
                collector_number="1",
            )
            session.add(c)
            session.flush()
            sc = SourceCardRow(
                source="myp",
                external_id="zero_ext",
                card_id=c.id,
                url="https://myp/zero",
                name_en="Zero Card",
                set_code="TST",
                collector_number="1",
            )
            session.add(sc)
            session.flush()
            session.add(
                PriceObservationRow(
                    source="myp",
                    external_id="zero_ext",
                    observed_at=today - timedelta(days=10),
                    median_price=Decimal("0.00"),
                    currency="BRL",
                )
            )
            session.add(
                PriceObservationRow(
                    source="myp",
                    external_id="zero_ext",
                    observed_at=today - timedelta(days=1),
                    median_price=Decimal("5.00"),
                    currency="BRL",
                )
            )
            session.commit()

        gainers, losers = repo.get_movers(days=30)
        all_ids = [m[1] for m in gainers + losers]
        assert "Zero Card" not in all_ids

    def test_excludes_card_with_only_pre_cutoff_prices(self, repo):
        """Cards with prices only before cutoff should be excluded."""
        today = date.today()
        engine = repo.engine
        with Session(engine) as session:
            c = CardRow(
                game="magic",
                name_en="Old Card",
                name_pt="Velho",
                set_code="OLD",
                collector_number="1",
            )
            session.add(c)
            session.flush()
            sc = SourceCardRow(
                source="myp",
                external_id="old_ext",
                card_id=c.id,
                url="https://myp/old",
                name_en="Old Card",
                set_code="OLD",
                collector_number="1",
            )
            session.add(sc)
            session.flush()
            # Both observations before cutoff (days=5 -> cutoff = today - 5)
            session.add(
                PriceObservationRow(
                    source="myp",
                    external_id="old_ext",
                    observed_at=today - timedelta(days=20),
                    median_price=Decimal("10.00"),
                    currency="BRL",
                )
            )
            session.add(
                PriceObservationRow(
                    source="myp",
                    external_id="old_ext",
                    observed_at=today - timedelta(days=15),
                    median_price=Decimal("12.00"),
                    currency="BRL",
                )
            )
            session.commit()

        gainers, losers = repo.get_movers(days=5)
        all_ids = [m[1] for m in gainers + losers]
        assert "Old Card" not in all_ids

    def test_empty_db(self, repo):
        gainers, losers = repo.get_movers(days=30)
        assert gainers == []
        assert losers == []

    def test_return_shape(self, repo):
        """Each tuple has 7 elements: card_id, name_en, name_pt, set_code,
        price_start, price_end, change_pct."""
        today = date.today()
        engine = repo.engine
        with Session(engine) as session:
            c = CardRow(
                game="magic",
                name_en="Shape Test",
                name_pt="Forma",
                set_code="TST",
                collector_number="1",
            )
            session.add(c)
            session.flush()
            sc = SourceCardRow(
                source="myp",
                external_id="shape_ext",
                card_id=c.id,
                url="https://myp/shape",
                name_en="Shape Test",
                set_code="TST",
                collector_number="1",
            )
            session.add(sc)
            session.flush()
            session.add(
                PriceObservationRow(
                    source="myp",
                    external_id="shape_ext",
                    observed_at=today - timedelta(days=10),
                    median_price=Decimal("5.00"),
                    currency="BRL",
                )
            )
            session.add(
                PriceObservationRow(
                    source="myp",
                    external_id="shape_ext",
                    observed_at=today - timedelta(days=1),
                    median_price=Decimal("8.00"),
                    currency="BRL",
                )
            )
            session.commit()

        gainers, losers = repo.get_movers(days=30)
        for mover in gainers + losers:
            assert len(mover) == 7
            card_id, name_en, name_pt, set_code, price_start, price_end, change_pct = mover
            assert isinstance(card_id, int)
            assert isinstance(name_en, str)
            assert price_start > 0


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


class TestGetLatestObservationDate:
    def test_empty_db(self, repo):
        result = repo.get_latest_observation_date()
        assert result is None

    def test_with_data(self, seeded_repo):
        result = seeded_repo.get_latest_observation_date()
        assert result == date(2026, 8, 15)

    def test_filtered_by_source(self, seeded_repo):
        result = seeded_repo.get_latest_observation_date(source="myp")
        assert result == date(2026, 8, 15)

    def test_filtered_by_nonexistent_source(self, seeded_repo):
        result = seeded_repo.get_latest_observation_date(source="nonexistent")
        assert result is None


class TestGetStaleCardsCount:
    def test_no_stale_when_all_fresh(self, seeded_repo):
        # Observations at 2026-08-10 and 2026-08-15; with stale_days=30
        # and today=2026-08-19, none are stale
        count = seeded_repo.get_stale_cards_count(stale_days=30)
        assert count == 0

    def test_with_stale_cards(self, seeded_repo):
        # With stale_days=3, cards observed before 2026-08-16 are stale.
        # ext1 last obs is 2026-08-15 (stale), ext2 last obs is 2026-08-12 (stale)
        count = seeded_repo.get_stale_cards_count(stale_days=3)
        assert count >= 1  # At least ext2 is stale (may vary with test date)

    def test_source_cards_without_observations_counted_as_stale(self, repo):
        """Source cards with zero observations should be counted as stale."""
        engine = repo.engine
        with Session(engine) as session:
            sc = SourceCardRow(
                source="myp",
                external_id="orphan1",
                url="https://myp/orphan1",
            )
            session.add(sc)
            session.commit()

        count = repo.get_stale_cards_count(stale_days=14)
        assert count == 1

    def test_empty_db(self, repo):
        count = repo.get_stale_cards_count()
        assert count == 0


class TestGetRecentErrorsCount:
    def test_empty_db(self, repo):
        count = repo.get_recent_errors_count()
        assert count == 0

    def test_counts_recent_unresolved_errors(self, repo):
        engine = repo.engine
        with Session(engine) as session:
            # Recent unresolved error
            e1 = CollectionErrorRow(
                source="myp",
                external_id="ext1",
                url="https://myp/ext1",
                error_type="http_error",
                error_message="503 Service Unavailable",
                resolved=0,
                timestamp=datetime.now() - timedelta(days=1),
            )
            # Old unresolved error (should not count with default days=7)
            e2 = CollectionErrorRow(
                source="myp",
                external_id="ext2",
                url="https://myp/ext2",
                error_type="http_error",
                error_message="500 Internal Server Error",
                resolved=0,
                timestamp=datetime.now() - timedelta(days=30),
            )
            # Recent but resolved error (should not count)
            e3 = CollectionErrorRow(
                source="myp",
                external_id="ext3",
                url="https://myp/ext3",
                error_type="http_error",
                error_message="404 Not Found",
                resolved=1,
                timestamp=datetime.now() - timedelta(days=1),
            )
            session.add_all([e1, e2, e3])
            session.commit()

        count = repo.get_recent_errors_count()
        assert count == 1

    def test_filtered_by_source(self, repo):
        engine = repo.engine
        with Session(engine) as session:
            e1 = CollectionErrorRow(
                source="myp",
                external_id="ext1",
                url="https://myp/ext1",
                error_type="http_error",
                error_message="503",
                resolved=0,
                timestamp=datetime.now() - timedelta(hours=1),
            )
            e2 = CollectionErrorRow(
                source="other",
                external_id="ext2",
                url="https://other/ext2",
                error_type="http_error",
                error_message="503",
                resolved=0,
                timestamp=datetime.now() - timedelta(hours=1),
            )
            session.add_all([e1, e2])
            session.commit()

        assert repo.get_recent_errors_count(source="myp") == 1
        assert repo.get_recent_errors_count(source="other") == 1
        assert repo.get_recent_errors_count() == 2


class TestGetSourceCardCount:
    def test_empty_db(self, repo):
        assert repo.get_source_card_count() == 0

    def test_with_data(self, seeded_repo):
        assert seeded_repo.get_source_card_count() == 2
        assert seeded_repo.get_source_card_count(source="myp") == 2
        assert seeded_repo.get_source_card_count(source="nonexistent") == 0


class TestGetCollectionTotalValue:
    """Tests for Repository.get_collection_total_value()."""

    def test_happy_path_linked_cards_with_prices(self, seeded_repo):
        """Linked cards with prices return the correct Decimal total."""
        ids = seeded_repo._test_ids
        engine = seeded_repo.engine
        with Session(engine) as session:
            # Two collection entries linked to cards with prices
            uc1 = UserCollectionRow(
                user_id="testuser",
                card_id=ids["c1"],
                set_code="2XM",
                collector_number="1",
                name_en="Lightning Bolt",
                quantity=2,
            )
            uc2 = UserCollectionRow(
                user_id="testuser",
                card_id=ids["c2"],
                set_code="2XM",
                collector_number="2",
                name_en="Counterspell",
                quantity=3,
            )
            session.add_all([uc1, uc2])
            session.commit()

        # c1 latest price = 6.00, qty=2 => 12.00
        # c2 latest price = 3.00, qty=3 => 9.00
        # total = 21.00
        result = seeded_repo.get_collection_total_value("testuser")
        assert result == Decimal("21.00")

    def test_no_linked_cards_returns_none(self, repo):
        """No linked cards (empty collection) returns None."""
        result = repo.get_collection_total_value("nouser")
        assert result is None

    def test_linked_cards_no_prices_returns_none(self, repo):
        """Linked cards but no price observations returns None."""
        engine = repo.engine
        with Session(engine) as session:
            # Create a card with no source cards / price observations
            card = CardRow(
                game="magic",
                name_en="No Price Card",
                set_code="TST",
                collector_number="999",
            )
            session.add(card)
            session.flush()

            uc = UserCollectionRow(
                user_id="testuser",
                card_id=card.id,
                set_code="TST",
                collector_number="999",
                name_en="No Price Card",
                quantity=1,
            )
            session.add(uc)
            session.commit()

        result = repo.get_collection_total_value("testuser")
        assert result is None

    def test_mixed_some_cards_have_prices(self, seeded_repo):
        """When some linked cards have prices and some do not, sums only priced ones."""
        ids = seeded_repo._test_ids
        engine = seeded_repo.engine
        with Session(engine) as session:
            # c1 has prices, c3 (Pikachu) has no source cards / prices
            uc1 = UserCollectionRow(
                user_id="mixeduser",
                card_id=ids["c1"],
                set_code="2XM",
                collector_number="1",
                name_en="Lightning Bolt",
                quantity=1,
            )
            uc2 = UserCollectionRow(
                user_id="mixeduser",
                card_id=ids["c3"],
                set_code="SV1",
                collector_number="25",
                name_en="Pikachu",
                quantity=4,
            )
            session.add_all([uc1, uc2])
            session.commit()

        # Only c1 has a price (6.00), qty=1 => 6.00
        result = seeded_repo.get_collection_total_value("mixeduser")
        assert result == Decimal("6.00")

    def test_unlinked_entries_ignored(self, seeded_repo):
        """Collection entries with card_id=None are not counted."""
        engine = seeded_repo.engine
        with Session(engine) as session:
            uc = UserCollectionRow(
                user_id="unlinked",
                card_id=None,
                set_code="2XM",
                collector_number="1",
                name_en="Unlinked Card",
                quantity=5,
            )
            session.add(uc)
            session.commit()

        result = seeded_repo.get_collection_total_value("unlinked")
        assert result is None


class TestCollectionMoversOptimized:
    """Tests for get_collection_movers_optimized using real SQLite DB."""

    def test_empty_collection_returns_empty(self, repo):
        gainers, losers = repo.get_collection_movers_optimized(999, days=7)
        assert gainers == []
        assert losers == []

    def test_single_price_point_excluded(self, repo):
        """Cards with only one price observation should be excluded."""
        engine = repo.engine
        with Session(engine) as session:
            card = CardRow(
                game="magic",
                name_en="Solo Card",
                set_code="TST",
                collector_number="1",
            )
            session.add(card)
            session.flush()

            uc = UserCollectionRow(
                user_id="1",
                card_id=card.id,
                set_code="TST",
                collector_number="1",
                name_en="Solo Card",
                quantity=1,
            )
            session.add(uc)

            sc = SourceCardRow(
                source="myp",
                external_id="myp_solo",
                card_id=card.id,
                url="http://test/solo",
            )
            session.add(sc)
            session.flush()

            obs = PriceObservationRow(
                source="myp",
                external_id="myp_solo",
                observed_at=date.today(),
                median_price=Decimal("10.00"),
            )
            session.add(obs)
            session.commit()

        # Only one observation in the period, so earliest == latest => excluded
        gainers, losers = repo.get_collection_movers_optimized(1, days=7)
        assert gainers == []
        assert losers == []

    def test_gainer_and_loser_detected(self, repo):
        """Cards with price increase/decrease are correctly classified."""
        engine = repo.engine
        today = date.today()
        yesterday = today - timedelta(days=1)

        with Session(engine) as session:
            # Gainer card: 10 -> 20
            c1 = CardRow(
                game="magic",
                name_en="Gainer",
                set_code="TST",
                collector_number="1",
            )
            # Loser card: 20 -> 10
            c2 = CardRow(
                game="magic",
                name_en="Loser",
                set_code="TST",
                collector_number="2",
            )
            session.add_all([c1, c2])
            session.flush()

            for card in [c1, c2]:
                uc = UserCollectionRow(
                    user_id="1",
                    card_id=card.id,
                    set_code="TST",
                    collector_number=card.collector_number,
                    name_en=card.name_en,
                    quantity=1,
                )
                session.add(uc)

                sc = SourceCardRow(
                    source="myp",
                    external_id=f"myp_{card.id}",
                    card_id=card.id,
                    url=f"http://test/{card.id}",
                )
                session.add(sc)

            session.flush()

            # Gainer prices
            session.add(
                PriceObservationRow(
                    source="myp",
                    external_id=f"myp_{c1.id}",
                    observed_at=yesterday,
                    median_price=Decimal("10.00"),
                )
            )
            session.add(
                PriceObservationRow(
                    source="myp",
                    external_id=f"myp_{c1.id}",
                    observed_at=today,
                    median_price=Decimal("20.00"),
                )
            )

            # Loser prices
            session.add(
                PriceObservationRow(
                    source="myp",
                    external_id=f"myp_{c2.id}",
                    observed_at=yesterday,
                    median_price=Decimal("20.00"),
                )
            )
            session.add(
                PriceObservationRow(
                    source="myp",
                    external_id=f"myp_{c2.id}",
                    observed_at=today,
                    median_price=Decimal("10.00"),
                )
            )
            session.commit()

            gainer_id = c1.id
            loser_id = c2.id

        gainers, losers = repo.get_collection_movers_optimized(1, days=7)

        assert len(gainers) == 1
        assert gainers[0][0] == gainer_id
        assert gainers[0][1] == "Gainer"
        assert gainers[0][8] == pytest.approx(100.0, abs=0.01)

        assert len(losers) == 1
        assert losers[0][0] == loser_id
        assert losers[0][1] == "Loser"
        assert losers[0][8] == pytest.approx(-50.0, abs=0.01)

    def test_direct_liga_prices_included(self, repo):
        """Direct liga_{card_id} pattern prices are picked up."""
        engine = repo.engine
        today = date.today()
        yesterday = today - timedelta(days=1)

        with Session(engine) as session:
            card = CardRow(
                game="magic",
                name_en="Liga Card",
                set_code="TST",
                collector_number="1",
            )
            session.add(card)
            session.flush()

            uc = UserCollectionRow(
                user_id="1",
                card_id=card.id,
                set_code="TST",
                collector_number="1",
                name_en="Liga Card",
                quantity=1,
            )
            session.add(uc)

            # No source_card, only direct liga prices
            session.add(
                PriceObservationRow(
                    source="liga",
                    external_id=f"liga_{card.id}",
                    observed_at=yesterday,
                    median_price=Decimal("5.00"),
                )
            )
            session.add(
                PriceObservationRow(
                    source="liga",
                    external_id=f"liga_{card.id}",
                    observed_at=today,
                    median_price=Decimal("15.00"),
                )
            )
            session.commit()
            card_id = card.id

        gainers, losers = repo.get_collection_movers_optimized(1, days=7)

        assert len(gainers) == 1
        assert gainers[0][0] == card_id
        assert gainers[0][8] == pytest.approx(200.0, abs=0.01)

    def test_investment_only_filter(self, repo):
        """investment_only=True excludes cards without acquisition_price."""
        engine = repo.engine
        today = date.today()
        yesterday = today - timedelta(days=1)

        with Session(engine) as session:
            c1 = CardRow(
                game="magic",
                name_en="Invested",
                set_code="TST",
                collector_number="1",
            )
            c2 = CardRow(
                game="magic",
                name_en="Not Invested",
                set_code="TST",
                collector_number="2",
            )
            session.add_all([c1, c2])
            session.flush()

            # c1 has acquisition_price, c2 does not
            uc1 = UserCollectionRow(
                user_id="1",
                card_id=c1.id,
                set_code="TST",
                collector_number="1",
                name_en="Invested",
                quantity=1,
                acquisition_price=Decimal("5.00"),
            )
            uc2 = UserCollectionRow(
                user_id="1",
                card_id=c2.id,
                set_code="TST",
                collector_number="2",
                name_en="Not Invested",
                quantity=1,
            )
            session.add_all([uc1, uc2])

            for card in [c1, c2]:
                sc = SourceCardRow(
                    source="myp",
                    external_id=f"myp_{card.id}",
                    card_id=card.id,
                    url=f"http://test/{card.id}",
                )
                session.add(sc)
                session.add(
                    PriceObservationRow(
                        source="myp",
                        external_id=f"myp_{card.id}",
                        observed_at=yesterday,
                        median_price=Decimal("10.00"),
                    )
                )
                session.add(
                    PriceObservationRow(
                        source="myp",
                        external_id=f"myp_{card.id}",
                        observed_at=today,
                        median_price=Decimal("20.00"),
                    )
                )
            session.commit()
            invested_id = c1.id

        # Without investment_only: both cards
        gainers_all, _ = repo.get_collection_movers_optimized(1, days=7)
        assert len(gainers_all) == 2

        # With investment_only: only invested card
        gainers_inv, _ = repo.get_collection_movers_optimized(
            1,
            days=7,
            investment_only=True,
        )
        assert len(gainers_inv) == 1
        assert gainers_inv[0][0] == invested_id

    def test_result_tuple_shape(self, repo):
        """Each result tuple has 9 elements."""
        engine = repo.engine
        today = date.today()
        yesterday = today - timedelta(days=1)

        with Session(engine) as session:
            card = CardRow(
                game="magic",
                name_en="Shape Test",
                set_code="TST",
                collector_number="42",
                image_uri="http://img/42.jpg",
            )
            session.add(card)
            session.flush()

            uc = UserCollectionRow(
                user_id="1",
                card_id=card.id,
                set_code="TST",
                collector_number="42",
                name_en="Shape Test",
                quantity=1,
            )
            sc = SourceCardRow(
                source="myp",
                external_id=f"myp_{card.id}",
                card_id=card.id,
                url="http://test",
            )
            session.add_all([uc, sc])
            session.flush()

            session.add(
                PriceObservationRow(
                    source="myp",
                    external_id=f"myp_{card.id}",
                    observed_at=yesterday,
                    median_price=Decimal("10.00"),
                )
            )
            session.add(
                PriceObservationRow(
                    source="myp",
                    external_id=f"myp_{card.id}",
                    observed_at=today,
                    median_price=Decimal("15.00"),
                )
            )
            session.commit()

        gainers, _ = repo.get_collection_movers_optimized(1, days=7)
        assert len(gainers) == 1
        t = gainers[0]
        assert len(t) == 9
        # card_id, card_name, set_code, collector_number, image_uri,
        # price_start, price_end, change_abs, change_pct
        assert isinstance(t[0], int)
        assert t[1] == "Shape Test"
        assert t[2] == "TST"
        assert t[3] == "42"
        assert t[4] == "http://img/42.jpg"
        assert isinstance(t[5], float)
        assert isinstance(t[6], float)
