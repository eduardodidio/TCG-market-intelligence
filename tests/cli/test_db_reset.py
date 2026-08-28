"""CLI integration tests for the db-reset command."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest
from click.testing import CliRunner
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from src.database.models import (
    CardRow,
    PriceObservationRow,
    ScanRunRow,
    SourceCardRow,
    UserCollectionRow,
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
    """Seed repo with minimal data for CLI tests."""
    with Session(repo.engine) as session:
        c1 = CardRow(game="magic", name_en="Lightning Bolt", set_code="2xm", collector_number="1")
        c2 = CardRow(game="magic", name_en="Counterspell", set_code="2xm", collector_number="2")
        session.add_all([c1, c2])
        session.flush()

        sc1 = SourceCardRow(
            source="liga",
            external_id="liga_1",
            card_id=c1.id,
            url="https://liga/1",
            name_en="Lightning Bolt",
        )
        session.add(sc1)

        session.add_all(
            [
                PriceObservationRow(
                    source="liga",
                    external_id="liga_1",
                    observed_at=date(2026, 8, 20),
                    median_price=Decimal("10.00"),
                    currency="BRL",
                ),
            ]
        )

        session.add(
            ScanRunRow(
                scan_type="collection",
                status="completed",
                cards_total=5,
                cards_processed=5,
            )
        )

        session.add(
            UserCollectionRow(
                user_id="user1",
                card_id=c1.id,
                set_code="2xm",
                collector_number="1",
                name_en="Lightning Bolt",
            )
        )

        session.commit()

    return repo


class TestDbResetDryRun:
    def test_db_reset_dry_run(self, seeded_repo):
        """Without --confirm, shows preview and does not delete."""
        from src.cli.main import cli

        runner = CliRunner()
        db_url = str(seeded_repo.engine.url)
        result = runner.invoke(cli, ["db-reset", "--db", db_url, "--skip-backup"])

        assert result.exit_code == 0
        assert "PREVIEW" in result.output or "dry-run" in result.output
        assert "--confirm" in result.output

        # No rows deleted
        with Session(seeded_repo.engine) as session:
            assert (
                session.execute(select(func.count()).select_from(PriceObservationRow)).scalar() == 1
            )
            assert session.execute(select(func.count()).select_from(CardRow)).scalar() == 2


class TestDbResetConfirm:
    def test_db_reset_confirm(self, seeded_repo, tmp_path):
        """With --confirm, performs actual deletion."""
        from src.cli.main import cli

        runner = CliRunner()
        db_url = str(seeded_repo.engine.url)

        result = runner.invoke(cli, ["db-reset", "--db", db_url, "--confirm", "--skip-backup"])

        assert result.exit_code == 0
        assert "Deleted" in result.output or "COMPLETE" in result.output

        # Verify deletion happened
        with Session(seeded_repo.engine) as session:
            assert (
                session.execute(select(func.count()).select_from(PriceObservationRow)).scalar() == 0
            )
            assert session.execute(select(func.count()).select_from(ScanRunRow)).scalar() == 0
            # Only collection-linked card remains
            assert session.execute(select(func.count()).select_from(CardRow)).scalar() == 1
            # Collection untouched
            assert (
                session.execute(select(func.count()).select_from(UserCollectionRow)).scalar() == 1
            )
