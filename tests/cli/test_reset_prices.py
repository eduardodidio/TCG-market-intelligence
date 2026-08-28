"""CLI integration tests for the reset-prices command."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from pathlib import Path
from unittest.mock import patch

import pytest
from click.testing import CliRunner
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from src.database.models import PriceObservationRow
from src.database.repository import Repository


@pytest.fixture()
def repo(tmp_path):
    """Create a Repository backed by a temp SQLite DB."""
    db_path = tmp_path / "test.db"
    db_url = f"sqlite:///{db_path}"
    return Repository(db_url=db_url)


@pytest.fixture()
def seeded_repo(repo):
    """Seed repo with price observations from multiple sources."""
    with Session(repo.engine) as session:
        session.add_all(
            [
                PriceObservationRow(
                    source="liga",
                    external_id="ext1",
                    observed_at=date(2026, 8, 20),
                    median_price=Decimal("10.00"),
                    currency="BRL",
                ),
                PriceObservationRow(
                    source="liga",
                    external_id="ext2",
                    observed_at=date(2026, 8, 20),
                    median_price=Decimal("15.00"),
                    currency="BRL",
                ),
                PriceObservationRow(
                    source="myp",
                    external_id="ext1",
                    observed_at=date(2026, 8, 19),
                    median_price=Decimal("5.50"),
                    currency="BRL",
                ),
                PriceObservationRow(
                    source="manual",
                    external_id="manual_ext1",
                    observed_at=date(2026, 8, 21),
                    median_price=Decimal("20.00"),
                    currency="BRL",
                ),
            ]
        )
        session.commit()
    return repo


def _count(repo: Repository, source: str | None = None) -> int:
    with Session(repo.engine) as session:
        stmt = select(func.count()).select_from(PriceObservationRow)
        if source is not None:
            stmt = stmt.where(PriceObservationRow.source == source)
        return session.execute(stmt).scalar() or 0


class TestDryRun:
    def test_no_confirm_shows_count_and_exits(self, seeded_repo):
        """Without --confirm, shows row count and does not delete."""
        from src.cli.main import cli

        runner = CliRunner()
        db_url = str(seeded_repo.engine.url)
        result = runner.invoke(cli, ["reset-prices", "--db", db_url])

        assert result.exit_code == 0
        assert "4" in result.output
        assert "DRY RUN" in result.output
        assert "--confirm" in result.output

        # No rows deleted
        assert _count(seeded_repo) == 4

    def test_dry_run_with_source_filter(self, seeded_repo):
        """Dry-run with --source shows filtered count."""
        from src.cli.main import cli

        runner = CliRunner()
        db_url = str(seeded_repo.engine.url)
        result = runner.invoke(cli, ["reset-prices", "--db", db_url, "--source", "liga"])

        assert result.exit_code == 0
        assert "2" in result.output
        assert "source='liga'" in result.output
        assert "DRY RUN" in result.output

        # No rows deleted
        assert _count(seeded_repo) == 4


class TestConfirmDelete:
    def test_confirm_deletes_all(self, seeded_repo, tmp_path):
        """With --confirm and no --source, deletes all observations."""
        from src.cli.main import cli

        runner = CliRunner()
        db_url = str(seeded_repo.engine.url)

        with patch("src.database.backup.backup_database") as mock_backup:
            mock_backup.return_value = Path(tmp_path / "backup.db")
            result = runner.invoke(cli, ["reset-prices", "--db", db_url, "--confirm"])

        assert result.exit_code == 0
        assert "Deleted 4" in result.output
        assert "Backup saved to" in result.output
        assert _count(seeded_repo) == 0

    def test_confirm_with_source_liga(self, seeded_repo, tmp_path):
        """With --source liga --confirm, only liga rows are deleted."""
        from src.cli.main import cli

        runner = CliRunner()
        db_url = str(seeded_repo.engine.url)

        with patch("src.database.backup.backup_database") as mock_backup:
            mock_backup.return_value = Path(tmp_path / "backup.db")
            result = runner.invoke(
                cli, ["reset-prices", "--db", db_url, "--source", "liga", "--confirm"]
            )

        assert result.exit_code == 0
        assert "Deleted 2" in result.output
        assert _count(seeded_repo, "liga") == 0
        assert _count(seeded_repo, "myp") == 1
        assert _count(seeded_repo, "manual") == 1

    def test_confirm_no_matching_rows(self, seeded_repo):
        """With --source that has no rows, exits gracefully."""
        from src.cli.main import cli

        runner = CliRunner()
        db_url = str(seeded_repo.engine.url)
        result = runner.invoke(
            cli,
            ["reset-prices", "--db", db_url, "--source", "nonexistent", "--confirm"],
        )

        assert result.exit_code == 0
        assert "0" in result.output
        assert _count(seeded_repo) == 4  # nothing deleted
