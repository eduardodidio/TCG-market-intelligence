"""Tests for src.utils.image_fallback — Scryfall fallback URL construction."""

from __future__ import annotations

from src.utils.image_fallback import fallback_image_uri


class TestFallbackImageUri:
    """Unit tests for fallback_image_uri helper."""

    def test_art_series_set_code_mapped(self):
        """Art series 'ashob' maps to 'hob' and suffix 'a' stripped."""
        result = fallback_image_uri("ashob", "44a")
        assert result == ("https://api.scryfall.com/cards/hob/44" "?format=image&version=normal")

    def test_regular_set_no_mapping_needed(self):
        """Regular set code passes through unchanged."""
        result = fallback_image_uri("ltr", "123")
        assert result == ("https://api.scryfall.com/cards/ltr/123" "?format=image&version=normal")

    def test_none_set_code_returns_none(self):
        result = fallback_image_uri(None, "44a")
        assert result is None

    def test_none_collector_number_returns_none(self):
        result = fallback_image_uri("ashob", None)
        assert result is None

    def test_both_none_returns_none(self):
        result = fallback_image_uri(None, None)
        assert result is None

    def test_empty_string_set_code_returns_none(self):
        result = fallback_image_uri("", "44a")
        assert result is None

    def test_empty_string_collector_number_returns_none(self):
        result = fallback_image_uri("ashob", "")
        assert result is None

    def test_collector_number_all_letters_returns_none(self):
        """If stripping letters leaves nothing, return None."""
        result = fallback_image_uri("ltr", "abc")
        assert result is None

    def test_collector_number_no_suffix(self):
        """Collector number without letter suffix stays as-is."""
        result = fallback_image_uri("fdn", "42")
        assert result == ("https://api.scryfall.com/cards/fdn/42" "?format=image&version=normal")

    def test_known_variant_mapping(self):
        """Borderless variant 'bldmr' maps to 'dmr'."""
        result = fallback_image_uri("bldmr", "10")
        assert result == ("https://api.scryfall.com/cards/dmr/10" "?format=image&version=normal")

    def test_uppercase_set_code_lowered(self):
        """Set codes are lowercased for the URL."""
        result = fallback_image_uri("ASHOB", "44a")
        assert result == ("https://api.scryfall.com/cards/hob/44" "?format=image&version=normal")

    def test_multi_letter_suffix_stripped(self):
        """Multiple trailing letters are stripped (e.g. '123ab')."""
        result = fallback_image_uri("ltr", "123ab")
        assert result == ("https://api.scryfall.com/cards/ltr/123" "?format=image&version=normal")
