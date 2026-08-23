"""F50-T02: Unit tests for price_source field in CollectionCard schema."""

from __future__ import annotations

from src.api.schemas.collection import CollectionCard, CollectionCardDetail


class TestCollectionCardPriceSourceField:
    """Scenario #21: CollectionCard Pydantic schema includes price_source field."""

    def test_collection_card_schema_has_price_source(self) -> None:
        """price_source field exists in CollectionCard schema."""
        card = CollectionCard(
            id=1,
            set_code="DMR",
            collector_number="123",
            price_source="manual",
        )
        assert card.price_source == "manual"

    def test_price_source_defaults_to_none(self) -> None:
        """price_source defaults to None when not provided."""
        card = CollectionCard(
            id=1,
            set_code="DMR",
            collector_number="123",
        )
        assert card.price_source is None

    def test_price_source_accepts_myp(self) -> None:
        """price_source accepts 'myp' value."""
        card = CollectionCard(
            id=1,
            set_code="DMR",
            collector_number="123",
            price_source="myp",
        )
        assert card.price_source == "myp"

    def test_price_source_accepts_jsonld_snapshot(self) -> None:
        """price_source accepts 'jsonld_snapshot' value."""
        card = CollectionCard(
            id=1,
            set_code="DMR",
            collector_number="123",
            price_source="jsonld_snapshot",
        )
        assert card.price_source == "jsonld_snapshot"

    def test_price_source_inherited_by_detail(self) -> None:
        """CollectionCardDetail inherits price_source from CollectionCard."""
        detail = CollectionCardDetail(
            id=1,
            set_code="DMR",
            collector_number="123",
            price_source="manual",
        )
        assert detail.price_source == "manual"

    def test_price_source_in_schema_fields(self) -> None:
        """price_source is in the model fields."""
        assert "price_source" in CollectionCard.model_fields
