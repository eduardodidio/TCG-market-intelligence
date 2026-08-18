"""Tests for the database repository."""

import os
import tempfile
from datetime import date, datetime
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
            identity=CardIdentity(game="magic", name_en="Test", set_code="LTR", collector_number="001"),
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
