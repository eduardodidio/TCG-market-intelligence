"""Comprehensive tests for the canonical Liga Magic URL builder.

Covers all card name variants: normal, split/DFC, commas, apostrophes,
accented characters, whitespace, empty strings, and real collection data.
"""

from __future__ import annotations

import pytest

from src.providers.liga.url import liga_url_for_card_name

BASE = "https://www.ligamagic.com.br/?view=cards/card&card="


class TestLigaUrlBasic:
    """Basic URL construction."""

    def test_simple_name(self) -> None:
        url = liga_url_for_card_name("Lightning Bolt")
        assert url == f"{BASE}Lightning+Bolt&show=1"

    def test_single_word(self) -> None:
        url = liga_url_for_card_name("Raze")
        assert url == f"{BASE}Raze&show=1"

    def test_always_has_show_param(self) -> None:
        url = liga_url_for_card_name("Sol Ring")
        assert "&show=1" in url

    def test_always_has_base_url(self) -> None:
        url = liga_url_for_card_name("Sol Ring")
        assert url.startswith("https://www.ligamagic.com.br/?view=cards/card")


class TestLigaUrlSpecialChars:
    """Special character encoding."""

    def test_comma(self) -> None:
        url = liga_url_for_card_name("Thalia, Guardian of Thraben")
        assert "Thalia%2C+Guardian+of+Thraben" in url

    def test_apostrophe(self) -> None:
        url = liga_url_for_card_name("Frodo's Ring")
        assert "Frodo%27s+Ring" in url

    def test_colon(self) -> None:
        url = liga_url_for_card_name("Teferi: Master of Time")
        assert "Teferi%3A+Master+of+Time" in url

    def test_hyphen(self) -> None:
        url = liga_url_for_card_name("Gadrak, the Crown-Scourge")
        assert "Crown-Scourge" in url  # hyphens are not encoded

    def test_plus_sign(self) -> None:
        """Plus sign in name must be encoded (not confused with space)."""
        url = liga_url_for_card_name("+2 Mace")
        assert "%2B2+Mace" in url


class TestLigaUrlSplitDfc:
    """Split and double-faced card handling — front face only."""

    def test_split_card(self) -> None:
        url = liga_url_for_card_name("Fire // Ice")
        assert "card=Fire&" in url
        assert "Ice" not in url.split("card=")[1]

    def test_dfc_card(self) -> None:
        url = liga_url_for_card_name("Painter's Studio // Defaced Gallery")
        assert "Painter%27s+Studio" in url
        assert "Defaced" not in url

    def test_dfc_with_comma(self) -> None:
        url = liga_url_for_card_name("Beorn, Reluctant Host // Till and Tend")
        assert "Beorn%2C+Reluctant+Host" in url
        assert "Till" not in url

    def test_art_card_suffix(self) -> None:
        url = liga_url_for_card_name("The Arkenstone // Seek the Heart (Art Card with Signature)")
        assert "The+Arkenstone" in url
        assert "Seek" not in url

    def test_adventure_card(self) -> None:
        url = liga_url_for_card_name("Rimrock Knight // Boulder Rush")
        assert "Rimrock+Knight" in url
        assert "Boulder" not in url

    def test_modal_dfc(self) -> None:
        url = liga_url_for_card_name("Valki, God of Lies // Tibalt, Cosmic Impostor")
        assert "Valki%2C+God+of+Lies" in url
        assert "Tibalt" not in url


class TestLigaUrlEdgeCases:
    """Edge cases and whitespace handling."""

    def test_leading_trailing_whitespace(self) -> None:
        url = liga_url_for_card_name("  Lightning Bolt  ")
        assert "Lightning+Bolt" in url
        assert "+" * 2 not in url.split("card=")[1].split("&")[0]

    def test_empty_string(self) -> None:
        url = liga_url_for_card_name("")
        assert url.startswith("https://www.ligamagic.com.br/")
        assert "&show=1" in url

    def test_whitespace_only(self) -> None:
        url = liga_url_for_card_name("   ")
        assert url.startswith("https://www.ligamagic.com.br/")
        assert "&show=1" in url


class TestLigaUrlAccentedChars:
    """Portuguese/accented character encoding."""

    def test_portuguese_name(self) -> None:
        url = liga_url_for_card_name("Dain, Rei dos Anoes")
        assert "Dain%2C+Rei+dos+Anoes" in url

    def test_accented_a(self) -> None:
        url = liga_url_for_card_name("Mox de Ambar")
        assert "Mox+de+Ambar" in url

    def test_tilde(self) -> None:
        url = liga_url_for_card_name("Dragao")
        assert "Dragao" in url


# -- Parametrized tests with real card names from the collection --

REAL_CARD_CASES = [
    # (card_name, expected_substring_in_url)
    ("Dragonlord's Servant", "Dragonlord%27s+Servant"),
    ("Bolt Bend", "Bolt+Bend"),
    ("Mox Amber", "Mox+Amber"),
    ("Den of the Bugbear", "Den+of+the+Bugbear"),
    ("Dragon's Fire", "Dragon%27s+Fire"),
    ("Inferno of the Star Mounts", "Inferno+of+the+Star+Mounts"),
    ("The Book of Exalted Deeds", "The+Book+of+Exalted+Deeds"),
    ("Chimil, the Inner Sun", "Chimil%2C+the+Inner+Sun"),
    ("Ojer Taq, Deepest Foundation", "Ojer+Taq%2C+Deepest+Foundation"),
    ("Linvala, Keeper of Silence", "Linvala%2C+Keeper+of+Silence"),
    ("Shinka, the Bloodsoaked Keep", "Shinka%2C+the+Bloodsoaked+Keep"),
    ("Akroma, Angel of Wrath", "Akroma%2C+Angel+of+Wrath"),
    ("Sephara, Sky's Blade", "Sephara%2C+Sky%27s+Blade"),
    ("Ugin, the Spirit Dragon", "Ugin%2C+the+Spirit+Dragon"),
    ("Avacyn, Angel of Hope", "Avacyn%2C+Angel+of+Hope"),
    # Split/DFC real cards
    ("Painter's Studio // Defaced Gallery", "Painter%27s+Studio"),
    ("Beorn, Reluctant Host // Till and Tend", "Beorn%2C+Reluctant+Host"),
    ("Bilbo Baggins, Burglar // Take a Glance", "Bilbo+Baggins%2C+Burglar"),
    ("Bilbo, Luckwearer // Burglar's Plot", "Bilbo%2C+Luckwearer"),
    ("Rimrock Knight // Boulder Rush", "Rimrock+Knight"),
    ("Thranduil, Sindarin Liege // Silvan Rally", "Thranduil%2C+Sindarin+Liege"),
    ("Velvetwing Butterflies // Gaze in Wonder", "Velvetwing+Butterflies"),
]


@pytest.mark.parametrize(
    "card_name, expected_substring",
    REAL_CARD_CASES,
    ids=[c[0][:40] for c in REAL_CARD_CASES],
)
def test_real_card_url(card_name: str, expected_substring: str) -> None:
    """Verify Liga URL for real card names from the collection."""
    url = liga_url_for_card_name(card_name)
    assert expected_substring in url, f"Expected '{expected_substring}' in URL: {url}"
    assert "&show=1" in url
    assert url.startswith("https://www.ligamagic.com.br/?view=cards/card")
    # Split/DFC cards must NOT contain "//" in the URL
    card_param = url.split("card=")[1].split("&")[0]
    assert "%2F%2F" not in card_param, f"URL contains encoded '//': {url}"
