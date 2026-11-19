"""Tests for CLI catalog command group (seed, scan, stats)."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

from click.testing import CliRunner

from src.cli.main import cli

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_seed_result(**overrides):
    """Build a mock SeedResult."""
    from src.catalog.seeder import SeedResult

    defaults = dict(
        cards_inserted=1000,
        cards_updated=0,
        cards_skipped=50,
        source_cards_created=1000,
        errors=[],
        elapsed_seconds=12.5,
    )
    defaults.update(overrides)
    return SeedResult(**defaults)


# ---------------------------------------------------------------------------
# catalog seed
# ---------------------------------------------------------------------------


class TestCatalogSeed:
    def test_seed_downloads_and_seeds(self, tmp_path):
        """catalog seed downloads bulk data and calls seed_catalog."""
        runner = CliRunner()
        bulk_file = tmp_path / "scryfall-default-cards-2026-09-04.json"
        bulk_file.write_text("[]")
        result_obj = _make_seed_result()

        with (
            patch("src.catalog.scryfall.download_bulk_data", return_value=bulk_file) as mock_dl,
            patch("src.catalog.seeder.seed_catalog", return_value=result_obj) as mock_seed,
        ):
            result = runner.invoke(cli, ["catalog", "seed", "--db", "sqlite:///test.db"])

        assert result.exit_code == 0, result.output
        mock_dl.assert_called_once()
        mock_seed.assert_called_once_with(
            db_url="sqlite:///test.db", bulk_path=bulk_file, batch_size=500
        )
        assert "Cards inserted:" in result.output
        assert "1,000" in result.output

    def test_seed_skip_download_uses_existing(self, tmp_path):
        """catalog seed --skip-download finds the most recent bulk file."""
        runner = CliRunner()
        result_obj = _make_seed_result()

        # Create a fake bulk file in data/catalog
        with patch("src.catalog.seeder.seed_catalog", return_value=result_obj) as mock_seed:
            with runner.isolated_filesystem(temp_dir=tmp_path):
                catalog_dir = Path("data/catalog")
                catalog_dir.mkdir(parents=True)
                bulk_file = catalog_dir / "scryfall-default-cards-2026-09-01.json"
                bulk_file.write_text("[]")

                result = runner.invoke(
                    cli,
                    ["catalog", "seed", "--skip-download", "--db", "sqlite:///test.db"],
                )

        assert result.exit_code == 0, result.output
        assert "Using existing file" in result.output
        mock_seed.assert_called_once()

    def test_seed_skip_download_no_files(self, tmp_path):
        """catalog seed --skip-download with no files exits with error."""
        runner = CliRunner()

        with runner.isolated_filesystem(temp_dir=tmp_path):
            Path("data/catalog").mkdir(parents=True)
            result = runner.invoke(
                cli,
                ["catalog", "seed", "--skip-download", "--db", "sqlite:///test.db"],
            )

        assert result.exit_code != 0
        assert "No bulk data files found" in result.output

    def test_seed_dry_run_counts_without_inserting(self, tmp_path):
        """catalog seed --dry-run counts cards but does not call seed_catalog."""
        runner = CliRunner()
        bulk_file = tmp_path / "scryfall-default-cards-2026-09-04.json"
        bulk_file.write_text("[]")

        # parse_bulk_cards returns an iterator of 3 items
        mock_cards = [MagicMock(), MagicMock(), MagicMock()]

        with (
            patch("src.catalog.scryfall.download_bulk_data", return_value=bulk_file),
            patch("src.catalog.scryfall.parse_bulk_cards", return_value=iter(mock_cards)),
            patch("src.catalog.seeder.seed_catalog") as mock_seed,
        ):
            result = runner.invoke(
                cli, ["catalog", "seed", "--dry-run", "--db", "sqlite:///test.db"]
            )

        assert result.exit_code == 0, result.output
        assert "DRY RUN" in result.output
        assert "3" in result.output
        mock_seed.assert_not_called()

    def test_seed_custom_batch_size(self, tmp_path):
        """catalog seed --batch-size passes the value to seed_catalog."""
        runner = CliRunner()
        bulk_file = tmp_path / "scryfall-default-cards-2026-09-04.json"
        bulk_file.write_text("[]")
        result_obj = _make_seed_result()

        with (
            patch("src.catalog.scryfall.download_bulk_data", return_value=bulk_file),
            patch("src.catalog.seeder.seed_catalog", return_value=result_obj) as mock_seed,
        ):
            result = runner.invoke(
                cli,
                ["catalog", "seed", "--batch-size", "100", "--db", "sqlite:///test.db"],
            )

        assert result.exit_code == 0, result.output
        mock_seed.assert_called_once_with(
            db_url="sqlite:///test.db", bulk_path=bulk_file, batch_size=100
        )

    def test_seed_summary_shows_errors(self, tmp_path):
        """catalog seed displays error count in summary."""
        runner = CliRunner()
        bulk_file = tmp_path / "scryfall-default-cards-2026-09-04.json"
        bulk_file.write_text("[]")
        result_obj = _make_seed_result(errors=["batch error 1", "batch error 2"])

        with (
            patch("src.catalog.scryfall.download_bulk_data", return_value=bulk_file),
            patch("src.catalog.seeder.seed_catalog", return_value=result_obj),
        ):
            result = runner.invoke(cli, ["catalog", "seed", "--db", "sqlite:///test.db"])

        assert result.exit_code == 0, result.output
        assert "Errors:                  2" in result.output


# ---------------------------------------------------------------------------
# catalog stats
# ---------------------------------------------------------------------------


class TestCatalogStats:
    def test_stats_displays_counts(self, tmp_path):
        """catalog stats queries DB and displays formatted output."""
        runner = CliRunner()

        from datetime import date

        from sqlalchemy import create_engine
        from sqlalchemy.orm import Session

        from src.database.models import Base, CardRow, PriceObservationRow, SourceCardRow

        db_path = tmp_path / "test_stats.db"
        db_url = f"sqlite:///{db_path}"
        engine = create_engine(db_url)
        Base.metadata.create_all(engine)

        with Session(engine) as session:
            for i in range(5):
                session.add(
                    CardRow(
                        game="magic",
                        name_en=f"Card {i}",
                        set_code="mh3",
                        collector_number=str(i),
                        rarity="R",
                        color_identity="W",
                        mana_cost="{W}",
                        type_line="Creature",
                    )
                )
            for i in range(3):
                session.add(
                    CardRow(
                        game="magic",
                        name_en=f"Card Neo {i}",
                        set_code="neo",
                        collector_number=str(i),
                        rarity="C",
                        color_identity="U",
                        mana_cost="{U}",
                        type_line="Instant",
                    )
                )
            session.commit()

            # Catalog source_cards use "myp_catalog_{set}_{num}" external_id
            for i in range(2):
                session.add(
                    SourceCardRow(
                        source="myp",
                        external_id=f"myp_catalog_mh3_{i}",
                        card_id=i + 1,
                        url=f"https://myp.example.com/card/{i}",
                        name_en=f"Card {i}",
                        set_code="mh3",
                        collector_number=str(i),
                    )
                )
            # MYP sweep source_cards use "myp_{card_id}" external_id
            for i in range(2):
                session.add(
                    SourceCardRow(
                        source="myp",
                        external_id=f"myp_{i + 1}",
                        card_id=i + 1,
                        url=f"https://myp.example.com/card/{i}",
                        name_en=f"Card {i}",
                        set_code="mh3",
                        collector_number=str(i),
                    )
                )
            session.commit()

            # Price observations reference the sweep external_id, not catalog
            for i in range(2):
                session.add(
                    PriceObservationRow(
                        source="myp",
                        external_id=f"myp_{i + 1}",
                        observed_at=date.today(),
                        median_price=10.0 + i,
                        currency="BRL",
                    )
                )
            session.commit()

        engine.dispose()

        result = runner.invoke(cli, ["catalog", "stats", "--db", db_url])

        assert result.exit_code == 0, result.output
        assert "CATALOG STATISTICS" in result.output
        assert "Total catalog cards:" in result.output
        assert "8" in result.output  # 5 + 3
        assert "Cards with price:" in result.output
        assert "mh3" in result.output
        assert "neo" in result.output

    def test_stats_cards_with_price_uses_card_id_join(self, tmp_path):
        """Cards with price count must work when price observation external_id
        differs from catalog source_card external_id (the real-world pattern).

        Catalog source_cards: external_id = "myp_catalog_{set}_{num}"
        Sweep source_cards:   external_id = "myp_{card_id}"
        Price observations:   external_id = "myp_{card_id}"

        The query must link through card_id, not external_id string matching.
        """
        runner = CliRunner()

        from datetime import date

        from sqlalchemy import create_engine
        from sqlalchemy.orm import Session

        from src.database.models import Base, CardRow, PriceObservationRow, SourceCardRow

        db_path = tmp_path / "test_stats_price_join.db"
        db_url = f"sqlite:///{db_path}"
        engine = create_engine(db_url)
        Base.metadata.create_all(engine)

        with Session(engine) as session:
            # 3 catalog cards
            for i in range(3):
                session.add(
                    CardRow(
                        game="magic",
                        name_en=f"Card {i}",
                        set_code="mh3",
                        collector_number=str(i),
                    )
                )
            session.commit()

            # Catalog source_cards for all 3
            for i in range(3):
                session.add(
                    SourceCardRow(
                        source="myp",
                        external_id=f"myp_catalog_mh3_{i}",
                        card_id=i + 1,
                        url=f"https://myp.example.com/card/{i}",
                        name_en=f"Card {i}",
                        set_code="mh3",
                        collector_number=str(i),
                    )
                )
            # Sweep source_cards for only 2 of 3 (card_id 1 and 2)
            for i in range(2):
                session.add(
                    SourceCardRow(
                        source="myp",
                        external_id=f"myp_{i + 1}",
                        card_id=i + 1,
                        url=f"https://myp.example.com/card/{i}",
                        name_en=f"Card {i}",
                        set_code="mh3",
                        collector_number=str(i),
                    )
                )
            session.commit()

            # Price observations only for card_id 1 and 2 (via sweep ext_id)
            for i in range(2):
                session.add(
                    PriceObservationRow(
                        source="myp",
                        external_id=f"myp_{i + 1}",
                        observed_at=date.today(),
                        median_price=10.0 + i,
                        currency="BRL",
                    )
                )
            session.commit()

        engine.dispose()

        result = runner.invoke(cli, ["catalog", "stats", "--db", db_url])

        assert result.exit_code == 0, result.output
        # Exactly 2 of 3 cards have prices
        assert "Cards with price:        2" in result.output
        assert "Cards without price:     1" in result.output

    def test_stats_empty_database(self, tmp_path):
        """catalog stats on empty DB shows zeros."""
        runner = CliRunner()

        from sqlalchemy import create_engine

        from src.database.models import Base

        db_path = tmp_path / "test_stats_empty.db"
        db_url = f"sqlite:///{db_path}"
        engine = create_engine(db_url)
        Base.metadata.create_all(engine)
        engine.dispose()

        result = runner.invoke(cli, ["catalog", "stats", "--db", db_url])

        assert result.exit_code == 0, result.output
        assert "Total catalog cards:     0" in result.output
        assert "Cards with price:        0" in result.output
        assert "Catalog seeded: no" in result.output
