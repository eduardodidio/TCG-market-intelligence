"""Tests for scripts/liga_debug.py — argument parsing, edition display, batch I/O.

NOTE: These tests cover argument parsing and output formatting only.
Full integration tests require Playwright + Liga access and are manual-only.
"""

from __future__ import annotations

import csv
import sys
from pathlib import Path

# Ensure project root is on sys.path so we can import the script
_project_root = str(Path(__file__).resolve().parent.parent.parent)
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from scripts.liga_debug import (  # noqa: E402
    _print_batch_summary,
    _read_batch_csv,
    _write_batch_csv,
    build_parser,
    format_edition_line,
    select_edition_from_matches,
)

# ---------------------------------------------------------------------------
# CLI argument parsing
# ---------------------------------------------------------------------------


class TestCliArgs:
    """Verify argparse configuration for all flags."""

    def test_single_card_minimal(self):
        parser = build_parser()
        args = parser.parse_args(["Lightning Bolt"])
        assert args.card_name == "Lightning Bolt"
        assert args.collector_number is None
        assert args.set_code is None
        assert args.batch is None
        assert args.limit is None
        assert args.no_headless is False

    def test_single_card_with_collector_number(self):
        parser = build_parser()
        args = parser.parse_args(["Lightning Bolt", "-cn", "123"])
        assert args.collector_number == "123"

    def test_cli_args_set_code(self):
        """--set-code / -sc argument is accepted and parsed correctly."""
        parser = build_parser()

        # Long form
        args = parser.parse_args(["Bolt", "--set-code", "fdn"])
        assert args.set_code == "fdn"

        # Short form
        args = parser.parse_args(["Bolt", "-sc", "cmm"])
        assert args.set_code == "cmm"

    def test_cli_args_set_code_with_collector_number(self):
        parser = build_parser()
        args = parser.parse_args(["Bolt", "-cn", "42", "-sc", "fdn"])
        assert args.collector_number == "42"
        assert args.set_code == "fdn"

    def test_cli_args_batch(self):
        """--batch / -b argument is accepted and parsed correctly."""
        parser = build_parser()

        # Long form
        args = parser.parse_args(["--batch", "mismatches.csv"])
        assert args.batch == "mismatches.csv"

        # Short form
        args = parser.parse_args(["-b", "my_file.csv"])
        assert args.batch == "my_file.csv"

    def test_cli_args_batch_with_limit(self):
        parser = build_parser()
        args = parser.parse_args(["--batch", "input.csv", "--limit", "10"])
        assert args.batch == "input.csv"
        assert args.limit == 10

    def test_cli_args_batch_no_headless(self):
        parser = build_parser()
        args = parser.parse_args(["-b", "input.csv", "--no-headless"])
        assert args.batch == "input.csv"
        assert args.no_headless is True

    def test_batch_mode_card_name_optional(self):
        """In batch mode, card_name should not be required."""
        parser = build_parser()
        args = parser.parse_args(["--batch", "test.csv"])
        assert args.card_name is None
        assert args.batch == "test.csv"

    def test_limit_is_integer(self):
        parser = build_parser()
        args = parser.parse_args(["-b", "test.csv", "--limit", "5"])
        assert args.limit == 5
        assert isinstance(args.limit, int)


# ---------------------------------------------------------------------------
# Edition display (3-tuple)
# ---------------------------------------------------------------------------


class TestEditionDisplay:
    """Verify that format_edition_line correctly uses 3-tuple data."""

    def test_edition_display_3tuple_basic(self):
        """Sigla is shown in the formatted output line."""
        line = format_edition_line("480612_1", "1", "fdn")
        assert "value=480612_1" in line
        assert "collector_number=1" in line
        assert "sigla=fdn" in line

    def test_edition_display_3tuple_no_match(self):
        """No MATCH marker when collector_number does not match."""
        line = format_edition_line("480612_1", "1", "fdn", collector_number="367")
        assert "MATCH" not in line

    def test_edition_display_3tuple_cn_match(self):
        """CN-only match marker when collector_number matches but no set_code."""
        line = format_edition_line("480612_1", "1", "fdn", collector_number="1")
        assert "MATCH (cn)" in line

    def test_edition_display_3tuple_cn_and_sigla_match(self):
        """CN+sigla match marker when both collector_number and set_code match."""
        line = format_edition_line("480612_1", "1", "fdn", collector_number="1", set_code="fdn")
        assert "MATCH (cn+sigla)" in line

    def test_edition_display_cn_match_sigla_mismatch(self):
        """CN matches but sigla does not — should show cn-only match."""
        line = format_edition_line("480612_1", "1", "fdn", collector_number="1", set_code="cmm")
        assert "MATCH (cn)" in line
        assert "cn+sigla" not in line

    def test_edition_display_empty_sigla(self):
        """Empty sigla is displayed without error."""
        line = format_edition_line("480612_1", "1", "")
        assert "sigla=" in line


# ---------------------------------------------------------------------------
# Edition selection logic (mirrors provider._select_edition)
# ---------------------------------------------------------------------------


class TestEditionSelection:
    """Verify select_edition_from_matches mirrors provider disambiguation."""

    def test_single_match_by_cn(self):
        editions = [("100_1", "1", "fdn"), ("200_367", "367", "cmm")]
        val, matched = select_edition_from_matches(editions, "367")
        assert matched is True
        assert val == "200_367"

    def test_no_match(self):
        editions = [("100_1", "1", "fdn")]
        val, matched = select_edition_from_matches(editions, "999")
        assert matched is False
        assert val is None

    def test_disambiguate_by_sigla(self):
        """When multiple editions share same CN, prefer sigla match."""
        editions = [
            ("100_157", "157", "afr"),
            ("200_157", "157", "ampafr"),
        ]
        # Without set_code — returns first match
        val, matched = select_edition_from_matches(editions, "157")
        assert matched is True
        assert val == "100_157"

        # With set_code=ampafr — returns the one with matching sigla
        val, matched = select_edition_from_matches(editions, "157", set_code="ampafr")
        assert matched is True
        assert val == "200_157"

    def test_sigla_no_match_falls_back_to_first(self):
        """If set_code doesn't match any sigla, fall back to first CN match."""
        editions = [
            ("100_157", "157", "afr"),
            ("200_157", "157", "ampafr"),
        ]
        val, matched = select_edition_from_matches(editions, "157", set_code="xxx")
        assert matched is True
        assert val == "100_157"

    def test_single_cn_match_ignores_sigla(self):
        """When only one CN match exists, sigla filtering is not needed."""
        editions = [("100_42", "42", "fdn")]
        val, matched = select_edition_from_matches(editions, "42", set_code="fdn")
        assert matched is True
        assert val == "100_42"

    def test_empty_editions(self):
        val, matched = select_edition_from_matches([], "1")
        assert matched is False
        assert val is None


# ---------------------------------------------------------------------------
# Batch CSV I/O
# ---------------------------------------------------------------------------


class TestBatchCsvRead:
    """Verify batch CSV reading logic."""

    def test_read_valid_csv(self, tmp_path):
        csv_file = tmp_path / "input.csv"
        csv_file.write_text(
            "name_en,collector_number,set_code,card_id\n"
            "Lightning Bolt,141,fdn,1001\n"
            "Counterspell,79,cmm,1002\n",
            encoding="utf-8",
        )
        rows = _read_batch_csv(csv_file)
        assert len(rows) == 2
        assert rows[0]["name_en"] == "Lightning Bolt"
        assert rows[0]["collector_number"] == "141"
        assert rows[0]["set_code"] == "fdn"
        assert rows[0]["card_id"] == "1001"

    def test_read_csv_missing_name_en(self, tmp_path):
        csv_file = tmp_path / "bad.csv"
        csv_file.write_text("card_name,price\nBolt,5.00\n", encoding="utf-8")
        rows = _read_batch_csv(csv_file)
        assert rows == []

    def test_read_csv_skips_empty_names(self, tmp_path):
        csv_file = tmp_path / "gaps.csv"
        csv_file.write_text(
            "name_en,collector_number\nBolt,1\n,\n  ,2\nShock,3\n",
            encoding="utf-8",
        )
        rows = _read_batch_csv(csv_file)
        assert len(rows) == 2
        assert rows[0]["name_en"] == "Bolt"
        assert rows[1]["name_en"] == "Shock"

    def test_read_csv_optional_columns(self, tmp_path):
        """CSV with only name_en column should still work."""
        csv_file = tmp_path / "minimal.csv"
        csv_file.write_text("name_en\nBolt\nShock\n", encoding="utf-8")
        rows = _read_batch_csv(csv_file)
        assert len(rows) == 2


class TestBatchCsvWrite:
    """Verify batch CSV writing logic."""

    def test_write_batch_csv(self, tmp_path):
        output = tmp_path / "output.csv"
        results = [
            {
                "card_name": "Bolt",
                "collector_number": "141",
                "set_code": "fdn",
                "edition_matched": True,
                "our_mid": "5.00",
                "liga_mid": "5.50",
                "diff_pct": "10.0",
                "status": "OK",
                "card_id": "1001",  # extra field — should be ignored
            }
        ]
        _write_batch_csv(output, results)
        assert output.exists()

        with open(output, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            rows = list(reader)
        assert len(rows) == 1
        assert rows[0]["card_name"] == "Bolt"
        assert rows[0]["liga_mid"] == "5.50"
        assert rows[0]["diff_pct"] == "10.0"
        assert rows[0]["status"] == "OK"
        # card_id should not be in output (extrasaction=ignore)
        assert "card_id" not in rows[0]

    def test_write_batch_csv_columns(self, tmp_path):
        """Verify the exact column order in the output CSV."""
        output = tmp_path / "cols.csv"
        _write_batch_csv(output, [])
        with open(output, "r", encoding="utf-8") as f:
            header = f.readline().strip()
        expected = (
            "card_name,collector_number,set_code,edition_matched,our_mid,liga_mid,diff_pct,status"
        )
        assert header == expected


# ---------------------------------------------------------------------------
# Batch summary output
# ---------------------------------------------------------------------------


class TestBatchSummary:
    """Verify the summary printout from batch results."""

    def test_print_batch_summary(self, capsys):
        results = [
            {"edition_matched": True, "liga_mid": "5.00", "diff_pct": "10.0", "status": "OK"},
            {"edition_matched": False, "liga_mid": "", "diff_pct": "", "status": "NO_PRICE"},
            {
                "edition_matched": True,
                "liga_mid": "100.0",
                "diff_pct": "80.0",
                "status": "BIG_DIFF",
            },
            {
                "edition_matched": True,
                "liga_mid": "3.00",
                "diff_pct": "-55.0",
                "status": "BIG_DIFF",
            },
            {"edition_matched": False, "liga_mid": "", "diff_pct": "", "status": "ERROR: timeout"},
        ]
        _print_batch_summary(results)
        captured = capsys.readouterr().out

        assert "Total processed:       5" in captured
        assert "Edition matched:       3" in captured
        assert "Edition NOT matched:   2" in captured
        assert "Price found:           3" in captured
        assert "Price NOT found:       2" in captured
        assert ">50% deviation:        2" in captured
        assert "Errors:                1" in captured

    def test_print_batch_summary_empty(self, capsys):
        _print_batch_summary([])
        captured = capsys.readouterr().out
        assert "Total processed:       0" in captured
