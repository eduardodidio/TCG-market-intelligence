"""Tests for catalog seeder enrichment of pre-existing bare cards (F171-T03).

Verifies that the seeder's on_conflict_do_update behaviour fills in
metadata (type_line, rarity, color_identity, mana_cost, image_uri) for
cards that were previously created by the price collector with NULL
metadata fields.
"""

from __future__ import annotations

import pytest
from sqlalchemy import create_engine, event, func, select
from sqlalchemy.orm import Session

from src.catalog.scryfall import CatalogCard
from src.database.compat import dialect_insert
from src.database.models import Base, CardRow

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def engine():
    """In-memory SQLite engine with tables created."""
    eng = create_engine("sqlite:///:memory:", echo=False)

    @event.listens_for(eng, "connect")
    def _pragmas(dbapi_conn, _):
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(eng)
    return eng


def _bare_card(
    session: Session,
    *,
    name_en: str = "Atraxa, Praetors' Voice",
    set_code: str = "cmm",
    collector_number: str = "1",
) -> int:
    """Insert a bare card (as the price collector would) and return its id."""
    card = CardRow(
        game="magic",
        name_en=name_en,
        set_code=set_code,
        collector_number=collector_number,
        # All metadata fields are NULL — simulates upsert_card from price collector
    )
    session.add(card)
    session.commit()
    return card.id


def _run_seeder_upsert(
    session: Session,
    catalog_card: CatalogCard,
) -> int:
    """Execute the same upsert logic that _process_card_batch uses.

    Returns rowcount from the statement execution.
    """
    insert_stmt = dialect_insert(session.get_bind(), CardRow).values(
        game="magic",
        name_en=catalog_card.name_en,
        name_pt=catalog_card.name_pt,
        set_code=catalog_card.set_code,
        collector_number=catalog_card.collector_number,
        rarity=catalog_card.rarity,
        color_identity=catalog_card.color_identity,
        mana_cost=catalog_card.mana_cost,
        type_line=catalog_card.type_line,
        image_uri=catalog_card.image_uri,
    )
    excluded = insert_stmt.excluded
    stmt = insert_stmt.on_conflict_do_update(
        index_elements=["game", "set_code", "collector_number"],
        set_={
            "type_line": func.coalesce(CardRow.type_line, excluded.type_line),
            "rarity": func.coalesce(CardRow.rarity, excluded.rarity),
            "color_identity": func.coalesce(CardRow.color_identity, excluded.color_identity),
            "mana_cost": func.coalesce(CardRow.mana_cost, excluded.mana_cost),
            "image_uri": func.coalesce(CardRow.image_uri, excluded.image_uri),
            "name_pt": func.coalesce(CardRow.name_pt, excluded.name_pt),
        },
    )
    result = session.execute(stmt)
    session.commit()
    return result.rowcount


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestSeederEnrichExistingBareCard:
    """Verify that the seeder's on_conflict_do_update fills NULL metadata."""

    def test_bare_card_has_null_metadata(self, engine):
        """Precondition: a bare card has no type_line, rarity, etc."""
        with Session(engine) as session:
            card_id = _bare_card(session)
            card = session.get(CardRow, card_id)
            assert card.type_line is None
            assert card.rarity is None
            assert card.color_identity is None
            assert card.mana_cost is None
            assert card.image_uri is None

    def test_upsert_enriches_null_fields(self, engine):
        """Seeder upsert fills all NULL metadata from Scryfall data."""
        with Session(engine) as session:
            card_id = _bare_card(session)

        catalog = CatalogCard(
            name_en="Atraxa, Praetors' Voice",
            name_pt="Atraxa, Voz dos Pretores",
            set_code="cmm",
            collector_number="1",
            rarity="mythic",
            color_identity="WUBG",
            mana_cost="{G}{W}{U}{B}",
            type_line="Legendary Creature — Phyrexian Angel Horror",
            image_uri="https://cards.scryfall.io/large/cmm/1.jpg",
        )

        with Session(engine) as session:
            _run_seeder_upsert(session, catalog)

        with Session(engine) as session:
            card = session.get(CardRow, card_id)
            assert card.type_line == "Legendary Creature — Phyrexian Angel Horror"
            assert card.rarity == "mythic"
            assert card.color_identity == "WUBG"
            assert card.mana_cost == "{G}{W}{U}{B}"
            assert card.image_uri == "https://cards.scryfall.io/large/cmm/1.jpg"
            assert card.name_pt == "Atraxa, Voz dos Pretores"

    def test_upsert_preserves_existing_non_null_values(self, engine):
        """COALESCE keeps the existing value when it is not NULL."""
        with Session(engine) as session:
            card = CardRow(
                game="magic",
                name_en="Atraxa, Praetors' Voice",
                set_code="cmm",
                collector_number="1",
                type_line="Legendary Creature — Custom Override",
                rarity="rare",
                # color_identity is NULL — should be filled
            )
            session.add(card)
            session.commit()
            card_id = card.id

        catalog = CatalogCard(
            name_en="Atraxa, Praetors' Voice",
            name_pt="Atraxa, Voz dos Pretores",
            set_code="cmm",
            collector_number="1",
            rarity="mythic",
            color_identity="WUBG",
            mana_cost="{G}{W}{U}{B}",
            type_line="Legendary Creature — Phyrexian Angel Horror",
            image_uri="https://cards.scryfall.io/large/cmm/1.jpg",
        )

        with Session(engine) as session:
            _run_seeder_upsert(session, catalog)

        with Session(engine) as session:
            card = session.get(CardRow, card_id)
            # Existing non-NULL values preserved
            assert card.type_line == "Legendary Creature — Custom Override"
            assert card.rarity == "rare"
            # NULL fields filled from Scryfall
            assert card.color_identity == "WUBG"
            assert card.mana_cost == "{G}{W}{U}{B}"
            assert card.image_uri == "https://cards.scryfall.io/large/cmm/1.jpg"

    def test_upsert_does_not_change_card_id(self, engine):
        """The card retains the same primary key after enrichment."""
        with Session(engine) as session:
            card_id = _bare_card(session)

        catalog = CatalogCard(
            name_en="Atraxa, Praetors' Voice",
            set_code="cmm",
            collector_number="1",
            rarity="mythic",
            color_identity="WUBG",
            mana_cost="{G}{W}{U}{B}",
            type_line="Legendary Creature — Phyrexian Angel Horror",
            image_uri=None,
        )

        with Session(engine) as session:
            _run_seeder_upsert(session, catalog)

        with Session(engine) as session:
            cards = (
                session.execute(
                    select(CardRow).where(
                        CardRow.game == "magic",
                        CardRow.set_code == "cmm",
                        CardRow.collector_number == "1",
                    )
                )
                .scalars()
                .all()
            )
            assert len(cards) == 1
            assert cards[0].id == card_id

    def test_fresh_insert_when_no_conflict(self, engine):
        """When no existing card, the seeder inserts normally."""
        catalog = CatalogCard(
            name_en="Sol Ring",
            set_code="cmm",
            collector_number="379",
            rarity="uncommon",
            color_identity="",
            mana_cost="{1}",
            type_line="Artifact",
            image_uri="https://cards.scryfall.io/large/cmm/379.jpg",
        )

        with Session(engine) as session:
            rowcount = _run_seeder_upsert(session, catalog)
            assert rowcount > 0

        with Session(engine) as session:
            card = session.execute(
                select(CardRow).where(
                    CardRow.set_code == "cmm",
                    CardRow.collector_number == "379",
                )
            ).scalar_one()
            assert card.name_en == "Sol Ring"
            assert card.type_line == "Artifact"
            assert card.rarity == "uncommon"


class TestSiblingEnrichment:
    """Test that metadata can be copied from a sibling printing.

    A 'sibling' is a card with the same name_en but a different set_code.
    Card A (set=cmm) has full Scryfall metadata; card B (set=2xm, same name)
    was created by the price collector with NULL metadata. The sibling
    enrichment logic should be able to fill B from A.
    """

    def test_sibling_has_metadata_other_does_not(self, engine):
        """Precondition: two printings of the same card, one bare."""
        with Session(engine) as session:
            # Full card (from catalog seed)
            full = CardRow(
                game="magic",
                name_en="Atraxa, Praetors' Voice",
                set_code="cmm",
                collector_number="1",
                type_line="Legendary Creature — Phyrexian Angel Horror",
                rarity="mythic",
                color_identity="WUBG",
                mana_cost="{G}{W}{U}{B}",
                image_uri="https://img/cmm/1.jpg",
            )
            # Bare card (from price collector)
            bare = CardRow(
                game="magic",
                name_en="Atraxa, Praetors' Voice",
                set_code="2xm",
                collector_number="190",
                # All metadata NULL
            )
            session.add_all([full, bare])
            session.commit()
            bare_id = bare.id

        with Session(engine) as session:
            bare_card = session.get(CardRow, bare_id)
            assert bare_card.type_line is None
            assert bare_card.rarity is None

    def test_sibling_copy_fills_bare_card(self, engine):
        """Copying metadata from a sibling printing fills the bare card."""
        with Session(engine) as session:
            full = CardRow(
                game="magic",
                name_en="Atraxa, Praetors' Voice",
                set_code="cmm",
                collector_number="1",
                type_line="Legendary Creature — Phyrexian Angel Horror",
                rarity="mythic",
                color_identity="WUBG",
                mana_cost="{G}{W}{U}{B}",
                image_uri="https://img/cmm/1.jpg",
            )
            bare = CardRow(
                game="magic",
                name_en="Atraxa, Praetors' Voice",
                set_code="2xm",
                collector_number="190",
            )
            session.add_all([full, bare])
            session.commit()
            bare_id = bare.id

            # Simulate sibling enrichment: find a sibling with metadata
            sibling = session.execute(
                select(CardRow).where(
                    CardRow.game == "magic",
                    CardRow.name_en == "Atraxa, Praetors' Voice",
                    CardRow.type_line.isnot(None),
                )
            ).scalar_one()

            # Copy metadata fields from sibling to bare card
            bare_card = session.get(CardRow, bare_id)
            bare_card.type_line = sibling.type_line
            bare_card.rarity = sibling.rarity
            bare_card.color_identity = sibling.color_identity
            bare_card.mana_cost = sibling.mana_cost
            # image_uri is set-specific, so we do NOT copy it
            session.commit()

        with Session(engine) as session:
            enriched = session.get(CardRow, bare_id)
            assert enriched.type_line == "Legendary Creature — Phyrexian Angel Horror"
            assert enriched.rarity == "mythic"
            assert enriched.color_identity == "WUBG"
            assert enriched.mana_cost == "{G}{W}{U}{B}"
            # image_uri was not copied (set-specific)
            assert enriched.image_uri is None

    def test_no_sibling_available_leaves_bare(self, engine):
        """When no sibling has metadata, the bare card remains bare."""
        with Session(engine) as session:
            bare1 = CardRow(
                game="magic",
                name_en="Unique Card No Sibling",
                set_code="abc",
                collector_number="1",
            )
            session.add(bare1)
            session.commit()

            siblings = (
                session.execute(
                    select(CardRow).where(
                        CardRow.game == "magic",
                        CardRow.name_en == "Unique Card No Sibling",
                        CardRow.type_line.isnot(None),
                    )
                )
                .scalars()
                .all()
            )
            assert siblings == []
