"""Tests for oracle_text handling in catalog seeder."""

from __future__ import annotations

from src.catalog.scryfall import CatalogCard


class TestCatalogCardOracleText:
    """Verify CatalogCard carries oracle_text through the pipeline."""

    def test_default_empty_oracle_text(self):
        card = CatalogCard(
            name_en="Sol Ring",
            set_code="cmr",
            collector_number="472",
            rarity="U",
            color_identity="",
            mana_cost="{1}",
            type_line="Artifact",
            image_uri=None,
        )
        assert card.oracle_text == ""

    def test_explicit_oracle_text(self):
        card = CatalogCard(
            name_en="Sol Ring",
            set_code="cmr",
            collector_number="472",
            rarity="U",
            color_identity="",
            mana_cost="{1}",
            type_line="Artifact",
            image_uri=None,
            oracle_text="{T}: Add {C}{C}.",
        )
        assert card.oracle_text == "{T}: Add {C}{C}."

    def test_oracle_text_is_frozen(self):
        card = CatalogCard(
            name_en="Sol Ring",
            set_code="cmr",
            collector_number="472",
            rarity="U",
            color_identity="",
            mana_cost="{1}",
            type_line="Artifact",
            image_uri=None,
            oracle_text="text",
        )
        # CatalogCard is frozen — mutation should raise
        try:
            card.oracle_text = "modified"  # type: ignore[misc]
            assert False, "Expected FrozenInstanceError"
        except AttributeError:
            pass
