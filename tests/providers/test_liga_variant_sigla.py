"""Tests for _variant_sigla_candidates helper (F129-T06)."""

from __future__ import annotations

from src.providers.liga.provider import _variant_sigla_candidates

# ── Unit: _variant_sigla_candidates ──────────────────────────────────


def test_variant_sigla_candidates_adds_promo_prefix():
    """'afr' should produce candidates including 'pafr' and 'ampafr'."""
    candidates = _variant_sigla_candidates("afr")
    assert "pafr" in candidates
    assert "ampafr" in candidates


def test_variant_sigla_candidates_strips_promo_prefix():
    """'pafr' should produce a candidate stripping the 'p' prefix -> 'afr'."""
    candidates = _variant_sigla_candidates("pafr")
    assert "afr" in candidates


def test_variant_sigla_candidates_strips_amp_prefix():
    """'ampafr' should produce a candidate stripping the 'amp' prefix -> 'afr'."""
    candidates = _variant_sigla_candidates("ampafr")
    assert "afr" in candidates


def test_variant_sigla_candidates_does_not_strip_single_char():
    """A single-character sigla starting with 'p' should not strip
    (would produce empty string)."""
    candidates = _variant_sigla_candidates("p")
    # Should NOT contain empty string from stripping 'p'
    assert "" not in candidates
    # But should still add promo prefixes
    assert "pp" in candidates
    assert "ampp" in candidates


def test_variant_sigla_candidates_short_amp_no_strip():
    """'amp' (exactly 3 chars) should not strip 'amp' prefix
    (would produce empty string)."""
    candidates = _variant_sigla_candidates("amp")
    assert "" not in candidates
    # p-strip: 'amp' starts with 'p'? No, starts with 'a'
    # So only promo additions
    assert "pamp" in candidates
    assert "ampamp" in candidates


def test_variant_sigla_candidates_normal_set():
    """A normal set code like 'mh3' should get promo prefixes only."""
    candidates = _variant_sigla_candidates("mh3")
    assert candidates == {"pmh3", "ampmh3"}


def test_variant_sigla_candidates_promo_set_both_directions():
    """'pdmu' should strip to 'dmu' and also add 'ppdmu', 'amppdmu'."""
    candidates = _variant_sigla_candidates("pdmu")
    assert "dmu" in candidates
    assert "ppdmu" in candidates
    assert "amppdmu" in candidates
