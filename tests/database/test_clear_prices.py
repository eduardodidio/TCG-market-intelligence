"""Tests for clear_prices_by_source in src.database.cleanup."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from pathlib import Path
from unittest.mock import patch

import pytest
from click.testing import CliRunner
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from src.database.cleanup import PROTECTED_SOURCES, clear_prices_by_source
from src.database.models import (
    PriceObservationRow,
    ScanRunRow,
)
from src.database.repository import Repository


@pytest.fixture()
def repo(tmp_path):
    """Create a Repository backed by a temp SQLite DB."""
    db_path = tmp_path / "test.db"
    db_url = f"sqlite:///{db_path}"
    return Repository(db_url=db_url)


@pytest.fixture()
def seeded_repo(repo):
    """Seed repo with price observations from multiple sources + a scan_run."""
    engine = repo.engine
    with Session(engine) as session:
        # MYP observations
        session.add_all(
            [
                PriceObservationRow(
                    source="myp",
                    external_id="ext1",
                    observed_at=date(2026, 8, 10),
                    median_price=Decimal("5.50"),
                    currency="BRL",
                ),
                PriceObservationRow(
                    source="myp",
                    external_id="ext1",
                    observed_at=date(2026, 8, 11),
                    median_price=Decimal("6.00"),
                    currency="BRL",
                ),
                PriceObservationRow(
                    source="myp",
                    external_id="ext2",
                    observed_at=date(2026, 8, 10),
                    median_price=Decimal("3.00"),
                    currency="BRL",
                ),
            ]
        )
        # jsonld_snapshot observations
        session.add_all(
            [
                PriceObservationRow(
                    source="jsonld_snapshot",
                    external_id="ext1",
                    observed_at=date(2026, 8, 12),
                    median_price=Decimal("5.75"),
                    currency="BRL",
                ),
            ]
        )
        # Liga observations (protected)
        session.add_all(
            [
                PriceObservationRow(
                    source="liga",
                    external_id="ext1",
                    observed_at=date(2026, 8, 13),
                    median_price=Decimal("7.00"),
                    currency="BRL",
                ),
            ]
        )
        # Manual observations (protected)
        session.add_all(
            [
                PriceObservationRow(
                    source="manual",
                    external_id="manual_ext1",
                    observed_at=date(2026, 8, 14),
                    median_price=Decimal("10.00"),
                    currency="BRL",
                ),
            ]
        )
        # A scan_run for audit trail
        session.add(
            ScanRunRow(
                scan_type="collection",
                status="completed",
                cards_total=5,
                cards_processed=5,
            )
        )
        session.commit()
    return repo


class TestClearPricesDryRun:
    def test_returns_correct_count(self, seeded_repo):
        """Dry-run should return count of matching rows without deleting."""
        db_url = str(seeded_repo.engine.url)
        result = clear_prices_by_source(db_url, "myp", dry_run=True)

        assert result.dry_run is True
        assert result.deleted == 3
        assert result.backup_path is None

    def test_does_not_mutate_database(self, seeded_repo):
        """After dry-run, row counts must be unchanged."""
        db_url = str(seeded_repo.engine.url)
        clear_prices_by_source(db_url, "myp", dry_run=True)

        with Session(seeded_repo.engine) as session:
            total = session.execute(select(func.count()).select_from(PriceObservationRow)).scalar()
            assert total == 6  # all 6 rows intact

    def test_zero_count_for_nonexistent_source(self, seeded_repo):
        """Dry-run with a source that has no rows should return 0."""
        db_url = str(seeded_repo.engine.url)
        result = clear_prices_by_source(db_url, "nonexistent", dry_run=True)

        assert result.deleted == 0


class TestClearPricesActualDelete:
    def test_deletes_correct_rows(self, seeded_repo):
        """Actual delete should remove only rows matching the source."""
        db_url = str(seeded_repo.engine.url)
        result = clear_prices_by_source(db_url, "myp", dry_run=False, skip_backup=True)

        assert result.dry_run is False
        assert result.deleted == 3

        with Session(seeded_repo.engine) as session:
            myp_count = session.execute(
                select(func.count())
                .select_from(PriceObservationRow)
                .where(PriceObservationRow.source == "myp")
            ).scalar()
            assert myp_count == 0

            # Other sources untouched
            remaining = session.execute(
                select(func.count()).select_from(PriceObservationRow)
            ).scalar()
            assert remaining == 3  # 1 jsonld + 1 liga + 1 manual

    def test_deletes_jsonld_snapshot(self, seeded_repo):
        """Can delete jsonld_snapshot source."""
        db_url = str(seeded_repo.engine.url)
        result = clear_prices_by_source(db_url, "jsonld_snapshot", dry_run=False, skip_backup=True)

        assert result.deleted == 1

        with Session(seeded_repo.engine) as session:
            remaining = session.execute(
                select(func.count()).select_from(PriceObservationRow)
            ).scalar()
            assert remaining == 5  # 3 myp + 1 liga + 1 manual


class TestProtectedSources:
    def test_refuses_liga(self, seeded_repo):
        """Must refuse to clear source='liga'."""
        db_url = str(seeded_repo.engine.url)
        with pytest.raises(ValueError, match="Refusing to clear protected source 'liga'"):
            clear_prices_by_source(db_url, "liga", dry_run=False, skip_backup=True)

    def test_refuses_manual(self, seeded_repo):
        """Must refuse to clear source='manual'."""
        db_url = str(seeded_repo.engine.url)
        with pytest.raises(ValueError, match="Refusing to clear protected source 'manual'"):
            clear_prices_by_source(db_url, "manual", dry_run=False, skip_backup=True)

    def test_refuses_even_dry_run(self, seeded_repo):
        """Protected source check applies even in dry-run mode."""
        db_url = str(seeded_repo.engine.url)
        with pytest.raises(ValueError, match="protected source"):
            clear_prices_by_source(db_url, "liga", dry_run=True)

    def test_protected_sources_set(self):
        """PROTECTED_SOURCES must contain liga and manual."""
        assert "liga" in PROTECTED_SOURCES
        assert "manual" in PROTECTED_SOURCES


class TestBackup:
    def test_backup_created_before_deletion(self, seeded_repo, tmp_path):
        """Backup should be called before actual deletion."""
        db_url = str(seeded_repo.engine.url)

        with patch("src.database.cleanup.backup_database") as mock_backup:
            mock_backup.return_value = Path(tmp_path / "fake_backup.db")
            result = clear_prices_by_source(db_url, "myp", dry_run=False, skip_backup=False)

        mock_backup.assert_called_once()
        assert result.backup_path is not None

    def test_skip_backup_flag(self, seeded_repo):
        """With skip_backup=True, no backup should be created."""
        db_url = str(seeded_repo.engine.url)

        with patch("src.database.cleanup.backup_database") as mock_backup:
            result = clear_prices_by_source(db_url, "myp", dry_run=False, skip_backup=True)

        mock_backup.assert_not_called()
        assert result.backup_path is None


class TestScanRunsUntouched:
    def test_scan_runs_preserved(self, seeded_repo):
        """scan_runs table must not be affected by clear_prices_by_source."""
        db_url = str(seeded_repo.engine.url)

        with Session(seeded_repo.engine) as session:
            before = session.execute(select(func.count()).select_from(ScanRunRow)).scalar()

        clear_prices_by_source(db_url, "myp", dry_run=False, skip_backup=True)

        with Session(seeded_repo.engine) as session:
            after = session.execute(select(func.count()).select_from(ScanRunRow)).scalar()

        assert after == before
        assert after == 1


class TestCLI:
    def test_without_confirm_runs_dry_run(self, seeded_repo):
        """CLI without --confirm should run dry-run and show count."""
        from src.cli.main import cli

        runner = CliRunner()
        db_url = str(seeded_repo.engine.url)
        result = runner.invoke(cli, ["db-clear-prices", "--db", db_url, "--source", "myp"])

        assert result.exit_code == 0
        assert "DRY RUN" in result.output
        assert "3" in result.output
        assert "--confirm" in result.output

        # Data should still be there
        with Session(seeded_repo.engine) as session:
            total = session.execute(select(func.count()).select_from(PriceObservationRow)).scalar()
            assert total == 6

    def test_with_confirm_deletes(self, seeded_repo):
        """CLI with --confirm should actually delete."""
        from src.cli.main import cli

        runner = CliRunner()
        db_url = str(seeded_repo.engine.url)
        result = runner.invoke(
            cli,
            ["db-clear-prices", "--db", db_url, "--source", "myp", "--confirm", "--skip-backup"],
        )

        assert result.exit_code == 0
        assert "Deleted 3" in result.output

        with Session(seeded_repo.engine) as session:
            myp_count = session.execute(
                select(func.count())
                .select_from(PriceObservationRow)
                .where(PriceObservationRow.source == "myp")
            ).scalar()
            assert myp_count == 0

    def test_protected_source_error(self, seeded_repo):
        """CLI with protected source should exit with error."""
        from src.cli.main import cli

        runner = CliRunner()
        db_url = str(seeded_repo.engine.url)
        result = runner.invoke(
            cli,
            ["db-clear-prices", "--db", db_url, "--source", "liga", "--confirm"],
        )

        assert result.exit_code == 1
        assert "protected source" in result.output or "protected source" in (
            result.output + (result.output or "")
        )
