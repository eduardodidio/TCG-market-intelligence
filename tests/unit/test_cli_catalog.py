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


def _make_sweep_result(**overrides):
    """Build a mock LigaSweepResult."""
    from src.collectors.liga_sweep import LigaSweepResult

    defaults = dict(
        total_eligible=200,
        total_processed=180,
        prices_found=150,
        prices_not_found=30,
        errors=0,
        batches_completed=9,
        dry_run=False,
    )
    defaults.update(overrides)
    return LigaSweepResult(**defaults)


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
# catalog scan
# ---------------------------------------------------------------------------


class TestCatalogScan:
    def test_scan_requires_set_option(self):
        """catalog scan without --set shows an error."""
        runner = CliRunner()
        result = runner.invoke(cli, ["catalog", "scan", "--db", "sqlite:///test.db"])
        assert result.exit_code != 0
        assert "Missing option" in result.output or "required" in result.output.lower()

    def test_scan_calls_liga_sweep(self):
        """catalog scan --set passes all options to run_liga_sweep."""
        runner = CliRunner()
        sweep_result = _make_sweep_result()

        with patch("src.cli.main.asyncio.run", return_value=sweep_result) as mock_run:
            result = runner.invoke(
                cli,
                [
                    "catalog",
                    "scan",
                    "--db",
                    "sqlite:///test.db",
                    "--set",
                    "mh3",
                    "--limit",
                    "10",
                    "--delay",
                    "2.0",
                    "--batch-size",
                    "5",
                    "--batch-pause",
                    "30",
                    "--max-age-days",
                    "3",
                ],
            )

        assert result.exit_code == 0, result.output
        mock_run.assert_called_once()
        # Verify summary was printed
        assert "LIGA SWEEP SUMMARY" in result.output

    def test_scan_dry_run(self):
        """catalog scan --dry-run passes dry_run=True and prints DRY RUN."""
        runner = CliRunner()
        sweep_result = _make_sweep_result(dry_run=True)

        with patch("src.cli.main.asyncio.run", return_value=sweep_result):
            result = runner.invoke(
                cli,
                [
                    "catalog",
                    "scan",
                    "--db",
                    "sqlite:///test.db",
                    "--set",
                    "mh3",
                    "--dry-run",
                ],
            )

        assert result.exit_code == 0, result.output
        assert "DRY RUN" in result.output

    def test_scan_default_options(self):
        """catalog scan uses correct defaults for delay, batch-size, etc."""
        runner = CliRunner()
        sweep_result = _make_sweep_result()

        with patch("src.cli.main.asyncio.run", return_value=sweep_result) as mock_run:
            result = runner.invoke(
                cli,
                ["catalog", "scan", "--db", "sqlite:///test.db", "--set", "neo"],
            )

        assert result.exit_code == 0, result.output
        assert mock_run.called


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

            for i in range(2):
                session.add(
                    SourceCardRow(
                        source="liga",
                        external_id=f"liga_catalog_mh3_{i}",
                        card_id=i + 1,
                        url=f"https://liga.example.com/card/{i}",
                        name_en=f"Card {i}",
                        set_code="mh3",
                        collector_number=str(i),
                    )
                )
            session.commit()

            for i in range(2):
                session.add(
                    PriceObservationRow(
                        source="liga",
                        external_id=f"liga_catalog_mh3_{i}",
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
        assert "Cards with Liga price:" in result.output
        assert "mh3" in result.output
        assert "neo" in result.output

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
        assert "Cards with Liga price:   0" in result.output
        assert "Catalog seeded: no" in result.output
