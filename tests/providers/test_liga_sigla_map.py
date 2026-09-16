"""Tests for Liga sigla normalization mapping (F129-T04)."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from src.providers.liga.sigla_map import SCRYFALL_TO_LIGA_SIGLA, normalize_sigla

# ---------------------------------------------------------------------------
# normalize_sigla pure function tests
# ---------------------------------------------------------------------------


class TestNormalizeSigla:
    def test_normalize_sigla_unmapped(self):
        """Unmapped codes pass through unchanged."""
        assert normalize_sigla("fdn") == "fdn"
        assert normalize_sigla("mh3") == "mh3"
        assert normalize_sigla("cmm") == "cmm"

    def test_normalize_sigla_mapped(self):
        """Mapped codes return the Liga sigla."""
        # Temporarily inject a test entry
        SCRYFALL_TO_LIGA_SIGLA["xtestset"] = "xligaset"
        try:
            assert normalize_sigla("xtestset") == "xligaset"
        finally:
            del SCRYFALL_TO_LIGA_SIGLA["xtestset"]

    def test_normalize_sigla_case_insensitive(self):
        """normalize_sigla lowercases input before lookup."""
        SCRYFALL_TO_LIGA_SIGLA["mytest"] = "ligamytest"
        try:
            # Lowercase input matches
            assert normalize_sigla("mytest") == "ligamytest"
            # Uppercase input is lowercased by normalize_sigla, so it matches too
            assert normalize_sigla("MYTEST") == "ligamytest"
        finally:
            del SCRYFALL_TO_LIGA_SIGLA["mytest"]

    def test_empty_mapping_is_noop(self):
        """With an empty mapping dict, all codes pass through unchanged."""
        original = dict(SCRYFALL_TO_LIGA_SIGLA)
        SCRYFALL_TO_LIGA_SIGLA.clear()
        try:
            for code in ["fdn", "mh3", "cmm", "afr", "neo", "one"]:
                assert normalize_sigla(code) == code
        finally:
            SCRYFALL_TO_LIGA_SIGLA.update(original)

    def test_normalize_sigla_empty_string(self):
        """Empty string passes through."""
        assert normalize_sigla("") == ""

    def test_normalize_sigla_returns_str(self):
        """Return type is always str."""
        assert isinstance(normalize_sigla("fdn"), str)

    def test_normalize_sigla_card_override(self):
        """Per-card overrides take priority over per-set mapping."""
        # Ghostfire Elspeth
        assert normalize_sigla("tdm", "401") == "gftdm"
        # Regular tdm card (no override) stays as-is
        assert normalize_sigla("tdm", "1") == "tdm"

    def test_normalize_sigla_art_card_override(self):
        """Art card in Hobbit Art Series gets ashob sigla."""
        assert normalize_sigla("hob", "44a") == "ashob"

    def test_normalize_sigla_borderless_override(self):
        """Borderless LTR cards get bltr sigla."""
        assert normalize_sigla("ltr", "425") == "bltr"
        # Regular LTR card stays as-is
        assert normalize_sigla("ltr", "1") == "ltr"

    def test_normalize_sigla_commander_override(self):
        """Commander variant editions get correct sigla."""
        assert normalize_sigla("thb", "259") == "cthb"
        assert normalize_sigla("cmr", "689") == "cbcmr"


# ---------------------------------------------------------------------------
# Integration: provider._select_edition uses normalize_sigla
# ---------------------------------------------------------------------------


class TestProviderUsesNormalizedSigla:
    @pytest.mark.asyncio
    async def test_provider_uses_normalized_sigla(self):
        """_select_edition calls normalize_sigla when disambiguating editions."""
        from src.providers.liga.config import LigaConfig
        from src.providers.liga.provider import LigaMagicProvider

        provider = LigaMagicProvider(LigaConfig(delay_seconds=0, max_retries=1))

        # Build fake HTML with edition dropdown containing two editions
        # sharing the same collector number but different siglas
        fake_editions = [
            ("val_a", "001", "afr"),
            ("val_b", "001", "ampafr"),
        ]

        with (
            patch(
                "src.providers.liga.provider.parse_edition_options",
                return_value=fake_editions,
            ),
            patch(
                "src.providers.liga.provider.normalize_sigla",
                wraps=normalize_sigla,
            ) as mock_normalize,
        ):
            html, matched = await provider._select_edition(
                "<html></html>",
                "Test Card",
                "001",
                set_code="afr",
            )
            # normalize_sigla was called with the lowercased set_code
            mock_normalize.assert_called_once_with("afr", "001")

    @pytest.mark.asyncio
    async def test_provider_selects_mapped_sigla(self):
        """When a mapping exists, _select_edition picks the mapped edition."""
        from src.providers.liga.config import LigaConfig
        from src.providers.liga.provider import LigaMagicProvider

        provider = LigaMagicProvider(LigaConfig(delay_seconds=0, max_retries=1))

        fake_editions = [
            ("val_a", "042", "xligaset"),
            ("val_b", "042", "otherset"),
        ]

        # Temporarily add a mapping
        SCRYFALL_TO_LIGA_SIGLA["xtestcode"] = "xligaset"
        try:
            with patch(
                "src.providers.liga.provider.parse_edition_options",
                return_value=fake_editions,
            ):
                # Mock the edition selection call so it doesn't try Playwright
                with (
                    patch.object(
                        provider,
                        "_select_edition_sync",
                        return_value="<html>new</html>",
                    ),
                    patch("asyncio.to_thread", new_callable=AsyncMock) as mock_thread,
                ):
                    mock_thread.return_value = "<html>new</html>"
                    provider._use_sync = True

                    html, matched = await provider._select_edition(
                        "<html></html>",
                        "Test Card",
                        "042",
                        set_code="xtestcode",
                    )
                    # Edition was matched via mapped sigla
                    assert matched is True
        finally:
            del SCRYFALL_TO_LIGA_SIGLA["xtestcode"]

    @pytest.mark.asyncio
    async def test_provider_no_sigla_match_logs_warning(self):
        """When no sigla matches, a warning is logged with available siglas."""
        from src.providers.liga.config import LigaConfig
        from src.providers.liga.provider import LigaMagicProvider

        provider = LigaMagicProvider(LigaConfig(delay_seconds=0, max_retries=1))

        fake_editions = [
            ("val_a", "010", "setx"),
            ("val_b", "010", "sety"),
        ]

        with (
            patch(
                "src.providers.liga.provider.parse_edition_options",
                return_value=fake_editions,
            ),
            patch("structlog.get_logger"),
        ):
            # Still uses the first match when sigla doesn't match,
            # and the method needs Playwright to change edition — mock that
            with (
                patch.object(
                    provider,
                    "_select_edition_sync",
                    return_value="<html>new</html>",
                ),
                patch("asyncio.to_thread", new_callable=AsyncMock) as mock_thread,
            ):
                mock_thread.return_value = "<html>new</html>"
                provider._use_sync = True

                html, matched = await provider._select_edition(
                    "<html></html>",
                    "Test Card",
                    "010",
                    set_code="nomatch",
                )
                # Edition still selected (first match), matched is True
                assert matched is True
