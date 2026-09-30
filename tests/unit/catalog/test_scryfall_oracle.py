"""Tests for oracle_text extraction in Scryfall parsing."""

from __future__ import annotations

from src.catalog.scryfall import _parse_card


class TestParseCardOracleText:
    """Verify _parse_card extracts oracle_text correctly."""

    def _base_raw(self, **overrides) -> dict:
        raw = {
            "name": "Lightning Bolt",
            "set": "lea",
            "collector_number": "161",
            "rarity": "common",
            "color_identity": ["R"],
            "mana_cost": "{R}",
            "type_line": "Instant",
            "games": ["paper"],
            "lang": "en",
            "image_uris": {"normal": "http://img/bolt.jpg"},
        }
        raw.update(overrides)
        return raw

    def test_simple_oracle_text(self):
        raw = self._base_raw(oracle_text="Lightning Bolt deals 3 damage to any target.")
        card = _parse_card(raw)
        assert card is not None
        assert card.oracle_text == "Lightning Bolt deals 3 damage to any target."

    def test_missing_oracle_text_defaults_empty(self):
        raw = self._base_raw()
        # No oracle_text key at all
        card = _parse_card(raw)
        assert card is not None
        assert card.oracle_text == ""

    def test_empty_oracle_text_string(self):
        raw = self._base_raw(oracle_text="")
        card = _parse_card(raw)
        assert card is not None
        assert card.oracle_text == ""

    def test_dfc_oracle_text_from_card_faces(self):
        raw = self._base_raw(
            oracle_text="",
            card_faces=[
                {"oracle_text": "Front face text."},
                {"oracle_text": "Back face text."},
            ],
        )
        card = _parse_card(raw)
        assert card is not None
        assert card.oracle_text == "Front face text.\nBack face text."

    def test_dfc_single_face_with_oracle(self):
        raw = self._base_raw(
            oracle_text="",
            card_faces=[
                {"oracle_text": "Only front."},
                {},
            ],
        )
        card = _parse_card(raw)
        assert card is not None
        assert card.oracle_text == "Only front."

    def test_oracle_text_takes_priority_over_faces(self):
        raw = self._base_raw(
            oracle_text="Direct text.",
            card_faces=[
                {"oracle_text": "Front."},
            ],
        )
        card = _parse_card(raw)
        assert card is not None
        assert card.oracle_text == "Direct text."

    def test_non_paper_card_filtered_out(self):
        raw = self._base_raw(games=["arena"], oracle_text="Some text")
        card = _parse_card(raw)
        assert card is None

    def test_non_english_card_filtered_out(self):
        raw = self._base_raw(lang="ja", oracle_text="Some text")
        card = _parse_card(raw)
        assert card is None
