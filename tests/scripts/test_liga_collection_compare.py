"""Tests for scripts/liga_collection_compare.py.

Covers: normalize_diacritics, directional status, hint classification,
and the BRL price parser.
"""

from __future__ import annotations

# The script inserts its parent-parent into sys.path, so we can import
# its public functions directly after path setup.
import sys
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from scripts.liga_collection_compare import (
    _parse_brl,
    classify_hint,
    normalize_diacritics,
)


# ---------------------------------------------------------------------------
# normalize_diacritics
# ---------------------------------------------------------------------------
class TestNormalizeDiacritics:
    """LOTR-themed diacritical names must be stripped cleanly."""

    def test_acute_accent(self):
        assert normalize_diacritics("Dáin") == "Dain"

    def test_acute_u(self):
        assert normalize_diacritics("Andúril") == "Anduril"

    def test_circumflex(self):
        assert normalize_diacritics("Barad-dûr") == "Barad-dur"

    def test_acute_e(self):
        assert normalize_diacritics("Sméagol") == "Smeagol"

    def test_tilde(self):
        assert normalize_diacritics("São Paulo") == "Sao Paulo"

    def test_cedilla(self):
        assert normalize_diacritics("Ação") == "Acao"

    def test_no_change_for_ascii(self):
        assert normalize_diacritics("Lightning Bolt") == "Lightning Bolt"

    def test_empty_string(self):
        assert normalize_diacritics("") == ""

    def test_multiple_accents(self):
        assert normalize_diacritics("Théodèn") == "Theoden"

    def test_umlaut(self):
        assert normalize_diacritics("Düsseldorf") == "Dusseldorf"

    def test_preserves_non_combining_specials(self):
        # Hyphens, slashes, spaces remain
        assert normalize_diacritics("Barad-dûr // Ação") == "Barad-dur // Acao"


# ---------------------------------------------------------------------------
# Directional status logic
# ---------------------------------------------------------------------------
class TestDirectionalStatus:
    """Verify directional status assignment from diff_pct values.

    We replicate the logic from compare_with_db inline to test the
    classification without needing a database connection.
    """

    @staticmethod
    def _classify_status(our_price: float, liga_price: float) -> str:
        """Replicate the status logic from compare_with_db."""
        diff = our_price - liga_price
        diff_pct = (diff / liga_price * 100) if liga_price > 0 else 0
        abs_pct = abs(diff_pct)
        is_above = diff_pct > 0

        if abs_pct > 50:
            return "BIG_ABOVE" if is_above else "BIG_BELOW"
        elif abs_pct > 20:
            return "MISMATCH_ABOVE" if is_above else "MISMATCH_BELOW"
        elif abs_pct > 5:
            return "DRIFT"
        return "OK"

    def test_big_above(self):
        # our=100, liga=50 -> +100% -> BIG_ABOVE
        assert self._classify_status(100, 50) == "BIG_ABOVE"

    def test_big_below(self):
        # our=50, liga=100 -> -50% -> exactly at boundary, need >50
        # our=40, liga=100 -> -60% -> BIG_BELOW
        assert self._classify_status(40, 100) == "BIG_BELOW"

    def test_mismatch_above(self):
        # our=130, liga=100 -> +30% -> MISMATCH_ABOVE
        assert self._classify_status(130, 100) == "MISMATCH_ABOVE"

    def test_mismatch_below(self):
        # our=75, liga=100 -> -25% -> MISMATCH_BELOW
        assert self._classify_status(75, 100) == "MISMATCH_BELOW"

    def test_drift(self):
        # our=110, liga=100 -> +10% -> DRIFT
        assert self._classify_status(110, 100) == "DRIFT"

    def test_ok(self):
        # our=103, liga=100 -> +3% -> OK
        assert self._classify_status(103, 100) == "OK"

    def test_exact_match(self):
        assert self._classify_status(100, 100) == "OK"

    def test_boundary_50_above(self):
        # our=150, liga=100 -> +50% -> exactly 50 is NOT > 50, so MISMATCH_ABOVE
        assert self._classify_status(150, 100) == "MISMATCH_ABOVE"

    def test_boundary_50_below(self):
        # our=50, liga=100 -> -50% -> exactly 50 is NOT > 50, so MISMATCH_BELOW
        assert self._classify_status(50, 100) == "MISMATCH_BELOW"

    def test_boundary_20_above(self):
        # our=120, liga=100 -> +20% -> exactly 20 is NOT > 20, so DRIFT
        assert self._classify_status(120, 100) == "DRIFT"

    def test_boundary_5(self):
        # our=105, liga=100 -> +5% -> exactly 5 is NOT > 5, so OK
        assert self._classify_status(105, 100) == "OK"

    def test_just_over_big_above(self):
        # our=151, liga=100 -> +51% -> BIG_ABOVE
        assert self._classify_status(151, 100) == "BIG_ABOVE"


# ---------------------------------------------------------------------------
# classify_hint
# ---------------------------------------------------------------------------
class TestClassifyHint:
    """Root-cause hint classification."""

    def test_foil_card(self):
        assert classify_hint("Card Name", "Foil", "Set Name", Decimal("10"), 30.0) == "foil_card"

    def test_foil_with_other_extras(self):
        assert classify_hint("Card", "Foil Etched", "Set", Decimal("10"), 30.0) == "foil_card"

    def test_dfc_card(self):
        assert classify_hint("Jace // Vryn", None, "Set", Decimal("10"), 30.0) == "dfc_card"

    def test_art_series_edition(self):
        assert classify_hint("Mountain", None, "Art Series: MH3", Decimal("5"), 30.0) == "art_card"

    def test_art_card_name(self):
        assert classify_hint("Art Card #42", None, "Regular Set", Decimal("5"), 30.0) == "art_card"

    def test_promo(self):
        assert classify_hint("Card", "Promo", "Set", Decimal("10"), 30.0) == "promo"

    def test_pre_release(self):
        assert classify_hint("Card", "Pre Release", "Set", Decimal("10"), 30.0) == "promo"

    def test_variant_edition_variantes(self):
        assert classify_hint("Card", None, "Set (Variantes)", Decimal("10"), 30.0) == "variant_ed"

    def test_variant_edition_borderless(self):
        assert classify_hint("Card", None, "Set (Borderless)", Decimal("10"), 30.0) == "variant_ed"

    def test_variant_edition_showcase(self):
        assert classify_hint("Card", None, "Set (Showcase)", Decimal("10"), 30.0) == "variant_ed"

    def test_variant_edition_retro(self):
        assert classify_hint("Card", None, "Set (Retro)", Decimal("10"), 30.0) == "variant_ed"

    def test_variant_edition_extended_art(self):
        result = classify_hint("Card", None, "Set (Extended Art)", Decimal("10"), 30.0)
        assert result == "variant_ed"

    def test_cheap_card(self):
        assert classify_hint("Card", None, "Set", Decimal("0.50"), 30.0) == "cheap_card"

    def test_cheap_card_boundary(self):
        # R$1.00 is NOT < R$1.00, so should NOT be cheap_card
        assert classify_hint("Card", None, "Set", Decimal("1.00"), 30.0) != "cheap_card"

    def test_expected(self):
        # Positive diff, no other flags, Liga > R$5
        assert classify_hint("Card", None, "Regular Set", Decimal("10.00"), 25.0) == "expected"

    def test_expected_requires_positive_diff(self):
        # Negative diff -> not expected
        assert classify_hint("Card", None, "Regular Set", Decimal("10.00"), -25.0) == ""

    def test_expected_requires_liga_above_5(self):
        # Liga = R$3 -> not expected (and not cheap_card since >= R$1)
        assert classify_hint("Card", None, "Regular Set", Decimal("3.00"), 25.0) == ""

    def test_no_hint(self):
        # Negative diff, Liga > R$5, no special flags -> empty
        assert classify_hint("Card", None, "Regular Set", Decimal("10.00"), -10.0) == ""

    def test_foil_takes_priority_over_dfc(self):
        # Card has both Foil extras AND " // " in name -> foil_card wins
        assert classify_hint("Front // Back", "Foil", "Set", Decimal("10"), 30.0) == "foil_card"

    def test_dfc_takes_priority_over_promo(self):
        # DFC name, but also Promo extras -> dfc_card wins (checked earlier)
        assert classify_hint("Front // Back", "Promo", "Set", Decimal("10"), 30.0) == "dfc_card"

    def test_none_extras_and_edition(self):
        # None extras and edition should not crash
        assert classify_hint("Card", None, None, Decimal("10"), 30.0) == "expected"

    def test_none_liga_buy(self):
        assert classify_hint("Card", None, "Set", None, 30.0) == ""


# ---------------------------------------------------------------------------
# _parse_brl
# ---------------------------------------------------------------------------
class TestParseBrl:
    """Brazilian Real price parsing."""

    def test_simple_price(self):
        assert _parse_brl("R$ 10,00") == Decimal("10.00")

    def test_thousands(self):
        assert _parse_brl("R$ 1.234,56") == Decimal("1234.56")

    def test_no_symbol(self):
        # Without R$ prefix — the function strips R$, so bare number should still work
        assert _parse_brl("10,50") == Decimal("10.50")

    def test_with_spaces(self):
        assert _parse_brl("  R$  42,99  ") == Decimal("42.99")

    def test_empty(self):
        assert _parse_brl("") is None

    def test_none_input(self):
        assert _parse_brl(None) is None

    def test_just_symbol(self):
        assert _parse_brl("R$ ") is None

    def test_zero(self):
        assert _parse_brl("R$ 0,00") == Decimal("0.00")

    def test_large_price(self):
        assert _parse_brl("R$ 12.345,67") == Decimal("12345.67")

    def test_cents_only(self):
        assert _parse_brl("R$ 0,50") == Decimal("0.50")

    def test_invalid_text(self):
        assert _parse_brl("abc") is None
