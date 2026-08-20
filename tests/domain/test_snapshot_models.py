"""Tests for JSON-LD snapshot domain models (JsonLdPrice, SnapshotSummary)."""

from datetime import datetime
from decimal import Decimal

from src.domain.models import CollectionError, JsonLdPrice, SnapshotSummary


class TestJsonLdPrice:
    def test_create_with_all_fields(self):
        price = JsonLdPrice(
            price=Decimal("29.90"),
            currency="BRL",
            availability="InStock",
        )
        assert price.price == Decimal("29.90")
        assert price.currency == "BRL"
        assert price.availability == "InStock"

    def test_defaults(self):
        price = JsonLdPrice(price=Decimal("10.00"))
        assert price.currency == "BRL"
        assert price.availability == "Unknown"

    def test_none_price(self):
        price = JsonLdPrice(price=None)
        assert price.price is None
        assert price.currency == "BRL"
        assert price.availability == "Unknown"

    def test_out_of_stock(self):
        price = JsonLdPrice(
            price=Decimal("45.00"),
            availability="OutOfStock",
        )
        assert price.availability == "OutOfStock"
        assert price.price == Decimal("45.00")

    def test_zero_price(self):
        price = JsonLdPrice(price=Decimal("0.00"))
        assert price.price == Decimal("0.00")

    def test_custom_currency(self):
        price = JsonLdPrice(
            price=Decimal("5.99"),
            currency="USD",
        )
        assert price.currency == "USD"


class TestSnapshotSummary:
    def test_create_with_defaults(self):
        summary = SnapshotSummary()
        assert summary.total_entries == 0
        assert summary.fetched == 0
        assert summary.stored == 0
        assert summary.skipped_existing == 0
        assert summary.skipped_zero_price == 0
        assert summary.errors == 0
        assert summary.error_details == []
        assert isinstance(summary.started_at, datetime)
        assert summary.finished_at is None

    def test_create_with_all_fields(self):
        started = datetime(2026, 8, 20, 10, 0, 0)
        finished = datetime(2026, 8, 20, 10, 35, 0)
        error = CollectionError(
            source="jsonld_snapshot",
            external_id="999",
            url="https://mypcards.com/magic/product/999/test",
            error_type="HTTPError",
            error_message="Connection timeout",
            http_status=504,
        )
        summary = SnapshotSummary(
            total_entries=100,
            fetched=85,
            stored=80,
            skipped_existing=10,
            skipped_zero_price=5,
            errors=5,
            error_details=[error],
            started_at=started,
            finished_at=finished,
        )
        assert summary.total_entries == 100
        assert summary.fetched == 85
        assert summary.stored == 80
        assert summary.skipped_existing == 10
        assert summary.skipped_zero_price == 5
        assert summary.errors == 5
        assert len(summary.error_details) == 1
        assert summary.error_details[0].error_type == "HTTPError"
        assert summary.started_at == started
        assert summary.finished_at == finished

    def test_started_at_auto_populates(self):
        before = datetime.now()
        summary = SnapshotSummary()
        after = datetime.now()
        assert before <= summary.started_at <= after

    def test_error_details_independent_instances(self):
        """Ensure default_factory creates independent lists."""
        s1 = SnapshotSummary()
        s2 = SnapshotSummary()
        assert s1.error_details is not s2.error_details
