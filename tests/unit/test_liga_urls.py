"""Pure unit tests for src.providers.liga.urls — no mocks needed."""

from __future__ import annotations

import pytest

from src.providers.liga.urls import (
    LIGA_BASE_URL,
    build_liga_card_url,
    is_valid_liga_card_url,
    liga_external_id,
)


class TestBuildLigaCardUrl:
    def test_simple_name(self):
        assert (
            build_liga_card_url("Lightning Bolt")
            == f"{LIGA_BASE_URL}/?view=cards/card&card=Lightning+Bolt&show=1"
        )

    def test_name_with_comma(self):
        url = build_liga_card_url("Dain, Dwarven King")
        assert "Dain%2C+Dwarven+King" in url

    def test_name_with_apostrophe(self):
        url = build_liga_card_url("Jötun Grunt")
        assert url.startswith(f"{LIGA_BASE_URL}/?view=cards/card&card=")
        assert "show=1" in url

    def test_name_with_slash(self):
        url = build_liga_card_url("Fire // Ice")
        assert "Fire+%2F%2F+Ice" in url

    def test_strips_leading_trailing_spaces(self):
        assert build_liga_card_url("  Lightning Bolt  ") == build_liga_card_url("Lightning Bolt")


class TestIsValidLigaCardUrl:
    def test_valid_www_host(self):
        assert is_valid_liga_card_url("https://www.ligamagic.com.br/?view=cards/card&card=X") is True

    def test_valid_bare_host(self):
        assert is_valid_liga_card_url("https://ligamagic.com.br/?view=cards/card&card=X") is True

    def test_http_rejected(self):
        assert is_valid_liga_card_url("http://www.ligamagic.com.br/?view=cards/card") is False

    def test_foreign_host_rejected(self):
        assert is_valid_liga_card_url("https://evil.com/?view=cards/card") is False

    def test_wrong_view_rejected(self):
        assert is_valid_liga_card_url("https://www.ligamagic.com.br/?view=cards/search") is False

    def test_none_rejected(self):
        assert is_valid_liga_card_url(None) is False

    def test_empty_string_rejected(self):
        assert is_valid_liga_card_url("") is False

    def test_garbage_rejected(self):
        assert is_valid_liga_card_url("not a url") is False

    def test_1001_chars_rejected(self):
        base = "https://www.ligamagic.com.br/?view=cards/card&card="
        padding = "x" * (1001 - len(base))
        url = base + padding
        assert len(url) == 1001
        assert is_valid_liga_card_url(url) is False

    def test_1000_chars_accepted(self):
        base = "https://www.ligamagic.com.br/?view=cards/card&card="
        padding = "x" * (1000 - len(base))
        url = base + padding
        assert len(url) == 1000
        assert is_valid_liga_card_url(url) is True


class TestLigaExternalId:
    def test_normal(self):
        assert liga_external_id(42, False) == "liga_42"

    def test_foil(self):
        assert liga_external_id(42, True) == "liga_42_foil"

    def test_zero_card_id_boundary(self):
        assert liga_external_id(0, False) == "liga_0"
        assert liga_external_id(0, True) == "liga_0_foil"
