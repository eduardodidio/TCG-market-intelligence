"""Tests for currency-aware CSV import (F171-T07).

Uses the shared fixtures from tests/fixtures/collection_import/ (F171-T01).
"""

from __future__ import annotations

import csv
import tempfile
from decimal import Decimal
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from src.collection.importer import import_collection_csv
from src.database.models import Base, UserCollectionRow

_FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "collection_import"


def _fake_rate_lookup(_d):
    return Decimal("5.40")


def _no_rate_lookup(_d):
    return None


@pytest.fixture()
def engine():
    eng = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(eng)
    return eng


def _prices(engine, user_id="u1") -> dict[tuple[str, str], Decimal | None]:
    with Session(engine) as session:
        rows = session.query(UserCollectionRow).filter_by(user_id=user_id).all()
        return {(r.set_code, r.collector_number): r.acquisition_price for r in rows}


class TestBrlFixturesUnchanged:
    """AC1: BRL fixtures (symbol, header, currency column) store values unchanged."""

    @pytest.mark.parametrize(
        "fixture,expected",
        [
            (
                "generic_brl_symbol.csv",
                {("m10", "146"): Decimal("10.00"), ("c21", "263"): Decimal("2.50")},
            ),
            (
                "liga_brl_with_price.csv",
                {("dom", "146"): Decimal("12.50"), ("c21", "263"): Decimal("0.75")},
            ),
            (
                "manabox_brl.csv",
                {("m10", "146"): Decimal("10.50"), ("c21", "263"): Decimal("1.75")},
            ),
        ],
    )
    def test_brl_fixture_values_unchanged(self, engine, fixture, expected):
        result = import_collection_csv(engine, _FIXTURES / fixture, user_id="u1")
        assert result["detected_currency"] == "BRL"
        prices = _prices(engine)
        for key, value in expected.items():
            assert prices[key] == value


class TestUsdFixturesConverted:
    """AC2: USD fixtures are converted to BRL via the rate."""

    @pytest.mark.parametrize(
        "fixture,expected",
        [
            (
                "generic_usd_symbol.csv",
                {("m10", "146"): Decimal("10.80"), ("c21", "263"): Decimal("2.70")},
            ),
            (
                "manabox_usd.csv",
                {("m10", "146"): Decimal("10.80"), ("c21", "263"): Decimal("1.89")},
            ),
        ],
    )
    def test_usd_fixture_values_converted(self, engine, fixture, expected):
        result = import_collection_csv(
            engine, _FIXTURES / fixture, user_id="u1", rate_lookup=_fake_rate_lookup
        )
        assert result["detected_currency"] == "USD"
        assert result["converted"] == result["priced"] > 0
        assert result["exchange_rate"] == "5.40"
        prices = _prices(engine)
        for key, value in expected.items():
            assert prices[key] == value


class TestUserOverride:
    """AC3: an explicit currency choice wins over auto-detection, for every row."""

    def test_brl_override_on_usd_file(self, engine):
        result = import_collection_csv(
            engine, _FIXTURES / "generic_usd_symbol.csv", user_id="u1", currency="BRL"
        )
        assert result["currency_source"] == "user"
        prices = _prices(engine)
        assert prices[("m10", "146")] == Decimal("2.00")

    def test_usd_override_on_brl_file(self, engine):
        result = import_collection_csv(
            engine,
            _FIXTURES / "generic_brl_symbol.csv",
            user_id="u1",
            currency="USD",
            rate_lookup=_fake_rate_lookup,
        )
        assert result["currency_source"] == "user"
        prices = _prices(engine)
        assert prices[("m10", "146")] == Decimal("54.00")


class TestAmbiguousDefault:
    """AC4: ambiguous files default to BRL with source 'default'."""

    def test_ambiguous_file_defaults_to_brl(self, engine):
        result = import_collection_csv(engine, _FIXTURES / "ambiguous_no_hint.csv", user_id="u1")
        assert result["currency_source"] == "default"
        assert result["detected_currency"] == "BRL"
        prices = _prices(engine)
        assert prices[("m10", "146")] == Decimal("10.00")


class TestNoRateAvailable:
    """AC5: no rate -> price dropped with a warning, import still succeeds."""

    def test_usd_without_rate_lookup_drops_price(self, engine):
        result = import_collection_csv(
            engine, _FIXTURES / "generic_usd_symbol.csv", user_id="u1", rate_lookup=_no_rate_lookup
        )
        assert result["priced"] == 0
        assert any("no_rate" in w for w in result["price_warnings"])
        assert result["imported"] == 3
        prices = _prices(engine)
        assert prices[("m10", "146")] is None

    def test_usd_without_any_rate_lookup_arg_drops_price(self, engine):
        result = import_collection_csv(engine, _FIXTURES / "generic_usd_symbol.csv", user_id="u1")
        assert result["priced"] == 0
        assert any("no_rate" in w for w in result["price_warnings"])


class TestDryRun:
    """AC8: dry_run detects without writing."""

    def test_dry_run_writes_nothing(self, engine):
        import_collection_csv(engine, _FIXTURES / "generic_brl_symbol.csv", user_id="u1")
        with Session(engine) as session:
            count_before = session.query(UserCollectionRow).filter_by(user_id="u1").count()

        result = import_collection_csv(
            engine, _FIXTURES / "generic_usd_symbol.csv", user_id="u1", dry_run=True
        )

        with Session(engine) as session:
            count_after = session.query(UserCollectionRow).filter_by(user_id="u1").count()

        assert count_before == count_after == 3
        assert result["dry_run"] is True
        assert result["new_entry_ids"] == []

    def test_dry_run_on_empty_csv_is_all_zeros(self, engine):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "empty.csv"
            with open(path, "w", newline="") as f:
                csv.writer(f).writerow(
                    ["Name", "Set code", "Collector number", "Quantity", "Price"]
                )

            result = import_collection_csv(engine, path, user_id="u1", dry_run=True)

        assert result == {
            "imported": 0,
            "skipped": 0,
            "linked": 0,
            "total_csv_rows": 0,
            "new_entry_ids": [],
            "detected_currency": "BRL",
            "currency_source": "default",
            "currency_confidence": "low",
            "currency_evidence": ["default: BRL"],
            "priced": 0,
            "converted": 0,
            "exchange_rate": None,
            "price_warnings": [],
            "dry_run": True,
        }


class TestLigaNoPriceRegression:
    """AC9: Liga import without a price column is unchanged."""

    def test_liga_no_price_fixture(self, engine):
        result = import_collection_csv(engine, _FIXTURES / "liga_brl_no_price.csv", user_id="u1")
        assert result["priced"] == 0
        assert result["imported"] == 3
        prices = _prices(engine)
        assert prices[("dom", "146")] is None
        assert result["currency_source"] == "origin"


class TestEdgeCases:
    def _write_csv(self, tmp_dir: str, header: list[str], rows: list[list[str]]) -> Path:
        path = Path(tmp_dir) / "collection.csv"
        with open(path, "w", encoding="utf-8", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(header)
            writer.writerows(rows)
        return path

    def test_empty_price_cell_not_counted(self, engine):
        with tempfile.TemporaryDirectory() as tmp:
            path = self._write_csv(
                tmp,
                ["Name", "Set code", "Collector number", "Quantity", "Price"],
                [["Lightning Bolt", "m10", "146", "1", ""]],
            )
            result = import_collection_csv(engine, path, user_id="u1")
            assert result["priced"] == 0
            assert result["price_warnings"] == []
            prices = _prices(engine)
            assert prices[("m10", "146")] is None

    def test_quantity_blank_defaults_to_one(self, engine):
        with tempfile.TemporaryDirectory() as tmp:
            path = self._write_csv(
                tmp,
                ["Name", "Set code", "Collector number", "Quantity"],
                [["Lightning Bolt", "m10", "146", ""]],
            )
            import_collection_csv(engine, path, user_id="u1")
            with Session(engine) as session:
                row = session.query(UserCollectionRow).filter_by(user_id="u1").one()
                assert row.quantity == 1

    def test_quantity_decimal_string_parsed(self, engine):
        with tempfile.TemporaryDirectory() as tmp:
            path = self._write_csv(
                tmp,
                ["Name", "Set code", "Collector number", "Quantity"],
                [["Lightning Bolt", "m10", "146", "2.0"]],
            )
            import_collection_csv(engine, path, user_id="u1")
            with Session(engine) as session:
                row = session.query(UserCollectionRow).filter_by(user_id="u1").one()
                assert row.quantity == 2

    def test_invalid_quantity_row_skipped(self, engine):
        with tempfile.TemporaryDirectory() as tmp:
            path = self._write_csv(
                tmp,
                ["Name", "Set code", "Collector number", "Quantity"],
                [["Lightning Bolt", "m10", "146", "abc"]],
            )
            result = import_collection_csv(engine, path, user_id="u1")
            assert result["imported"] == 0
            assert result["skipped"] == 1

    def test_bom_header_is_handled(self, engine):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "collection.csv"
            with open(path, "w", encoding="utf-8-sig", newline="") as f:
                writer = csv.writer(f)
                writer.writerow(["Name", "Set code", "Collector number", "Quantity", "Price"])
                writer.writerow(["Lightning Bolt", "m10", "146", "1", "R$ 10,00"])
            result = import_collection_csv(engine, path, user_id="u1")
            assert result["imported"] == 1
            prices = _prices(engine)
            assert prices[("m10", "146")] == Decimal("10.00")

    def test_unparseable_price_warns_but_imports_row(self, engine):
        with tempfile.TemporaryDirectory() as tmp:
            path = self._write_csv(
                tmp,
                ["Name", "Set code", "Collector number", "Quantity", "Price"],
                [["Lightning Bolt", "m10", "146", "1", "abc"]],
            )
            result = import_collection_csv(engine, path, user_id="u1")
            assert result["imported"] == 1
            assert result["priced"] == 0
            assert any("invalid_price" in w for w in result["price_warnings"])
            prices = _prices(engine)
            assert prices[("m10", "146")] is None

    def test_eur_symbol_warns_unsupported_currency(self, engine):
        with tempfile.TemporaryDirectory() as tmp:
            path = self._write_csv(
                tmp,
                ["Name", "Set code", "Collector number", "Quantity", "Price"],
                [["Lightning Bolt", "m10", "146", "1", "EUR 9,00"]],
            )
            result = import_collection_csv(engine, path, user_id="u1")
            assert result["imported"] == 1
            assert result["priced"] == 0
            assert any("unsupported_currency" in w for w in result["price_warnings"])
            prices = _prices(engine)
            assert prices[("m10", "146")] is None

    def test_25_bad_prices_caps_warnings_at_20_plus_summary(self, engine):
        with tempfile.TemporaryDirectory() as tmp:
            rows = [
                [f"Card {i}", "m10", str(i), "1", "abc"] for i in range(25)
            ]
            path = self._write_csv(
                tmp, ["Name", "Set code", "Collector number", "Quantity", "Price"], rows
            )
            result = import_collection_csv(engine, path, user_id="u1")
            assert result["imported"] == 25
            assert len(result["price_warnings"]) == 21
            assert result["price_warnings"][-1] == "... and 5 more"


class TestExistingConverterUnchanged:
    """converter.py has no monetary fields; F171-T07 makes no change to it."""

    def test_row_to_collection_entry_has_no_price_field(self):
        import inspect

        from src.collection.converter import row_to_collection_entry

        source = inspect.getsource(row_to_collection_entry)
        assert "price" not in source.lower()
