"""Tests for _scryfall_image_url with set code mapping."""

from __future__ import annotations

from src.api.routers.collection import _scryfall_image_url


class TestScryfallImageUrl:
    """Verify that _scryfall_image_url maps variant set codes correctly."""

    def test_borderless_bldmr(self):
        url = _scryfall_image_url("bldmr", "437")
        assert "/cards/dmr/437?" in url
        assert "format=image" in url
        assert "version=normal" in url

    def test_extended_art_exdmu(self):
        url = _scryfall_image_url("exdmu", "410")
        assert "/cards/dmu/410?" in url

    def test_secret_lair_sld158(self):
        url = _scryfall_image_url("sld158", "1245")
        assert "/cards/sld/1245?" in url

    def test_standard_code_passthrough(self):
        url = _scryfall_image_url("dmr", "100")
        assert "/cards/dmr/100?" in url

    def test_standard_code_passthrough_dmu(self):
        url = _scryfall_image_url("dmu", "42")
        assert "/cards/dmu/42?" in url

    def test_showcase_srltr(self):
        url = _scryfall_image_url("srltr", "55")
        assert "/cards/ltr/55?" in url

    def test_borderless_bl2x2(self):
        url = _scryfall_image_url("bl2x2", "300")
        assert "/cards/2x2/300?" in url

    def test_uppercase_input(self):
        url = _scryfall_image_url("BLDMR", "437")
        assert "/cards/dmr/437?" in url

    def test_url_format(self):
        url = _scryfall_image_url("dmr", "100")
        assert url == ("https://api.scryfall.com/cards/dmr/100" "?format=image&version=normal")
