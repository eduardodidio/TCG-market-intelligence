"""Tests for Scryfall card parsing, including DFC image URI fallback."""

from src.catalog.scryfall import _parse_card


def _base_card(**overrides) -> dict:
    """Build a minimal Scryfall card dict for testing."""
    card = {
        "name": "Lightning Bolt",
        "set": "m21",
        "collector_number": "199",
        "rarity": "uncommon",
        "color_identity": ["R"],
        "mana_cost": "{R}",
        "type_line": "Instant",
        "games": ["paper"],
        "lang": "en",
        "image_uris": {
            "normal": "https://cards.scryfall.io/normal/front/bolt.jpg",
        },
    }
    card.update(overrides)
    return card


class TestParseCardImageUri:
    """Tests for _parse_card image_uri extraction."""

    def test_standard_card_uses_top_level_image_uris(self):
        """Standard cards have image_uris at the top level."""
        raw = _base_card()
        card = _parse_card(raw)
        assert card is not None
        assert card.image_uri == "https://cards.scryfall.io/normal/front/bolt.jpg"

    def test_dfc_uses_card_faces_fallback(self):
        """Double-faced cards have no top-level image_uris; use card_faces[0]."""
        raw = _base_card(
            name="Fable of the Mirror-Breaker // Reflection of Kiki-Jiki",
            image_uris=None,  # DFCs have no top-level image_uris
            card_faces=[
                {
                    "name": "Fable of the Mirror-Breaker",
                    "image_uris": {
                        "normal": "https://cards.scryfall.io/normal/front/fable.jpg",
                    },
                },
                {
                    "name": "Reflection of Kiki-Jiki",
                    "image_uris": {
                        "normal": "https://cards.scryfall.io/normal/back/fable.jpg",
                    },
                },
            ],
        )
        card = _parse_card(raw)
        assert card is not None
        assert card.image_uri == "https://cards.scryfall.io/normal/front/fable.jpg"

    def test_card_with_neither_image_uris_nor_faces(self):
        """Cards with no image_uris and no card_faces get image_uri=None."""
        raw = _base_card(image_uris=None)
        # Ensure no card_faces key at all
        raw.pop("card_faces", None)
        card = _parse_card(raw)
        assert card is not None
        assert card.image_uri is None

    def test_dfc_with_faces_but_no_face_image_uris(self):
        """DFC where card_faces[0] exists but has no image_uris."""
        raw = _base_card(
            name="Some DFC // Back Side",
            image_uris=None,
            card_faces=[
                {"name": "Some DFC"},  # no image_uris key
                {"name": "Back Side"},
            ],
        )
        card = _parse_card(raw)
        assert card is not None
        assert card.image_uri is None

    def test_dfc_with_empty_card_faces_list(self):
        """DFC with an empty card_faces list stays None."""
        raw = _base_card(image_uris=None, card_faces=[])
        card = _parse_card(raw)
        assert card is not None
        assert card.image_uri is None

    def test_non_paper_card_filtered_out(self):
        """Non-paper cards return None from _parse_card."""
        raw = _base_card(games=["arena"])
        assert _parse_card(raw) is None

    def test_non_english_card_filtered_out(self):
        """Non-English cards return None from _parse_card."""
        raw = _base_card(lang="pt")
        assert _parse_card(raw) is None

    def test_top_level_image_uris_takes_priority_over_faces(self):
        """If top-level image_uris exists, card_faces is not consulted."""
        raw = _base_card(
            card_faces=[
                {
                    "name": "Front",
                    "image_uris": {
                        "normal": "https://cards.scryfall.io/normal/front/face.jpg",
                    },
                },
            ],
        )
        card = _parse_card(raw)
        assert card is not None
        # Should use top-level, not face
        assert card.image_uri == "https://cards.scryfall.io/normal/front/bolt.jpg"
