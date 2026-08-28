"""Tests for is_foil_entry() helper in src.collection.converter."""

from __future__ import annotations

import pytest

from src.collection.converter import is_foil_entry


class TestIsFoilEntry:
    """Unit tests for the is_foil_entry pure function."""

    def test_foil_uppercase(self) -> None:
        assert is_foil_entry("Foil") is True

    def test_foil_lowercase(self) -> None:
        assert is_foil_entry("foil") is True

    def test_foil_mixed_case(self) -> None:
        assert is_foil_entry("FOIL") is True

    def test_none_returns_false(self) -> None:
        assert is_foil_entry(None) is False

    def test_empty_string_returns_false(self) -> None:
        assert is_foil_entry("") is False

    def test_signed_only_returns_false(self) -> None:
        assert is_foil_entry("Signed") is False

    def test_foil_comma_signed(self) -> None:
        assert is_foil_entry("Foil, Signed") is True

    def test_signed_comma_foil(self) -> None:
        assert is_foil_entry("Signed, Foil") is True

    def test_foil_etched(self) -> None:
        assert is_foil_entry("Foil Etched") is True

    def test_unrelated_text(self) -> None:
        assert is_foil_entry("Promo") is False

    @pytest.mark.parametrize(
        "extras",
        ["Foil", "foil", "FOIL", "Foil, Signed", "Signed, Foil", "Foil Etched"],
    )
    def test_foil_variants_parametrized(self, extras: str) -> None:
        assert is_foil_entry(extras) is True

    @pytest.mark.parametrize(
        "extras",
        [None, "", "Signed", "Promo", "Altered"],
    )
    def test_non_foil_variants_parametrized(self, extras: str | None) -> None:
        assert is_foil_entry(extras) is False
