"""Tests for the database repository."""

from datetime import date, timedelta
from decimal import Decimal

import pytest

from src.database.repository import Repository
from src.domain.models import (
    CardIdentity,
    CollectionError,
    HistoricalPrice,
    SourceCard,
)


@pytest.fixture
def repo(tmp_path):
    db_path = tmp_path / "test.db"
    return Repository(f"sqlite:///{db_path}")


class TestUpsertSourceCard:
    def test_insert_new(self, repo):
        card = SourceCard(
            source="myp",
            external_id="12345",
            url="https://mypcards.com/magic/produto/12345/test",
            sku="magic_ltr_001",
            identity=CardIdentity(
                game="magic",
                name_en="Test Card",
                name_pt="Carta Teste",
                set_code="LTR",
                collector_number="001",
            ),
        )
        card_id = repo.upsert_source_card(card)
        assert card_id > 0

    def test_idempotent(self, repo):
        card = SourceCard(
            source="myp",
            external_id="12345",
            url="https://example.com/card",
            sku="magic_ltr_001",
            identity=CardIdentity(
                game="magic",
                name_en="Test",
                set_code="LTR",
                collector_number="001",
            ),
        )
        id1 = repo.upsert_source_card(card)
        id2 = repo.upsert_source_card(card)
        assert id1 == id2

    def test_upsert_with_card_id(self, repo):
        """upsert_source_card stores the card_id FK when provided."""
        card = SourceCard(
            source="myp",
            external_id="55555",
            url="https://example.com/card/55555",
            sku="magic_tst_001",
            identity=CardIdentity(
                game="magic",
                name_en="Test",
                name_pt="Teste",
                set_code="TST",
                collector_number="001",
            ),
        )
        canonical_id = repo.upsert_card(card)
        sc_id = repo.upsert_source_card(card, card_id=canonical_id)
        # Verify the link was stored
        from sqlalchemy import select
        from sqlalchemy.orm import Session

        from src.database.models import SourceCardRow

        with Session(repo.engine) as s:
            sc = s.execute(select(SourceCardRow).where(SourceCardRow.id == sc_id)).scalar_one()
            assert sc.card_id == canonical_id

    def test_upsert_updates_card_id_on_existing(self, repo):
        """When source_card exists with card_id=NULL, upsert updates it."""
        card = SourceCard(
            source="myp",
            external_id="66666",
            url="https://example.com/card/66666",
            sku="magic_tst_002",
            identity=CardIdentity(
                game="magic",
                name_en="Test2",
                set_code="TST",
                collector_number="002",
            ),
        )
        # First insert without card_id
        sc_id = repo.upsert_source_card(card)
        # Then upsert with card_id
        canonical_id = repo.upsert_card(card)
        sc_id2 = repo.upsert_source_card(card, card_id=canonical_id)
        assert sc_id == sc_id2
        from sqlalchemy import select
        from sqlalchemy.orm import Session

        from src.database.models import SourceCardRow

        with Session(repo.engine) as s:
            sc = s.execute(select(SourceCardRow).where(SourceCardRow.id == sc_id)).scalar_one()
            assert sc.card_id == canonical_id


class TestLinkOrphanSourceCards:
    def test_links_orphans_to_canonical_cards(self, repo):
        """link_orphan_source_cards matches by game+set_code+collector_number."""
        card = SourceCard(
            source="myp",
            external_id="77777",
            url="https://example.com/card/77777",
            sku="magic_tst_003",
            identity=CardIdentity(
                game="magic",
                name_en="Orphan Card",
                name_pt="Carta Orfao",
                set_code="TST",
                collector_number="003",
            ),
        )
        # Create canonical card and source_card separately (no link)
        canonical_id = repo.upsert_card(card)
        repo.upsert_source_card(card)  # card_id=None

        linked = repo.link_orphan_source_cards()
        assert linked == 1

        from sqlalchemy import select
        from sqlalchemy.orm import Session

        from src.database.models import SourceCardRow

        with Session(repo.engine) as s:
            sc = s.execute(
                select(SourceCardRow).where(SourceCardRow.external_id == "77777")
            ).scalar_one()
            assert sc.card_id == canonical_id

    def test_already_linked_not_counted(self, repo):
        """Cards already linked are not re-processed."""
        card = SourceCard(
            source="myp",
            external_id="88888",
            url="https://example.com/card/88888",
            sku="magic_tst_004",
            identity=CardIdentity(
                game="magic",
                name_en="Linked Card",
                set_code="TST",
                collector_number="004",
            ),
        )
        canonical_id = repo.upsert_card(card)
        repo.upsert_source_card(card, card_id=canonical_id)

        linked = repo.link_orphan_source_cards()
        assert linked == 0

    def test_orphan_without_matching_card(self, repo):
        """Orphan source_card with no matching canonical card stays unlinked."""
        card = SourceCard(
            source="myp",
            external_id="99999",
            url="https://example.com/card/99999",
            sku="magic_xxx_001",
            identity=CardIdentity(
                game="magic",
                name_en="No Match",
                set_code="XXX",
                collector_number="001",
            ),
        )
        repo.upsert_source_card(card)  # no canonical card exists

        linked = repo.link_orphan_source_cards()
        assert linked == 0


class TestInsertPriceObservations:
    def test_insert_new(self, repo):
        prices = [
            HistoricalPrice(
                source="myp",
                external_id="12345",
                observed_at=date(2026, 1, 1),
                median_price=Decimal("100.00"),
                currency="BRL",
            ),
            HistoricalPrice(
                source="myp",
                external_id="12345",
                observed_at=date(2026, 1, 8),
                median_price=Decimal("105.00"),
                currency="BRL",
            ),
        ]
        count = repo.insert_price_observations(prices)
        assert count == 2

    def test_skip_duplicates(self, repo):
        prices = [
            HistoricalPrice(
                source="myp",
                external_id="12345",
                observed_at=date(2026, 1, 1),
                median_price=Decimal("100.00"),
                currency="BRL",
            ),
        ]
        repo.insert_price_observations(prices)
        count = repo.insert_price_observations(prices)
        assert count == 0

    def test_empty_list(self, repo):
        assert repo.insert_price_observations([]) == 0

    def test_insert_10_new_observations(self, repo):
        """Happy path: insert 10 new observations, verify count == 10."""
        prices = [
            HistoricalPrice(
                source="myp",
                external_id="card1",
                observed_at=date(2026, 1, i + 1),
                median_price=Decimal("10.00") + Decimal(i),
                currency="BRL",
            )
            for i in range(10)
        ]
        count = repo.insert_price_observations(prices)
        assert count == 10

    def test_duplicates_return_zero(self, repo):
        """Insert 10, then insert same 10 again, verify second call returns 0."""
        prices = [
            HistoricalPrice(
                source="myp",
                external_id="card1",
                observed_at=date(2026, 2, i + 1),
                median_price=Decimal("20.00"),
                currency="BRL",
            )
            for i in range(10)
        ]
        repo.insert_price_observations(prices)
        count = repo.insert_price_observations(prices)
        assert count == 0

    def test_mixed_new_and_duplicate(self, repo):
        """Insert 10, then insert 15 where 10 overlap, verify count == 5."""
        first_batch = [
            HistoricalPrice(
                source="myp",
                external_id="card2",
                observed_at=date(2026, 3, i + 1),
                median_price=Decimal("30.00"),
                currency="BRL",
            )
            for i in range(10)
        ]
        repo.insert_price_observations(first_batch)

        second_batch = [
            HistoricalPrice(
                source="myp",
                external_id="card2",
                observed_at=date(2026, 3, i + 1),
                median_price=Decimal("30.00"),
                currency="BRL",
            )
            for i in range(15)
        ]
        count = repo.insert_price_observations(second_batch)
        assert count == 5

    def test_large_batch_exceeds_chunk_size(self, repo):
        """Insert 600 observations (exceeds chunk size 500), verify all inserted."""
        prices = [
            HistoricalPrice(
                source="myp",
                external_id="card3",
                observed_at=date(2024, 1, 1) + timedelta(days=i),
                median_price=Decimal("5.00"),
                currency="BRL",
            )
            for i in range(600)
        ]
        count = repo.insert_price_observations(prices)
        assert count == 600
        assert repo.get_observation_count("myp") == 600

    def test_single_observation(self, repo):
        """Boundary: insert single observation, verify count == 1."""
        prices = [
            HistoricalPrice(
                source="myp",
                external_id="card4",
                observed_at=date(2026, 6, 1),
                median_price=Decimal("99.99"),
                currency="BRL",
            ),
        ]
        count = repo.insert_price_observations(prices)
        assert count == 1


class TestCollectionErrors:
    def test_insert_and_retrieve(self, repo):
        error = CollectionError(
            source="myp",
            external_id="99999",
            url="https://example.com/card/99999",
            error_type="HTTPError",
            error_message="404 Not Found",
            http_status=404,
        )
        repo.insert_error(error)
        errors = repo.get_unresolved_errors("myp")
        assert len(errors) == 1
        assert errors[0].external_id == "99999"

    def test_mark_resolved(self, repo):
        error = CollectionError(
            source="myp",
            external_id="99999",
            url="https://example.com/card/99999",
            error_type="HTTPError",
            error_message="404 Not Found",
        )
        repo.insert_error(error)
        repo.mark_errors_resolved("myp", "99999")
        errors = repo.get_unresolved_errors("myp")
        assert len(errors) == 0
