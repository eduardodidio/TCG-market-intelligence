"""Tests for F103-T01: new card catalog columns."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import Session

from src.database.models import Base, CardRow
from src.database.repository import Repository


class TestCardRowNewColumns:
    """Verify CardRow model has the 5 new catalog columns."""

    def test_cards_table_has_new_columns(self) -> None:
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(engine)

        inspector = inspect(engine)
        columns = {col["name"] for col in inspector.get_columns("cards")}
        expected_new = {"rarity", "color_identity", "mana_cost", "type_line", "image_uri"}
        assert expected_new.issubset(columns)

    def test_cards_table_has_all_expected_columns(self) -> None:
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(engine)

        inspector = inspect(engine)
        columns = {col["name"] for col in inspector.get_columns("cards")}
        expected = {
            "id",
            "game",
            "name_en",
            "name_pt",
            "set_code",
            "collector_number",
            "rarity",
            "color_identity",
            "mana_cost",
            "type_line",
            "image_uri",
            "created_at",
            "updated_at",
        }
        assert expected == columns

    def test_cards_table_has_rarity_index(self) -> None:
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(engine)

        inspector = inspect(engine)
        indexes = inspector.get_indexes("cards")
        index_names = {idx["name"] for idx in indexes}
        assert "ix_card_rarity" in index_names

    def test_cards_table_has_color_identity_index(self) -> None:
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(engine)

        inspector = inspect(engine)
        indexes = inspector.get_indexes("cards")
        index_names = {idx["name"] for idx in indexes}
        assert "ix_card_color_identity" in index_names


class TestCardRowNewColumnsInsert:
    """Insert cards with new columns and read back."""

    def test_insert_card_with_all_new_fields(self) -> None:
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(engine)

        now = datetime(2026, 9, 4, 12, 0, 0)
        row = CardRow(
            game="magic",
            name_en="Snapcaster Mage",
            name_pt="Mago Taumaturgo",
            set_code="ISD",
            collector_number="78",
            rarity="R",
            color_identity="U",
            mana_cost="{1}{U}",
            type_line="Creature — Human Wizard",
            image_uri="https://cards.scryfall.io/normal/front/7/e/7e41765e.jpg",
            created_at=now,
            updated_at=now,
        )

        with Session(engine) as session:
            session.add(row)
            session.commit()
            session.refresh(row)

            assert row.id is not None
            assert row.rarity == "R"
            assert row.color_identity == "U"
            assert row.mana_cost == "{1}{U}"
            assert row.type_line == "Creature — Human Wizard"
            assert row.image_uri == "https://cards.scryfall.io/normal/front/7/e/7e41765e.jpg"

    def test_insert_card_with_null_new_fields(self) -> None:
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(engine)

        row = CardRow(
            game="magic",
            name_en="Unknown Card",
        )

        with Session(engine) as session:
            session.add(row)
            session.commit()
            session.refresh(row)

            assert row.id is not None
            assert row.rarity is None
            assert row.color_identity is None
            assert row.mana_cost is None
            assert row.type_line is None
            assert row.image_uri is None

    def test_insert_colorless_card(self) -> None:
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(engine)

        row = CardRow(
            game="magic",
            name_en="Sol Ring",
            set_code="C21",
            collector_number="263",
            rarity="U",
            color_identity="",
            mana_cost="{1}",
            type_line="Artifact",
        )

        with Session(engine) as session:
            session.add(row)
            session.commit()
            session.refresh(row)

            assert row.color_identity == ""
            assert row.rarity == "U"

    def test_insert_multicolor_card(self) -> None:
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(engine)

        row = CardRow(
            game="magic",
            name_en="Omnath, Locus of Creation",
            rarity="M",
            color_identity="WURG",
            mana_cost="{R}{G}{W}{U}",
            type_line="Legendary Creature — Elemental",
        )

        with Session(engine) as session:
            session.add(row)
            session.commit()
            session.refresh(row)

            assert row.rarity == "M"
            assert row.color_identity == "WURG"


class TestCardMigrationIdempotent:
    """Migration via _ensure_columns is idempotent."""

    def test_ensure_columns_idempotent(self) -> None:
        """Running _ensure_columns twice does not raise errors."""
        repo = Repository(db_url="sqlite:///:memory:")
        # _ensure_columns already ran in __init__, call it again
        repo._ensure_columns()

        # Verify columns exist
        inspector = inspect(repo.engine)
        columns = {col["name"] for col in inspector.get_columns("cards")}
        assert "rarity" in columns
        assert "color_identity" in columns
        assert "mana_cost" in columns
        assert "type_line" in columns
        assert "image_uri" in columns

    def test_migration_adds_columns_to_existing_table(self) -> None:
        """Simulate pre-existing cards table without new columns."""
        engine = create_engine("sqlite:///:memory:")
        # Create a minimal cards table without new columns
        with engine.begin() as conn:
            conn.execute(
                text(
                    """CREATE TABLE cards (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        game VARCHAR(50) NOT NULL,
                        name_en VARCHAR(500) NOT NULL,
                        name_pt VARCHAR(500),
                        set_code VARCHAR(20),
                        collector_number VARCHAR(20),
                        created_at DATETIME,
                        updated_at DATETIME
                    )"""
                )
            )

        # Now create repo pointing at this engine (it will run _ensure_columns)
        repo = Repository.__new__(Repository)
        repo.engine = engine
        repo._setup_sqlite_pragmas()
        repo._ensure_columns()

        inspector = inspect(engine)
        columns = {col["name"] for col in inspector.get_columns("cards")}
        assert "rarity" in columns
        assert "color_identity" in columns
        assert "mana_cost" in columns
        assert "type_line" in columns
        assert "image_uri" in columns

    def test_migration_creates_indexes(self) -> None:
        """Verify indexes are created during migration."""
        repo = Repository(db_url="sqlite:///:memory:")

        inspector = inspect(repo.engine)
        indexes = inspector.get_indexes("cards")
        index_names = {idx["name"] for idx in indexes}
        assert "ix_card_rarity" in index_names
        assert "ix_card_color_identity" in index_names


class TestExistingCardBehaviorUnchanged:
    """Existing card fields still work correctly after schema change."""

    def test_existing_fields_preserved(self) -> None:
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(engine)

        now = datetime(2026, 9, 4, 12, 0, 0)
        row = CardRow(
            game="magic",
            name_en="Lightning Bolt",
            name_pt="Relampago",
            set_code="M10",
            collector_number="146",
            created_at=now,
            updated_at=now,
        )

        with Session(engine) as session:
            session.add(row)
            session.commit()
            session.refresh(row)

            assert row.game == "magic"
            assert row.name_en == "Lightning Bolt"
            assert row.name_pt == "Relampago"
            assert row.set_code == "M10"
            assert row.collector_number == "146"
            assert row.created_at == now
            assert row.updated_at == now
            # New columns default to None
            assert row.rarity is None
            assert row.color_identity is None
