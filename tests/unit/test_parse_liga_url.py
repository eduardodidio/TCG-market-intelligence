"""Tests for parse_liga_card_url in src/providers/liga/url.py."""

from __future__ import annotations

import pytest

from src.providers.liga.url import parse_liga_card_url


class TestParseLigaCardUrl:
    """Unit tests for Liga URL parsing."""

    def test_basic_url_with_card_name(self):
        url = "https://www.ligamagic.com.br/?view=cards/card&card=Ajani+Goldmane"
        name, set_code = parse_liga_card_url(url)
        assert name == "Ajani Goldmane"
        assert set_code is None

    def test_url_with_card_and_edition(self):
        url = "https://www.ligamagic.com.br/?view=cards/card&card=Lightning+Bolt&ed=m14"
        name, set_code = parse_liga_card_url(url)
        assert name == "Lightning Bolt"
        assert set_code == "m14"

    def test_url_with_encoded_special_chars(self):
        url = "https://www.ligamagic.com.br/?view=cards/card&card=Jace%2C+the+Mind+Sculptor"
        name, set_code = parse_liga_card_url(url)
        assert name == "Jace, the Mind Sculptor"
        assert set_code is None

    def test_url_with_dfc_double_slash(self):
        url = "https://www.ligamagic.com.br/?view=cards/card&card=Delver+of+Secrets+%2F%2F+Insectile+Aberration"
        name, set_code = parse_liga_card_url(url)
        assert name == "Delver of Secrets // Insectile Aberration"

    def test_url_with_show_param(self):
        """Extra params like &show=1 should not interfere."""
        url = "https://www.ligamagic.com.br/?view=cards/card&card=Sol+Ring&show=1"
        name, set_code = parse_liga_card_url(url)
        assert name == "Sol Ring"
        assert set_code is None

    def test_url_with_edition_uppercase(self):
        url = "https://www.ligamagic.com.br/?view=cards/card&card=Sol+Ring&ed=CMR"
        name, set_code = parse_liga_card_url(url)
        assert set_code == "CMR"

    def test_invalid_domain_raises(self):
        with pytest.raises(ValueError, match="ligamagic.com.br"):
            parse_liga_card_url("https://www.google.com/?card=Test")

    def test_missing_card_param_raises(self):
        with pytest.raises(ValueError, match="card"):
            parse_liga_card_url("https://www.ligamagic.com.br/?view=cards/card")

    def test_empty_card_param_raises(self):
        with pytest.raises(ValueError, match="card"):
            parse_liga_card_url("https://www.ligamagic.com.br/?view=cards/card&card=")

    def test_blank_card_param_raises(self):
        with pytest.raises(ValueError, match="card"):
            parse_liga_card_url("https://www.ligamagic.com.br/?view=cards/card&card=+++")

    def test_http_url_accepted(self):
        url = "http://www.ligamagic.com.br/?view=cards/card&card=Mountain"
        name, _ = parse_liga_card_url(url)
        assert name == "Mountain"

    def test_subdomain_variant(self):
        url = "https://ligamagic.com.br/?view=cards/card&card=Forest"
        name, _ = parse_liga_card_url(url)
        assert name == "Forest"

    def test_empty_edition_ignored(self):
        url = "https://www.ligamagic.com.br/?view=cards/card&card=Island&ed="
        name, set_code = parse_liga_card_url(url)
        assert name == "Island"
        assert set_code is None
