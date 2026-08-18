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
