"""Tests for CLI `import-csv --currency` and dry-run currency detection (F171-T13)."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from click.testing import CliRunner
from sqlalchemy import create_engine

from src.cli.main import cli
from src.database.models import Base, UserCollectionRow

_FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "collection_import"


def _db_url(tmp_path: Path) -> str:
    return f"sqlite:///{tmp_path / 'test.db'}"


class TestImportCsvDryRun:
    def test_dry_run_detects_usd_from_symbol(self, tmp_path):
        runner = CliRunner()
        result = runner.invoke(
            cli,
            [
                "import-csv",
                "--file",
                str(_FIXTURES / "generic_usd_symbol.csv"),
                "--user-id",
                "u1",
                "--dry-run",
                "--db",
                _db_url(tmp_path),
            ],
        )

        assert result.exit_code == 0
        assert "Currency:          USD" in result.output
        assert "Source:" in result.output
        assert "Confidence:" in result.output
        assert "Priced rows:" in result.output

    def test_dry_run_currency_override_is_honored(self, tmp_path):
        runner = CliRunner()
        result = runner.invoke(
            cli,
            [
                "import-csv",
                "--file",
                str(_FIXTURES / "generic_usd_symbol.csv"),
                "--user-id",
                "u1",
                "--dry-run",
                "--currency",
                "BRL",
                "--db",
                _db_url(tmp_path),
            ],
        )

        assert result.exit_code == 0
        assert "Currency:          BRL" in result.output
        assert "Source:            user" in result.output

    def test_dry_run_currency_override_lowercase_accepted(self, tmp_path):
        runner = CliRunner()
        result = runner.invoke(
            cli,
            [
                "import-csv",
                "--file",
                str(_FIXTURES / "generic_usd_symbol.csv"),
                "--user-id",
                "u1",
                "--dry-run",
                "--currency",
                "usd",
                "--db",
                _db_url(tmp_path),
            ],
        )

        assert result.exit_code == 0
        assert "Currency:          USD" in result.output
        assert "Source:            user" in result.output

    def test_dry_run_liga_no_price_fixture(self, tmp_path):
        runner = CliRunner()
        result = runner.invoke(
            cli,
            [
                "import-csv",
                "--file",
                str(_FIXTURES / "liga_brl_no_price.csv"),
                "--user-id",
                "u1",
                "--dry-run",
                "--db",
                _db_url(tmp_path),
            ],
        )

        assert result.exit_code == 0
        assert "Priced rows:       0" in result.output
        assert "Source:            origin" in result.output

    def test_invalid_currency_choice_is_usage_error(self, tmp_path):
        runner = CliRunner()
        result = runner.invoke(
            cli,
            [
                "import-csv",
                "--file",
                str(_FIXTURES / "generic_usd_symbol.csv"),
                "--user-id",
                "u1",
                "--dry-run",
                "--currency",
                "EUR",
                "--db",
                _db_url(tmp_path),
            ],
        )

        assert result.exit_code == 2


class TestImportCsvRealImport:
    def test_confirm_declined_aborts_without_writes(self, tmp_path):
        runner = CliRunner()
        result = runner.invoke(
            cli,
            [
                "import-csv",
                "--file",
                str(_FIXTURES / "generic_usd_symbol.csv"),
                "--user-id",
                "u1",
                "--db",
                _db_url(tmp_path),
            ],
            input="n\n",
        )

        assert "Aborted" in result.output

    def test_real_import_stores_converted_usd_values(self, tmp_path):
        db_url = _db_url(tmp_path)
        engine = create_engine(db_url)
        Base.metadata.create_all(engine)

        from decimal import Decimal

        runner = CliRunner()
        with patch(
            "src.services.currency.CurrencyConverter.get_display_rate",
            return_value=Decimal("5.40"),
        ):
            result = runner.invoke(
                cli,
                [
                    "import-csv",
                    "--file",
                    str(_FIXTURES / "generic_usd_symbol.csv"),
                    "--user-id",
                    "u1",
                    "--db",
                    db_url,
                ],
                input="y\n",
            )

        assert result.exit_code == 0, result.output
        assert "Priced:" in result.output
        assert "Converted USD->BRL:" in result.output
        assert "Rate:" in result.output

        from decimal import Decimal

        from sqlalchemy.orm import Session

        with Session(engine) as session:
            rows = session.query(UserCollectionRow).filter_by(user_id="u1").all()

        assert len(rows) > 0
        bolt = next(r for r in rows if r.collector_number == "146")
        assert bolt.acquisition_price == Decimal("10.80")
