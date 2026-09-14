"""Pure unit tests for src.providers.liga.urls — no mocks needed."""

from __future__ import annotations

import pytest

from src.providers.liga.urls import (
    LIGA_BASE_URL,
    build_liga_card_url,
    is_valid_liga_card_url,
    liga_external_id,
    resolve_liga_card_url,
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


class TestResolveLigaCardUrl:
    _STORED = "https://www.ligamagic.com.br/?view=cards/card&card=123&show=1"
    _STORED_FOIL = "https://www.ligamagic.com.br/?view=cards/card&card=123f&show=1"

    def test_returns_stored_non_foil(self):
        store = {"liga_7": self._STORED}
        url = resolve_liga_card_url(
            7, is_foil=False, fallback_name="Bolt", lookup=store.get
        )
        assert url == self._STORED

    def test_foil_prefers_foil_key(self):
        store = {"liga_7": self._STORED, "liga_7_foil": self._STORED_FOIL}
        url = resolve_liga_card_url(
            7, is_foil=True, fallback_name="Bolt", lookup=store.get
        )
        assert url == self._STORED_FOIL

    def test_foil_falls_back_to_non_foil_key(self):
        store = {"liga_7": self._STORED}
        url = resolve_liga_card_url(
            7, is_foil=True, fallback_name="Bolt", lookup=store.get
        )
        assert url == self._STORED

    def test_non_foil_never_reads_foil_key(self):
        store = {"liga_7_foil": self._STORED_FOIL}
        url = resolve_liga_card_url(
            7, is_foil=False, fallback_name="Lightning Bolt", lookup=store.get
        )
        assert url == build_liga_card_url("Lightning Bolt")

    def test_invalid_stored_url_falls_back_to_name(self):
        store = {"liga_7": "https://evil.com/?view=cards/card"}
        url = resolve_liga_card_url(
            7, is_foil=False, fallback_name="Lightning Bolt", lookup=store.get
        )
        assert url == build_liga_card_url("Lightning Bolt")

    def test_no_card_id_uses_name_without_lookup(self):
        calls: list[str] = []

        def lookup(key: str) -> str | None:
            calls.append(key)
            return None

        url = resolve_liga_card_url(
            None, is_foil=False, fallback_name="Lightning Bolt", lookup=lookup
        )
        assert url == build_liga_card_url("Lightning Bolt")
        assert calls == []  # lookup never called when card_id is None

    def test_no_stored_and_no_name_returns_none(self):
        url = resolve_liga_card_url(
            7, is_foil=False, fallback_name="", lookup=lambda _k: None
        )
        assert url is None
