"""Tests for the ``catalog enrich`` CLI command (F171-T02)."""

from __future__ import annotations

from click.testing import CliRunner
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from src.cli.main import cli
from src.database.models import Base, CardRow


def _seed_db(db_url: str, cards: list[dict]) -> None:
    """Insert card rows directly for test setup."""
    engine = create_engine(db_url, echo=False)
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        for card_data in cards:
            session.add(CardRow(**card_data))
        session.commit()
    engine.dispose()


def _get_card(db_url: str, set_code: str, collector_number: str) -> CardRow | None:
    """Fetch a single card by set_code + collector_number."""
    engine = create_engine(db_url, echo=False)
    with Session(engine) as session:
        stmt = select(CardRow).where(
            CardRow.set_code == set_code,
            CardRow.collector_number == collector_number,
        )
        card = session.execute(stmt).scalar_one_or_none()
        if card:
            # Detach from session by reading all fields
            result = CardRow(
                id=card.id,
                game=card.game,
                name_en=card.name_en,
                name_pt=card.name_pt,
                set_code=card.set_code,
                collector_number=card.collector_number,
                type_line=card.type_line,
                rarity=card.rarity,
                color_identity=card.color_identity,
                mana_cost=card.mana_cost,
                image_uri=card.image_uri,
            )
    engine.dispose()
    return result


class TestCatalogEnrich:
    """Test the ``catalog enrich`` CLI command."""

    def test_enrich_copies_metadata_from_sibling(self, tmp_path):
        """Cards missing metadata get enriched from a sibling with same name_en."""
        db_url = f"sqlite:///{tmp_path / 'test.db'}"

        _seed_db(
            db_url,
            [
                # Donor: has full metadata (seeded by catalog)
                {
                    "game": "magic",
                    "name_en": "Lightning Bolt",
                    "set_code": "m3c",
                    "collector_number": "1",
                    "type_line": "Instant",
                    "rarity": "C",
                    "color_identity": "R",
                    "mana_cost": "{R}",
                    "image_uri": "https://img.scryfall.com/bolt.jpg",
                },
                # Target 1: missing metadata (created by price collector)
                {
                    "game": "magic",
                    "name_en": "Lightning Bolt",
                    "set_code": "sta",
                    "collector_number": "42",
                },
                # Target 2: also missing metadata
                {
                    "game": "magic",
                    "name_en": "Lightning Bolt",
                    "set_code": "2xm",
                    "collector_number": "99",
                },
            ],
        )

        runner = CliRunner()
        result = runner.invoke(cli, ["catalog", "enrich", "--db", db_url])

        assert result.exit_code == 0
        assert "Enriched from siblings:" in result.output
        assert "2" in result.output  # 2 cards enriched

        # Verify the cards got enriched
        card1 = _get_card(db_url, "sta", "42")
        assert card1 is not None
        assert card1.type_line == "Instant"
        assert card1.rarity == "C"
        assert card1.color_identity == "R"
        assert card1.mana_cost == "{R}"
        assert card1.image_uri == "https://img.scryfall.com/bolt.jpg"

        card2 = _get_card(db_url, "2xm", "99")
        assert card2 is not None
        assert card2.type_line == "Instant"

    def test_dry_run_does_not_modify(self, tmp_path):
        """--dry-run reports counts but does not write to the database."""
        db_url = f"sqlite:///{tmp_path / 'test.db'}"

        _seed_db(
            db_url,
            [
                {
                    "game": "magic",
                    "name_en": "Sol Ring",
                    "set_code": "cmr",
                    "collector_number": "1",
                    "type_line": "Artifact",
                    "rarity": "U",
                    "color_identity": "",
                    "mana_cost": "{1}",
                },
                {
                    "game": "magic",
                    "name_en": "Sol Ring",
                    "set_code": "c21",
                    "collector_number": "5",
                },
            ],
        )

        runner = CliRunner()
        result = runner.invoke(cli, ["catalog", "enrich", "--db", db_url, "--dry-run"])

        assert result.exit_code == 0
        assert "DRY RUN" in result.output
        assert "1" in result.output  # 1 card missing

        # Card should still be NULL
        card = _get_card(db_url, "c21", "5")
        assert card is not None
        assert card.type_line is None

    def test_no_sibling_metadata_reports_still_missing(self, tmp_path):
        """Cards with no sibling that has metadata are reported as still-missing."""
        db_url = f"sqlite:///{tmp_path / 'test.db'}"

        _seed_db(
            db_url,
            [
                # Two printings of same card, both missing metadata
                {
                    "game": "magic",
                    "name_en": "Orphan Card",
                    "set_code": "xyz",
                    "collector_number": "1",
                },
                {
                    "game": "magic",
                    "name_en": "Orphan Card",
                    "set_code": "abc",
                    "collector_number": "2",
                },
            ],
        )

        runner = CliRunner()
        result = runner.invoke(cli, ["catalog", "enrich", "--db", db_url])

        assert result.exit_code == 0
        assert "Still missing (no donor):" in result.output
        assert "2" in result.output

        # Cards should still be NULL
        card = _get_card(db_url, "xyz", "1")
        assert card is not None
        assert card.type_line is None

    def test_empty_database(self, tmp_path):
        """Command runs without error on an empty database."""
        db_url = f"sqlite:///{tmp_path / 'test.db'}"

        engine = create_engine(db_url, echo=False)
        Base.metadata.create_all(engine)
        engine.dispose()

        runner = CliRunner()
        result = runner.invoke(cli, ["catalog", "enrich", "--db", db_url])

        assert result.exit_code == 0
        assert "0" in result.output
        assert "Nothing to do" in result.output

    def test_all_cards_have_metadata(self, tmp_path):
        """When no cards are missing metadata, the command reports nothing to do."""
        db_url = f"sqlite:///{tmp_path / 'test.db'}"

        _seed_db(
            db_url,
            [
                {
                    "game": "magic",
                    "name_en": "Lightning Bolt",
                    "set_code": "m3c",
                    "collector_number": "1",
                    "type_line": "Instant",
                    "rarity": "C",
                    "color_identity": "R",
                    "mana_cost": "{R}",
                },
            ],
        )

        runner = CliRunner()
        result = runner.invoke(cli, ["catalog", "enrich", "--db", db_url])

        assert result.exit_code == 0
        assert "Nothing to do" in result.output

    def test_mixed_enrichable_and_orphan(self, tmp_path):
        """Mix of enrichable cards and cards with no donor."""
        db_url = f"sqlite:///{tmp_path / 'test.db'}"

        _seed_db(
            db_url,
            [
                # Donor for Lightning Bolt
                {
                    "game": "magic",
                    "name_en": "Lightning Bolt",
                    "set_code": "m3c",
                    "collector_number": "1",
                    "type_line": "Instant",
                    "rarity": "C",
                    "color_identity": "R",
                    "mana_cost": "{R}",
                },
                # Missing Lightning Bolt (enrichable)
                {
                    "game": "magic",
                    "name_en": "Lightning Bolt",
                    "set_code": "sta",
                    "collector_number": "42",
                },
                # Missing Orphan (no donor)
                {
                    "game": "magic",
                    "name_en": "Unique Card",
                    "set_code": "xyz",
                    "collector_number": "99",
                },
            ],
        )

        runner = CliRunner()
        result = runner.invoke(cli, ["catalog", "enrich", "--db", db_url])

        assert result.exit_code == 0
        assert "Enriched from siblings:" in result.output

        # Lightning Bolt should be enriched
        bolt = _get_card(db_url, "sta", "42")
        assert bolt is not None
        assert bolt.type_line == "Instant"

        # Unique Card should still be NULL
        orphan = _get_card(db_url, "xyz", "99")
        assert orphan is not None
        assert orphan.type_line is None

    def test_partial_donor_metadata(self, tmp_path):
        """Donor with some NULL fields only copies non-NULL values."""
        db_url = f"sqlite:///{tmp_path / 'test.db'}"

        _seed_db(
            db_url,
            [
                # Donor: has type_line but no image_uri
                {
                    "game": "magic",
                    "name_en": "Partial Card",
                    "set_code": "aaa",
                    "collector_number": "1",
                    "type_line": "Creature — Human",
                    "rarity": "R",
                    # image_uri and mana_cost intentionally NULL
                },
                # Target: missing all metadata
                {
                    "game": "magic",
                    "name_en": "Partial Card",
                    "set_code": "bbb",
                    "collector_number": "2",
                },
            ],
        )

        runner = CliRunner()
        result = runner.invoke(cli, ["catalog", "enrich", "--db", db_url])

        assert result.exit_code == 0

        card = _get_card(db_url, "bbb", "2")
        assert card is not None
        assert card.type_line == "Creature — Human"
        assert card.rarity == "R"
        assert card.image_uri is None  # Donor didn't have it
        assert card.mana_cost is None  # Donor didn't have it
