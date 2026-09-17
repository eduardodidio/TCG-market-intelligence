"""Tests for src.services.purchase_matcher."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from src.services.purchase_matcher import (
    match_purchases,
    normalize_name,
)
from src.services.purchase_parser import ParsedPurchaseItem

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_parsed(
    *,
    name_en: str | None = None,
    name_pt: str | None = None,
    set_code: str | None = None,
    cn: str | None = None,
    quantity: int = 1,
    price: str = "1.00",
    order_number: str = "#1",
) -> ParsedPurchaseItem:
    return ParsedPurchaseItem(
        card_name_pt=name_pt,
        card_name_en=name_en,
        set_name=None,
        set_code=set_code,
        collector_number=cn,
        language="EN",
        quality="NM",
        quantity=quantity,
        unit_price=Decimal(price),
        is_foil=False,
        extras=[],
        order_number=order_number,
        order_date=date(2025, 1, 1),
        store_name="Test Store",
        source_file="test.html",
    )


class _FakeEntry:
    """Minimal stand-in for UserCollectionRow used in unit tests."""

    def __init__(
        self,
        id: int,
        name_en: str | None = None,
        name_pt: str | None = None,
        set_code: str | None = None,
        collector_number: str | None = None,
        quantity: int = 1,
        acquisition_price: Decimal | None = None,
    ):
        self.id = id
        self.name_en = name_en
        self.name_pt = name_pt
        self.set_code = set_code
        self.collector_number = collector_number
        self.quantity = quantity
        self.acquisition_price = acquisition_price


# ---------------------------------------------------------------------------
# Normalisation
# ---------------------------------------------------------------------------


class TestNormalizeName:
    def test_lowercase(self):
        assert normalize_name("Dragon Tempest") == "dragon tempest"

    def test_accent_removal(self):
        assert normalize_name("Dragão") == "dragao"

    def test_cedilla(self):
        assert normalize_name("Proteção") == "protecao"

    def test_strip_whitespace(self):
        assert normalize_name("  Hello  ") == "hello"


# ---------------------------------------------------------------------------
# Exact match (confidence 1.0)
# ---------------------------------------------------------------------------


class TestExactMatch:
    def test_name_set_cn(self):
        item = _make_parsed(name_en="Dragon's Fire", set_code="AFR", cn="139")
        entry = _FakeEntry(1, name_en="Dragon's Fire", set_code="afr", collector_number="139")
        report = match_purchases([item], [entry])
        assert len(report.matched) == 1
        assert report.matched[0].confidence == 1.0
        assert report.matched[0].match_method == "exact"
        assert report.matched[0].collection_entry_id == 1

    def test_case_insensitive(self):
        item = _make_parsed(name_en="dragon's fire", set_code="AFR", cn="139")
        entry = _FakeEntry(1, name_en="Dragon's Fire", set_code="afr", collector_number="139")
        report = match_purchases([item], [entry])
        assert report.matched[0].confidence == 1.0


# ---------------------------------------------------------------------------
# Name + set match (confidence 0.95)
# ---------------------------------------------------------------------------


class TestNameSetMatch:
    def test_name_and_set_no_cn(self):
        item = _make_parsed(name_en="Dragon Tempest", set_code="DTK")
        entry = _FakeEntry(1, name_en="Dragon Tempest", set_code="dtk", collector_number="136")
        report = match_purchases([item], [entry])
        assert report.matched[0].confidence == 0.95
        assert report.matched[0].match_method == "name_set"

    def test_pt_name_match(self):
        item = _make_parsed(name_pt="Tempestade Dragônica", set_code="DTK")
        entry = _FakeEntry(1, name_pt="Tempestade Dragônica", set_code="dtk")
        report = match_purchases([item], [entry])
        assert report.matched[0].confidence == 0.95


# ---------------------------------------------------------------------------
# Name + CN match (confidence 0.85)
# ---------------------------------------------------------------------------


class TestNameCnMatch:
    def test_name_cn_different_set(self):
        item = _make_parsed(name_en="Dragon's Fire", set_code=None, cn="139")
        entry = _FakeEntry(1, name_en="Dragon's Fire", set_code="afr", collector_number="139")
        report = match_purchases([item], [entry])
        assert report.matched[0].confidence == 0.85
        assert report.matched[0].match_method == "name_cn"


# ---------------------------------------------------------------------------
# Name-only match (confidence 0.7)
# ---------------------------------------------------------------------------


class TestNameOnlyMatch:
    def test_name_only(self):
        item = _make_parsed(name_en="Dragon's Fire")
        entry = _FakeEntry(1, name_en="Dragon's Fire", set_code="afr")
        report = match_purchases([item], [entry])
        assert report.matched[0].confidence == 0.7
        assert report.matched[0].match_method == "name_only"


# ---------------------------------------------------------------------------
# No match
# ---------------------------------------------------------------------------


class TestNoMatch:
    def test_unknown_card(self):
        item = _make_parsed(name_en="Nonexistent Card")
        entry = _FakeEntry(1, name_en="Dragon's Fire", set_code="afr")
        report = match_purchases([item], [entry])
        assert len(report.unmatched) == 1
        assert report.unmatched[0].skip_reason == "No matching collection entry found"

    def test_empty_collection(self):
        item = _make_parsed(name_en="Dragon's Fire")
        report = match_purchases([item], [])
        assert len(report.unmatched) == 1


# ---------------------------------------------------------------------------
# Cross-language matching
# ---------------------------------------------------------------------------


class TestCrossLanguageMatch:
    def test_pt_name_matches_collection_pt(self):
        item = _make_parsed(name_pt="Tempestade Dragônica", set_code="DTK")
        entry = _FakeEntry(1, name_pt="Tempestade Dragônica", set_code="dtk")
        report = match_purchases([item], [entry])
        assert report.matched[0].confidence == 0.95

    def test_parsed_pt_matches_collection_en(self):
        """Parsed PT name tried against EN index as fallback."""
        item = _make_parsed(name_pt="Dragon Tempest", name_en=None)
        entry = _FakeEntry(1, name_en="Dragon Tempest", set_code="dtk")
        report = match_purchases([item], [entry])
        assert report.matched[0].confidence == 0.7  # name_only via cross-language


# ---------------------------------------------------------------------------
# Accent normalisation
# ---------------------------------------------------------------------------


class TestAccentMatch:
    def test_accented_pt_name(self):
        item = _make_parsed(name_pt="Dragão Ancestral")
        entry = _FakeEntry(1, name_pt="Dragão Ancestral")
        report = match_purchases([item], [entry])
        assert len(report.matched) == 1

    def test_missing_accent_still_matches(self):
        item = _make_parsed(name_pt="Dragao Ancestral")
        entry = _FakeEntry(1, name_pt="Dragão Ancestral")
        report = match_purchases([item], [entry])
        assert len(report.matched) == 1


# ---------------------------------------------------------------------------
# Already has price
# ---------------------------------------------------------------------------


class TestAlreadyHasPrice:
    def test_flagged_correctly(self):
        item = _make_parsed(name_en="Dragon's Fire", set_code="AFR", cn="139")
        entry = _FakeEntry(
            1,
            name_en="Dragon's Fire",
            set_code="afr",
            collector_number="139",
            acquisition_price=Decimal("5.00"),
        )
        report = match_purchases([item], [entry])
        assert report.matched[0].already_has_price is True
        assert report.matched[0].current_acquisition_price == Decimal("5.00")

    def test_prefers_entry_without_price(self):
        item = _make_parsed(name_en="Dragon's Fire")
        entry1 = _FakeEntry(1, name_en="Dragon's Fire", acquisition_price=Decimal("5.00"))
        entry2 = _FakeEntry(2, name_en="Dragon's Fire", acquisition_price=None)
        report = match_purchases([item], [entry1, entry2])
        assert report.matched[0].collection_entry_id == 2
        assert report.matched[0].already_has_price is False


# ---------------------------------------------------------------------------
# DFC prefix match
# ---------------------------------------------------------------------------


class TestDfcMatch:
    def test_front_face_matches_dfc_entry(self):
        """Parsed 'Terror of the Peaks' matches 'Terror of the Peaks // Back'."""
        item = _make_parsed(name_en="Terror of the Peaks")
        entry = _FakeEntry(1, name_en="Terror of the Peaks // Some Back Face")
        report = match_purchases([item], [entry])
        assert len(report.matched) == 1
        assert report.matched[0].confidence == 0.7

    def test_dfc_entry_matches_front_only_parsed(self):
        """Collection has front // back, parsed has just front."""
        item = _make_parsed(name_en="Delver of Secrets", set_code="MID", cn="47")
        entry = _FakeEntry(
            1,
            name_en="Delver of Secrets // Insectile Aberration",
            set_code="mid",
            collector_number="47",
        )
        report = match_purchases([item], [entry])
        assert len(report.matched) == 1
        assert report.matched[0].confidence == 1.0


# ---------------------------------------------------------------------------
# Special characters
# ---------------------------------------------------------------------------


class TestSpecialChars:
    def test_apostrophe(self):
        item = _make_parsed(name_en="Sarkhan's Triumph", set_code="DTK")
        entry = _FakeEntry(1, name_en="Sarkhan's Triumph", set_code="dtk")
        report = match_purchases([item], [entry])
        assert len(report.matched) == 1


# ---------------------------------------------------------------------------
# Duplicate detection
# ---------------------------------------------------------------------------


class TestDuplicateDetection:
    def test_multiple_parsed_same_entry(self):
        item1 = _make_parsed(name_en="Dragon's Fire", set_code="AFR", order_number="#1")
        item2 = _make_parsed(name_en="Dragon's Fire", set_code="AFR", order_number="#2")
        entry = _FakeEntry(1, name_en="Dragon's Fire", set_code="afr")
        report = match_purchases([item1, item2], [entry])
        assert report.total_matched == 2
        assert len(report.warnings) >= 1
        assert "Multiple parsed items" in report.warnings[0]


# ---------------------------------------------------------------------------
# Report totals
# ---------------------------------------------------------------------------


class TestReportTotals:
    def test_totals(self):
        items = [
            _make_parsed(name_en="Dragon's Fire", set_code="AFR"),
            _make_parsed(name_en="Unknown Card"),
        ]
        entry = _FakeEntry(1, name_en="Dragon's Fire", set_code="afr")
        report = match_purchases(items, [entry])
        assert report.total_parsed == 2
        assert report.total_matched == 1
        assert len(report.matched) == 1
        assert len(report.unmatched) == 1
