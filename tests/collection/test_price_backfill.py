"""Tests for src.collection.price_backfill — DeckCheck CSV price import."""

from __future__ import annotations

import csv
from decimal import Decimal
from pathlib import Path
from unittest.mock import MagicMock

from src.collection.price_backfill import (
    _convert_price,
    _normalize_key,
    _parse_price,
    backfill_from_deckcheck_csv,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_entry(
    entry_id: int,
    name_en: str,
    set_code: str,
    collector_number: str,
    acquisition_price=None,
):
    """Create a mock UserCollectionRow."""
    entry = MagicMock()
    entry.id = entry_id
    entry.name_en = name_en
    entry.set_code = set_code
    entry.collector_number = collector_number
    entry.acquisition_price = acquisition_price
    return entry


def _write_csv(tmp_path: Path, rows: list[dict]) -> Path:
    """Write a DeckCheck CSV to a temp file and return its path."""
    csv_path = tmp_path / "deckcheck.csv"
    fieldnames = [
        "Card Scryfall ID",
        "Name",
        "Set Code",
        "Set Name",
        "Collector Number",
        "Rarity",
        "Finish",
        "Finish Display",
        "Quantity",
        "Purchase Price",
        "Current Price",
        "Total Value",
        "Is Proxy",
        "Binder Name",
        "Binder Type",
        "DeckCheck Binder Type",
        "Created At",
        "Updated At",
    ]
    with open(csv_path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            full_row = {fn: "" for fn in fieldnames}
            full_row.update(row)
            writer.writerow(full_row)
    return csv_path


def _make_repo(entries: list):
    """Create a mock Repository that returns entries from list_collection."""
    repo = MagicMock()
    repo.list_collection.return_value = entries
    repo.transaction.return_value.__enter__ = MagicMock(return_value=MagicMock())
    repo.transaction.return_value.__exit__ = MagicMock(return_value=False)
    return repo


# ---------------------------------------------------------------------------
# Unit tests: _parse_price
# ---------------------------------------------------------------------------


class TestParsePrice:
    def test_valid_decimal(self):
        assert _parse_price("0.19") == Decimal("0.19")

    def test_valid_integer(self):
        assert _parse_price("12") == Decimal("12")

    def test_zero_returns_none(self):
        assert _parse_price("0") is None
        assert _parse_price("0.00") is None

    def test_empty_returns_none(self):
        assert _parse_price("") is None
        assert _parse_price("  ") is None

    def test_invalid_returns_none(self):
        assert _parse_price("abc") is None


# ---------------------------------------------------------------------------
# Unit tests: _convert_price
# ---------------------------------------------------------------------------


class TestConvertPrice:
    def test_brl_passthrough(self):
        assert _convert_price(Decimal("10.00"), "BRL", None) == Decimal("10.00")

    def test_usd_with_rate(self):
        result = _convert_price(Decimal("1.00"), "USD", Decimal("5.70"))
        assert result == Decimal("5.70")

    def test_usd_fractional(self):
        result = _convert_price(Decimal("0.19"), "USD", Decimal("5.70"))
        assert result == Decimal("1.08")

    def test_usd_no_rate_returns_none(self):
        assert _convert_price(Decimal("1.00"), "USD", None) is None

    def test_usd_zero_rate_returns_none(self):
        assert _convert_price(Decimal("1.00"), "USD", Decimal("0")) is None

    def test_unsupported_currency_returns_none(self):
        assert _convert_price(Decimal("1.00"), "EUR", None) is None


# ---------------------------------------------------------------------------
# Unit tests: _normalize_key
# ---------------------------------------------------------------------------


class TestNormalizeKey:
    def test_lowercases_and_strips(self):
        assert _normalize_key("  Abrade ", " VOW ", " 139 ") == ("abrade", "vow", "139")


# ---------------------------------------------------------------------------
# Integration tests: backfill_from_deckcheck_csv
# ---------------------------------------------------------------------------


class TestBackfillFromDeckcheckCsv:
    def test_match_by_name_set_number(self, tmp_path):
        """Exact match on (name, set_code, collector_number)."""
        csv_rows = [
            {
                "Name": "Abrade",
                "Set Code": "vow",
                "Collector Number": "139",
                "Purchase Price": "0.19",
            },
        ]
        csv_path = _write_csv(tmp_path, csv_rows)
        entry = _make_entry(1, "Abrade", "vow", "139")
        repo = _make_repo([entry])

        result = backfill_from_deckcheck_csv(
            csv_path,
            repo,
            user_id="1",
            currency="USD",
            exchange_rate=Decimal("5.70"),
        )

        assert result.total_csv_rows == 1
        assert result.matched == 1
        assert result.applied == 1
        assert result.not_found == 0
        repo.update_collection_entry.assert_called_once()
        call_args = repo.update_collection_entry.call_args
        assert call_args[0][0] == 1  # entry_id
        assert call_args[0][2]["acquisition_price"] == Decimal("1.08")

    def test_fallback_match_by_set_number(self, tmp_path):
        """When name doesn't match, fall back to (set_code, collector_number)."""
        csv_rows = [
            {
                "Name": "Abrade",
                "Set Code": "vow",
                "Collector Number": "139",
                "Purchase Price": "0.19",
            },
        ]
        csv_path = _write_csv(tmp_path, csv_rows)
        # DB entry has a different English name (e.g. Portuguese imported)
        entry = _make_entry(1, "Abrasar", "vow", "139")
        repo = _make_repo([entry])

        result = backfill_from_deckcheck_csv(
            csv_path,
            repo,
            user_id="1",
            currency="USD",
            exchange_rate=Decimal("5.70"),
        )

        assert result.matched == 1
        assert result.applied == 1

    def test_skip_when_price_already_set(self, tmp_path):
        """Entries with existing acquisition_price are skipped."""
        csv_rows = [
            {
                "Name": "Abrade",
                "Set Code": "vow",
                "Collector Number": "139",
                "Purchase Price": "0.19",
            },
        ]
        csv_path = _write_csv(tmp_path, csv_rows)
        entry = _make_entry(1, "Abrade", "vow", "139", acquisition_price=Decimal("2.00"))
        repo = _make_repo([entry])

        result = backfill_from_deckcheck_csv(
            csv_path,
            repo,
            user_id="1",
            currency="USD",
            exchange_rate=Decimal("5.70"),
        )

        assert result.matched == 1
        assert result.skipped_has_price == 1
        assert result.applied == 0
        repo.update_collection_entry.assert_not_called()

    def test_overwrite_existing_price(self, tmp_path):
        """With overwrite=True, existing prices are replaced."""
        csv_rows = [
            {
                "Name": "Abrade",
                "Set Code": "vow",
                "Collector Number": "139",
                "Purchase Price": "0.19",
            },
        ]
        csv_path = _write_csv(tmp_path, csv_rows)
        entry = _make_entry(1, "Abrade", "vow", "139", acquisition_price=Decimal("2.00"))
        repo = _make_repo([entry])

        result = backfill_from_deckcheck_csv(
            csv_path,
            repo,
            user_id="1",
            currency="USD",
            exchange_rate=Decimal("5.70"),
            overwrite=True,
        )

        assert result.matched == 1
        assert result.skipped_has_price == 0
        assert result.applied == 1

    def test_brl_currency_no_conversion(self, tmp_path):
        """BRL prices are used directly without conversion."""
        csv_rows = [
            {
                "Name": "Abrade",
                "Set Code": "vow",
                "Collector Number": "139",
                "Purchase Price": "5.50",
            },
        ]
        csv_path = _write_csv(tmp_path, csv_rows)
        entry = _make_entry(1, "Abrade", "vow", "139")
        repo = _make_repo([entry])

        result = backfill_from_deckcheck_csv(
            csv_path,
            repo,
            user_id="1",
            currency="BRL",
        )

        assert result.applied == 1
        call_args = repo.update_collection_entry.call_args
        assert call_args[0][2]["acquisition_price"] == Decimal("5.50")

    def test_dry_run_no_writes(self, tmp_path):
        """Dry run computes counts but writes nothing."""
        csv_rows = [
            {
                "Name": "Abrade",
                "Set Code": "vow",
                "Collector Number": "139",
                "Purchase Price": "0.19",
            },
        ]
        csv_path = _write_csv(tmp_path, csv_rows)
        entry = _make_entry(1, "Abrade", "vow", "139")
        repo = _make_repo([entry])

        result = backfill_from_deckcheck_csv(
            csv_path,
            repo,
            user_id="1",
            currency="USD",
            exchange_rate=Decimal("5.70"),
            dry_run=True,
        )

        assert result.matched == 1
        assert result.applied == 0
        repo.update_collection_entry.assert_not_called()
        repo.transaction.assert_not_called()

    def test_not_found_when_no_match(self, tmp_path):
        """CSV row with no matching collection entry counts as not_found."""
        csv_rows = [
            {
                "Name": "Lightning Bolt",
                "Set Code": "m21",
                "Collector Number": "1",
                "Purchase Price": "1.00",
            },
        ]
        csv_path = _write_csv(tmp_path, csv_rows)
        entry = _make_entry(1, "Abrade", "vow", "139")
        repo = _make_repo([entry])

        result = backfill_from_deckcheck_csv(
            csv_path,
            repo,
            user_id="1",
            currency="USD",
            exchange_rate=Decimal("5.70"),
        )

        assert result.not_found == 1
        assert result.matched == 0

    def test_case_insensitive_matching(self, tmp_path):
        """Matching should be case-insensitive."""
        csv_rows = [
            {
                "Name": "ABRADE",
                "Set Code": "VOW",
                "Collector Number": "139",
                "Purchase Price": "0.19",
            },
        ]
        csv_path = _write_csv(tmp_path, csv_rows)
        entry = _make_entry(1, "Abrade", "vow", "139")
        repo = _make_repo([entry])

        result = backfill_from_deckcheck_csv(
            csv_path,
            repo,
            user_id="1",
            currency="USD",
            exchange_rate=Decimal("5.70"),
        )

        assert result.matched == 1

    def test_zero_price_skipped(self, tmp_path):
        """Rows with zero purchase price are skipped (not_found)."""
        csv_rows = [
            {
                "Name": "Abrade",
                "Set Code": "vow",
                "Collector Number": "139",
                "Purchase Price": "0.00",
            },
        ]
        csv_path = _write_csv(tmp_path, csv_rows)
        entry = _make_entry(1, "Abrade", "vow", "139")
        repo = _make_repo([entry])

        result = backfill_from_deckcheck_csv(
            csv_path,
            repo,
            user_id="1",
            currency="USD",
            exchange_rate=Decimal("5.70"),
        )

        assert result.not_found == 1
        assert result.matched == 0

    def test_multiple_rows_mixed_results(self, tmp_path):
        """Multiple CSV rows: some match, some skip, some not found."""
        csv_rows = [
            {
                "Name": "Abrade",
                "Set Code": "vow",
                "Collector Number": "139",
                "Purchase Price": "0.19",
            },
            {"Name": "Bolt", "Set Code": "m21", "Collector Number": "1", "Purchase Price": "1.00"},
            {
                "Name": "Counterspell",
                "Set Code": "cmm",
                "Collector Number": "55",
                "Purchase Price": "0.50",
            },
        ]
        csv_path = _write_csv(tmp_path, csv_rows)
        entries = [
            _make_entry(1, "Abrade", "vow", "139"),
            _make_entry(2, "Counterspell", "cmm", "55", acquisition_price=Decimal("3.00")),
        ]
        repo = _make_repo(entries)

        result = backfill_from_deckcheck_csv(
            csv_path,
            repo,
            user_id="1",
            currency="USD",
            exchange_rate=Decimal("5.70"),
        )

        assert result.total_csv_rows == 3
        assert result.matched == 2
        assert result.not_found == 1
        assert result.skipped_has_price == 1
        assert result.applied == 1
