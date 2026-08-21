"""Tests for deck text parser."""

from __future__ import annotations

from src.decks.parser import parse_deck_text


class TestParseBasicFormat:
    def test_qty_and_name(self):
        result = parse_deck_text("4 Lightning Bolt")
        assert len(result) == 1
        assert result[0]["name_en"] == "Lightning Bolt"
        assert result[0]["quantity"] == 4
        assert result[0]["set_code"] is None
        assert result[0]["collector_number"] is None

    def test_single_quantity(self):
        result = parse_deck_text("1 Counterspell")
        assert result[0]["quantity"] == 1

    def test_name_only_defaults_qty_1(self):
        result = parse_deck_text("Island")
        assert result[0]["name_en"] == "Island"
        assert result[0]["quantity"] == 1


class TestParseWithSet:
    def test_set_code(self):
        result = parse_deck_text("4 Lightning Bolt [LEA]")
        assert result[0]["set_code"] == "lea"
        assert result[0]["collector_number"] is None

    def test_set_and_number(self):
        result = parse_deck_text("4 Lightning Bolt [LEA:161]")
        assert result[0]["set_code"] == "lea"
        assert result[0]["collector_number"] == "161"

    def test_lowercase_set(self):
        result = parse_deck_text("2 Force of Will [ALL]")
        assert result[0]["set_code"] == "all"


class TestParseComments:
    def test_hash_comment(self):
        result = parse_deck_text("# This is a comment\n4 Lightning Bolt")
        assert len(result) == 1
        assert result[0]["name_en"] == "Lightning Bolt"

    def test_double_slash_comment(self):
        result = parse_deck_text("// Sideboard\n2 Pyroblast")
        assert len(result) == 1
        assert result[0]["name_en"] == "Pyroblast"


class TestParseEdgeCases:
    def test_empty_string(self):
        assert parse_deck_text("") == []

    def test_only_comments(self):
        assert parse_deck_text("# comment\n// another") == []

    def test_blank_lines(self):
        result = parse_deck_text("\n\n4 Bolt\n\n2 Island\n\n")
        assert len(result) == 2

    def test_whitespace_lines(self):
        result = parse_deck_text("   \n4 Bolt")
        assert len(result) == 1

    def test_multiword_name(self):
        result = parse_deck_text("4 Teferi, Hero of Dominaria")
        assert result[0]["name_en"] == "Teferi, Hero of Dominaria"

    def test_name_with_apostrophe(self):
        result = parse_deck_text("1 Urza's Tower")
        assert result[0]["name_en"] == "Urza's Tower"


class TestParseMultipleLines:
    def test_full_deck(self):
        text = """
# Main Deck
4 Lightning Bolt [LEA:161]
4 Chain Lightning [LEG]
4 Rift Bolt
20 Mountain

# Sideboard
// Not yet decided
"""
        result = parse_deck_text(text)
        assert len(result) == 4
        assert result[0]["name_en"] == "Lightning Bolt"
        assert result[0]["quantity"] == 4
        assert result[0]["set_code"] == "lea"
        assert result[0]["collector_number"] == "161"
        assert result[1]["name_en"] == "Chain Lightning"
        assert result[1]["set_code"] == "leg"
        assert result[2]["name_en"] == "Rift Bolt"
        assert result[2]["set_code"] is None
        assert result[3]["name_en"] == "Mountain"
        assert result[3]["quantity"] == 20
