"""Tests for MYP variant set code mapping utility."""

from __future__ import annotations

import pytest

from src.utils.set_code_map import map_to_scryfall_set_code


class TestKnownVariantMappings:
    """Each known variant code maps to the correct Scryfall set code."""

    @pytest.mark.parametrize(
        "myp_code, expected",
        [
            # Borderless
            ("bldmr", "dmr"),
            ("blfdn", "fdn"),
            ("bl2x2", "2x2"),
            ("bltr", "ltr"),
            ("blltr", "ltr"),
            # Extended Art
            ("exdmu", "dmu"),
            ("eafic", "fic"),
            ("eahoc", "hoc"),
            # Showcase
            ("srltr", "ltr"),
            ("skmh2", "mh2"),
            # Full-art / Etched
            ("feclb", "clb"),
            ("fesnc", "snc"),
            # Special/Misc
            ("smbro", "bro"),
            # Commander Borderless
            ("cbznr", "znr"),
            # Commander variant
            ("cthb", "thb"),
            # Bundle/Box
            ("bbfdn", "fdn"),
            # Draft/Hobby
            ("dhhob", "hob"),
            # Draft variant
            ("dftdm", "tdm"),
            # Gift variant
            ("gftdm", "tdm"),
            # Promo/Prerelease
            ("pltr", "ltr"),
            # Vault/Visual
            ("vvow", "vow"),
            # Special Commander
            ("schob", "hob"),
            ("schoc", "hoc"),
            # Art Series
            ("ashob", "hob"),
        ],
    )
    def test_known_variant(self, myp_code: str, expected: str) -> None:
        assert map_to_scryfall_set_code(myp_code) == expected


class TestSecretLair:
    """Secret Lair codes with numeric suffixes map to 'sld'."""

    @pytest.mark.parametrize("code", ["sld158", "sld1", "sld99999", "SLD42"])
    def test_secret_lair_with_digits(self, code: str) -> None:
        assert map_to_scryfall_set_code(code) == "sld"


class TestPassthrough:
    """Standard set codes pass through unchanged."""

    @pytest.mark.parametrize("code", ["dmr", "dmu", "ltr", "clb", "snc", "2x2"])
    def test_standard_code_unchanged(self, code: str) -> None:
        assert map_to_scryfall_set_code(code) == code


class TestUnknownCodes:
    """Unknown codes return unchanged (lowercased), no crash."""

    @pytest.mark.parametrize("code", ["xyz", "unknown123", "a", ""])
    def test_unknown_code_returns_lowercased(self, code: str) -> None:
        assert map_to_scryfall_set_code(code) == code.lower()


class TestCaseInsensitive:
    """Input is case-insensitive."""

    @pytest.mark.parametrize(
        "myp_code, expected",
        [
            ("BLDMR", "dmr"),
            ("BLdmr", "dmr"),
            ("Bldmr", "dmr"),
            ("EXDMU", "dmu"),
            ("SLD158", "sld"),
            ("DMR", "dmr"),
        ],
    )
    def test_case_insensitive(self, myp_code: str, expected: str) -> None:
        assert map_to_scryfall_set_code(myp_code) == expected


class TestPrefixHeuristic:
    """Unknown codes with known prefixes get prefix stripped."""

    @pytest.mark.parametrize(
        "myp_code, expected",
        [
            ("blxyz", "xyz"),
            ("exabc", "abc"),
            ("eaqrs", "qrs"),
            ("skfoo", "foo"),
            ("febar", "bar"),
            # ash prefix (3-char) — ensure heuristic works for longer prefixes
            ("ashxyz", "xyz"),
            # vv prefix
            ("vvnew", "new"),
        ],
    )
    def test_prefix_stripping_heuristic(self, myp_code: str, expected: str) -> None:
        assert map_to_scryfall_set_code(myp_code) == expected

    def test_single_char_remainder_not_stripped(self) -> None:
        """Remainder must be 2-5 chars to be treated as a set code."""
        # "bla" has prefix "bl" + remainder "a" (1 char) — too short
        assert map_to_scryfall_set_code("bla") == "bla"

    def test_long_remainder_not_stripped(self) -> None:
        """Remainder > 5 chars is not treated as a set code."""
        assert map_to_scryfall_set_code("blabcdef") == "blabcdef"
