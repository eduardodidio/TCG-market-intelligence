"""Tests for DFC / split / variant card name handling in Liga sweep."""

from __future__ import annotations

from src.collectors.liga_sweep import _clean_card_name, _normalize_collector_number
from src.providers.liga.url import liga_url_for_card_name

# -- _clean_card_name tests --------------------------------------------------


def test_clean_card_name_strips_collector_number():
    assert _clean_card_name("Lightning Bolt (#333)") == "Lightning Bolt"


def test_clean_card_name_strips_art_card():
    assert _clean_card_name("Plains (Art Card)") == "Plains"
    assert _clean_card_name("Forest (Art Card with Signature)") == "Forest"


def test_clean_card_name_strips_borderless():
    assert _clean_card_name("Thoughtseize (Borderless)") == "Thoughtseize"


def test_clean_card_name_strips_extended_art():
    assert _clean_card_name("Jeweled Lotus (Extended Art)") == "Jeweled Lotus"


def test_clean_card_name_strips_showcase():
    assert _clean_card_name("Brainstorm (Showcase)") == "Brainstorm"


def test_clean_card_name_strips_etched():
    assert _clean_card_name("Swords to Plowshares (Etched)") == "Swords to Plowshares"


def test_clean_card_name_strips_retro_frame():
    assert _clean_card_name("Urza's Saga (Retro Frame)") == "Urza's Saga"


def test_clean_card_name_preserves_normal_names():
    """Regular card names without annotations stay unchanged."""
    assert _clean_card_name("Lightning Bolt") == "Lightning Bolt"
    assert _clean_card_name("Uro, Titan of Nature's Wrath") == "Uro, Titan of Nature's Wrath"
    assert _clean_card_name("Fire // Ice") == "Fire // Ice"


def test_clean_card_name_dfc_name_unchanged():
    """DFC names with ' // ' are left as-is; the URL builder handles splitting."""
    name = "The Arkenstone // Seek the Heart"
    assert _clean_card_name(name) == name


def test_clean_card_name_case_insensitive():
    """Variant annotations are matched case-insensitively."""
    assert _clean_card_name("Plains (BORDERLESS)") == "Plains"
    assert _clean_card_name("Forest (art card)") == "Forest"
    assert _clean_card_name("Island (extended art)") == "Island"


def test_clean_card_name_multiple_annotations():
    """Multiple annotations are all stripped."""
    assert _clean_card_name("Card (#123) (Borderless)") == "Card"


# -- _normalize_collector_number tests ----------------------------------------


def test_normalize_collector_number_strips_suffix():
    assert _normalize_collector_number("32a") == "32"
    assert _normalize_collector_number("44b") == "44"


def test_normalize_collector_number_no_suffix():
    assert _normalize_collector_number("367") == "367"


def test_normalize_collector_number_not_single_letter():
    """Mid-string letters are NOT stripped — only trailing single letter."""
    assert _normalize_collector_number("3a2") == "3a2"


def test_normalize_collector_number_none():
    assert _normalize_collector_number(None) is None


def test_normalize_collector_number_empty_string():
    assert _normalize_collector_number("") == ""


def test_normalize_collector_number_uppercase_ignored():
    """Only lowercase trailing letters are stripped."""
    assert _normalize_collector_number("32A") == "32A"


def test_normalize_collector_number_letters_only():
    """Pure letter strings are unchanged."""
    assert _normalize_collector_number("abc") == "abc"


# -- URL builder DFC test -----------------------------------------------------


def test_url_builder_dfc():
    """Verify liga_url_for_card_name splits DFC names and uses only the front face."""
    url = liga_url_for_card_name("The Arkenstone // Seek the Heart")
    assert "The+Arkenstone" in url
    assert "Seek" not in url
    assert "Heart" not in url
