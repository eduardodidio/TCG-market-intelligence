"""Tests for src.collection.batch_parser — pure text parser."""

from __future__ import annotations

from decimal import Decimal

from src.collection.batch_parser import parse_batch_text


class TestParseQuantityAndName:
    """Basic quantity + card name parsing."""

    def test_qty_and_name(self) -> None:
        result = parse_batch_text("2 Lightning Bolt")
        assert len(result) == 1
        p = result[0]
        assert p.quantity == 2
        assert p.name == "Lightning Bolt"
        assert p.error is None

    def test_name_only_defaults_qty_1(self) -> None:
        result = parse_batch_text("Lightning Bolt")
        assert len(result) == 1
        assert result[0].quantity == 1
        assert result[0].name == "Lightning Bolt"

    def test_qty_with_x_suffix(self) -> None:
        result = parse_batch_text("2x Lightning Bolt")
        assert len(result) == 1
        assert result[0].quantity == 2
        assert result[0].name == "Lightning Bolt"

    def test_qty_with_x_and_set(self) -> None:
        result = parse_batch_text("2x Lightning Bolt [m15]")
        assert len(result) == 1
        p = result[0]
        assert p.quantity == 2
        assert p.name == "Lightning Bolt"
        assert p.set_code == "m15"


class TestSetCode:
    """Set code extraction in brackets."""

    def test_set_code_lowercase(self) -> None:
        result = parse_batch_text("Lightning Bolt [M15]")
        assert result[0].set_code == "m15"

    def test_set_code_preserved_in_name(self) -> None:
        result = parse_batch_text("2 Lightning Bolt [m15]")
        assert result[0].name == "Lightning Bolt"
        assert result[0].set_code == "m15"


class TestQualityLanguageExtras:
    """Quality, language, and extras parsing."""

    def test_full_format(self) -> None:
        result = parse_batch_text("2 Lightning Bolt [m15] NM EN Foil")
        assert len(result) == 1
        p = result[0]
        assert p.quantity == 2
        assert p.name == "Lightning Bolt"
        assert p.set_code == "m15"
        assert p.quality == "NM"
        assert p.language == "EN"
        assert p.extras == "Foil"
        assert p.error is None

    def test_quality_sp_language_br(self) -> None:
        result = parse_batch_text("3x Swords to Plowshares [ice] SP BR")
        assert len(result) == 1
        p = result[0]
        assert p.quantity == 3
        assert p.name == "Swords to Plowshares"
        assert p.set_code == "ice"
        assert p.quality == "SP"
        assert p.language == "BR"

    def test_all_quality_codes(self) -> None:
        for code in ("M", "NM", "SP", "MP", "HP", "D"):
            result = parse_batch_text(f"Test Card {code}")
            assert result[0].quality == code, f"Failed for quality code {code}"

    def test_extras_case_insensitive(self) -> None:
        result = parse_batch_text("Lightning Bolt foil")
        assert result[0].extras == "foil"
        assert result[0].name == "Lightning Bolt"

    def test_extras_promo(self) -> None:
        result = parse_batch_text("Lightning Bolt Promo")
        assert result[0].extras == "Promo"

    def test_extras_extended_art(self) -> None:
        result = parse_batch_text("Lightning Bolt Extended Art")
        assert result[0].extras == "Extended Art"

    def test_extras_etched(self) -> None:
        result = parse_batch_text("Lightning Bolt Etched")
        assert result[0].extras == "Etched"

    def test_extras_pre_release(self) -> None:
        result = parse_batch_text("Lightning Bolt Pre Release")
        assert result[0].extras == "Pre Release"

    def test_multiple_extras(self) -> None:
        result = parse_batch_text("Lightning Bolt Foil Promo")
        assert result[0].extras == "Foil, Promo"


class TestSkipLines:
    """Empty lines and comments are skipped."""

    def test_empty_line_skipped(self) -> None:
        result = parse_batch_text("")
        assert len(result) == 0

    def test_comment_skipped(self) -> None:
        result = parse_batch_text("# this is a comment")
        assert len(result) == 0

    def test_whitespace_only_skipped(self) -> None:
        result = parse_batch_text("   \t  ")
        assert len(result) == 0


class TestMultiLine:
    """Multi-line text parsing."""

    def test_multiple_lines(self) -> None:
        text = "2 Lightning Bolt\n1 Swords to Plowshares\nCounterspell"
        result = parse_batch_text(text)
        assert len(result) == 3
        assert result[0].name == "Lightning Bolt"
        assert result[0].quantity == 2
        assert result[1].name == "Swords to Plowshares"
        assert result[1].quantity == 1
        assert result[2].name == "Counterspell"
        assert result[2].quantity == 1

    def test_mixed_with_comments_and_blanks(self) -> None:
        text = "# My cards\n\n2 Lightning Bolt\n# another comment\nCounterspell\n"
        result = parse_batch_text(text)
        assert len(result) == 2
        assert result[0].name == "Lightning Bolt"
        assert result[1].name == "Counterspell"

    def test_line_numbers_correct(self) -> None:
        text = "# header\n\n2 Lightning Bolt\nCounterspell"
        result = parse_batch_text(text)
        assert result[0].line_number == 3
        assert result[1].line_number == 4


class TestErrors:
    """Error cases."""

    def test_no_card_name_after_qty(self) -> None:
        # "2 [m15]" has qty=2, set=m15, but no card name remaining
        result = parse_batch_text("2 [m15]")
        assert len(result) == 1
        assert result[0].error == "No card name found"

    def test_bare_number_treated_as_name(self) -> None:
        # "2" without trailing space is treated as card name, not qty
        result = parse_batch_text("2")
        assert len(result) == 1
        assert result[0].name == "2"
        assert result[0].quantity == 1
        assert result[0].error is None

    def test_raw_text_preserved(self) -> None:
        result = parse_batch_text("2 Lightning Bolt [m15] NM EN Foil")
        assert result[0].raw_text == "2 Lightning Bolt [m15] NM EN Foil"


class TestEdgeCases:
    """Edge cases."""

    def test_card_name_with_comma(self) -> None:
        result = parse_batch_text("Arlinn, the Pack's Hope")
        assert result[0].name == "Arlinn, the Pack's Hope"

    def test_card_name_with_apostrophe(self) -> None:
        result = parse_batch_text("Tasha's Hideous Laughter")
        assert result[0].name == "Tasha's Hideous Laughter"

    def test_large_quantity(self) -> None:
        result = parse_batch_text("99 Lightning Bolt")
        assert result[0].quantity == 99


class TestPrice:
    """Optional price token with currency (AC7)."""

    def test_brl_price_full_format(self) -> None:
        result = parse_batch_text("2 Lightning Bolt [m10] NM R$12,50")
        p = result[0]
        assert p.quantity == 2
        assert p.name == "Lightning Bolt"
        assert p.set_code == "m10"
        assert p.quality == "NM"
        assert p.price == Decimal("12.50")
        assert p.price_currency == "BRL"
        assert p.error is None

    def test_usd_price(self) -> None:
        result = parse_batch_text("Sol Ring US$3.10")
        p = result[0]
        assert p.name == "Sol Ring"
        assert p.price == Decimal("3.10")
        assert p.price_currency == "USD"

    def test_at_prefix_price_currency_none(self) -> None:
        result = parse_batch_text("Lightning Bolt @ 5,00")
        p = result[0]
        assert p.name == "Lightning Bolt"
        assert p.price == Decimal("5.00")
        assert p.price_currency is None

    def test_name_with_digits_no_price(self) -> None:
        result = parse_batch_text("Borrowing 100,000 Arrows")
        p = result[0]
        assert p.name == "Borrowing 100,000 Arrows"
        assert p.price is None
        assert p.price_currency is None
        assert p.error is None

    def test_price_before_set_code(self) -> None:
        result = parse_batch_text("Lightning Bolt R$12,50 [m10]")
        p = result[0]
        assert p.name == "Lightning Bolt"
        assert p.set_code == "m10"
        assert p.price == Decimal("12.50")
        assert p.price_currency == "BRL"

    def test_two_price_tokens_last_wins(self) -> None:
        result = parse_batch_text("Lightning Bolt R$5,00 US$3.10")
        p = result[0]
        assert p.price == Decimal("3.10")
        assert p.price_currency == "USD"

    def test_price_with_space_after_symbol(self) -> None:
        result = parse_batch_text("Lightning Bolt R$ 12,50")
        assert result[0].price == Decimal("12.50")
        assert result[0].price_currency == "BRL"

    def test_lowercase_symbol(self) -> None:
        result = parse_batch_text("lightning bolt r$12,50")
        assert result[0].price == Decimal("12.50")
        assert result[0].price_currency == "BRL"

    def test_symbol_not_followed_by_digit_no_match(self) -> None:
        result = parse_batch_text("Lightning Bolt R$abc")
        p = result[0]
        assert p.price is None
        assert p.price_currency is None
        assert p.error is None
        assert "R$abc" in p.name

    def test_invalid_price_multiple_separators(self) -> None:
        result = parse_batch_text("Lightning Bolt R$1.2.3,4,5")
        p = result[0]
        assert p.price is None
        assert p.error == "Invalid price: 1.2.3,4,5"

    def test_price_boundary_min(self) -> None:
        result = parse_batch_text("Lightning Bolt R$0,01")
        assert result[0].price == Decimal("0.01")
        assert result[0].error is None

    def test_price_above_limit_is_error(self) -> None:
        result = parse_batch_text("Lightning Bolt R$1000000,01")
        p = result[0]
        assert p.price is None
        assert p.error == "Invalid price: 1000000,01"
